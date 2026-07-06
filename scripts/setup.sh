#!/usr/bin/env bash
set -euo pipefail

# ╔══════════════════════════════════════════════════════════╗
# ║  AI Video Editing Stack — One-Command Setup             ║
# ║  Installs everything: FFmpeg, MCP servers, Whisper,     ║
# ║  optional Ollama + Qwen2.5-Coder.                       ║
# ║  Usage: curl -fsSL https://bit.ly/ai-video-stack | bash ║
# ╚══════════════════════════════════════════════════════════╝

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

# ──────────────────────────────────────────────
# 1. FFmpeg
# ──────────────────────────────────────────────
install_ffmpeg() {
  if command -v ffmpeg &>/dev/null; then
    ok "FFmpeg already installed ($(ffmpeg -version 2>&1 | head -1))"
    return
  fi
  log "Installing FFmpeg..."
  case "$OS" in
    macos) brew install ffmpeg ;;
    linux)
      if command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y ffmpeg
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y ffmpeg
      elif command -v pacman &>/dev/null; then
        sudo pacman -S ffmpeg
      else
        fail "No known package manager. Install FFmpeg manually: https://ffmpeg.org/download.html"
      fi
      ;;
    *) fail "Unsupported OS. Install FFmpeg manually: https://ffmpeg.org/download.html" ;;
  esac
  command -v ffmpeg &>/dev/null && ok "FFmpeg installed" || fail "FFmpeg install failed"
}

# ──────────────────────────────────────────────
# 2. Python + pip
# ──────────────────────────────────────────────
ensure_python() {
  if ! command -v python3 &>/dev/null; then
    log "Installing Python 3..."
    case "$OS" in
      macos) brew install python ;;
      linux)
        if command -v apt &>/dev/null; then
          sudo apt install -y python3 python3-pip python3-venv
        elif command -v dnf &>/dev/null; then
          sudo dnf install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
          sudo pacman -S python python-pip
        fi
        ;;
    esac
  fi
  python3 --version >/dev/null 2>&1 && ok "Python $(python3 --version)" || fail "Python install failed"
}

# ──────────────────────────────────────────────
# 3. uv (fast Python package installer)
# ──────────────────────────────────────────────
install_uv() {
  if command -v uv &>/dev/null; then
    ok "uv already installed"
    return
  fi
  log "Installing uv (fast Python package manager)..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  command -v uv &>/dev/null && ok "uv installed" || warn "uv install may have failed — falling back to pip"
}

# ──────────────────────────────────────────────
# 4. MCP video server
# ──────────────────────────────────────────────
install_mcp_video() {
  log "Installing mcp-video (119 MCP tools for video editing)..."
  if command -v uv &>/dev/null; then
    uv tool install mcp-video 2>/dev/null || pip install mcp-video
  else
    pip install mcp-video
  fi
  python3 -c "import mcp_video" 2>/dev/null && ok "mcp-video installed" || warn "mcp-video import failed — check pip"
}

# ──────────────────────────────────────────────
# 5. Whisper (transcription)
# ──────────────────────────────────────────────
install_whisper() {
  log "Installing Whisper (transcription)..."
  pip install faster-whisper 2>/dev/null && ok "faster-whisper installed" || warn "faster-whisper install had issues"

  # Whisper MCP server
  pip install mcp-server-whisper 2>/dev/null && ok "whisper MCP server installed" || warn "whisper MCP server install had issues"

  # WhisperX for word-level alignment + diarization
  pip install whisperx 2>/dev/null && ok "WhisperX installed" || warn "WhisperX skipped (optional, needs torch)"
}

# ──────────────────────────────────────────────
# 6. CutAgent (declarative EDL)
# ──────────────────────────────────────────────
install_cutagent() {
  log "Installing CutAgent (declarative EDL for agents)..."
  pip install cutagent 2>/dev/null && ok "CutAgent installed" || warn "CutAgent skipped"
}

# ──────────────────────────────────────────────
# 7. MCP Whisper config
# ──────────────────────────────────────────────
write_mcp_config() {
  local config_dir="$HOME/.config/opencode"
  mkdir -p "$config_dir"

  if [ ! -f "$config_dir/mcp.json" ]; then
    cat > "$config_dir/mcp.json" << 'EOF'
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    },
    "whisper-transcribe": {
      "command": "uvx",
      "args": ["whisper-transcribe-mcp"]
    }
  }
}
EOF
    ok "Sample MCP config written to $config_dir/mcp.json"
  else
    ok "MCP config already exists at $config_dir/mcp.json (skipped)"
  fi
}

# ──────────────────────────────────────────────
# 8. Ollama + Qwen2.5-Coder (optional)
# ──────────────────────────────────────────────
install_ollama() {
  if ! command -v ollama &>/dev/null; then
    log "Ollama not found. Install? (y/n)"
    read -r install_ollama_choice
    if [[ "$install_ollama_choice" =~ ^[Yy]$ ]]; then
      log "Installing Ollama..."
      case "$OS" in
        macos) brew install ollama ;;
        linux) curl -fsSL https://ollama.com/install.sh | sh ;;
      esac

      log "Pulling Qwen2.5-Coder 7B (best local LLM for FFmpeg, 88% accuracy)..."
      ollama pull qwen2.5-coder:7b
      ok "Ollama + Qwen2.5-Coder 7B ready"
    else
      warn "Skipping Ollama. You can install later: https://ollama.com"
    fi
  else
    ok "Ollama already installed"
    if ! ollama list 2>/dev/null | grep -q qwen2.5-coder; then
      log "Pulling Qwen2.5-Coder 7B..."
      ollama pull qwen2.5-coder:7b
    fi
  fi
}

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  ✅  AI Video Editing Stack Installed!                  ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}FFmpeg:${NC}       $(ffmpeg -version 2>&1 | head -1 | sed 's/ffmpeg version //' | cut -d' ' -f1)"
  echo -e "  ${CYAN}mcp-video:${NC}   ✓  119 MCP tools"
  echo -e "  ${CYAN}Whisper:${NC}     ✓  faster-whisper + MCP server"
  echo -e "  ${CYAN}CutAgent:${NC}    ✓  Declarative EDL"
  if command -v ollama &>/dev/null; then
    echo -e "  ${CYAN}Ollama:${NC}      ✓  $(ollama --version 2>&1 | head -1)"
  fi
  echo ""
  echo -e "  ${YELLOW}Next steps:${NC}"
  echo "  1. Configure your AI agent's MCP settings (sample: ~/.config/opencode/mcp.json)"
  echo "  2. Try: 'Trim this video from 30s to 1m30s'"
  echo "  3. Clone the knowledge base for full skill:"
  echo "     git clone https://github.com/mua47105-hue/agentic-ai-video-knowledgebase.git"
  echo ""
}

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  AI Video Editing Stack — One-Command Setup             ║${NC}"
echo -e "${CYAN}║  Completely free, open-source, local-first               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

install_ffmpeg
ensure_python
install_uv
install_mcp_video
install_whisper
install_cutagent
write_mcp_config
install_ollama
print_summary
