#!/data/data/com.termux/files/usr/bin/zsh
set -e
pkg update -y && pkg upgrade -y
pkg install -y python mpv ffmpeg git uv

# install deps using uv
uv sync

termux-wake-lock
echo "Setup complete with uv."
