#!/usr/bin/env python3
"""Termux Voice Satellite — Server

Minimal server that accepts audio from a voice satellite device,
transcribes it with Whisper (OpenAI API or local whisper.cpp),
checks for wake word, chats with an LLM (OpenAI/Ollama/any OpenAI-compatible),
and returns the response.

Setup:
    pip install flask openai
    Create a .env file next to server.py with your settings (see below)
    python server.py

The server reads from a .env file in the same directory. Example .env:
    OPENAI_API_KEY=sk-your-key-here
    LLM_PROVIDER=openai
    LLM_MODEL=gpt-4o-mini

Or for fully local (no API keys):
    pip install flask openai faster-whisper
    ollama pull llama3.2
    # .env file:
    LLM_PROVIDER=ollama

Environment variables:
    PORT              — server port (default: 5001)
    LLM_PROVIDER      — "openai" or "ollama" (default: openai)
    LLM_MODEL         — model name (default: gpt-4o-mini / llama3.2)
    LLM_BASE_URL      — custom base URL for OpenAI-compatible APIs
    OPENAI_API_KEY     — required for OpenAI provider; optional for STT
    STT_PROVIDER       — "auto", "openai", or "local" (default: auto)
                         auto = openai if API key set, local otherwise
    WHISPER_MODEL_SIZE — local whisper model: tiny/base/small/medium/large (default: base)
    API_KEY            — shared secret for satellite auth (optional)
    SYSTEM_PROMPT      — custom system prompt (optional)
"""

import base64
import io
import logging
import os
import re
import time
from pathlib import Path

# Load .env file if it exists (same directory as server.py)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and value and key not in os.environ:
                os.environ[key] = value

from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("voice-server")

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────────

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini" if LLM_PROVIDER == "openai" else "llama3.2")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1" if LLM_PROVIDER == "ollama" else None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STT_PROVIDER = os.getenv("STT_PROVIDER", "auto")  # "auto", "openai", "local"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large
API_KEY = os.getenv("API_KEY", "")

# Auto-detect STT provider
if STT_PROVIDER == "auto":
    if OPENAI_API_KEY:
        STT_PROVIDER = "openai"
    else:
        STT_PROVIDER = "local"

DEFAULT_SYSTEM_PROMPT = (
    "You are a voice assistant. The user spoke aloud and will hear your response "
    "through a speaker. Keep answers to 2-3 sentences. Use plain conversational "
    "language — no markdown, no bullet points, no asterisks. Be direct and helpful."
)
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

# Rate limiting
_last_request: dict[str, float] = {}
COOLDOWN = 1.0


# ── Auth ────────────────────────────────────────────────────

def _check_auth() -> bool:
    if not API_KEY:
        return True
    return request.headers.get("Authorization") == f"Bearer {API_KEY}"


# ── STT ─────────────────────────────────────────────────────

def _transcribe_openai(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe using OpenAI Whisper API."""
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        response = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return response.text
    except Exception as e:
        return f"[STT Error: {e}]"


_whisper_model = None


def _transcribe_local(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe using faster-whisper (local, no API key needed)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return "[STT Error: faster-whisper not installed. Run: pip install faster-whisper]"

    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}' (first request takes a moment)...")
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, compute_type="int8")
        logger.info("Whisper model loaded.")

    tmp = None
    try:
        import tempfile
        # Write to temp file, close it before passing to whisper (Windows compatibility)
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.write(fd, audio_bytes)
        os.close(fd)
        segments, _ = _whisper_model.transcribe(tmp, beam_size=5)
        text = " ".join(s.text.strip() for s in segments)
        return text if text else "[silence]"
    except Exception as e:
        logger.error(f"Local STT error: {e}", exc_info=True)
        return f"[STT Error: {e}]"
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe audio to text."""
    if STT_PROVIDER == "openai":
        return _transcribe_openai(audio_bytes, filename)
    if STT_PROVIDER == "local":
        return _transcribe_local(audio_bytes, filename)
    return "[STT Error: unknown provider]"


# ── LLM ─────────────────────────────────────────────────────

def _chat(user_message: str, context: str = "") -> str:
    """Send message to LLM and get response."""
    try:
        import openai

        kwargs = {}
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        if LLM_PROVIDER == "ollama":
            kwargs["api_key"] = "ollama"  # Ollama doesn't need a real key
        else:
            kwargs["api_key"] = OPENAI_API_KEY

        client = openai.OpenAI(**kwargs)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation context
        if context:
            for line in context.strip().split("\n"):
                if line.startswith("User: "):
                    messages.append({"role": "user", "content": line[6:]})
                elif line.startswith("Assistant: "):
                    messages.append({"role": "assistant", "content": line[11:]})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM error: {e}")
        low = str(e).lower()
        if "rate_limit" in low or "429" in str(e):
            return "Sorry, I'm being rate limited. Try again in a moment."
        return "Sorry, something went wrong. Try again."


# ── TTS (optional server-side) ──────────────────────────────

def _generate_tts(text: str) -> str | None:
    """Generate TTS audio as base64 MP3. Returns None if unavailable."""
    if not OPENAI_API_KEY or LLM_PROVIDER == "ollama":
        return None
    try:
        import requests as req
        resp = req.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini-tts", "input": text[:3000], "voice": "sage",
                  "instructions": "Speak clearly and conversationally.", "response_format": "mp3"},
            timeout=30,
        )
        if resp.status_code == 200:
            return base64.b64encode(resp.content).decode("ascii")
    except Exception:
        pass
    return None


# ── Routes ──────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "llm": LLM_PROVIDER, "model": LLM_MODEL, "stt": STT_PROVIDER})


@app.route("/voice", methods=["POST"])
def voice():
    """Main endpoint: accepts audio, transcribes, chats, returns response."""
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401

    node_id = request.form.get("node_id", "unknown")
    wake_word = request.form.get("wake_word", "").lower()
    context = request.form.get("context", "")
    want_audio = request.form.get("tts", "false").lower() == "true"

    # Rate limit
    now = time.time()
    last = _last_request.get(node_id, 0)
    if now - last < COOLDOWN:
        return jsonify({"error": "rate limited"}), 429
    _last_request[node_id] = now

    # Get audio
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "no audio file"}), 400

    audio_bytes = audio_file.read()
    if len(audio_bytes) > 10 * 1024 * 1024:
        return jsonify({"error": "audio too large"}), 400

    # Transcribe
    transcript = _transcribe(audio_bytes, filename=audio_file.filename or "audio.wav")
    if transcript.startswith("[STT Error"):
        return jsonify({"error": transcript}), 500

    logger.info(f"[{node_id}] Heard: \"{transcript}\"")

    # Wake word check (punctuation-insensitive)
    normalized = re.sub(r"[^a-z0-9 ]", "", transcript.lower())
    wake_normalized = re.sub(r"[^a-z0-9 ]", "", wake_word)

    if wake_normalized and wake_normalized not in normalized:
        return jsonify({"text": "", "transcript": transcript, "wake_word_detected": False, "node_id": node_id})

    # Extract command after wake word
    command = transcript
    if wake_normalized:
        wake_words = wake_normalized.split()
        pattern = r"(?i)" + r"[^a-zA-Z0-9]*".join(re.escape(w) for w in wake_words)
        parts = re.split(pattern, transcript, maxsplit=1)
        if len(parts) > 1:
            command = parts[1].lstrip(" ,.:;!?-")
        else:
            command = ""

        if not command:
            return jsonify({"text": "", "transcript": transcript, "wake_word_detected": True,
                            "awaiting_command": True, "node_id": node_id})

    logger.info(f"[{node_id}] Command: \"{command}\"")

    # Chat with LLM
    result = _chat(command, context=context)
    logger.info(f"[{node_id}] Response: {result[:100]}")

    response = {"text": result, "transcript": transcript, "command": command,
                "wake_word_detected": True, "node_id": node_id}

    if want_audio:
        audio_b64 = _generate_tts(result)
        if audio_b64:
            response["audio_base64"] = audio_b64
            response["audio_format"] = "mp3"

    return jsonify(response)


# ── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    print("=" * 50)
    print(" Voice Satellite Server")
    print("=" * 50)
    print(f"  LLM:     {LLM_PROVIDER} ({LLM_MODEL})")
    stt_detail = f"{STT_PROVIDER}" + (f" ({WHISPER_MODEL_SIZE})" if STT_PROVIDER == "local" else "")
    print(f"  STT:     {stt_detail}")
    print(f"  Auth:    {'enabled' if API_KEY else 'disabled'}")
    print(f"  Listen:  http://0.0.0.0:{port}/voice")
    if STT_PROVIDER == "local":
        print(f"  Note:    First request will download the Whisper model (~150MB for 'base')")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
