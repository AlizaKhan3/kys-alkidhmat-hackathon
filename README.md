# Stand-In: Smash & Sauce Kitchen (Rocketathon, Track 1)

A rule-grounded stand-in for ONE real chef. Answers only from his interview; escalates everything else and says why.

## Run (2 minutes, free, offline-capable)
    pip install -r requirements.txt
    uvicorn backend.main:app --port 8000        # open http://localhost:8000
    python testing/run_eval.py                  # builds the 30-question review sheet
Works with NO LLM (answers are the chef's own words, verbatim). Optional free phrasing:
- Local: install Ollama, `ollama pull llama3.1:8b` (auto-detected). Or Groq free tier: `set GROQ_API_KEY=...`
- Guard: if the LLM writes any number not present in retrieved chef content, it is discarded and the verbatim answer is used.
- Use `python testing/run_eval.py --llm` to score the LLM path too.

## How it decides (backend/engine.py)
1. Escalation rules (regex, run FIRST): allergy, food safety, medical, legal, off-topic -> escalate with reason.
2. Retrieval: IDF-weighted keyword match over interview entries + IF/THEN rules + preferences (top 3).
3. Score >= 0.60 and documented -> **Confident**; 0.30-0.60 or "inferred" entry -> **Qualified**; below 0.30 -> **Escalated**.
4. Every answer shows source ids + the exact chef text + interview note (tap "Source").

## BEFORE THE DEMO: what you MUST do (this is 80% of the score)
`knowledge/kb.json` currently holds **SAMPLE entries written by us so the system runs. They are NOT the chef's views.**
1. Get the chef's **written consent**; set `consent_confirmed: true` and fill name/bio in `chef_profile`.
2. Interview 3+ hours (see guide section 6). Replace every SAMPLE entry with his real words; put timestamp/note in `source`; set `verified: true` after he confirms it.
3. Turn each troubleshooting answer into a rule (`rules`), each "never/always" into `preferences`, each "ask a doctor/officer" into `escalation_topics`.
4. Tune `CONFIDENT/QUALIFIED` in engine.py after review.
5. Run `python testing/run_eval.py`, have the chef fill `chef_mark` (agree / disagree / should_have_escalated). The sidebar shows the real tally automatically, failures included.
6. Note: the "30/30" routing check only proves the code works on sample data. It is NOT the chef's Agree rate.

## Submission pieces
- **Bill of provenance**: device (old phone/laptop), mic/speaker, any salvaged part: what it was / where from / where it goes after. Software is free/open-source (FastAPI, Ollama/Llama or Groq free tier).
- **Honesty note (draft)**: Strong: escalation and traceable rules. Weak: keyword retrieval (no embeddings), basic avatar, small knowledge base. Paste chef review scores, including disagreements.
- Live demo order: intro+consent -> burger -> troubleshooting -> pasta -> edge case (gluten-free, qualified) -> off-domain (steak, escalated) -> open a Source panel -> show review results.
# kys-alkidhmat-hackathon
# kys-alkidhmat-hackathon
