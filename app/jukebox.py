import json
import os
import queue as q
import socket
import sqlite3
import subprocess
import threading
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory

VERSION = "0.0.1"

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
IPC_SOCK = os.environ.get("MPV_IPC", "/tmp/mpv.sock")
MPV_EXTRA = (
    os.environ.get("MPV_EXTRA", "").split() if os.environ.get("MPV_EXTRA") else []
)

app = Flask(__name__)
play_queue = []
current = None
state_lock = threading.Lock()
cmd_queue = q.Queue()


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


def resolve_media(q_or_url):
    import threading

    import yt_dlp

    music_dir = os.path.expanduser("~/storage/Music")
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "default_search": "ytsearch",
        "outtmpl": f"{music_dir}/%(title)s.%(ext)s",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(q_or_url, download=False)
        if "entries" in info:
            info = info["entries"][0]

        video_id = info.get("id")
        title = info.get("title") or "Unknown"
        uploader = info.get("uploader") or info.get("channel") or ""
        duration = info.get("duration") or 0

        # Check if already downloaded first
        db_dir = "/app/data" if os.path.exists("/app") else "data"
        try:
            conn = sqlite3.connect(f"{db_dir}/music.db")
            existing = conn.execute(
                "SELECT filepath FROM downloads WHERE title = ?", (title,)
            ).fetchone()
            conn.close()

            if existing and os.path.exists(existing[0]):
                print(f"⏭ Playing {title} from local file")
                return {
                    "title": title,
                    "uploader": uploader,
                    "duration": duration,
                    "url": existing[0],  # Use local file path
                }
        except Exception:
            pass

        # Start download in background
        def download_bg():
            try:
                # Check if already downloaded
                db_dir = "/app/data" if os.path.exists("/app") else "data"
                conn = sqlite3.connect(f"{db_dir}/music.db")
                existing = conn.execute(
                    "SELECT filepath FROM downloads WHERE title = ?", (title,)
                ).fetchone()

                if existing and os.path.exists(existing[0]):
                    conn.close()
                    print(f"⏭ {title} already downloaded")
                    return

                os.makedirs(music_dir, exist_ok=True)
                ydl.download([info["webpage_url"]])
                # Save to database
                filepath = f"{music_dir}/{title}.{info.get('ext', 'm4a')}"
                conn.execute(
                    "INSERT OR REPLACE INTO downloads (id, title, uploader, duration, url, filepath) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        video_id,
                        title,
                        uploader,
                        duration,
                        info["webpage_url"],
                        filepath,
                    ),
                )
                conn.commit()
                conn.close()
                print(f"✓ Download of {title} complete")
            except Exception:
                pass

        threading.Thread(target=download_bg, daemon=True).start()

        return {
            "title": title,
            "uploader": uploader,
            "duration": duration,
            "url": info.get("url"),
        }


def fill_autoplay_queue():
    """Fill queue with 3 autoplay suggestions"""
    try:
        db_dir = "/app/data" if os.path.exists("/app") else "data"
        conn = sqlite3.connect(f"{db_dir}/music.db")
        last_song = conn.execute(
            "SELECT title, uploader FROM downloads ORDER BY downloaded_at DESC LIMIT 1"
        ).fetchone()
        random_songs = conn.execute(
            "SELECT title, uploader FROM downloads ORDER BY RANDOM() LIMIT 3"
        ).fetchall()
        conn.close()
        
        if last_song:
            import random
            search_options = [
                f"{last_song[1]} songs",
                f"{random_songs[0][1] if random_songs else last_song[1]} music",
                f"songs like {last_song[0]}",
                "trending music 2024",
            ]
            
            for i in range(3):
                try:
                    search_query = random.choice(search_options)
                    autoplay_meta = resolve_media(search_query)
                    autoplay_item = {
                        "id": uuid.uuid4().hex[:8],
                        **autoplay_meta,
                        "added_by": "autoplay",
                    }
                    play_queue.append(autoplay_item)
                    print(f"🎵 Added to queue ({search_query}): {autoplay_item['title']}")
                except Exception:
                    pass
    except Exception:
        pass


def player_loop():
    global current
    while True:
        with state_lock:
            # Keep queue filled with 3 songs
            if len(play_queue) < 3:
                fill_autoplay_queue()
            
            if current is None and play_queue:
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
                    current = None
        except Exception:
            pass
        time.sleep(0.2)


threading.Thread(target=player_loop, daemon=True).start()


@app.get("/")
def ui():
    return send_from_directory(".", "jukebox.html")


@app.get("/queue")
def get_queue():
    with state_lock:
        now_with_progress = current.copy() if current else None
        if now_with_progress:
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(IPC_SOCK)
                s.sendall(
                    (
                        json.dumps({"command": ["get_property", "time-pos"]}) + "\n"
                    ).encode()
                )
                data = s.recv(2048).decode()
                s.close()
                if '"data":' in data:
                    pos = json.loads(data).get("data", 0) or 0
                    now_with_progress["position"] = int(pos)
            except Exception:
                now_with_progress["position"] = 0
        return jsonify({"now": now_with_progress, "queue": play_queue})


@app.post("/add")
def add():
    payload = request.get_json(silent=True) or {}
    qstr = payload.get("q") or request.args.get("q", "").strip()
    added_by = payload.get("by") or request.remote_addr
    if not qstr:
        return jsonify(error="missing q"), 400
    try:
        meta = resolve_media(qstr)
        item = {"id": uuid.uuid4().hex[:8], **meta, "added_by": added_by}
        with state_lock:
            play_queue.append(item)
        return jsonify(ok=True, item=item)
    except Exception as e:
        return jsonify(error=str(e)), 500


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


if __name__ == "__main__":
    print(f"Starting Wi-Fi Jukebox v{VERSION}")
    app.run(host=HOST, port=PORT)
