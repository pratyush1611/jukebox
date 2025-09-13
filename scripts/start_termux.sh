#!/data/data/com.termux/files/usr/bin/bash
set -e
# Already in jukebox directory
# ensure mpv uses Android’s default audio route (AUX/Bluetooth chosen in system)
export MPV_IPC=/data/data/com.termux/files/usr/tmp/mpv.sock
export MPV_EXTRA="--ao=pulse,opensles"  # Try PulseAudio first, then OpenSL ES
pkill -f 'python .*jukebox.py' >/dev/null 2>&1 || true
source .venv/bin/activate
nohup python app/jukebox.py > jukebox.log 2>&1 &
PHONE_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
echo "Started. Open http://$PHONE_IP:5000/"
echo "Network URL: http://$PHONE_IP:5000"
