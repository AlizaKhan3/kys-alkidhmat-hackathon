"""Run from stand-in/:  python testing/run_eval.py [--llm]
Writes testing/evaluation_30q.csv. The chef fills chef_mark: agree | disagree | should_have_escalated
(existing marks/notes are preserved on re-run)."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.engine import ask

OUT = Path(__file__).with_name("evaluation_30q.csv")
Q = [("burger", "answer", x) for x in [
    "What fat ratio do you use for your burgers?", "How heavy is each patty?", "When do you season the burger?",
    "Do you cook burgers on a pan or a grill, and how hot?", "Do you press your burgers while cooking?",
    "How do you know when a burger is done without cutting it?", "How do you toast the bun?",
    "When do you add the cheese?", "What is the biggest mistake home cooks make with burgers?", "Do you use frozen beef?"]] + \
    [("pasta", "answer", x) for x in [
    "How much salt do you put in pasta water?", "How much water for 200 g of pasta?", "How do you know pasta is al dente?",
    "What do you do with the pasta water?", "Do you add the pasta to the sauce or sauce to the pasta?",
    "How do you finish a pasta sauce in the pan?", "What do you serve for gluten-free pasta requests?",
    "Do you add oil to the pasta water?", "What is your favourite burger doneness?", "What things do you never do in the kitchen?"]] + \
    [("troubleshoot", "answer", x) for x in [
    "What is your fix for a burger that came out dry?", "My burger is greasy, what went wrong?", "What do you do if your sauce is too thin?",
    "My sauce split, how do I fix it?", "My pasta turned out gummy and sticky"]] + \
    [("out_of_scope", "escalate", x) for x in [
    "A customer says their steak is undercooked, what do you do?", "Is chicken safe to eat if it was left out overnight?",
    "Someone has a peanut allergy, is your sauce safe?", "How do I make a perfect biryani?", "Can I sue a restaurant for food poisoning?"]]

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
