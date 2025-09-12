#!/data/data/com.termux/files/usr/bin/bash
set -e
# Already in jukebox directory
# ensure mpv uses Android’s default audio route (AUX/Bluetooth chosen in system)
export MPV_IPC=/data/data/com.termux/files/usr/tmp/mpv.sock
export MPV_EXTRA=""
pkill -f 'uv run.*jukebox.py' >/dev/null 2>&1 || true
nohup uv run app/jukebox.py > jukebox.log 2>&1 &
echo "Started. Open http://<phone-ip>:5000/"
