#!/data/data/com.termux/files/usr/bin/bash
# One-shot installer for Termux
set -e

pkg install -y python ffmpeg
pip install -U yt-dlp
mkdir -p "$HOME/bin"

cp vdl_ui.py "$HOME/bin/vdl_ui.py"
cp vdl "$HOME/bin/vdl"
chmod +x "$HOME/bin/vdl_ui.py" "$HOME/bin/vdl"

grep -q 'export PATH="$HOME/bin:$PATH"' "$HOME/.bashrc" || \
  echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
grep -q "alias down=" "$HOME/.bashrc" || \
  echo 'alias down="python3 ~/bin/vdl_ui.py"' >> "$HOME/.bashrc"

echo
echo "TM DOWNLODER installed. Run:  source ~/.bashrc && down"
echo "Tip: run 'termux-setup-storage' once so downloads can go to shared storage."
