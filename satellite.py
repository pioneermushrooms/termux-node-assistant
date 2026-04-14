#!/data/data/com.termux/files/usr/bin/python3
"""Termux Voice Satellite — Client

Always-on voice assistant that runs on any Android phone via Termux.
Listens for a wake word, records speech, sends audio to a server for
STT + LLM processing, and speaks the response through the phone speaker.

Supports conversation sessions — after the first wake word, stays in
session mode (no wake word needed) until you say goodbye or go silent.

Requirements (phone):
    pip install pyaudio requests

Requirements (server):
    Run server.py on any machine, or point at any OpenAI-compatible API.

Usage:
    termux-wake-lock
    python satellite.py
"""

import array
import math
import os
import struct
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import pyaudio
import requests as http

# ── Configuration ───────────────────────────────────────────

def _load_config() -> dict:
    config = {}
    for path in [Path(__file__).parent / "config.env", Path.home() / ".voice-satellite.env"]:
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    config[key.strip()] = value.strip()
            break
    return config


_cfg = _load_config()

SERVER_URL = os.getenv("SERVER_URL", _cfg.get("SERVER_URL", "http://localhost:5001"))
API_KEY = os.getenv("API_KEY", _cfg.get("API_KEY", ""))
NODE_ID = os.getenv("NODE_ID", _cfg.get("NODE_ID", "android-satellite"))
WAKE_WORD = os.getenv("WAKE_WORD", _cfg.get("WAKE_WORD", "jarvis")).lower()

# Audio
RATE = 16000
CHANNELS = 1
CHUNK = 4000
FORMAT = pyaudio.paInt16

# Voice activity detection
SILENCE_THRESHOLD = int(_cfg.get("SILENCE_THRESHOLD", "400"))
SILENCE_DURATION = float(_cfg.get("SILENCE_DURATION", "2.0"))
MAX_RECORD_SECONDS = int(_cfg.get("MAX_RECORD_SECONDS", "30"))
MIN_SPEECH_SECONDS = 0.5

# Session
SESSION_TIMEOUT = int(_cfg.get("SESSION_TIMEOUT", "30"))

# Goodbye / done phrases
GOODBYE_WORDS = {"bye", "goodbye", "goodnight"}
DONE_PHRASES = {"okay", "ok", "cool", "got it", "alright", "thanks",
                "thank you", "thats all", "that's all", "im good",
                "i'm good", "never mind", "perfect", "awesome", "great"}


# ── Audio helpers ───────────────────────────────────────────

def _rms(data: bytes) -> int:
    samples = array.array("h", data)
    if not samples:
        return 0
    return int(math.sqrt(sum(s * s for s in samples) / len(samples)))


def _beep(freq: int = 800, ms: int = 150):
    try:
        sr = 16000
        n = int(sr * ms / 1000)
        raw = b"".join(struct.pack("<h", int(16000 * math.sin(2 * math.pi * freq * i / sr))) for i in range(n))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
            wf = wave.open(tmp, "wb")
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(raw); wf.close()
        subprocess.run(["termux-media-player", "play", tmp], capture_output=True, timeout=5)
        time.sleep(ms / 1000 + 0.1)
        subprocess.run(["termux-media-player", "stop"], capture_output=True, timeout=3)
        os.unlink(tmp)
    except Exception:
        pass


def _speak(text: str, stream=None):
    try:
        subprocess.run(["termux-tts-speak", "-r", "1.1", text], timeout=120)
    except Exception:
        pass
    if stream:
        try:
            for _ in range(8):
                stream.read(CHUNK, exception_on_overflow=False)
        except Exception:
            pass


def _to_wav(frames: list[bytes]) -> bytes:
    import io
    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(CHANNELS); wf.setsampwidth(2); wf.setframerate(RATE)
    wf.writeframes(b"".join(frames)); wf.close()
    return buf.getvalue()


# ── Server communication ────────────────────────────────────

def _send(wav: bytes, wake_word: str = "", context: str = "") -> dict:
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    try:
        r = http.post(
            f"{SERVER_URL}/voice",
            files={"audio": ("speech.wav", wav, "audio/wav")},
            data={"node_id": NODE_ID, "wake_word": wake_word, "context": context, "tts": "false"},
            headers=headers, timeout=300,
        )
        if r.status_code == 429:
            return {"error": "rate_limited", "speak": "Hold on, try again in a few seconds."}
        r.raise_for_status()
        return r.json()
    except http.exceptions.ConnectionError:
        return {"error": "no_connection", "speak": "Can't reach the server."}
    except http.exceptions.Timeout:
        return {"error": "timeout", "speak": "That took too long. Try again."}
    except Exception as e:
        return {"error": str(e), "speak": "Something went wrong."}


# ── Recording ───────────────────────────────────────────────

def _record(stream) -> list[bytes] | None:
    frames, silent, heard = [], 0, False
    sil_chunks = int(SILENCE_DURATION * RATE / CHUNK)
    max_chunks = int(MAX_RECORD_SECONDS * RATE / CHUNK)
    min_chunks = int(MIN_SPEECH_SECONDS * RATE / CHUNK)

    for _ in range(max_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        if _rms(data) < SILENCE_THRESHOLD:
            silent += 1
            if heard and silent >= sil_chunks and len(frames) > min_chunks:
                break
        else:
            heard = True
            silent = 0
    return frames if heard else None


def _is_goodbye(text: str) -> bool:
    import re
    words = set(re.sub(r"[^a-z ]", "", text.lower()).split())
    return bool(words & GOODBYE_WORDS)


def _is_done(text: str) -> bool:
    import re
    cleaned = re.sub(r"[^a-z ]", "", text.lower()).strip()
    if len(cleaned.split()) > 4:
        return False
    return any(cleaned == p or cleaned.startswith(p + " ") for p in DONE_PHRASES)


# ── Main loop ──────────────────────────────────────────────

def main():
    print("=" * 50)
    print(" Voice Satellite")
    print("=" * 50)
    print(f"  Server:    {SERVER_URL}")
    print(f"  Wake word: \"{WAKE_WORD}\"")
    print(f"  Threshold: {SILENCE_THRESHOLD}")
    print("=" * 50)

    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)

    print(f"\nListening... say \"{WAKE_WORD}\" to start.\n")

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if _rms(data) < SILENCE_THRESHOLD:
                continue

            # Speech detected
            frames = [data]
            more = _record(stream)
            if more:
                frames.extend(more)

            dur = len(frames) * CHUNK / RATE
            print(f"  [*] Recorded {dur:.1f}s, sending...")

            resp = _send(_to_wav(frames), wake_word=WAKE_WORD)

            if "error" in resp:
                print(f"  [!] {resp['error']}")
                if resp.get("speak"):
                    _speak(resp["speak"])
                continue

            transcript = resp.get("transcript", "")
            if transcript:
                print(f"  [>] \"{transcript}\"")

            if not resp.get("wake_word_detected"):
                print(f"  [.] No wake word")
                continue

            # Wake word detected
            _beep(880, 120)

            if resp.get("awaiting_command"):
                print(f"  [*] Listening for command...")
                frames = _record(stream)
                if not frames:
                    _beep(400, 100)
                    continue
                print(f"  [*] Checking...")
                _speak("Checking.")
                resp = _send(_to_wav(frames), wake_word="")
                if "error" in resp:
                    print(f"  [!] {resp['error']}")
                    continue
                transcript = resp.get("transcript", "")
                if transcript:
                    print(f"  [>] \"{transcript}\"")

            text = resp.get("text", "")
            if text:
                cmd = resp.get("command", transcript)
                print(f"  [cmd] {cmd}")
                print(f"  [<<] {text[:150]}{'...' if len(text) > 150 else ''}")
                _speak(text, stream)

                # Enter session
                ctx = f"User: {cmd}\nAssistant: {text}"
                _session(stream, ctx)

    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


def _session(stream, ctx: str):
    print(f"  [session] Speak freely, say \"bye\" to end.\n")
    _beep(600, 100)
    idle = time.time()

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        if _rms(data) < SILENCE_THRESHOLD:
            if time.time() - idle > SESSION_TIMEOUT:
                print(f"  [session] Timeout")
                _beep(400, 200)
                print(f"\nListening... say \"{WAKE_WORD}\" to start.\n")
                return
            continue

        idle = time.time()
        frames = [data]
        more = _record(stream)
        if more:
            frames.extend(more)

        dur = len(frames) * CHUNK / RATE
        print(f"  [*] {dur:.1f}s, sending...")

        resp = _send(_to_wav(frames), wake_word="", context=ctx)
        if "error" in resp:
            print(f"  [!] {resp['error']}")
            if resp.get("speak"):
                _speak(resp["speak"])
            idle = time.time()
            continue

        transcript = resp.get("transcript", "")
        text = resp.get("text", "")

        if transcript:
            print(f"  [>] \"{transcript}\"")

        if transcript and _is_goodbye(transcript):
            _speak("No prob.", stream)
            _beep(400, 200)
            print(f"\nListening... say \"{WAKE_WORD}\" to start.\n")
            return

        if transcript and _is_done(transcript):
            _beep(400, 200)
            print(f"\nListening... say \"{WAKE_WORD}\" to start.\n")
            return

        if text:
            print(f"  [<<] {text[:150]}{'...' if len(text) > 150 else ''}")
            _speak(text, stream)
            ctx += f"\nUser: {transcript}\nAssistant: {text}"
            if len(ctx) > 3000:
                ctx = "\n".join(ctx.split("\n")[-20:])
            _beep(600, 100)
            idle = time.time()


if __name__ == "__main__":
    main()
