"""Run: uvicorn backend.main:app --port 8000   (from the stand-in/ folder)"""
import json, csv, time
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.engine import ask, KB, ROOT

app = FastAPI(title="Stand-In: Smash & Sauce Kitchen")
LOG = ROOT / "testing" / "conversation_log.jsonl"


class Q(BaseModel):
    question: str


@app.post("/ask")
def _ask(q: Q):
    r = ask(q.question)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(t=time.time(), q=q.question, **{k: r[k] for k in ("status", "score", "mode")}, ids=[s["id"] for s in r["sources"]])) + "\n")
    return r


@app.get("/profile")
def profile():
    return dict(KB["chef_profile"], escalation_topics=[dict(topic=t["topic"], reason=t["reason"]) for t in KB["escalation_topics"]],
                counts={k: len(KB[k]) for k in ("interview_entries", "rules", "preferences")})


@app.get("/results")
def results():
    p = ROOT / "testing" / "evaluation_30q.csv"
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")
