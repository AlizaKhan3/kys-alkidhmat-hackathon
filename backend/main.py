"""Run: uvicorn backend.main:app --port 8000   (from the stand-in/ folder)"""
import json, csv, time, os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.engine import ask, get_kb, ROOT
from backend.voice import router as voice_router, whisper_ready


def _load_dotenv():
    """Pull GROQ_API_KEY etc. from stand-in/.env without requiring python-dotenv."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

app = FastAPI(title="Stand-In: Chef Nisa · Smash & Sauce Kitchen")
app.include_router(voice_router)
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")
LOG = ROOT / "testing" / "conversation_log.jsonl"


class Q(BaseModel):
    question: str
    history: list | None = None  # optional [{q,a}, ...] for follow-ups like "its recipe"


@app.post("/ask")
def _ask(q: Q):
    r = ask(q.question, history=q.history)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(t=time.time(), q=q.question, **{k: r[k] for k in ("status", "score", "mode")}, ids=[s["id"] for s in r["sources"]])) + "\n")
    return r


@app.get("/profile")
def profile():
    kb = get_kb()
    return dict(kb["chef_profile"], escalation_topics=[dict(topic=t["topic"], reason=t["reason"]) for t in kb["escalation_topics"]],
                counts={k: len(kb[k]) for k in ("interview_entries", "rules", "preferences")})


@app.get("/voice/status")
def voice_status():
    return whisper_ready()


@app.get("/results")
def results():
    p = ROOT / "testing" / "evaluation_30q.csv"
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")
