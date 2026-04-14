# termux-node-assistant

Turn any old Android phone into an always-on voice assistant. No app development, no root, no Play Store — just Termux.

```
"Hey Jarvis, what's the weather?"
  → Phone mic picks up speech
  → Audio sent to your server
  → Whisper transcribes, LLM responds
  → Phone speaker reads the answer
  → Keeps listening for follow-up questions
```

Works with **OpenAI, Ollama, or any OpenAI-compatible API** — including fully local setups.

## Why

You have an old phone in a drawer. It has a mic, a speaker, WiFi, and 4-8GB of RAM. This project turns it into a smart speaker that connects to any LLM — cloud or local.

No existing project does this. The voice assistant ecosystem is fragmented between Home Assistant satellites (locked to HA), desktop-only tools, and abandoned Mycroft forks. This is the missing piece: a simple, generic voice client for Termux that talks to any backend.

## Quick Start

### Step 1: Set up the server (your computer — 2 minutes)

The server runs on any computer on your WiFi. It handles speech-to-text and LLM chat.

**Option A: OpenAI (easiest — requires API key, ~$0.01/interaction)**

1. Get an OpenAI API key: go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys), sign in, click "Create new secret key", copy it
2. Download `server.py` from this repo
3. Run:
```bash
pip install flask openai
OPENAI_API_KEY=sk-your-key-here python server.py
```

**Option B: Ollama (free, fully local, no API key for LLM)**

1. Install Ollama from [ollama.com](https://ollama.com) (Mac, Linux, or Windows)
2. Pull a model: `ollama pull llama3.2` (takes a few minutes, ~2GB download)
3. Download `server.py` from this repo
4. Run:
```bash
pip install flask openai
LLM_PROVIDER=ollama python server.py
```

> Note: Ollama handles the LLM for free, but speech-to-text still uses OpenAI's Whisper API by default. Set `OPENAI_API_KEY` for that (~$0.006 per 30 seconds of audio). Local Whisper support is on the roadmap.

**Option C: Any OpenAI-compatible API (LM Studio, vLLM, text-generation-webui)**
```bash
pip install flask openai
LLM_BASE_URL=http://my-server:8080/v1 LLM_MODEL=my-model python server.py
```

**Once the server starts, you'll see:**
```
  Listen:  http://0.0.0.0:5001/voice
```

**Now find your computer's IP address** (the phone needs this):
- **Windows:** open PowerShell, run `ipconfig | findstr IPv4`
- **Mac:** run `ifconfig | grep "inet " | grep -v 127`
- **Linux:** run `hostname -I`

It looks like `192.168.1.42` or `10.0.0.146`. Write it down.

### Step 2: Set up the phone (5 minutes, one-time)

1. **Install two apps from F-Droid** (NOT the Play Store — the Play Store version of Termux is broken):
   - [Termux](https://f-droid.org/en/packages/com.termux/) — the terminal
   - [Termux:API](https://f-droid.org/en/packages/com.termux.api/) — gives Termux access to the mic and speaker

2. **Grant microphone permission:**
   - Go to Settings > Apps > Termux:API > Permissions > Microphone > Allow
   - If "Microphone" doesn't appear: force-stop both Termux AND Termux:API in Settings > Apps, then reopen Termux

3. **Open Termux and paste this one-liner:**
```bash
curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh | bash
```

4. **Answer 4 questions when prompted:**

| Question | What to enter | Example |
|----------|--------------|---------|
| **Server URL** | `http://` + your computer's IP (from step 1) + `:5001` | `http://192.168.1.42:5001` |
| **API key** | Make up a password, or press Enter for none. If you set one, start the server with `API_KEY=yourpassword python server.py` | `mykey123` or just Enter |
| **Wake word** | The phrase you'll say to activate the assistant | `jarvis` |
| **Device name** | A name for this phone (useful if you set up multiple) | `kitchen-phone` |

### Step 3: Start it

On the phone in Termux:
```bash
termux-wake-lock
python ~/voice-satellite/satellite.py
```

Say your wake word, then speak!

### Step 4: Verify

If it's not working, test the connection from the phone:
```bash
curl http://YOUR_SERVER_IP:5001/health
```

Should return `{"status": "ok", ...}`. If not:
- Is the server still running on your computer?
- Are both devices on the same WiFi?
- **Windows firewall blocking?** Run as admin: `netsh advfirewall firewall add rule name="Voice Server" dir=in action=allow protocol=TCP localport=5001`

## How It Works

```
Phone (Termux)                         Server (your computer)
┌──────────────────────┐               ┌────────────────────────┐
│  PyAudio (mic)       │               │  server.py             │
│  ↓                   │   HTTP POST   │  ↓                     │
│  Energy detection    │──────────────→│  Whisper STT           │
│  (speech? record it) │               │  ↓                     │
│  ↓                   │               │  Wake word check       │
│  WAV audio blob      │               │  ↓                     │
│                      │   JSON resp   │  LLM (OpenAI/Ollama)   │
│  termux-tts-speak  ←│←──────────────│  ↓                     │
│  (Android TTS)       │               │  Response text         │
└──────────────────────┘               └────────────────────────┘
```

**Phone:** `pyaudio` + `requests` — no ML models, no heavy packages.

**Server:** `flask` + `openai` — works with any OpenAI-compatible API including Ollama.

## Features

- **Wake word activation** — say your phrase to start, configurable to anything
- **Conversation sessions** — after first response, keeps listening without wake word
- **Session context** — follow-up questions remember what you were talking about
- **Smart session ending** — "bye", "thanks", "okay" end the conversation naturally
- **Mic drain after TTS** — prevents speaker audio from bleeding into the next recording
- **Beep confirmations** — audio feedback when wake word is detected
- **Rate limiting** — prevents accidental rapid-fire API calls
- **Bearer token auth** — optional shared secret between phone and server

## Configuration

Edit `~/voice-satellite/config.env` on the phone:

| Variable | Default | What it does |
|----------|---------|-------------|
| `SERVER_URL` | `http://localhost:5001` | Your server's address |
| `API_KEY` | (empty) | Auth token (must match server's `API_KEY`) |
| `WAKE_WORD` | `jarvis` | What you say to activate |
| `NODE_ID` | `android-satellite` | Name for this device |
| `SILENCE_THRESHOLD` | `400` | Mic sensitivity — lower = picks up quieter speech (try 200-700) |
| `SILENCE_DURATION` | `2.0` | Seconds of silence before it stops recording |
| `MAX_RECORD_SECONDS` | `30` | Max recording length per utterance |
| `SESSION_TIMEOUT` | `30` | Seconds of silence before ending a conversation |

Server environment variables (set when running `python server.py`):

| Variable | Default | What it does |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `LLM_MODEL` | `gpt-4o-mini` | Which model to chat with |
| `LLM_BASE_URL` | (auto-detected) | Custom API endpoint URL |
| `OPENAI_API_KEY` | — | Required for OpenAI LLM + Whisper STT |
| `API_KEY` | (empty) | Must match the phone's config |
| `SYSTEM_PROMPT` | (built-in) | Custom personality for the assistant |
| `PORT` | `5001` | Server port |

## Always-On Setup

Want to leave the phone running 24/7 as a smart speaker?

**Prevent Android from killing Termux:**
1. Settings > Apps > Termux > Battery > Unrestricted
2. Settings > Apps > Termux:API > Battery > Unrestricted
3. Keep the phone plugged in

**Run in background (survives SSH disconnects):**
```bash
termux-wake-lock
nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &
```

**Auto-start when phone boots** (install [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/) from F-Droid):
```bash
mkdir -p ~/.termux/boot
echo 'termux-wake-lock && nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &' > ~/.termux/boot/voice.sh
chmod +x ~/.termux/boot/voice.sh
```

**Check logs:**
```bash
tail -f ~/voice-satellite/voice.log
```

**Restart if it crashed:**
```bash
pkill -f satellite.py
nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Can't reach the server" | Check `SERVER_URL` in config.env. Test with `curl http://SERVER_IP:5001/health`. Both devices must be on the same WiFi. |
| No speech detected | Lower `SILENCE_THRESHOLD` (try 200 or 300) |
| Cuts off mid-sentence | Increase `SILENCE_DURATION` (try 2.5 or 3.0) |
| PyAudio error -9999 | Mic permission not granted. Install Termux:API **app** from F-Droid, force-stop both apps, reopen Termux, run `termux-microphone-record -f test.wav -l 3` to trigger permission dialog |
| `termux-microphone-record` no output | Termux:API app not installed (it's separate from the `termux-api` package). Install from F-Droid. |
| 15-second recordings of nothing | Speaker audio bleeding into mic. Lower phone volume. |
| Windows firewall blocking | Admin PowerShell: `netsh advfirewall firewall add rule name="Voice Server" dir=in action=allow protocol=TCP localport=5001` |

## Roadmap

- [ ] Local Whisper STT via whisper.cpp (no cloud needed for transcription)
- [ ] Self-contained mode (everything on the phone — whisper.cpp + llama.cpp)
- [ ] Silero VAD (ML-based silence detection, much more accurate than energy threshold)
- [ ] openWakeWord (ML-based wake word detection, uses less CPU)
- [ ] Piper TTS (local TTS, alternative to Android's built-in engine)
- [ ] Web dashboard for configuration

## License

MIT
