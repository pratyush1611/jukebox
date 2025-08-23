# Wi-Fi Jukebox

A web-based music player that runs on Android (via Termux) and lets people on the same Wi-Fi network add YouTube videos to a shared queue. Music plays through the Android phone's speakers.

## Features

- Add songs via YouTube URL or search
- Shared queue visible to all users
- Playback controls with progress bar and seek functionality
- Auto-downloads music to ~/storage/Music/
- SQLite database tracks downloaded songs
- Auto-play similar songs when queue is empty
- Web interface accessible from any device

## Quick Start

### On Android (Termux)

```bash
# Clone and setup
git clone <repo-url>
cd jukebox
bash scripts/setup_termux.sh
bash scripts/setup_boot.sh  # Optional: auto-start on boot
bash scripts/start_termux.sh
```

### Local Testing (Docker)

```bash
# For development/testing on laptop
docker build -t jukebox .
docker run -p 5000:5000 jukebox
```

Open http://localhost:5000 in your browser.

## Requirements

- Python 3.12+
- mpv player
- ffmpeg

## Environment Variables

- `PORT`: Server port (default: 5000)
- `MPV_IPC`: MPV socket path (default: /tmp/mpv.sock)
- `MPV_EXTRA`: Additional MPV arguments