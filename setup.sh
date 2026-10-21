#!/usr/bin/env bash
# One-time (and safe-to-repeat) setup for the brainrod pipeline on macOS.
# Usage: ./setup.sh   (run from anywhere; it works relative to this file)
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"
echo "==> Project folder: $ROOT"

# 1. Homebrew (not installed automatically)
if ! command -v brew >/dev/null 2>&1; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$b" ] && eval "$("$b" shellenv)" && break
  done
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "!! Homebrew is not installed."
  echo "   Install it from https://brew.sh (paste the one-line command into Terminal),"
  echo "   follow the 'Next steps' it prints, then run ./setup.sh again."
  exit 1
fi
echo "==> Homebrew: $(brew --prefix)"

# 2. ffmpeg + Python 3.12
for pkg in ffmpeg python@3.12; do
  if brew list --versions "$pkg" >/dev/null 2>&1; then
    echo "==> $pkg already installed"
  else
    echo "==> Installing $pkg"
    brew install "$pkg"
  fi
done
PY="$(brew --prefix)/bin/python3.12"
[ -x "$PY" ] || PY="$(brew --prefix python@3.12)/bin/python3.12"

# 3. Virtual environment
if [ ! -x .venv/bin/python ]; then
  echo "==> Creating .venv"
  "$PY" -m venv .venv
else
  echo "==> .venv already exists"
fi
.venv/bin/python -m pip install --quiet --upgrade pip
echo "==> Installing Python packages"
.venv/bin/pip install --quiet -r requirements.txt

# 4. Downloads (only if missing)
fetch() {  # fetch <url> <dest>
  if [ -s "$2" ]; then
    echo "==> $2 already present"
  else
    echo "==> Downloading $2"
    mkdir -p "$(dirname "$2")"
    curl -fL --retry 3 -o "$2.part" "$1"
    mv "$2.part" "$2"
  fi
}
KOKORO=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
fetch "$KOKORO/kokoro-v1.0.onnx" assets/models/kokoro-v1.0.onnx
fetch "$KOKORO/voices-v1.0.bin"  assets/models/voices-v1.0.bin

GF=https://github.com/google/fonts/raw/main
fetch "$GF/apache/luckiestguy/LuckiestGuy-Regular.ttf" assets/fonts/LuckiestGuy-Regular.ttf
fetch "$GF/ofl/anton/Anton-Regular.ttf"                assets/fonts/Anton-Regular.ttf
fetch "$GF/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf"     assets/fonts/Fredoka.ttf

# 5. Quick check
echo "==> Checking imports"
.venv/bin/python -c "import kokoro_onnx, soundfile, numpy, PIL; print('   Python packages OK')"
ffmpeg -version | head -1 | sed 's/^/   /'
echo
echo "Setup complete. Test render:"
echo "  .venv/bin/python pipeline/render.py queue/facts/f001.json"
