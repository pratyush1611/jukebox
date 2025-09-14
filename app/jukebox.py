import glob
import json
import os
import queue as q
import random
import socket
import sqlite3
import subprocess
import threading
import time
import traceback
import uuid

import requests
import yt_dlp
from flask import Flask, jsonify, request, send_from_directory

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
# Use Termux path if running on Android, otherwise use /tmp
default_sock = (
    "/data/data/com.termux/files/usr/tmp/mpv.sock"
    if os.path.exists("/data/data/com.termux")
    else "/tmp/mpv.sock"
)
IPC_SOCK = os.environ.get("MPV_IPC", default_sock)
MPV_EXTRA = (
    os.environ.get("MPV_EXTRA", "").split() if os.environ.get("MPV_EXTRA") else []
)
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")

app = Flask(__name__)
play_queue = []
current = None
played_history = []  # Track played songs in current session
state_lock = threading.Lock()
cmd_queue = q.Queue()
suggested_songs = set()  # Track already suggested songs


def mpv_start():
    if os.path.exists(IPC_SOCK):
        os.remove(IPC_SOCK)
    args = [
        "mpv",
        "--no-video",
        "--terminal=no",
        "--idle=yes",
        f"--input-ipc-server={IPC_SOCK}",
        "--volume=100",
        "--ytdl=no",
    ] + MPV_EXTRA
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


mpv = mpv_start()


def init_db():
    db_dir = "/app/data" if os.path.exists("/app") else "data"
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(f"{db_dir}/music.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id TEXT PRIMARY KEY,
            title TEXT,
            uploader TEXT,
            duration INTEGER,
            url TEXT,
            filepath TEXT,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def mpv_send(cmd):
    for _ in range(3):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(IPC_SOCK)
            s.sendall((json.dumps(cmd) + "\n").encode())
            s.close()
            return True
        except Exception:
            time.sleep(0.2)
    return False


def resolve_media(q_or_url, allow_age_restricted=False):
    music_dir = os.path.expanduser(
        "~/storage/music"
    )  # Use lowercase symlink to Android Music
    # Create temp directory for search metadata
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    ydl_opts = {
        "format": "bestaudio[acodec*=opus]/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 1,
        "noplaylist": True,
        "default_search": "ytsearch5:",  # Fewer results for faster search
        "writeinfojson": True,
        "writethumbnail": True,
        "embedthumbnail": True,
        "outtmpl": {
            "default": "temp/search_%(title)s.%(ext)s",
            "infojson": "temp/search_%(title)s.%(ext)s",
            "thumbnail": "temp/search_%(title)s.%(ext)s",
        },
    }

    # Add cookies if available (check multiple locations)
    cookie_paths = [
        "cookies.txt",  # Current directory
        os.path.expanduser("~/cookies.txt"),  # Home directory
        "/data/data/com.termux/files/home/cookies.txt",  # Termux home
        os.path.expanduser("~/storage/downloads/cookies.txt"),  # Android downloads
    ]

    for cookie_path in cookie_paths:
        if os.path.exists(cookie_path):
            ydl_opts["cookiefile"] = cookie_path
            print(f"🍪 Using cookies from: {cookie_path}")
            break

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(q_or_url, download=False)
            if "entries" in info:
                # Filter for music: duration 1-10 minutes, music-related titles
                music_entries = []
                for entry in info["entries"]:
                    duration = entry.get("duration", 0)
                    title = entry.get("title", "").lower()
                    uploader = entry.get("uploader", "").lower()

                    # Skip age-restricted content unless allowed
                    if (
                        not allow_age_restricted
                        and entry.get("age_limit")
                        and entry.get("age_limit") > 0
                    ):
                        continue

                    # Skip if too long (>20 min) or too short (<30 sec)
                    if duration and (duration > 1200 or duration < 30):
                        continue

                    # Prefer music-related content
                    music_keywords = [
                        "official",
                        "music",
                        "audio",
                        "song",
                        "album",
                        "single",
                    ]
                    avoid_keywords = [
                        "podcast",
                        "interview",
                        "live stream",
                        "tutorial",
                        "review",
                    ]

                    has_music_keyword = any(
                        keyword in title or keyword in uploader
                        for keyword in music_keywords
                    )
                    has_avoid_keyword = any(
                        keyword in title or keyword in uploader
                        for keyword in avoid_keywords
                    )

                    if has_avoid_keyword:
                        continue

                    music_entries.append((entry, has_music_keyword))

                if music_entries:
                    # Sort by music preference (music keywords first)
                    music_entries.sort(key=lambda x: x[1], reverse=True)
                    info = music_entries[0][0]
                else:
                    # Fallback to first entry if no good matches
                    info = info["entries"][0]

            video_id = info.get("id")
            title = info.get("title") or "Unknown"
            artist = (
                info.get("artist")
                or info.get("uploader")
                or info.get("channel")
                or "Unknown"
            )
            album = info.get("album") or "Unknown Album"
            release_year = info.get("release_year") or "Unknown"
            duration = info.get("duration") or 0

            # Create organized path: Artist/Year Album/
            if (
                artist != "Unknown"
                and release_year != "Unknown"
                and album != "Unknown Album"
            ):
                target_dir = f"{music_dir}/{artist}/{release_year} {album}"
            else:
                target_dir = f"{music_dir}/{artist}"

            # Check if already downloaded
            db_dir = "/app/data" if os.path.exists("/app") else "data"
            try:
                conn = sqlite3.connect(f"{db_dir}/music.db")
                existing = conn.execute(
                    "SELECT filepath FROM downloads WHERE title = ? AND uploader = ?",
                    (title, artist),
                ).fetchone()
                conn.close()

                if existing and os.path.exists(existing[0]):
                    print(f"⏭ Playing {title} by {artist} from local file")
                    return {
                        "title": title,
                        "uploader": artist,
                        "duration": duration,
                        "url": existing[0],
                    }
            except Exception:
                pass

            # Start download in background
            def download_bg():
                try:
                    os.makedirs(target_dir, exist_ok=True)

                    # Download with organized structure
                    download_opts = ydl_opts.copy()
                    # Ensure metadata directory exists
                    metadata_dir = f"{target_dir}/metadata"
                    os.makedirs(metadata_dir, exist_ok=True)

                    # Enable metadata only for actual downloads
                    download_opts["writeinfojson"] = True
                    download_opts["writethumbnail"] = True
                    download_opts["embedthumbnail"] = True

                    # Add cookies for downloads too
                    for cookie_path in cookie_paths:
                        if os.path.exists(cookie_path):
                            download_opts["cookiefile"] = cookie_path
                            break

                    download_opts["outtmpl"] = {
                        "default": f"{target_dir}/{artist} - {title}.%(ext)s",
                        "infojson": f"{metadata_dir}/{artist} - {title}.%(ext)s",
                        "thumbnail": f"{metadata_dir}/{artist} - {title}.%(ext)s",
                    }

                    with yt_dlp.YoutubeDL(download_opts) as download_ydl:
                        download_ydl.download([info["webpage_url"]])

                    # Find the downloaded file
                    audio_files = glob.glob(f"{target_dir}/{artist} - {title}.*")
                    audio_files = [
                        f
                        for f in audio_files
                        if not f.endswith(".json") and not f.endswith(".jpg")
                    ]

                    if audio_files:
                        filepath = audio_files[0]

                        # Save to database
                        db_dir = "/app/data" if os.path.exists("/app") else "data"
                        conn = sqlite3.connect(f"{db_dir}/music.db")
                        conn.execute(
                            "INSERT OR REPLACE INTO downloads (id, title, uploader, duration, url, filepath) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                video_id,
                                title,
                                artist,
                                duration,
                                info["webpage_url"],
                                filepath,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        print(f"✓ Downloaded: {artist} - {title}")

                except Exception as e:
                    print(f"Download failed: {e}")

            threading.Thread(target=download_bg, daemon=True).start()

            return {
                "title": title,
                "uploader": artist,
                "duration": duration,
                "url": info.get("url"),
            }

        except Exception as e:
            print(f"yt-dlp failed: {e}")
            return None


def get_lastfm_recommendations(artist, track=None):
    """Get recommendations from Last.fm API"""
    if not LASTFM_API_KEY:
        return []
    try:
        if track:
            # Get similar tracks
            url = f"http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist={artist}&track={track}&api_key={LASTFM_API_KEY}&format=json&limit=10"
            response = requests.get(url, timeout=5)
            data = response.json()
            if "similartracks" in data and "track" in data["similartracks"]:
                tracks = data["similartracks"]["track"]
                return [f"{t['artist']['name']} {t['name']}" for t in tracks[:5]]

        # Fallback to similar artists
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist={artist}&api_key={LASTFM_API_KEY}&format=json&limit=10"
        response = requests.get(url, timeout=5)
        data = response.json()
        if "similarartists" in data and "artist" in data["similarartists"]:
            artists = data["similarartists"]["artist"]
            return [f"{a['name']} songs" for a in artists[:5]]
    except Exception as e:
        print(f"Last.fm API failed: {e}")
    return []


def fill_autoplay_queue():
    """Fill queue with 3 autoplay suggestions using Last.fm (only if within same session)"""
    try:
        db_dir = "/app/data" if os.path.exists("/app") else "data"
        conn = sqlite3.connect(f"{db_dir}/music.db")

        # Check if we're in the same session (last song < 3 hours ago)
        last_song_time = conn.execute(
            "SELECT downloaded_at FROM downloads ORDER BY downloaded_at DESC LIMIT 1"
        ).fetchone()

        if not last_song_time:
            print("🎵 No listening history - skipping autoplay suggestions")
            conn.close()
            return

        # Check if last song was more than 3 hours ago
        import datetime

        last_time = datetime.datetime.fromisoformat(last_song_time[0])
        now = datetime.datetime.now()
        hours_since = (now - last_time).total_seconds() / 3600

        if hours_since > 3:
            print(
                f"🎵 New session detected ({hours_since:.1f}h since last song) - skipping autoplay"
            )
            suggested_songs.clear()  # Clear suggestions for new session
            conn.close()
            return

        recent_songs = conn.execute(
            "SELECT title, uploader FROM downloads ORDER BY downloaded_at DESC LIMIT 5"
        ).fetchall()

        # Get all songs played in last 3 hours to avoid repeating
        played_recently = conn.execute(
            "SELECT title, uploader FROM downloads WHERE downloaded_at > datetime('now', '-3 hours')"
        ).fetchall()
        played_set = {f"{title}-{artist}" for title, artist in played_recently}

        conn.close()

        print(f"🎵 Same session ({hours_since:.1f}h ago) - adding autoplay suggestions")

        search_options = []

        # Get Last.fm recommendations based on recent songs
        for title, artist in recent_songs[:3]:  # Use last 3 songs
            recommendations = get_lastfm_recommendations(artist, title)
            search_options.extend(recommendations)

        # Add some variety
        search_options.extend(
            [
                f"{recent_songs[0][1]} top songs",  # Latest artist's top songs
                f"trending music {__import__('datetime').datetime.now().year}",
            ]
        )

        # Remove duplicates and shuffle
        search_options = list(set(search_options))
        random.shuffle(search_options)

        added_count = 0
        for search_query in search_options:
            if added_count >= 3:
                break
            try:
                autoplay_meta = resolve_media(search_query)
                if autoplay_meta:
                    song_id = f"{autoplay_meta['title']}-{autoplay_meta['uploader']}"

                    # Skip if already suggested, in current queue, or played recently
                    if (
                        song_id in suggested_songs
                        or song_id in played_set
                        or any(
                            item.get("title") == autoplay_meta["title"]
                            and item.get("uploader") == autoplay_meta["uploader"]
                            for item in play_queue
                        )
                    ):
                        print(f"🔄 Skipping duplicate/recent: {autoplay_meta['title']}")
                        continue

                    autoplay_item = {
                        "id": uuid.uuid4().hex[:8],
                        **autoplay_meta,
                        "added_by": "autoplay",
                    }
                    play_queue.append(autoplay_item)
                    suggested_songs.add(song_id)
                    added_count += 1
                    print(
                        f"🎵 Added via Last.fm ({search_query}): {autoplay_item['title']}"
                    )
            except Exception as e:
                print(f"Autoplay failed for {search_query}: {e}")
    except Exception as e:
        print(f"Fill autoplay queue failed: {e}")


def player_loop():
    global current
    while True:
        with state_lock:
            # Keep queue filled with 3 songs
            if len(play_queue) < 3:
                fill_autoplay_queue()

            if current is None and play_queue:
                next_song = play_queue[0]
                # Skip loading placeholders, wait for them to resolve
                if not next_song.get("loading", False) and next_song.get("url"):
                    current = play_queue.pop(0)
                    mpv_send({"command": ["loadfile", current["url"], "replace"]})
        # Keep queue filled
        with state_lock:
            if len(play_queue) < 3:
                fill_autoplay_queue()

        try:
            cmd = cmd_queue.get(timeout=0.3)
            if cmd == "skip":
                mpv_send({"command": ["stop"]})  # goes idle
                with state_lock:
                    current = None
            elif cmd == "pause":
                mpv_send({"command": ["set_property", "pause", True]})
            elif cmd == "play":
                mpv_send({"command": ["set_property", "pause", False]})
        except q.Empty:
            pass
        # detect idle => track ended
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(IPC_SOCK)
            s.sendall(
                (
                    json.dumps({"command": ["get_property", "idle-active"]}) + "\n"
                ).encode()
            )
            data = s.recv(2048).decode()
            s.close()
            if '"data":true' in data:
                with state_lock:
                    if current:  # Add finished song to history
                        played_history.append(current)
                        # Keep only last 20 songs in history
                        if len(played_history) > 20:
                            played_history.pop(0)
                    current = None
        except Exception:
            pass
        time.sleep(0.2)


threading.Thread(target=player_loop, daemon=True).start()


@app.get("/")
def landing():
    return send_from_directory(".", "landing.html")

@app.get("/app")
def ui():
    return send_from_directory(".", "jukebox.html")

@app.get("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.get("/queue")
def get_queue():
    try:
        with state_lock:
            now_with_progress = current.copy() if current else None
            if now_with_progress:
                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.connect(IPC_SOCK)
                    # Get both position and pause state
                    s.sendall(
                        (
                            json.dumps({"command": ["get_property", "time-pos"]}) + "\n"
                        ).encode()
                    )
                    data = s.recv(2048).decode()
                    if '"data":' in data:
                        pos = json.loads(data).get("data", 0) or 0
                        now_with_progress["position"] = int(pos)

                    # Get pause state
                    s.sendall(
                        (
                            json.dumps({"command": ["get_property", "pause"]}) + "\n"
                        ).encode()
                    )
                    pause_data = s.recv(2048).decode()
                    if '"data":' in pause_data:
                        is_paused = json.loads(pause_data).get("data", False)
                        now_with_progress["paused"] = is_paused
                    s.close()
                except Exception:
                    now_with_progress["position"] = 0
                    now_with_progress["paused"] = False

            response_data = {"now": now_with_progress, "queue": play_queue, "history": played_history}
            response = jsonify(response_data)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    except Exception as e:
        print(f"❌ Queue endpoint error: {e}")
        return jsonify({"now": None, "queue": []}), 500


@app.post("/add")
def add():
    payload = request.get_json(silent=True) or {}
    qstr = payload.get("q") or request.args.get("q", "").strip()
    play_next = payload.get("play_next", False)
    allow_age_restricted = payload.get("allow_age_restricted", False)
    added_by = payload.get("by") or request.remote_addr
    if not qstr:
        return jsonify(error="missing q"), 400

    # Add placeholder immediately for responsive UI
    placeholder_item = {
        "id": uuid.uuid4().hex[:8],
        "title": f"🔍 Searching YouTube: {qstr[:30]}...",
        "uploader": "Loading...",
        "duration": 0,
        "url": None,
        "added_by": added_by,
        "loading": True,
    }

    with state_lock:
        if play_next:
            play_queue.insert(0, placeholder_item)
            insert_pos = 0
        else:
            # Find last user-added song and insert after it
            insert_pos = len(play_queue)  # Default to end
            for i in range(len(play_queue) - 1, -1, -1):  # Search backwards
                if play_queue[i].get("added_by") != "autoplay":
                    insert_pos = i + 1
                    break
                elif i == 0:  # All songs are autoplay
                    insert_pos = 0
            play_queue.insert(insert_pos, placeholder_item)

    # Resolve media in background and update placeholder
    def resolve_and_update():
        global current
        try:
            print(f"🔍 Resolving: {qstr}")
            meta = resolve_media(qstr, allow_age_restricted)
            if meta:
                with state_lock:
                    # Find and update the placeholder
                    for i, item in enumerate(play_queue):
                        if item["id"] == placeholder_item["id"]:
                            play_queue[i] = {
                                "id": placeholder_item["id"],
                                **meta,
                                "added_by": added_by,
                            }
                            # If this was first in queue and nothing is playing, start it
                            if i == 0 and current is None:
                                current = play_queue.pop(0)
                                mpv_send(
                                    {"command": ["loadfile", current["url"], "replace"]}
                                )
                                print(f"▶️ Started playing: {current['title']}")
                            break
                print(f"✅ Resolved: {meta['title']}")
            else:
                # Remove placeholder if resolution failed
                with state_lock:
                    play_queue[:] = [
                        item
                        for item in play_queue
                        if item["id"] != placeholder_item["id"]
                    ]
                print(f"❌ Failed to resolve: {qstr}")
        except Exception as e:
            # Remove placeholder on error
            with state_lock:
                play_queue[:] = [
                    item for item in play_queue if item["id"] != placeholder_item["id"]
                ]
            print(f"❌ Add failed for {qstr}: {e}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            # Also log to file
            with open("error.log", "a") as f:
                f.write(f"Error resolving {qstr}: {e}\n{traceback.format_exc()}\n\n")

    threading.Thread(target=resolve_and_update, daemon=True).start()
    return jsonify(ok=True, item=placeholder_item)


@app.post("/skip")
def skip():
    cmd_queue.put("skip")
    return jsonify(ok=True)


@app.post("/pause")
def pause():
    cmd_queue.put("pause")
    return jsonify(ok=True)


@app.post("/play")
def play_cmd():
    cmd_queue.put("play")
    return jsonify(ok=True)


@app.post("/seek")
def seek():
    payload = request.get_json(silent=True) or {}
    pos = payload.get("pos", 0)
    try:
        mpv_send({"command": ["set_property", "time-pos", float(pos)]})
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(error=str(e)), 500


def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            # In Docker, this might return container IP, so also check host IP
            if ip.startswith("172.") or ip.startswith("10."):
                # Try to get host IP from environment or network interfaces
                import subprocess

                try:
                    result = subprocess.run(
                        ["ip", "route", "get", "1"], capture_output=True, text=True
                    )
                    for line in result.stdout.split("\n"):
                        if "src" in line:
                            host_ip = line.split("src")[1].strip().split()[0]
                            if not host_ip.startswith(
                                "172."
                            ) and not host_ip.startswith("10."):
                                return host_ip
                except Exception:
                    pass
            return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    local_ip = get_local_ip()
    print("\n" + "=" * 50)
    print("🎵 Wi-Fi Jukebox Started!")
    print("=" * 50)
    print(f"📱 Local access:  http://localhost:{PORT}")
    print(f"🌐 Network access: http://{local_ip}:{PORT}")
    print("\n📋 Share this URL with others on your WiFi:")
    print(f"   http://{local_ip}:{PORT}")
    print("=" * 50 + "\n")
    app.run(host=HOST, port=PORT)
