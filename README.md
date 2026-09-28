# Stand-In: Smash & Sauce Kitchen (Rocketathon, Track 1)

A rule-grounded stand-in for ONE real chef, **Chef Nisa** (owner, Smash & Sauce Kitchen). Answers only from her interview and QA manual, in English or Roman Urdu; escalates everything else and says why.

## Run (2 minutes, free, offline-capable)
    pip install -r requirements.txt
    uvicorn backend.main:app --port 8000        # open http://localhost:8000
    python testing/run_eval.py                  # builds the 30-question review sheet
Works with NO LLM (answers are the chef's own words, verbatim). Optional free phrasing:
- Local: install Ollama, `ollama pull llama3.1:8b` (auto-detected). Or Groq free tier: `set GROQ_API_KEY=...`
- Guard: if the LLM writes any number not present in retrieved chef content, it is discarded and the verbatim answer is used.
- Use `python testing/run_eval.py --llm` to score the LLM path too.

## How it decides (backend/engine.py)
1. Escalation rules (regex, run FIRST): allergy/gluten, food safety, medical, complaints/legal, events/bulk/discounts, off-menu -> escalate with reason.
2. Retrieval: IDF-weighted keyword match over interview entries + IF/THEN rules + preferences + documented gaps (top 3). If the best match is a documented gap (e.g. exact 1 kg patty quantities), it escalates and shows why.
   The answer comes back in the language of the question (English or Roman Urdu).
3. Score >= 0.60 and documented -> **Confident**; 0.30-0.60 or "inferred" entry -> **Qualified**; below 0.30 -> **Escalated**.
4. Every answer shows source ids + the exact chef text + interview note (tap "Source").

## Knowledge base status
`knowledge/kb.json` is built from Chef Nisa's own material (copies in `knowledge/sources/`):
- `interview_en.txt` / `interview_roman_urdu.txt`: her interview transcript
- `QA_Manual.pdf`: her Smash & Sauce operations manual

Every entry carries a `source` (section or Q-number) and has English + Roman Urdu text. Written consent is signed (`consent_confirmed: true`).

Still to do with Nisa:
1. Record the rest of the interview (track asks for 3+ hours): 1 kg patty measurements, burger sauce quantities, chicken marinade quantities, masala fries. Until then these are `documented_gaps` and the bot escalates them.
2. Go through each entry with her; set `verified: true` on the ones she confirms.
3. Tune `CONFIDENT/QUALIFIED` in engine.py after review.
4. Run `python testing/run_eval.py`, have her fill `chef_mark` (agree / disagree / should_have_escalated). The sidebar shows the real tally automatically, failures included.
5. Note: the "30/30" routing check only proves the code routes correctly. It is NOT her Agree rate.

## Submission pieces
- **Bill of provenance**: device (old phone/laptop), mic/speaker, any salvaged part: what it was / where from / where it goes after. Software is free/open-source (FastAPI, Ollama/Llama or Groq free tier).
- **Honesty note (draft)**: Strong: escalation and traceable rules. Weak: keyword retrieval (no embeddings), basic avatar, small knowledge base. Paste chef review scores, including disagreements.
- Live demo order: intro+consent -> burger (patty mixture) -> troubleshooting in Roman Urdu (patty toot rahi hai) -> pasta -> documented gap (1 kg quantities, escalated) -> allergy/off-menu (escalated) -> open a Source panel -> show review results.
# kys-alkidhmat-hackathon
# kys-alkidhmat-hackathon
