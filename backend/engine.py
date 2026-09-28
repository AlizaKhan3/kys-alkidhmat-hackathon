"""Stand-In engine (stdlib only). Flow: manners -> escalation -> retrieval -> confidence -> phrasing."""
import json, re, math, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = json.loads((ROOT / "knowledge" / "kb.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "system_prompt.md").read_text(encoding="utf-8")
STOP = set("the a an is are do you your i to of for in on it how what when why my me and or with be if can should does did that this so we went wrong tell about please give say".split())
CONFIDENT, QUALIFIED = 0.60, 0.30  # thresholds: tune after the 30-question review

# Social / manners intents — answered in-role without inventing kitchen knowledge.
_SALAAM = re.compile(
    r"\b(as+[- ]?sal+a+m(?:u|o)?[- ]?(?:alaikum|alaykum|aleikum)?|"
    r"sal+a+m(?:u|o)?[- ]?(?:alaikum|alaykum|aleikum)?|"
    r"assalamualaikum)\b",
    re.I,
)
_HELLO = re.compile(r"\b(hi|hello|hey|yo|good\s*(morning|afternoon|evening|night)|aoa)\b", re.I)
_THANKS = re.compile(r"\b(thanks|thank\s*you|thx|shukriya|shukria|jazak(?:allah)?(?:\s*khair)?)\b", re.I)
_BYE = re.compile(r"\b(bye|goodbye|good\s*night|see\s*you|allah\s*hafiz|khuda\s*hafiz|take\s*care)\b", re.I)
_WHO = re.compile(r"\b(who\s+are\s+you|what\s+are\s+you|introduce\s+yourself|your\s+name|are\s+you\s+(?:a\s+)?(?:bot|ai|robot|human|real|the\s+chef))\b", re.I)
_HOWARE = re.compile(r"\b(how\s+are\s+you|how(?:'s|s|\s+is)\s+it\s+going|what'?s\s+up)\b", re.I)
_SORRY = re.compile(r"\b(sorry|apolog(?:y|ies|ise|ize)|my\s+bad)\b", re.I)
_HELP = re.compile(r"^\s*(help|can\s+you\s+help(?:\s+me)?|are\s+you\s+there|anybody\s+there)\s*[?.!]?\s*$", re.I)
_ACK = re.compile(
    r"^\s*(great|ok|okay|cool|nice|awesome|perfect|sweet|alright|all\s*right|got\s*it|"
    r"makes\s*sense|sounds\s*good|good|fine|sure|yep|yeah|yes|right|understood|"
    r"excellent|wonderful|lovely|nice\s*one|theek\s*hai|achha|acha)\s*[!.]*\s*$",
    re.I,
)
# Kitchen-ish leftovers → don't treat the whole message as pure manners.
_KITCHENISH = re.compile(
    r"\b(burger|patty|smash|pasta|sauce|salt|fat|ratio|cook|fry|grill|cheese|bun|steak|"
    r"allerg|gluten|recipe|temperature|season|oil|dough|noodle|meat|beef)\b",
    re.I,
)


def toks(s):
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def _manners_reply(answer):
    return dict(status="confident", reason="", sources=[], score=1.0, mode="manners",
                unverified=False, answer=answer)


def check_manners(q):
    """Warm, in-role social replies. Pure greetings only — kitchen questions still retrieve."""
    q = (q or "").strip()
    if not q or _KITCHENISH.search(q):
        return None
    profile = KB["chef_profile"]
    name, kitchen = profile["name"], profile["kitchen"]
    intro = (
        f"I'm the stand-in for {name} at {kitchen} — covering for him while he's not here. "
        f"I only speak from what he taught me about smash burgers and pasta sauces; "
        f"if he didn't say it, I'll send you back to him."
    )

    if _SALAAM.search(q) and len(q) < 80:
        return _manners_reply(f"Wa alaikum assalam! {intro} What would you like to ask?")
    if _WHO.search(q):
        return _manners_reply(
            f"{intro} I'm not the chef himself and I'm not a free-roaming AI — "
            f"just his kitchen stand-in for the questions he prepared me for."
        )
    if _HOWARE.search(q) and len(q) < 60:
        return _manners_reply(
            f"I'm doing well, thank you — ready to help the line while {name} is away. "
            f"Ask me anything he covered about burgers or pasta."
        )
    if _THANKS.search(q) and len(q) < 80:
        return _manners_reply(
            f"You're welcome. If something else comes up on burgers or pasta, I'm here — "
            f"and for anything he didn't teach me, please ask {name} directly."
        )
    if _BYE.search(q) and len(q) < 60:
        return _manners_reply(
            f"Take care! Come back anytime with a kitchen question — "
            f"and give {name} my regards when you see him."
        )
    if _SORRY.search(q) and len(q) < 80:
        return _manners_reply(
            f"No worries at all. Ask again whenever you're ready — "
            f"I'll stick to what {name} actually told us."
        )
    if _HELP.search(q):
        return _manners_reply(
            f"Yes — I'm here. {intro} Try a burger or pasta question, or say Assalam o Alaikum anytime."
        )
    if _ACK.search(q):
        return _manners_reply(
            f"Glad that helps. Whenever you're ready, ask another burger or pasta question — "
            f"I'll stick to what {name} taught me."
        )
    if _HELLO.search(q) and len(q) < 40:
        return _manners_reply(f"Hello! {intro} What can I help you with?")
    return None


def _docs():
    out = []
    for e in KB["interview_entries"]:
        out.append(dict(e, kind="interview", head=e["question"] + " " + " ".join(e.get("tags", [])),
                        body=e["chef_answer"], text=e["chef_answer"]))
    for r in KB["rules"]:
        out.append(dict(r, kind="rule", head=r["condition"] + " " + " ".join(r.get("tags", [])),
                        body=r["chef_action"], text=f"If {r['condition']}: {r['chef_action']}",
                        source=r.get("source", "rule"), confidence=r.get("confidence", "documented")))
    for p in KB["preferences"]:
        out.append(dict(p, kind="preference", head=p["item"] + " " + " ".join(p.get("tags", [])),
                        body=p["chef_stance"], text=f"{p['item']}: {p['chef_stance']}",
                        source=p.get("source", "preference"), confidence=p.get("confidence", "documented")))
    for d in out:
        d["h"], d["b"] = set(toks(d["head"])), set(toks(d["body"]))
    return out


DOCS = _docs()
_df = {}
for _d in DOCS:
    for _t in _d["h"] | _d["b"]:
        _df[_t] = _df.get(_t, 0) + 1
IDF = lambda t: math.log(1 + len(DOCS) / (1 + _df.get(t, 0)))


def retrieve(q, k=3):
    qt = set(toks(q))
    if not qt:
        return []
    tot = sum(IDF(t) for t in qt)
    scored = []
    for d in DOCS:
        s = sum(IDF(t) * (1 if t in d["h"] else 0.5 if t in d["b"] else 0) for t in qt) / tot
        if s > 0:  # tie-break: prefer docs whose head is mostly covered by the query (precision)
            prec = sum(1 for t in d["h"] if t in qt) / max(len(d["h"]), 1)
            scored.append((round(s, 3), d, s * (0.7 + 0.3 * prec)))
    scored.sort(key=lambda x: -x[2])
    if scored:
        scored = [x for x in scored if x[0] >= 0.6 * scored[0][0]]  # drop weak secondary sources
    return [(s, d) for s, d, _ in scored[:k]]


def check_escalation(q):
    for t in KB["escalation_topics"]:
        if re.search(t["pattern"], q, re.I):
            return t
    return None


def _llm(q, ctx):
    """Free options only: local Ollama, or Groq free tier via GROQ_API_KEY. Returns None if unavailable."""
    ctx_txt = "\n".join(f"[{d['id']}] {d['text']}" for _, d in ctx)
    msgs = [{"role": "system", "content": PROMPT.replace("[Chef Name]", KB["chef_profile"]["name"])},
            {"role": "user", "content": f"RETRIEVED CHEF KNOWLEDGE:\n{ctx_txt}\n\nQUESTION: {q}"}]
    try:
        if os.getenv("GROQ_API_KEY"):
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                json.dumps({"model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), "messages": msgs, "temperature": 0.1}).encode(),
                {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["GROQ_API_KEY"]})
            return json.load(urllib.request.urlopen(req, timeout=12))["choices"][0]["message"]["content"].strip()
        req = urllib.request.Request(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat",
            json.dumps({"model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"), "messages": msgs, "stream": False,
                        "options": {"temperature": 0.1}}).encode(), {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=25))["message"]["content"].strip()
    except Exception:
        return None


def _grounded(text, ctx):
    """Hallucination guard: every number in the reply must appear in retrieved content."""
    src = " ".join(d["text"] for _, d in ctx)
    return all(n in src for n in re.findall(r"\d+(?:\.\d+)?", text))


def ask(q, use_llm=True):
    q = (q or "").strip()
    name = KB["chef_profile"]["name"]
    manners = check_manners(q)
    if manners:
        return manners
    greet = bool(_SALAAM.search(q) or (_HELLO.search(q) and len(q) < 120))
    esc = check_escalation(q)
    if esc:
        return dict(status="escalated", reason=esc["reason"], sources=[], score=0, mode="rule", unverified=False,
                    answer=f"{name} would want to handle this in person. {esc['reason']}")
    hits = retrieve(q)
    score = hits[0][0] if hits else 0
    if score < QUALIFIED:
        return dict(status="escalated", sources=[], score=score, mode="threshold", unverified=False,
                    reason="Outside what the chef documented in his interview.",
                    answer=f"{name} hasn't told me how he'd handle this, so I won't guess. Please ask him directly.")
    ctx = [h for h in hits if h[0] >= QUALIFIED][:3]
    top = ctx[0][1]
    status = "confident" if score >= CONFIDENT and top["confidence"] == "documented" else "qualified"
    text, mode = None, "verbatim"
    if use_llm:
        text = _llm(q, ctx)
        if text and _grounded(text, ctx):
            mode = "llm"
        else:
            text = None
    if not text:
        text = " ".join(d["text"] for _, d in ctx[:2 if status == "qualified" else 1])
    if status == "qualified":
        text += " (Heads-up: the chef didn't address this exact case; this is his closest documented guidance.)"
    if greet:
        text = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + text
    return dict(status=status, answer=text, score=score, mode=mode, reason="",
                unverified=any(not d.get("verified", False) for _, d in ctx),
                sources=[dict(id=d["id"], kind=d["kind"], source=d["source"], text=d["text"], score=s) for s, d in ctx])
