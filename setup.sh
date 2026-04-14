#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────
# Voice Satellite — One-command Termux setup
#
# Turns any Android phone into an always-on voice assistant.
# Connects to any LLM backend (OpenAI, Ollama, or custom).
#
# Prerequisites:
#   1. Termux from F-Droid (NOT Play Store)
#   2. Termux:API from F-Droid (for mic + speaker access)
#   3. Grant mic permission when prompted
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh | bash
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
pkg install -y python portaudio termux-api jq curl

# ── 2. Python packages ──────────────────────────────────────
echo ""
echo "[2/4] Installing Python packages..."
pip install pyaudio requests

# ── 3. Create directory + download satellite ────────────────
echo ""
echo "[3/4] Setting up voice satellite..."
INSTALL_DIR="$HOME/voice-satellite"
mkdir -p "$INSTALL_DIR"

REPO_URL="https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main"

# Always download latest satellite.py
echo "  Downloading satellite.py..."
curl -sL "$REPO_URL/satellite.py" -o "$INSTALL_DIR/satellite.py"
echo "  Done."

# ── 4. Create config ────────────────────────────────────────
echo ""
CONFIG="$INSTALL_DIR/config.env"
if [ -f "$CONFIG" ]; then
    echo "[4/4] Config already exists — skipping"
else
    echo "[4/4] Creating config..."

    # Interactive setup
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

    cat > "$CONFIG" << EOF
# Voice Satellite Configuration
SERVER_URL=$server_url
API_KEY=$api_key
NODE_ID=$node_id
WAKE_WORD=$wake_word

# Tuning (adjust if needed)
SILENCE_THRESHOLD=400
SILENCE_DURATION=2.0
MAX_RECORD_SECONDS=30
SESSION_TIMEOUT=30
EOF

    echo "  -> Saved to $CONFIG"
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
    echo "  Make sure Termux:API app is installed from F-Droid"
    echo "  and microphone permission is granted."
    echo "  Try: Settings > Apps > Termux:API > Permissions > Microphone"
    rm -f "$INSTALL_DIR/test.wav"
fi

# ── Done ────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Setup complete!                  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Start the satellite:"
echo "    termux-wake-lock"
echo "    python $INSTALL_DIR/satellite.py"
echo ""
echo "  Run in background:"
echo "    nohup python -u $INSTALL_DIR/satellite.py > $INSTALL_DIR/voice.log 2>&1 &"
echo ""
echo "  Auto-start on boot (install Termux:Boot from F-Droid):"
echo "    mkdir -p ~/.termux/boot"
echo "    echo 'termux-wake-lock && nohup python -u $INSTALL_DIR/satellite.py > $INSTALL_DIR/voice.log 2>&1 &' > ~/.termux/boot/voice.sh"
echo "    chmod +x ~/.termux/boot/voice.sh"
echo ""
