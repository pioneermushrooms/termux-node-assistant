#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────
# Voice Satellite — Termux setup
#
# Turns any Android phone into an always-on voice assistant.
# Connects to any LLM backend (OpenAI, Ollama, llama.cpp).
#
# Prerequisites:
#   1. Termux (from F-Droid or Play Store)
#   2. Termux:API app (from F-Droid or Play Store)
#   3. Microphone permission granted to Termux and Termux:API
#
# Usage (download and run):
#   curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh -o setup.sh
#   bash setup.sh
# ─────────────────────────────────────────────────────────────

set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Voice Satellite Setup            ║"
echo "  ║     Turn this phone into a voice     ║"
echo "  ║     assistant in 60 seconds          ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 1. System packages ──────────────────────────────────────
echo "[1/4] Installing system packages..."
pkg update -y
pkg install -y python portaudio termux-api curl

# ── 2. Python packages ──────────────────────────────────────
echo ""
echo "[2/4] Installing Python packages..."
pip install pyaudio requests

# ── 3. Create directory + download satellite ────────────────
echo ""
echo "[3/4] Downloading voice satellite..."
INSTALL_DIR="$HOME/voice-satellite"
mkdir -p "$INSTALL_DIR"

REPO_URL="https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main"
curl -sL "$REPO_URL/satellite.py" -o "$INSTALL_DIR/satellite.py"

# Verify download worked (not a 404 page)
if head -1 "$INSTALL_DIR/satellite.py" | grep -q "python"; then
    echo "  Downloaded satellite.py"
else
    echo "  ERROR: Download failed. Get satellite.py manually from:"
    echo "  https://github.com/pioneermushrooms/termux-node-assistant"
    echo "  and place it in $INSTALL_DIR/"
fi

# ── 4. Create config ────────────────────────────────────────
echo ""
CONFIG="$INSTALL_DIR/config.env"
if [ -f "$CONFIG" ]; then
    echo "[4/4] Config already exists — skipping"
    echo "  Edit with: nano $CONFIG"
else
    echo "[4/4] Creating config..."

    # Detect if running interactively or piped (curl | bash)
    if [ -t 0 ]; then
        # Interactive — ask questions
        echo ""
        echo "  Quick setup — press Enter for defaults"
        echo ""

        read -p "  Server URL [http://localhost:5001]: " server_url
        server_url="${server_url:-http://localhost:5001}"

        read -p "  API key (leave blank if none): " api_key

        read -p "  Wake word [jarvis]: " wake_word
        wake_word="${wake_word:-jarvis}"

        read -p "  Device name [android-satellite]: " node_id
        node_id="${node_id:-android-satellite}"
    else
        # Piped — use defaults
        echo "  (non-interactive mode — using defaults)"
        echo "  Edit config after setup: nano $CONFIG"
        server_url="http://localhost:5001"
        api_key=""
        wake_word="jarvis"
        node_id="android-satellite"
    fi

    cat > "$CONFIG" << EOF
# Voice Satellite Configuration
# Edit this file: nano $CONFIG

# Your server's address (where server.py is running)
SERVER_URL=$server_url

# Shared auth token (must match server's API_KEY, or leave blank)
API_KEY=$api_key

# Device name
NODE_ID=$node_id

# What you say to activate the assistant
WAKE_WORD=$wake_word

# Tuning (adjust if needed)
SILENCE_THRESHOLD=400
SILENCE_DURATION=2.0
MAX_RECORD_SECONDS=30
SESSION_TIMEOUT=30
EOF

    echo "  -> Config saved to $CONFIG"
    echo ""
    echo "  IMPORTANT: Edit the config with your server's IP address:"
    echo "    nano $CONFIG"
fi

# ── 5. Test mic access ──────────────────────────────────────
echo ""
echo "Testing microphone access..."
termux-microphone-record -f "$INSTALL_DIR/test.wav" -l 2 2>/dev/null &
MIC_PID=$!
sleep 3
termux-microphone-record -q 2>/dev/null
wait $MIC_PID 2>/dev/null

if [ -f "$INSTALL_DIR/test.wav" ] && [ -s "$INSTALL_DIR/test.wav" ]; then
    echo "  Mic works!"
    rm -f "$INSTALL_DIR/test.wav"
else
    echo ""
    echo "  WARNING: Mic test failed!"
    echo "  Checklist:"
    echo "    1. Is the Termux:API app installed? (separate app, not just the package)"
    echo "    2. Settings > Apps > Termux > Permissions > Microphone > Allow"
    echo "    3. Settings > Apps > Termux:API > Permissions > Microphone > Allow"
    echo "    4. If permissions don't appear: force-stop both apps, reopen Termux"
    rm -f "$INSTALL_DIR/test.wav"
fi

# ── Done ────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Setup complete!                  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Edit your config (set your server IP):"
echo "       nano $CONFIG"
echo ""
echo "  2. Start the satellite:"
echo "       termux-wake-lock"
echo "       python $INSTALL_DIR/satellite.py"
echo ""
echo "  3. Run in background (optional):"
echo "       nohup python -u $INSTALL_DIR/satellite.py > $INSTALL_DIR/voice.log 2>&1 &"
echo ""
echo "  Server setup instructions:"
echo "    https://github.com/pioneermushrooms/termux-node-assistant"
echo ""
