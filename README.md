# termux-node-assistant

Turn any old Android phone into an always-on voice assistant. No app development, no root — just Termux.

```
"Hey Jarvis, what's the weather?"
  → Phone mic picks up speech
  → Audio sent to your server
  → Whisper transcribes, LLM responds
  → Phone speaker reads the answer
  → Keeps listening for follow-up questions
```

Works with **OpenAI, Ollama, llama.cpp, or any OpenAI-compatible API** — including fully local setups with zero cloud dependency.

## Why

You have an old phone in a drawer. It has a mic, a speaker, WiFi, and 4-8GB of RAM. This project turns it into a smart speaker that connects to any LLM — cloud or local.

No existing project does this. The voice assistant ecosystem is fragmented between Home Assistant satellites (locked to HA), desktop-only tools, and abandoned Mycroft forks. This is the missing piece: a simple, generic voice client for Termux that talks to any backend.

## How It Works

The phone is just a mic and speaker. The AI runs on a separate machine — your desktop, a server, a Raspberry Pi, or even a cloud VM.

```
Phone (Termux)                         Server (any machine on your network)
┌──────────────────────┐               ┌────────────────────────┐
│  Mic picks up speech │               │  server.py             │
│  ↓                   │   audio file  │  ↓                     │
│  Detects someone     │──────────────→│  Whisper (STT)         │
│  is talking          │               │  ↓                     │
│  ↓                   │               │  Wake word check       │
│  Records until       │               │  ↓                     │
│  silence             │   text back   │  LLM (your choice)     │
│  ↓                   │←──────────────│  ↓                     │
│  Speaks response     │               │  Response              │
│  through speaker     │               │                        │
└──────────────────────┘               └────────────────────────┘
```

**What runs on the phone:** `satellite.py` — listens to mic, sends audio, speaks response. Two Python packages: `pyaudio` and `requests`.

**What runs on your server:** `server.py` — receives audio, transcribes with Whisper, chats with your LLM, returns text. You choose the LLM.

## Quick Start

### Step 1: Set up the server (on your computer)

The "server" is any computer on your network that will run the AI. 

1. Download `server.py` from this repo to that machine
2. Install dependencies: `pip install flask openai`
3. Create a `.env` file in the same folder as `server.py` with your settings (see options below)
4. Run: `python server.py`

The server reads all config from the `.env` file — no need to set environment variables in your terminal. Pick one option and create your `.env` accordingly:

---

**Option A: OpenAI — easiest**

Requires an [OpenAI API key](https://platform.openai.com/api-keys) (~$0.01 per voice interaction).

```bash
pip install flask openai
```

`.env` file:
```
OPENAI_API_KEY=sk-your-key-here
```

That's it. Run `python server.py`.

---

**Option B: Ollama + OpenAI Whisper — free LLM, cheap STT**

1. Install [Ollama](https://ollama.com) (Mac, Linux, Windows)
2. Pull a model: `ollama pull llama3.2` (~2GB download)

```bash
pip install flask openai
```

`.env` file:
```
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=ollama
```

> The LLM is free (Ollama runs locally). The OpenAI key is only used for Whisper speech-to-text (~$0.006 per 30 seconds of audio).

---

**Option C: Fully local — zero cloud, zero API keys**

Uses Ollama for the LLM and faster-whisper for speech-to-text. Nothing leaves your network.

1. Install [Ollama](https://ollama.com) and pull a model: `ollama pull llama3.2`

```bash
pip install flask openai faster-whisper
```

`.env` file:
```
LLM_PROVIDER=ollama
```

> No API keys needed. First request downloads the Whisper model (~150MB). Needs 8GB+ RAM.

---

**Option D: llama.cpp — run any GGUF model (Gemma 4, Llama, Mistral, etc.)**

For maximum control. Download any GGUF model from [HuggingFace](https://huggingface.co/models?sort=trending&search=gguf) and run it directly.

1. Start the model in one terminal: `llama-server -m your-model.gguf --port 8080`
2. In another terminal:

```bash
pip install flask openai faster-whisper
```

`.env` file:
```
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=gemma-4
```

Run `python server.py`.

> **Running on the phone itself?** A device with 6GB RAM can run small quantized models (Gemma 2B, Phi-3 mini, Qwen2-1.5B). Install llama.cpp in Termux: `pkg install cmake clang && git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build && cmake --build build --config Release`. Use Termux sessions (swipe from left edge) or background processes (`llama-server ... &`) to run both. Use [scrcpy](https://github.com/Genymobile/scrcpy) to control the phone from your computer if the screen is damaged.

---

**Option E: Any OpenAI-compatible API (LM Studio, vLLM, etc.)**

```bash
pip install flask openai faster-whisper
```

`.env` file:
```
LLM_BASE_URL=http://my-server:8080/v1
LLM_MODEL=my-model
```

---

**Once the server starts, you'll see:**
```
==================================================
 Voice Satellite Server
==================================================
  LLM:     ollama (llama3.2)
  STT:     openai
  Auth:    disabled
  Listen:  http://0.0.0.0:5001/voice
==================================================
```

**Find your server's IP address** (the phone needs this to connect):
- **Windows PowerShell:** `ipconfig | findstr IPv4`
- **Mac:** `ifconfig | grep "inet " | grep -v 127`
- **Linux:** `hostname -I`

It looks like `192.168.1.42` or `10.0.0.89`. Write it down — you'll enter it on the phone.

### Step 2: Set up the phone

#### Install apps (requires the phone screen)

1. Install **[Termux](https://f-droid.org/en/packages/com.termux/)** — from F-Droid or the Play Store
2. Install **[Termux:API](https://f-droid.org/en/packages/com.termux.api/)** — from F-Droid or the Play Store. This is a **separate app** that gives Termux access to the mic and speaker.

> **Damaged screen?** Use [scrcpy](https://github.com/Genymobile/scrcpy) on your computer to mirror the phone screen over USB. You only need the screen for installing apps and granting permissions.

#### Grant microphone permission

- Go to **Settings > Apps > Termux > Permissions > Microphone > Allow**
- Also: **Settings > Apps > Termux:API > Permissions > Microphone > Allow**
- If "Microphone" doesn't appear: force-stop both **Termux** AND **Termux:API** in Settings > Apps, then reopen Termux. A permission popup should appear when you first use the mic.

#### Set up SSH (so you can do the rest from your computer's keyboard)

Open Termux on the phone and type these commands — this is the last thing you need to type on the phone itself:

```bash
pkg install openssh
passwd
# Type a password (you'll use this to SSH in)
sshd
whoami
# Note the username (e.g. u0_a383)
```

**Find the phone's IP** — on your computer (with phone connected via USB):
```
# Windows (from your scrcpy folder or wherever adb is):
adb shell ip route
# Look for the number after "src" — that's the phone's IP (e.g. 10.0.0.231)

# Or on Mac/Linux:
adb shell ip route | awk '{print $NF}'
```

**SSH in from your computer:**
```bash
ssh -p 8022 USERNAME@PHONE_IP
# Example: ssh -p 8022 u0_a383@10.0.0.231
```

Now you can type everything from your computer's keyboard.

#### Install the satellite

From your SSH session:

```bash
curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh | bash
```

> **Note:** The setup script asks 4 questions (server URL, API key, wake word, device name). If they get skipped (can happen with `curl | bash`), edit the config manually — see below.

#### Configure

Edit the config file:

```bash
nano ~/voice-satellite/config.env
```

Make sure it looks like this (with your server's actual IP):

```
SERVER_URL=http://YOUR_SERVER_IP:5001
API_KEY=
WAKE_WORD=jarvis
NODE_ID=my-phone
SILENCE_THRESHOLD=400
SILENCE_DURATION=2.0
MAX_RECORD_SECONDS=30
SESSION_TIMEOUT=30
```

| Field | What to enter |
|-------|--------------|
| `SERVER_URL` | `http://` + your server's IP + `:5001` (e.g. `http://10.0.0.89:5001`) |
| `API_KEY` | Leave blank unless you started the server with `API_KEY=something` |
| `WAKE_WORD` | Whatever phrase you want to say to activate (e.g. `jarvis`, `computer`, `hey assistant`) |

Save with **Ctrl+O**, Enter, **Ctrl+X**.

### Step 3: Start it

Test the connection first:
```bash
curl http://YOUR_SERVER_IP:5001/health
```

Should return `{"status": "ok", ...}`. If not, see Troubleshooting below.

Then start:
```bash
termux-wake-lock
python ~/voice-satellite/satellite.py
```

Say your wake word, then speak!

## Features

- **Wake word activation** — say your phrase to start, configurable to anything
- **Conversation sessions** — after first response, keeps listening without wake word
- **Session context** — follow-up questions remember what you were talking about
- **Smart session ending** — "bye", "thanks", "okay" end the conversation naturally
- **Mic drain after TTS** — prevents speaker audio from bleeding into the next recording
- **Beep confirmations** — audio feedback when wake word is detected
- **Rate limiting** — prevents accidental rapid-fire API calls
- **Bearer token auth** — optional shared secret between phone and server
- **Fully local capable** — Ollama or llama.cpp for LLM + faster-whisper for STT = zero cloud

## Keeping It Always-On

By default, the mic only works while Termux is the active app on screen. To keep it running 24/7:

**1. Prevent Android from killing Termux:**
- Settings > Apps > Termux > Battery > **Unrestricted**
- Settings > Apps > Termux:API > Battery > **Unrestricted**
- Keep the phone plugged in

**2. Run in background** (survives SSH disconnects and screen-off):
```bash
termux-wake-lock
nohup python -u ~/voice-satellite/satellite.py > ~/voice-satellite/voice.log 2>&1 &
```

> `termux-wake-lock` is critical — without it, Android will suspend Termux when the screen turns off and the mic will stop working.

**3. Auto-start when phone boots** (install [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/) from F-Droid):
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

## Configuration Reference

**Phone** (`~/voice-satellite/config.env`):

| Variable | Default | What it does |
|----------|---------|-------------|
| `SERVER_URL` | `http://localhost:5001` | Your server's address |
| `API_KEY` | (empty) | Auth token — must match the server's `API_KEY` if set |
| `WAKE_WORD` | `jarvis` | What you say to activate |
| `NODE_ID` | `android-satellite` | Name for this device |
| `SILENCE_THRESHOLD` | `400` | Mic sensitivity — lower = picks up quieter speech (try 200-700) |
| `SILENCE_DURATION` | `2.0` | Seconds of silence before it stops recording |
| `MAX_RECORD_SECONDS` | `30` | Max recording length per utterance |
| `SESSION_TIMEOUT` | `30` | Seconds of silence before ending a conversation |

**Server** (environment variables, set before running `python server.py`):

| Variable | Default | What it does |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `LLM_MODEL` | `gpt-4o-mini` | Which model to use |
| `LLM_BASE_URL` | (auto) | Custom endpoint URL (for llama.cpp, LM Studio, etc.) |
| `OPENAI_API_KEY` | — | Required for OpenAI LLM and/or cloud Whisper STT |
| `STT_PROVIDER` | `auto` | `auto` (cloud if API key set, local otherwise), `openai`, or `local` |
| `WHISPER_MODEL_SIZE` | `base` | Local Whisper model: `tiny` (39MB) / `base` (141MB) / `small` (466MB) / `medium` (1.5GB) / `large` (3GB) |
| `API_KEY` | (empty) | Shared secret — must match the phone's `API_KEY` if set. This is NOT your OpenAI key. |
| `SYSTEM_PROMPT` | (built-in) | Custom personality for the assistant |
| `PORT` | `5001` | Server port |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Can't reach the server" | Check `SERVER_URL` in config.env. Test: `curl http://SERVER_IP:5001/health`. Both devices must be on the same WiFi. |
| 401 Unauthorized on server | Your OpenAI API key isn't set or is expired. Re-set it: `$env:OPENAI_API_KEY='sk-...'` (Windows) or `export OPENAI_API_KEY=sk-...` (Mac/Linux) |
| 500 Server Error | Check the server terminal for error messages. Common cause: missing OpenAI key or faster-whisper not installed. |
| No speech detected | Lower `SILENCE_THRESHOLD` in config.env (try 200 or 300) |
| Cuts off mid-sentence | Increase `SILENCE_DURATION` (try 2.5 or 3.0) |
| Mic only works with Termux open | Run `termux-wake-lock` before starting. Set battery to Unrestricted for both Termux apps. |
| PyAudio error -9999 | Mic permission not granted to **Termux** (not just Termux:API). Settings > Apps > Termux > Permissions > Microphone > Allow. Force-stop both apps and reopen if needed. |
| `termux-microphone-record` no output | Termux:API **app** not installed (it's separate from the `termux-api` package). Install from F-Droid or Play Store. |
| 15-second recordings of nothing | Speaker audio bleeding into mic. Lower phone volume. |
| Windows firewall blocking | Admin PowerShell: `netsh advfirewall firewall add rule name="Voice Server" dir=in action=allow protocol=TCP localport=5001` |
| Can't find phone's IP | Connect via USB, run `adb shell ip route` — IP is the number after `src` |
| Setup script skips questions | `curl \| bash` doesn't support interactive prompts. Edit config manually: `nano ~/voice-satellite/config.env` |
| PowerShell `$env:` not working | Use single quotes around values: `$env:OPENAI_API_KEY='sk-...'`. Set on a separate line, not inline. |
| `latin-1 codec` encoding error | Config file has invisible special characters. Re-create it: delete and re-edit with `nano` |

## Roadmap

- [x] Local Whisper STT via faster-whisper (no cloud needed for transcription)
- [x] Ollama + llama.cpp support (fully local LLM)
- [ ] Silero VAD (ML-based silence detection, much more accurate than energy threshold)
- [ ] openWakeWord (ML-based wake word detection, uses less CPU)
- [ ] Piper TTS (local TTS, alternative to Android's built-in engine)
- [ ] Multi-node support (multiple phones, one server, location-aware responses)
- [ ] Web dashboard for configuration

## License

MIT
