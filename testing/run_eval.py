"""Run from stand-in/:  python testing/run_eval.py [--llm]
Writes testing/evaluation_30q.csv. The chef fills chef_mark: agree | disagree | should_have_escalated
(existing marks/notes are preserved on re-run)."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.engine import ask

OUT = Path(__file__).with_name("evaluation_30q.csv")
# 30 questions covering PDF ops manual + interview transcripts.
Q = [("burger", "answer", x) for x in [
    "What is your exact beef mince formula?",
    "What are the patty weights for Classic and Double Smash Burgers?",
    "How do you prepare your beef patty mixture?",
    "What goes into your burger sauce?",
    "Do you press the patty after flipping?",
    "How do you make homemade pickles?",
    "What cheese do you use for burgers?",
    "What is the assembly order for a Classic Smash Burger?",
    "Why does the patty break while frying?",
    "What temperature should the griddle be?"]] + \
    [("pasta", "answer", x) for x in [
    "Which pasta brand and shape do you use?",
    "How long do you boil the pasta?",
    "How do you marinate the chicken?",
    "How do you build the Signature Alfredo white sauce?",
    "What is the price of a Classic Smash Burger?",
    "What packaging do you use for burgers and pasta?",
    "What are the Never rules in the kitchen?",
    "How do you manage lunchtime orders during university?",
    "Where do you buy ingredients now?",
    "Do you offer masala fries?"]] + \
    [("troubleshoot", "answer", x) for x in [
    "The burger patty turned out dry — what went wrong?",
    "The Alfredo sauce is thin and watery — how do you fix it?",
    "The Alfredo sauce split — how do you recover it?",
    "Caramelized onions smell bitter — can they be salvaged?",
    "What did you learn from the Habitt stall loss?"]] + \
    [("out_of_scope", "escalate", x) for x in [
    "A customer wants a beef steak medium rare, can you make it?",
    "Is chicken safe to eat if it was left out overnight?",
    "Someone has a peanut allergy, is your sauce safe?",
    "Give me the exact gram measurements for your 1 kg patty mix",
    "Can I sue a restaurant for food poisoning?"]]

old = {}
if OUT.exists():
    old = {r["question"]: r for r in csv.DictReader(OUT.open(encoding="utf-8"))}
rows, ok = [], 0
for i, (g, exp, q) in enumerate(Q, 1):
    r = ask(q, use_llm="--llm" in sys.argv)
    got = "escalate" if r["status"] == "escalated" else "answer"
    ok += got == exp
    p = old.get(q, {})
    rows.append(dict(id=i, group=g, question=q, expected=exp, status=r["status"], score=r["score"], mode=r["mode"],
                     answer=r["answer"], sources=";".join(s["id"] for s in r["sources"]),
                     auto_check="PASS" if got == exp else "FAIL", chef_mark=p.get("chef_mark", ""), notes=p.get("notes", "")))
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(f"routing check: {ok}/{len(Q)} behaved as designed (answer vs escalate). Chef review still required.")
for r in rows:
    if r["auto_check"] == "FAIL":
        print("FAIL:", r["question"], "->", r["status"], r["score"], r["sources"])
