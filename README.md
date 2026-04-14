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

### Phone setup (2 minutes)

1. Install **Termux** + **Termux:API** from [F-Droid](https://f-droid.org) (not Play Store)
2. Open Termux and paste this one-liner:

```bash
curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh | bash
```

That's it. It installs everything, downloads the satellite script, and walks you through config.

3. Grant mic permission when prompted (or: Settings > Apps > Termux:API > Permissions > Microphone)

### Server setup (1 minute)

**Option A: OpenAI (easiest)**
```bash
pip install flask openai
OPENAI_API_KEY=sk-... python server.py
```

**Option B: Ollama (free, local)**
```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
pip install flask openai
LLM_PROVIDER=ollama python server.py
```

**Option C: Any OpenAI-compatible API**
```bash
LLM_BASE_URL=http://my-server:8080/v1 LLM_MODEL=my-model python server.py
```

### Start

On the phone:
```bash
termux-wake-lock
python ~/voice-satellite/satellite.py
```

Say your wake word, then speak. Done.

## How It Works

```
Phone (Termux)                         Server (anywhere)
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

**Phone dependencies:** `pyaudio`, `requests` — that's it. No ML models, no heavy packages.

**Server dependencies:** `flask`, `openai` — works with any OpenAI-compatible API including Ollama.

## Features

- **Wake word activation** — configurable phrase, matched after Whisper transcription
- **Conversation sessions** — after first response, keeps listening without wake word
- **Session context** — follow-up questions remember what you were talking about
- **Smart session ending** — "bye", "thanks", "okay" end the session naturally
- **Mic drain after TTS** — prevents speaker audio from being captured back
- **Beep confirmations** — audio feedback when wake word detected
- **Rate limiting** — prevents accidental rapid-fire API calls
- **Bearer token auth** — optional shared secret between phone and server

## Configuration

Edit `~/voice-satellite/config.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `http://localhost:5001` | Your server address |
| `API_KEY` | (empty) | Shared auth token |
| `WAKE_WORD` | `jarvis` | What to say to activate |
| `NODE_ID` | `android-satellite` | Device identifier |
| `SILENCE_THRESHOLD` | `400` | Mic sensitivity (lower = more sensitive) |
| `SILENCE_DURATION` | `2.0` | Seconds of silence before stopping recording |
| `MAX_RECORD_SECONDS` | `30` | Max recording length |
| `SESSION_TIMEOUT` | `30` | Seconds of silence before ending session |

Server environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_BASE_URL` | (auto) | Custom API endpoint |
| `OPENAI_API_KEY` | — | Required for OpenAI |
| `STT_PROVIDER` | `openai` | `openai` (more options coming) |
| `API_KEY` | (empty) | Must match phone config |
| `SYSTEM_PROMPT` | (built-in) | Custom personality |
| `PORT` | `5001` | Server port |

## Always-On Setup

**Prevent Android from killing Termux:**
1. Settings > Apps > Termux > Battery > Unrestricted
2. Same for Termux:API
3. Keep phone plugged in

**Run in background (survives SSH disconnect):**
```bash
termux-wake-lock
nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &
```

**Auto-start on boot (install Termux:Boot from F-Droid):**
```bash
mkdir -p ~/.termux/boot
echo 'termux-wake-lock && nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &' > ~/.termux/boot/voice.sh
chmod +x ~/.termux/boot/voice.sh
```

**Check logs:**
```bash
tail -f ~/voice-satellite/voice.log
```

## Troubleshooting

**"Can't reach the server"** — check SERVER_URL in config.env, test with `curl $SERVER_URL/health`

**No speech detected** — lower SILENCE_THRESHOLD (try 200-300)

**Cuts off mid-sentence** — increase SILENCE_DURATION (try 2.5 or 3.0)

**Mic permission denied** — install Termux:API *app* from F-Droid (not just the package), force-stop both Termux apps, reopen

**PyAudio error -9999** — mic permission not granted. See above.

**15s recordings of silence** — TTS speaker audio bleeding into mic. The script drains the buffer but you may need to lower speaker volume.

## Roadmap

- [ ] Local Whisper STT (whisper.cpp, no cloud needed)
- [ ] Self-contained mode (everything on the phone — whisper.cpp + llama.cpp)
- [ ] Silero VAD (ML-based silence detection, much more accurate)
- [ ] openWakeWord (ML-based wake word, lower CPU than always-transcribing)
- [ ] Piper TTS (local TTS alternative to Android built-in)
- [ ] Web dashboard for config (instead of editing config.env)

## License

MIT
