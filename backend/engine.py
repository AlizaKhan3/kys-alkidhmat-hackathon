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
    r"allerg|gluten|recipe|temperature|season|oil|dough|noodle|meat|beef|pickle|fries|"
    r"alfredo|griddle|mince|mayo|chicken|packaging|foil|habitt)\b",
    re.I,
)


def toks(s):
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def _pronouns():
    """Return (subject, object, possessive) from chef_profile — default she/her from consent docs."""
    raw = (KB.get("chef_profile", {}).get("pronouns") or "she/her").lower()
    if raw.startswith("he"):
        return "he", "him", "his"
    if raw.startswith("they"):
        return "they", "them", "their"
    return "she", "her", "her"


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
    subj, obj, pos = _pronouns()
    be = "are" if subj == "they" else "is"
    intro = (
        f"I'm the stand-in for {name} at {kitchen} — covering for {obj} while {subj} {be} not here. "
        f"I only speak from what {subj} taught me about smash burgers, pasta, and {pos} documented kitchen practice; "
        f"if {subj} didn't say it, I'll send you back to {obj}."
    )

    if _SALAAM.search(q) and len(q) < 80:
        return _manners_reply(f"Wa alaikum assalam! {intro} What would you like to ask?")
    if _WHO.search(q):
        return _manners_reply(
            f"{intro} I'm not the chef {obj}self and I'm not a free-roaming AI — "
            f"just {pos} kitchen stand-in for the questions {subj} prepared me for."
        )
    if _HOWARE.search(q) and len(q) < 60:
        return _manners_reply(
            f"I'm doing well, thank you — ready to help the line while {name} is away. "
            f"Ask me anything {subj} covered about burgers or pasta."
        )
    if _THANKS.search(q) and len(q) < 80:
        return _manners_reply(
            f"You're welcome. If something else comes up on burgers or pasta, I'm here — "
            f"and for anything {subj} didn't teach me, please ask {name} directly."
        )
    if _BYE.search(q) and len(q) < 60:
        return _manners_reply(
            f"Take care! Come back anytime with a kitchen question — "
            f"and give {name} my regards when you see {obj}."
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
        head = " ".join([
            e.get("question", ""), e.get("question_ru", ""),
            " ".join(e.get("tags", [])),
        ])
        body = " ".join(x for x in [e.get("chef_answer", ""), e.get("chef_answer_ru", "")] if x)
        out.append(dict(e, kind="interview", head=head, body=body, text=e["chef_answer"]))
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
    tot = sum(IDF(t) for t in qt) or 1.0
    scored = []
    for d in DOCS:
        head_hit = sum(IDF(t) for t in qt if t in d["h"])
        body_hit = sum(IDF(t) for t in qt if t in d["b"] and t not in d["h"])
        s = (head_hit + 0.45 * body_hit) / tot
        if s > 0:
            prec = sum(1 for t in qt if t in d["h"]) / max(len(qt), 1)
            kind_bonus = 0.04 if d["kind"] == "interview" else 0.0
            # Prefer entries whose question/tags actually name the ask (higher precision).
            rank = s * (0.55 + 0.45 * prec) + kind_bonus + 0.02 * prec
            scored.append((round(s, 3), d, rank, prec))
    scored.sort(key=lambda x: (-x[2], -x[3], x[1]["id"]))
    if scored:
        scored = [x for x in scored if x[0] >= 0.55 * scored[0][0]]
    return [(s, d) for s, d, _, _ in scored[:k]]


_LLM_REFUSAL_PHRASES = (
    "escalat",
    "ask the chef directly",
    "outside what the chef documented",
    "i can't answer this",
    "i cannot answer this",
    "please ask him",
    "please ask her",
    "please ask the chef",
    "ask him directly",
    "ask her directly",
)

# Map escalation topics → chef-authored reply entries (verbatim when present).
_ESC_ANSWER_IDS = {
    "E01": "Q31",  # allergen script from ops manual
    "E05": "Q32",  # polite off-menu refusal from ops manual
}


def _entry_by_id(eid):
    for e in KB.get("interview_entries", []):
        if e.get("id") == eid:
            return e
    return None


def _clean_chef_script(text):
    """Strip 'Respond politely:' / 'Escalate immediately and say:' wrappers."""
    t = (text or "").strip()
    t = re.sub(r'^(Respond politely|Escalate immediately and say)\s*:\s*', '', t, flags=re.I)
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        t = t[1:-1]
    return t.strip()


def check_escalation(q):
    """Match escalation topics. Explicit off-menu / safety patterns always win."""
    for t in KB["escalation_topics"]:
        if re.search(t["pattern"], q, re.I):
            return t
    return None


def _escalation_payload(esc):
    """Build an accurate escalated reply — prefer the chef's documented script + source."""
    name = KB["chef_profile"]["name"]
    reason = esc["reason"]
    eid = _ESC_ANSWER_IDS.get(esc["id"])
    entry = _entry_by_id(eid) if eid else None
    if entry:
        answer = _clean_chef_script(entry["chef_answer"])
        sources = [dict(id=entry["id"], kind="interview", source=entry.get("source", ""),
                        text=entry["chef_answer"], score=1.0)]
        return dict(status="escalated", reason=reason, sources=sources, score=0,
                    mode="rule", unverified=not entry.get("verified", False), answer=answer)
    return dict(
        status="escalated", reason=reason, sources=[], score=0, mode="rule", unverified=False,
        answer=f"{name} would want to handle this in person. {reason}",
    )


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
    """Hallucination guard: every number in the reply must appear in retrieved chef text."""
    src = " ".join(d["text"] for _, d in ctx)
    if not all(n in src for n in re.findall(r"\d+(?:\.\d+)?", text)):
        return False
    # Reject replies that invent cooking claims not supported by retrieved tokens.
    src_toks = set(toks(src))
    claim_toks = [t for t in toks(text) if t not in STOP and len(t) > 3]
    if not claim_toks:
        return False
    supported = sum(1 for t in claim_toks if t in src_toks)
    return supported / len(claim_toks) >= 0.72


def ask(q, use_llm=False):
    """Answer only from chef KB. LLM is off by default so we never invent kitchen facts."""
    q = (q or "").strip()
    name = KB["chef_profile"]["name"]
    subj, obj, pos = _pronouns()
    manners = check_manners(q)
    if manners:
        return manners
    greet = bool(_SALAAM.search(q) or (_HELLO.search(q) and len(q) < 120))
    esc = check_escalation(q)
    if esc:
        payload = _escalation_payload(esc)
        if greet:
            payload["answer"] = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + payload["answer"]
        return payload
    hits = retrieve(q)
    score = hits[0][0] if hits else 0
    if score < QUALIFIED:
        return dict(status="escalated", sources=[], score=score, mode="threshold", unverified=False,
                    reason="Outside what the chef documented in her interview and operations manual.",
                    answer=(f"{name} hasn't told me how {subj} would handle this, so I won't guess. "
                            f"Please ask {obj} directly."))
    # Only keep strong-enough neighbors; never stitch weak unrelated chunks into a fake answer.
    ctx = [h for h in hits if h[0] >= max(QUALIFIED, 0.75 * score)][:3]
    top = ctx[0][1]
    status = "confident" if score >= CONFIDENT and top["confidence"] == "documented" else "qualified"
    text, mode, reason = None, "verbatim", ""
    # Optional LLM rephrase — discarded unless fully grounded in retrieved chef text.
    if use_llm or os.getenv("STANDIN_USE_LLM") == "1":
        text = _llm(q, ctx)
        if text and _grounded(text, ctx):
            mode = "llm"
            lowered = text.lower()
            if any(p in lowered for p in _LLM_REFUSAL_PHRASES):
                status = "escalated"
                mode = "llm_refusal"
                reason = "Deferred by model to the chef."
        else:
            text = None
    if not text:
        # Verbatim: always the single top source (never hybridize two recipes).
        text = top["text"]
    if status == "qualified":
        text += (f" (Heads-up: {name} didn't address this exact case in the docs {subj} gave us; "
                 f"this is {pos} closest documented guidance.)")
    if greet:
        text = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + text
    return dict(status=status, answer=text, score=score, mode=mode, reason=reason,
                unverified=any(not d.get("verified", False) for _, d in ctx),
                sources=[dict(id=d["id"], kind=d["kind"], source=d["source"], text=d["text"], score=s) for s, d in ctx])
