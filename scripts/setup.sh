#!/usr/bin/env bash
set -euo pipefail

# AI Video Editing Stack — One-Command Setup (Phase 1 rewrite)
# Installs: FFmpeg, Python venv, all declared Python deps, mcp-video, faster-whisper.
# Optional: Ollama + qwen2.5-coder:7b.
# Fail-fast: any install error exits non-zero with a clear message.

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[AI-VIDEO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

detect_os() {
  case "$(uname -s)" in
    Darwin*)  echo "macos" ;;
    Linux*)   echo "linux" ;;
    MINGW*|MSYS*) echo "windows" ;;
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
    linux)
      if command -v apt &>/dev/null; then sudo apt update && sudo apt install -y ffmpeg
      elif command -v dnf &>/dev/null; then sudo dnf install -y ffmpeg
      elif command -v pacman &>/dev/null; then sudo pacman -S --noconfirm ffmpeg
      else fail "No known package manager. Install FFmpeg manually: https://ffmpeg.org/download.html"
      fi ;;
    *) fail "Unsupported OS. Install FFmpeg manually." ;;
  esac
fi
ok "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"

# 2. Python 3.10+
if ! command -v python3 &>/dev/null; then
  log "Installing Python 3..."
  case "$OS" in
    macos) brew install python ;;
    linux)
      if command -v apt &>/dev/null; then sudo apt install -y python3 python3-pip python3-venv
      elif command -v dnf &>/dev/null; then sudo dnf install -y python3 python3-pip
      elif command -v pacman &>/dev/null; then sudo pacman -S --noconfirm python python-pip
      fi ;;
  esac
fi
PYVER=$(python3 -c 'import sys; print(tuple(sys.version_info[:2]))')
if [[ "$PYVER" == "(3,"* ]] && [[ "${PYVER:3:1}" -lt 10 ]]; then
  fail "Python 3.10+ required, found $(python3 --version)"
fi
ok "Python: $(python3 --version)"

# 3. venv
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ ! -d ".venv" ]]; then
    log "Creating .venv..."
    python3 -m venv .venv || fail "venv creation failed"
  fi
  log "Activating .venv..."
  source .venv/bin/activate
fi
ok "Virtualenv: ${VIRTUAL_ENV}"

# 4. Upgrade pip + install requirements
log "Upgrading pip..."
python3 -m pip install --upgrade pip wheel setuptools || fail "pip upgrade failed"

log "Installing Python dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt || fail "requirements.txt install failed"
ok "Python dependencies installed"

# 5. mcp-video + faster-whisper (also in requirements.txt, but double-check)
log "Installing mcp-video + faster-whisper..."
python3 -m pip install --upgrade mcp-video faster-whisper || fail "mcp-video/whisper install failed"
ok "mcp-video + faster-whisper installed"

# 6. Optional Ollama
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
    log "Pulling qwen2.5-coder:7b (~4.7GB)..."
    ollama pull qwen2.5-coder:7b || warn "ollama pull failed — you can do this manually later"
    ok "Ollama + qwen2.5-coder:7b ready"
  else
    warn "Skipping Ollama. Install later: https://ollama.com"
  fi
else
  ok "Ollama already installed"
fi

# 7. Doctor check (Phase 2 delivers doctor.py; for now, just import-check)
log "Verifying imports..."
python3 -c "
import importlib
mods = ['yaml', 'numpy', 'matplotlib', 'PIL', 'requests', 'bs4', 'librosa', 'scipy', 'cv2', 'opentimelineio']
failed = []
for m in mods:
    try:
        importlib.import_module(m)
    except ImportError as e:
        failed.append((m, str(e)))
if failed:
    print('Missing imports:')
    for m, e in failed:
        print(f'  {m}: {e}')
    exit(1)
print('All core imports OK.')
" || fail "import verification failed"

# 8. Print MCP config snippets for each agent
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  AI Video Editing Stack Installed                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}FFmpeg:${NC}      $(ffmpeg -version 2>&1 | head -1 | sed 's/ffmpeg version //')"
echo -e "  ${CYAN}Python:${NC}      $(python3 --version)"
echo -e "  ${CYAN}venv:${NC}        ${VIRTUAL_ENV:-none}"
echo -e "  ${CYAN}mcp-video:${NC}   $(python3 -c 'import mcp_video; print(getattr(mcp_video, \"__version__\", \"unknown\"))' 2>/dev/null || echo 'import failed')"
echo -e "  ${CYAN}faster-whisper:${NC} $(python3 -c 'import faster_whisper; print(\"OK\")' 2>/dev/null || echo 'import failed')"
if command -v ollama &>/dev/null; then
  echo -e "  ${CYAN}Ollama:${NC}      $(ollama --version 2>&1 | head -1)"
fi
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo "  1. Configure your AI agent's MCP settings. Pick ONE of:"
echo ""
echo "     Claude Code (~/.claude/mcp.json):"
echo '       {"mcpServers":{"mcp-video":{"command":"uvx","args":["mcp-video"]}}}'
echo ""
echo "     Cursor (Settings MCP):"
echo '       Add server "mcp-video" with command "uvx mcp-video"'
echo ""
echo "     OpenCode (~/.config/opencode/mcp.json):"
echo '       {"mcpServers":{"mcp-video":{"command":"uvx","args":["mcp-video"]},"whisper":{"command":"uvx","args":["whisper-transcribe-mcp"]}}}'
echo ""
echo "  2. List recipes:"
echo "     python3 -m kb.tools.recipe_runner --list"
echo ""
echo "  3. Run a recipe:"
echo "     python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4"
echo ""
echo "  4. Verify environment (Phase 2):"
echo "     python3 scripts/doctor.py"
echo ""
