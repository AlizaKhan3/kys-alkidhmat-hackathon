# Stand-In · Chef Nisa (Smash & Sauce Kitchen)

**Rocketathon Track 1** — a stand-in for one real chef: **Nisa** of Smash & Sauce Kitchen (aunt of Laiba).

She answers only from what she documented (interview + recipes + ops manual). Outside that scope she **escalates and says why**. No paid model required for core answers.

---

## Quick start

```bash
cd stand-in
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional — mic polish (Groq Whisper) + faster Neerja TTS path
export GROQ_API_KEY='gsk_...'      # or put it in a gitignored .env

python -m uvicorn backend.main:app --port 8000 --reload
```

Open **http://127.0.0.1:8000**

Copy `.env.example` → `.env` if you prefer file-based keys (`.env` is gitignored).

---

## What this is

| Piece | Detail |
|---|---|
| **Person** | Chef Nisa — smash beef burgers + Creamy Chicken Alfredo Pasta |
| **Consent** | Written consent on profile (`consent_confirmed: true`) |
| **Knowledge** | Verbatim retrieval from chef docs — not free-form LLM inventing recipes |
| **Limits** | Allergy, food safety, legal, off-menu → escalate with reason |
| **Presence** | Avatar + female voice (Neerja / browser female fallback) + mic |
| **Honesty** | Chef-reviewed 30Q sheet; failures kept visible in the UI |

---

## Knowledge sources (with consent)

| File | Role |
|---|---|
| `Smash_and_Sauce_QA_Manual.pdf` | Ops Q&A / rules |
| `Smash_and_Sauce_Kitchen_cleaned.txt` | Interview (EN) |
| `samshandsaucekitchen_romanurdu.txt` | Interview (Roman Urdu) |
| `Burger_Recipe.txt` | Measured smash-burger recipe |
| `CREAMY CHICKEN ALFREDO PASTA RECIPE.txt` | Alfredo pasta recipe |
| `extra Question_Answers.txt` | Troubleshooting Q&A |

Rebuild the knowledge base after editing sources:

```bash
python knowledge/build_kb.py
```

This writes `knowledge/kb.json` (~97 interview chunks, 13 rules, 7 escalation topics). The server hot-reloads when `kb.json` changes.

---

## How it decides (`backend/engine.py`)

1. **Manners / identity** — greetings, “who is Nisa?”, “what do you cook?”, “don’t speak too much”.
2. **Hard recipe routes** — pasta/burger recipe asks, boil-time, typo fixes (`paste` → `pasta`).
3. **Escalation first** — allergy, food safety, medical, legal, off-menu, off-topic.
4. **Retrieval** — IDF keyword match over interview + rules + preferences; prefer head overlap so weak matches don’t invent answers.
5. **Confidence** — strong documented match → **Confident**; too weak → **Escalated** (no bluffing).
6. **Sources** — every kitchen answer can show provenance (tap Source).
7. **Short context** — last few chat turns resolve follow-ups like “also its recipe” (browser memory only; cleared on refresh).

Optional LLM rephrase (Ollama / Groq) is **off by default**. If enabled, any reply with numbers not in retrieved chef text is discarded.

---

## Voice & mic

| Feature | How |
|---|---|
| **Speak answers** | Toggle in the left panel (default ON) |
| **TTS** | Prefer `en-IN-NeerjaNeural` via `/speak`; if slow (>~1.5s) → female browser voice |
| **Mic** | Tap 🎤 → speak → ⏹. Live captions + optional Groq Whisper polish |
| **Barge-in** | Tap mic while she talks to cut in; “please stop” handled as interrupt |

Without `GROQ_API_KEY`, mic still works via browser live captions; Whisper polish is skipped.

---

## Demo script (judges · ~2 minutes)

1. Intro: Chef **Nisa**, consent, Smash & Sauce specialty.  
2. Burger: *What goes into your burger sauce?* → source panel.  
3. Pasta: *Share the creamy pasta recipe* → Creamy Chicken Alfredo overview.  
4. Escalate: *Someone has a peanut allergy* → escalate + why.  
5. Honesty note: chef review tally in the sidebar.

Suggested prompts that work well:

- Who is Nisa? / What do you cook?  
- What is your beef mince formula?  
- Burger recipe / How long do you boil pasta?  
- My pasta sauce became too thick  
- Can you make a steak?  

---

## Chef review (honesty note)

`testing/evaluation_30q.csv` — chef-approved:

| Mark | Count |
|---|---|
| Agree | 24 |
| Disagree | 2 |
| Should have escalated | 4 |

Disagreements kept on record (e.g. historical retrieval misses). Rebuild sheet with:

```bash
python testing/run_eval.py
```

---

## Project layout

```
backend/
  main.py          # FastAPI: /ask /profile /results /speak /transcribe
  engine.py        # escalation + retrieval + context follow-ups
  voice.py         # Groq Whisper STT + edge-tts TTS
frontend/
  index.html       # Stand-In room UI
  assets/          # Chef avatar frames
knowledge/
  kb.json          # Built knowledge base
  build_kb.py      # Rebuild from chef docs
  PROVENANCE.json  # Software / source provenance notes
testing/
  evaluation_30q.csv
  run_eval.py
```

---

## Submission checklist (Track 1)

- [x] Real named person + written consent  
- [x] Knowledge base with sources on answers  
- [x] Escalation with reasons  
- [x] Presence (face + voice + mic)  
- [x] Honesty note (30Q chef marks, failures included)  
- [ ] Bill of provenance — fill salvaged hardware in `knowledge/PROVENANCE.json` before live judging  

Software stack is free/open: FastAPI, keyword retrieval, edge-tts, optional Groq free tier / local Ollama.
