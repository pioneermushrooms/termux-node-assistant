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

Works with **OpenAI, Ollama, llama.cpp, or any OpenAI-compatible API** — including fully local setups with zero cloud dependency.

## Why

You have an old phone in a drawer. It has a mic, a speaker, WiFi, and 4-8GB of RAM. This project turns it into a smart speaker that connects to any LLM — cloud or local.

No existing project does this. The voice assistant ecosystem is fragmented between Home Assistant satellites (locked to HA), desktop-only tools, and abandoned Mycroft forks. This is the missing piece: a simple, generic voice client for Termux that talks to any backend.

## How It Works

The phone is just a mic and speaker. All the AI runs on a separate machine (your desktop, a server, a Raspberry Pi — anything on your network).

```
Phone (Termux)                         Server (any machine)
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

## Quick Start

### Step 1: Choose your LLM backend and start the server

The "server" is any machine on your network — a desktop, laptop, NAS, Raspberry Pi, or even a cloud VM. It runs the AI. Pick one option:

---

**Option A: Fully local — zero cloud, zero cost, fully private**

Everything runs on your machine. No API keys, no accounts, no data leaves your network.

1. **Install Ollama** from [ollama.com](https://ollama.com) — available for Mac, Linux, and Windows. This runs the LLM.
2. **Pull a model** (one-time download):
   ```bash
   ollama pull llama3.2          # 2GB, good for most questions
   # or for better quality:
   ollama pull llama3.1:8b       # 4.7GB
   ```
3. **Download `server.py`** from this repo to your machine
4. **Install Python deps and start:**
   ```bash
   pip install flask openai faster-whisper
   LLM_PROVIDER=ollama python server.py
   ```

> **What's happening:** Ollama handles the LLM chat. `faster-whisper` handles speech-to-text locally. No API keys needed. First voice request downloads the Whisper model (~150MB). Needs 8GB+ RAM.

---

**Option B: llama.cpp — run any GGUF model locally (even on the phone itself)**

Run any quantized model from [HuggingFace](https://huggingface.co/models?sort=trending&search=gguf). This can run on a separate computer OR directly on the phone — a device with 6GB RAM can run small models like Gemma 2B, Phi-3 mini, or Qwen2-1.5B.

> **Tip:** If your phone has a damaged screen, use [scrcpy](https://github.com/Genymobile/scrcpy) on your computer to mirror the phone's display and type commands from your keyboard. This is highly recommended for the setup steps below.

1. **Install llama.cpp** — on your computer ([build instructions](https://github.com/ggml-org/llama.cpp#build) or [prebuilt releases](https://github.com/ggml-org/llama.cpp/releases)), or in Termux on the phone:
   ```bash
   pkg install cmake clang
   git clone https://github.com/ggml-org/llama.cpp
   cd llama.cpp && cmake -B build && cmake --build build --config Release
   ```
2. **Download a GGUF model** — pick a size that fits your RAM:
   - **4GB RAM:** Qwen2-1.5B-Q4, Phi-3-mini-Q4
   - **6GB RAM:** Gemma-2-2B-Q4, Llama-3.2-3B-Q4
   - **8GB+ RAM:** Gemma-4-12B-Q4, Llama-3.1-8B-Q4
3. **Start the model server.** In Termux, you need two sessions — swipe from the left edge of the screen to open the session drawer, tap "New session":

   **Session 1 — start the model:**
   ```bash
   ./llama.cpp/build/bin/llama-server -m your-model.gguf --port 8080
   ```

   **Session 2 — start the voice server:**
   ```bash
   pip install flask openai faster-whisper
   LLM_BASE_URL=http://localhost:8080/v1 LLM_MODEL=local python server.py
   ```

   > **Or run both in one session** using background processes:
   > ```bash
   > ./llama.cpp/build/bin/llama-server -m your-model.gguf --port 8080 &
   > sleep 5
   > LLM_BASE_URL=http://localhost:8080/v1 LLM_MODEL=local python server.py
   > ```

> **Zero cloud, zero cost, fully private.** No data ever leaves the device. Works in airplane mode after setup. Run Gemma, Llama, Mistral, Phi, Qwen — any model with a GGUF release.

---

**Option C: OpenAI — easiest setup, cloud-based, ~$0.01/interaction**

1. **Get an API key:** go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys), sign in, click "Create new secret key", copy it. Requires a credit card on file.
2. **Download `server.py`** from this repo
3. **Start:**
   ```bash
   pip install flask openai
   OPENAI_API_KEY=sk-your-key-here python server.py
   ```

> Uses GPT-4o-mini for chat and OpenAI Whisper for speech-to-text. Fast and high quality but costs ~$0.01 per voice interaction.

---

**Option D: Mix and match — free LLM + cloud STT**

Use Ollama for the LLM (free) and OpenAI just for speech-to-text (cheap, higher quality than local Whisper):

```bash
pip install flask openai
OPENAI_API_KEY=sk-your-key LLM_PROVIDER=ollama python server.py
```

> Best quality-to-cost ratio. LLM is free, STT costs ~$0.006 per 30 seconds of audio.

---

**Option E: Any OpenAI-compatible API**

Works with LM Studio, vLLM, text-generation-webui — anything that serves `/v1/chat/completions`:

```bash
pip install flask openai faster-whisper
LLM_BASE_URL=http://my-server:8080/v1 LLM_MODEL=my-model python server.py
```

---

**Once the server starts, you'll see:**
```
  LLM:     ollama (llama3.2)
  STT:     local (base)
  Listen:  http://0.0.0.0:5001/voice
```

**Now find your server machine's IP** (you'll need this for the phone):
- **Windows:** open PowerShell, run `ipconfig | findstr IPv4`
- **Mac:** `ifconfig | grep "inet " | grep -v 127`
- **Linux:** `hostname -I`

It looks like `192.168.1.42` or `10.0.0.146`. Write it down.

### Step 2: Set up the phone

**Install two apps from F-Droid** (requires tapping the phone screen):

1. Open [F-Droid](https://f-droid.org) on the phone
2. Search and install **[Termux](https://f-droid.org/en/packages/com.termux/)** — this is the terminal that runs on your phone
3. Search and install **[Termux:API](https://f-droid.org/en/packages/com.termux.api/)** — this gives Termux access to the microphone and speaker

> **Important:** Install from F-Droid, NOT the Play Store. The Play Store version of Termux is outdated and broken.

> **Cracked or hard-to-use screen?** Use [scrcpy](https://github.com/Genymobile/scrcpy) to mirror your phone screen to your computer over USB. You only need the screen for installing apps and granting permissions — everything else can be done over SSH.

**Grant microphone permission** (requires tapping the screen or scrcpy):

- Go to **Settings > Apps > Termux:API > Permissions > Microphone > Allow**
- If "Microphone" doesn't appear in the list: force-stop both **Termux** AND **Termux:API** in Settings > Apps, then reopen Termux and try again

**Set up SSH so you can do the rest from your computer:**

On the phone (type this in Termux — it's the last thing you need to type on the phone itself):
```bash
pkg install openssh && sshd
whoami
# Note the username it prints (e.g. u0_a383)
```

Now from your computer, SSH in — no more typing on the phone:
```bash
ssh -p 8022 USERNAME@PHONE_IP
# Example: ssh -p 8022 u0_a383@192.168.1.50
```

> **Finding the phone's IP:** In Termux, run `ifconfig wlan0 | grep inet` — the number after `inet` is the phone's IP.

> **Setting an SSH password:** Run `passwd` in Termux to set a password for SSH login.

**Run the installer** (from your SSH session):

```bash
curl -sL https://raw.githubusercontent.com/pioneermushrooms/termux-node-assistant/main/setup.sh | bash
```

**Answer 4 questions when prompted:**

| Question | What to enter | Example |
|----------|--------------|---------|
| **Server URL** | `http://` + your server machine's IP + `:5001` | `http://192.168.1.42:5001` |
| **API key** | A shared password (make one up), or press Enter for none | `mykey123` or just Enter |
| **Wake word** | The phrase you'll say to activate | `jarvis` |
| **Device name** | A name for this phone | `kitchen-phone` |

> If you set an API key, start the server with the same key: `API_KEY=mykey123 python server.py`

### Step 3: Start it

```bash
termux-wake-lock
python ~/voice-satellite/satellite.py
```

Say your wake word, then speak!

### Step 4: Verify

Test the connection from the phone:
```bash
curl http://YOUR_SERVER_IP:5001/health
```

Should return `{"status": "ok", ...}`. If not:
- Is the server still running?
- Are both devices on the same WiFi network?
- **Windows firewall blocking?** Run as admin: `netsh advfirewall firewall add rule name="Voice Server" dir=in action=allow protocol=TCP localport=5001`

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

## Configuration

Edit `~/voice-satellite/config.env` on the phone to tune settings:

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
| `OPENAI_API_KEY` | — | Required for OpenAI LLM; enables cloud Whisper STT |
| `STT_PROVIDER` | `auto` | `auto` (cloud if API key set, local otherwise), `openai`, or `local` |
| `WHISPER_MODEL_SIZE` | `base` | Local Whisper model: `tiny` (39MB) / `base` (141MB) / `small` (466MB) / `medium` (1.5GB) / `large` (3GB) |
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
| Hard to type on cracked screen | Use [scrcpy](https://github.com/Genymobile/scrcpy) to mirror phone to your computer, or SSH in: `pkg install openssh && sshd` then `ssh -p 8022 user@PHONE_IP` |

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
