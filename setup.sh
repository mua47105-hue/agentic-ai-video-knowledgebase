#!/usr/bin/env bash
set -euo pipefail

# AI Video Editing Stack — One-Command Setup
# Installs: FFmpeg, Python deps, mcp-video, faster-whisper, yt-dlp, optional Ollama.
# Run: bash setup.sh

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[AI-VIDEO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

detect_os() {
  case "$(uname -s)" in
    Darwin*)  echo "macos" ;;
    Linux*)   echo "linux" ;;
    *)        echo "unknown" ;;
  esac
}

OS=$(detect_os)
log "Detected OS: ${OS}"

# 1. FFmpeg
if ! command -v ffmpeg &>/dev/null; then
  log "Installing FFmpeg..."
  case "$OS" in
    macos) brew install ffmpeg ;;
    linux) sudo apt update && sudo apt install -y ffmpeg || sudo dnf install -y ffmpeg || sudo pacman -S --noconfirm ffmpeg ;;
    *) fail "Install FFmpeg manually: https://ffmpeg.org/download.html" ;;
  esac
fi
ok "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"

# 2. Python 3.10+
if ! command -v python3 &>/dev/null; then
  log "Installing Python 3..."
  case "$OS" in
    macos) brew install python ;;
    linux) sudo apt install -y python3 python3-pip python3-venv || true ;;
  esac
fi
ok "Python: $(python3 --version)"

# 3. Install package in editable mode (P0 #10 fix: makes kb importable from anywhere)
log "Installing package in editable mode (pip install -e .)..."
python3 -m pip install --upgrade pip wheel setuptools -q || true
python3 -m pip install -e . -q || warn "editable install failed — try: pip install -e '.[all]'"
ok "Package installed (kb.tools.* now importable from anywhere)"

# 4. Core deps
log "Installing core dependencies..."
python3 -m pip install -r requirements.txt -q || warn "some requirements failed"
ok "Core dependencies installed"

# 5. mcp-video + faster-whisper
log "Installing mcp-video + faster-whisper..."
python3 -m pip install --upgrade mcp-video faster-whisper -q || warn "mcp-video/whisper install had issues"
ok "mcp-video + faster-whisper installed"

# 6. yt-dlp (for online music sources — YouTube trending + Internet Archive)
log "Installing yt-dlp (online music sources)..."
python3 -m pip install --upgrade yt-dlp -q || warn "yt-dlp install had issues"
ok "yt-dlp installed"

# rembg (background removal — gated, opt-in)
python3 -m pip install rembg -q || warn "rembg install failed"
# auto-editor (auto silence/motion cut — MIT)
python3 -m pip install auto-editor -q || warn "auto-editor install failed"
# MoviePy (complex composition — MIT)
python3 -m pip install moviepy -q || warn "MoviePy install failed"

# 7. Optional Ollama
if ! command -v ollama &>/dev/null; then
  echo ""
  read -rp "${CYAN}[AI-VIDEO]${NC} Install Ollama + qwen2.5-coder:7b for local LLM? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Installing Ollama..."
    case "$OS" in
      macos) brew install ollama ;;
      linux) curl -fsSL https://ollama.com/install.sh | sh ;;
    esac
    log "Pulling qwen2.5-coder:7b..."
    ollama pull qwen2.5-coder:7b || warn "ollama pull failed"
    ok "Ollama + qwen2.5-coder:7b ready"
  else
    warn "Skipping Ollama. Install later: https://ollama.com"
  fi
else
  ok "Ollama already installed"
fi

# 8. Verify
log "Verifying imports..."
python3 -c "
import importlib
mods = ['yaml', 'numpy', 'cv2', 'librosa']
if mods:
    for m in mods:
        try: importlib.import_module(m)
        except ImportError: print(f'  missing: {m}')
    print('  core imports OK')
" || warn "some imports failed"

echo ""
echo -e "${GREEN}=== AI Video Editing Stack Installed ===${NC}"
echo "  Next steps:"
echo "  1. List recipes: python3 -m kb.tools.recipe_runner --list"
echo "  2. Analyze: python3 -m kb.tools.recipe_runner --analyze-only input.mp4 --output /tmp/"
echo "  3. Run: python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4"
