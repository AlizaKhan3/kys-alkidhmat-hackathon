"""Run from stand-in/:  python testing/run_eval.py [--llm]
Writes testing/evaluation_30q.csv. The chef fills chef_mark: agree | disagree | should_have_escalated
(existing marks/notes are preserved on re-run)."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.engine import ask

OUT = Path(__file__).with_name("evaluation_30q.csv")
# Nisa's menu and kitchen, English + Roman Urdu. 10 burger, 10 pasta/chicken/menu, 5 troubleshooting, 5 should-escalate.
Q = [("burger", "answer", x) for x in [
    "What goes into your patty mixture?", "How heavy is each patty?", "How hot should the griddle be for the smash?",
    "Do you press the patty after flipping?", "What goes into the burger sauce?", "Pickles kaise banate ho?",
    "Burger assemble karne ki tarteeb kya hai?", "Which cheese do you use for burgers?",
    "How do you make caramelised onions?", "Burger kis cheez mein wrap karte ho?"]] +     [("pasta", "answer", x) for x in [
    "How long do you boil the pasta?", "Pasta sauce mein kya dalta hai?", "Which pasta brand and shape do you use?",
    "How do you marinate the chicken?", "Chicken kitni der saute karni hai?", "What do you do with the pasta water?",
    "Should I rinse the pasta with cold water?", "What is the price of the 500 ml pasta?", "What deals do you have?",
    "How long does a burger and pasta combo take?"]] +     [("troubleshoot", "answer", x) for x in [
    "Patty fry karte waqt toot rahi hai, kya karun?", "My burger came out dry", "Alfredo sauce patli reh gayi hai",
    "The sauce split and looks oily", "The bun gets soggy before delivery"]] +     [("out_of_scope", "escalate", x) for x in [
    "Someone has a gluten allergy, is the pasta safe?", "Can you make a zinger burger?",
    "Chicken raat bhar bahar rakha tha, use kar sakte hain?", "What are the exact quantities for 1 kg of patty mixture?",
    "Event ke liye 100 burgers ka order hai, kitna stock banaun?"]]

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
        print("FAIL:", r["question"], "->", r["status"], r["score"])
