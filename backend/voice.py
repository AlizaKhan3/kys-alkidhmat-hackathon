"""Voice I/O: Groq Whisper STT + edge-tts TTS. Browser APIs remain the UI fallback."""
import os
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
# Female Indian-English voice ONLY — Chef Nisa. Never fall back to male.
FEMALE_EDGE_VOICES = (
    "en-IN-NeerjaNeural",  # primary
    "en-GB-SoniaNeural",
    "en-US-JennyNeural",
    "en-AU-NatashaNeural",
)
_EDGE_REQ = os.getenv("EDGE_TTS_VOICE", FEMALE_EDGE_VOICES[0]).strip()
_MALE_HINTS = ("guy", "ryan", "prabhat", "davis", "tony", "eric", "christopher", "male", "andrew", "brian")
if any(h in _EDGE_REQ.lower() for h in _MALE_HINTS) and os.getenv("ALLOW_MALE_TTS") != "1":
    EDGE_VOICE = FEMALE_EDGE_VOICES[0]
else:
    EDGE_VOICE = _EDGE_REQ or FEMALE_EDGE_VOICES[0]


class SpeakIn(BaseModel):
    text: str


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Speech → text via Groq Whisper. Needs GROQ_API_KEY."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise HTTPException(503, detail="GROQ_API_KEY not set")

    data = await audio.read()
    if not data:
        raise HTTPException(400, detail="Empty audio")
    if len(data) < 1500:
        raise HTTPException(400, detail=f"Audio too small ({len(data)} bytes) — speak longer")

    filename = audio.filename or "audio.wav"
    content_type = audio.content_type or "application/octet-stream"
    print(f"[transcribe] {filename} {content_type} {len(data)} bytes")

    try:
        import aiohttp
    except ImportError as e:
        raise HTTPException(500, detail="aiohttp missing (install edge-tts)") from e

    # Whisper uses the filename extension to pick a decoder — keep it honest.
    lower = filename.lower()
    if not lower.endswith((".wav", ".webm", ".mp3", ".mp4", ".m4a", ".ogg", ".flac", ".mpeg", ".mpga")):
        ext = "wav" if "wav" in (content_type or "") else "webm"
        filename = f"audio.{ext}"
        lower = filename.lower()
    if lower.endswith(".wav"):
        content_type = "audio/wav"
    elif lower.endswith(".webm"):
        content_type = "audio/webm"
    elif lower.endswith((".mp4", ".m4a")):
        content_type = "audio/mp4"

    form = aiohttp.FormData()
    form.add_field("file", data, filename=filename, content_type=content_type)
    form.add_field("model", WHISPER_MODEL)
    form.add_field("response_format", "json")
    form.add_field("language", "en")
    form.add_field("temperature", "0")
    # Bias toward kitchen questions; cuts down silence hallucinations.
    form.add_field(
        "prompt",
        "Questions about smash burgers, pasta, sauce, salt, fat ratio, cooking, chef kitchen.",
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROQ_URL,
                data=form,
                headers={"Authorization": f"Bearer {key}"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status >= 400:
                    raise HTTPException(resp.status, detail=body.get("error", body))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Groq Whisper failed: {e}") from e

    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(422, detail="No speech detected")
    return {"text": text, "model": WHISPER_MODEL}


@router.post("/speak")
async def speak(body: SpeakIn):
    """Text → MP3 via edge-tts (no API key)."""
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, detail="Empty text")

    try:
        import edge_tts
    except ImportError as e:
        raise HTTPException(500, detail="edge-tts not installed") from e

    voices = [EDGE_VOICE] + [v for v in FEMALE_EDGE_VOICES if v != EDGE_VOICE]
    last_err = None
    for voice in voices:
        try:
            communicate = edge_tts.Communicate(text, voice)
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            if chunks:
                print(f"[speak] voice={voice} bytes={sum(len(c) for c in chunks)}")
                return Response(content=b"".join(chunks), media_type="audio/mpeg")
        except Exception as e:
            last_err = e
            print(f"[speak] {voice} failed: {e}")
            continue

    raise HTTPException(502, detail=f"edge-tts failed (female voices): {last_err}")
