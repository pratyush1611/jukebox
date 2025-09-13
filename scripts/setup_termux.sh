#!/data/data/com.termux/files/usr/bin/zsh
set -e
pkg update -y && pkg upgrade -y
pkg install -y python mpv ffmpeg git uv

# Setup storage access to Android folders
termux-setup-storage

# Export host IP for network access
export HOST_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
echo "Host IP: $HOST_IP"

# install deps using uv (much faster now without ruff)
echo "Installing Python dependencies..."
uv sync --no-dev  # Skip ruff for faster Termux install

termux-wake-lock
echo "Setup complete with uv. Music will be stored in ~/storage/music (Android Music folder)"
