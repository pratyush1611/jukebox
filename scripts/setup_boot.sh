#!/data/data/com.termux/files/usr/bin/bash
# Setup auto-start on boot for Termux
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start.sh <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/jukebox
git pull --rebase || true
bash scripts/start_termux.sh
SH
chmod +x ~/.termux/boot/start.sh
echo "Boot script installed. Jukebox will auto-start on Termux boot."