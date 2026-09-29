"""Stand-In engine (stdlib only). Flow: manners -> escalation -> retrieval -> confidence -> phrasing."""
import json, re, math, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_KB_PATH = ROOT / "knowledge" / "kb.json"
_KB_MTIME = None
KB = {}


def get_kb():
    """Hot-reload kb.json when it changes so profile/name updates without a full restart."""
    global KB, _KB_MTIME, DOCS, IDF, _df
    mtime = _KB_PATH.stat().st_mtime
    if not KB or _KB_MTIME != mtime:
        KB = json.loads(_KB_PATH.read_text(encoding="utf-8"))
        _KB_MTIME = mtime
        # Rebuild retrieval index whenever knowledge changes.
        if "DOCS" in globals() and callable(globals().get("_docs")):
            DOCS = _docs()
            _df = {}
            for _d in DOCS:
                for _t in _d["h"] | _d["b"]:
                    _df[_t] = _df.get(_t, 0) + 1
            IDF = lambda t: math.log(1 + len(DOCS) / (1 + _df.get(t, 0)))
    return KB


get_kb()
PROMPT = (ROOT / "system_prompt.md").read_text(encoding="utf-8")
STOP = set("the a an is are do you your i to of for in on it how what when why my me and or with be if can should does did that this so we went wrong tell about please give say share dont don't too much".split())
# Raise floor so weak keyword noise (0.3–0.5) cannot invent wrong kitchen advice.
CONFIDENT, QUALIFIED = 0.62, 0.52
BRIEF_MODE = False  # set by "don't speak too much" — shorter spoken answers only

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
_WHO_CHEF = re.compile(
    r"\b(?:who(?:'|\u2019)?s|who\s+is)\s+(?:nisa|the\s+chef|chef\s+nisa)|"
    r"tell\s+me\s+about\s+(?:nisa|the\s+chef|chef\s+nisa)|"
    r"what(?:'|\u2019)?s\s+nisa|what\s+is\s+nisa\b",
    re.I,
)
_STOP = re.compile(
    r"^\s*(?:please\s+)?(?:stop|wait|hold\s+on|hold\s+up|hang\s+on|cancel|never\s*mind|nvm|"
    r"shut\s*up|quiet|silence|enough|bas\s+karo|ruk\s+jao|chup)(?:\s+please)?\s*[.!]?\s*$|"
    r"\b(?:please\s+stop|stop\s+talking|stop\s+speaking|can\s+you\s+stop)\b",
    re.I,
)
_HOWARE = re.compile(r"\b(how\s+are\s+you|how(?:'s|s|\s+is)\s+it\s+going|what'?s\s+up)\b", re.I)
_SORRY = re.compile(r"\b(sorry|apolog(?:y|ies|ise|ize)|my\s+bad)\b", re.I)
_HELP = re.compile(r"^\s*(help|can\s+you\s+help(?:\s+me)?|are\s+you\s+there|anybody\s+there)\s*[?.!]?\s*$", re.I)
_ACK = re.compile(
    r"^\s*(great|ok|okay|cool|nice|awesome|perfect|sweet|alright|all\s*right|got\s*it|"
    r"makes\s*sense|sounds\s*good|good|fine|sure|yep|yeah|yes|right|understood|"
    r"excellent|wonderful|lovely|nice\s*one|theek\s*hai|achha|acha)\s*[!.]*\s*$",
    re.I,
)
# Menu / specialty overview — must beat retrieval or "what do you cook?" becomes a random recipe step.
_WHAT_COOK = re.compile(
    r"\b(?:what\s+do\s+you\s+(?:cook|make|serve|offer|prepare|sell)|"
    r"what\s+(?:can|do)\s+you\s+(?:cook|make|serve)|"
    r"what\s+(?:are\s+you|is\s+(?:nisa|she|the\s+chef))\s+(?:cook|making|known)|"
    r"what(?:'s|\s+is)\s+(?:on\s+)?(?:your|the)\s+menu|"
    r"what\s+does\s+(?:nisa|she|the\s+chef)\s+(?:cook|make|serve)|"
    r"tell\s+me\s+what\s+(?:you|nisa|she)\s+(?:cook|make|serve)|"
    r"(?:your|nisa(?:'s)?)\s+(?:specialty|speciality|signature|dishes?|menu))\b",
    re.I,
)
_BRIEF = re.compile(
    r"(?:don'?t|do\s+not|pls|please)?\s*(?:speak|talk|say)\s+(?:too\s+)?(?:much|long)|"
    r"\bbe\s+brief\b|\bshort\s+answers?\b|\bkeep\s+it\s+short\b|\bless\s+talking\b|"
    r"\bstop\s+rambling\b|\bconcise\b",
    re.I,
)
_PASTA_RECIPE = re.compile(
    r"\b(?:creamy\s+)?(?:chicken\s+)?(?:alfredo\s+)?(?:pasta|paste)\s+recipe|"
    r"\brecipe\s+(?:of|for)\s+(?:creamy\s+)?(?:chicken\s+)?(?:alfredo\s+)?(?:pasta|paste)|"
    r"\b(?:share|give|tell|show|send).{0,24}(?:pasta|paste|alfredo).{0,12}recipe|"
    r"\b(?:how\s+(?:do\s+you\s+)?(?:make|cook|prepare)\s+(?:the\s+)?(?:creamy\s+)?(?:chicken\s+)?(?:alfredo\s+)?(?:pasta|paste))\b|"
    r"\balfredo\b.*\brecipe\b|\brecipe\b.*\balfredo\b|"
    r"\bpasta\b.*\brecipe\b|\brecipe\b.*\bpasta\b",
    re.I,
)
_BOIL_PASTA = re.compile(
    r"\b(?:how\s+long|kitni\s+der|boil(?:ing)?\s+time|minutes?).{0,40}\b(?:pasta|paste|penne)\b|"
    r"\b(?:pasta|paste|penne).{0,40}\b(?:boil|boiling|al\s*dente)\b|"
    r"\bhow\s+(?:do\s+you\s+)?boil\s+(?:the\s+)?(?:pasta|paste|penne)\b",
    re.I,
)
_BURGER_RECIPE = re.compile(
    r"\b(?:smash\s+)?(?:beef\s+)?burger\s+recipe|"
    r"\brecipe\s+(?:of|for)\s+(?:the\s+)?(?:smash\s+)?(?:beef\s+)?burger|"
    r"\b(?:share|give|tell|show|send).{0,24}burger.{0,12}recipe|"
    r"\bhow\s+(?:do\s+you\s+)?(?:make|cook|prepare)\s+(?:a\s+|the\s+)?(?:smash\s+)?burger\b",
    re.I,
)
_GREET_PREFIX = re.compile(
    r"^\s*(?:(?:hi|hello|hey|yo|aoa|assalam\s*o?\s*alaikum|salaam)[,!]?\s*)+"
    r"(?:(?:chef\s+)?nisa[,!]?\s*)?",
    re.I,
)
# Kitchen-ish leftovers → don't treat the whole message as pure manners.
_KITCHENISH = re.compile(
    r"\b(burger|patty|smash|pasta|sauce|salt|fat|ratio|cook|fry|grill|cheese|bun|steak|"
    r"allerg|gluten|recipe|temperature|season|oil|dough|noodle|meat|beef|pickle|fries|"
    r"alfredo|griddle|mince|mayo|chicken|packaging|foil|habitt|menu|specialty)\b",
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


def _normalize_q(q):
    """Fix common typos / speech errors before retrieval."""
    q = (q or "").strip()
    reps = (
        (r"\bpaste\b", "pasta"),
        (r"\bcremy\b", "creamy"),
        (r"\balferedo\b", "alfredo"),
        (r"\balferdo\b", "alfredo"),
        (r"\brecep(e|ie)\b", "recipe"),
        (r"\bburgeres\b", "burgers"),
        (r"\bdon t\b", "don't"),
    )
    for pat, rep in reps:
        q = re.sub(pat, rep, q, flags=re.I)
    return q


def _force_entry(eid, score=1.0):
    e = _entry_by_id(eid)
    if not e:
        return None
    text = e.get("chef_answer") or e.get("chef_action") or ""
    return dict(
        status="confident", reason="", score=score, mode="verbatim", unverified=not e.get("verified", False),
        answer=text,
        sources=[dict(id=e["id"], kind="interview", source=e.get("source", ""), text=text, score=score)],
    )


def _menu_reply(q):
    """Profile specialty: beef smash burgers + Alfredo pasta at Smash & Sauce."""
    profile = KB["chef_profile"]
    name, kitchen = profile["name"], profile["kitchen"]
    specialty = profile.get("specialty") or "smash beef burgers and Signature Alfredo pasta"
    greet = "Hello! " if _HELLO.search(q) or _SALAAM.search(q) else ""
    if _SALAAM.search(q):
        greet = "Wa alaikum assalam! "
    answer = (
        f"{greet}At {kitchen}, {name} cooks smash beef burgers and Creamy Chicken Alfredo Pasta"
        f" — {specialty}. Ask for the burger recipe or the Alfredo pasta recipe for full steps."
    )
    return _manners_reply(answer)


def check_manners(q):
    """Warm, in-role social replies. Pure greetings only — kitchen questions still retrieve."""
    global BRIEF_MODE
    q = (q or "").strip()
    if not q:
        return None
    if _BRIEF.search(q) and not _PASTA_RECIPE.search(q) and not _BURGER_RECIPE.search(q):
        BRIEF_MODE = True
        return _manners_reply(
            "Got it — I'll keep answers short. Ask a burger or pasta question whenever you're ready."
        )
    if _WHAT_COOK.search(q):
        return _menu_reply(q)
    if _KITCHENISH.search(q):
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
    if _STOP.search(q):
        return _manners_reply("Okay — I've stopped. I'm listening. Go ahead.")
    if _WHO_CHEF.search(q):
        rel = (profile.get("relationship") or "").strip()
        bio = (profile.get("bio") or "").strip()
        bits = [f"{name} is the chef this stand-in represents at {kitchen}."]
        if rel:
            bits.append(f"She is the {rel[0].lower() + rel[1:]}." if rel.lower().startswith("aunt") else f"She is {rel}.")
        if bio:
            bits.append(bio)
        bits.append(f"I answer only from what {name} documented — burgers, pasta, and kitchen practice — and escalate anything else back to her.")
        return _manners_reply(" ".join(bits))
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
    ql = q.lower()
    pasta_ask = bool(re.search(r"\b(pasta|paste|alfredo|penne)\b", ql))
    burger_ask = bool(re.search(r"\b(burger|patty|smash|mince)\b", ql))
    recipe_ask = "recipe" in ql or "how" in qt
    scored = []
    for d in DOCS:
        head_hit = sum(IDF(t) for t in qt if t in d["h"])
        body_hit = sum(IDF(t) for t in qt if t in d["b"] and t not in d["h"])
        s = (head_hit + 0.35 * body_hit) / tot
        if s <= 0:
            continue
        prec = sum(1 for t in qt if t in d["h"] or t in d["b"]) / max(len(qt), 1)
        head_prec = sum(1 for t in qt if t in d["h"]) / max(len(qt), 1)
        kind_bonus = 0.04 if d["kind"] == "interview" else 0.0
        eid = d.get("id", "")
        # Prefer dedicated recipe docs over loose extra-Q&A when asking for recipes.
        if recipe_ask and eid.startswith(("AP", "BR", "Q")):
            kind_bonus += 0.12
        if pasta_ask and (eid.startswith("AP") or d.get("category") == "pasta"):
            kind_bonus += 0.18
        if burger_ask and (eid.startswith("BR") or d.get("category") == "burger"):
            kind_bonus += 0.18
        # Downrank weak meta Q&A when the ask is clearly a recipe.
        if recipe_ask and eid.startswith("XQ") and head_prec < 0.35:
            kind_bonus -= 0.25
        rank = s * (0.45 + 0.55 * head_prec) + kind_bonus + 0.05 * prec
        scored.append((round(s, 3), d, rank, head_prec))
    scored.sort(key=lambda x: (-x[2], -x[3], x[1]["id"]))
    if scored:
        # Keep only neighbors close to the best rank — drops random weak hits.
        best = scored[0][2]
        scored = [x for x in scored if x[2] >= 0.72 * best]
    return [(s, d) for s, d, _, _ in scored[:k]]


def _entry_by_id(eid):
    for e in KB.get("interview_entries", []):
        if e.get("id") == eid:
            return e
    return None


# Map escalation topics → chef-authored reply entries (verbatim when present).
_ESC_ANSWER_IDS = {
    "E01": "Q31",  # allergen script from ops manual
    "E05": "Q32",  # polite off-menu refusal from ops manual
}


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


def ask(q, use_llm=False):
    """Answer only from chef KB. LLM is off by default so we never invent kitchen facts."""
    global BRIEF_MODE
    get_kb()
    q = _normalize_q(q)
    name = KB["chef_profile"]["name"]
    subj, obj, pos = _pronouns()
    manners = check_manners(q)
    if manners:
        return manners
    greet = bool(_SALAAM.search(q) or (_HELLO.search(q) and len(q) < 120))
    q_core = _GREET_PREFIX.sub("", q).strip() or q
    q_core = _normalize_q(q_core)

    # Hard routes — never invent from weak keyword noise.
    if _BOIL_PASTA.search(q_core) and not _PASTA_RECIPE.search(q_core):
        forced = _force_entry("I12") or _force_entry("AP01")
        if forced:
            if greet:
                forced["answer"] = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + forced["answer"]
            if BRIEF_MODE and len(forced["answer"]) > 280:
                forced["answer"] = forced["answer"][:280].rsplit(" ", 1)[0] + "…"
            return forced
    if _PASTA_RECIPE.search(q_core):
        forced = _force_entry("AP00")
        if forced:
            if greet:
                forced["answer"] = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + forced["answer"]
            if BRIEF_MODE and len(forced["answer"]) > 280:
                forced["answer"] = forced["answer"][:280].rsplit(" ", 1)[0] + "…"
            return forced
    if _BURGER_RECIPE.search(q_core):
        forced = _force_entry("BR00")
        if forced:
            if greet:
                forced["answer"] = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + forced["answer"]
            if BRIEF_MODE and len(forced["answer"]) > 280:
                forced["answer"] = forced["answer"][:280].rsplit(" ", 1)[0] + "…"
            return forced

    esc = check_escalation(q_core)
    if esc:
        payload = _escalation_payload(esc)
        if greet:
            payload["answer"] = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + payload["answer"]
        return payload

    hits = retrieve(q_core)
    if not hits:
        return dict(status="escalated", sources=[], score=0, mode="threshold", unverified=False,
                    reason="Outside what the chef documented in her interview and operations manual.",
                    answer=(f"{name} hasn't told me how {subj} would handle this, so I won't guess. "
                            f"Please ask {obj} directly."))

    qt = set(toks(q_core))

    def head_prec(doc):
        if not qt:
            return 0.0
        return sum(1 for t in qt if t in doc.get("h", set())) / max(len(qt), 1)

    # Prefer HEAD overlap so "how long … pasta" does not become cheese-melt timing.
    hits = sorted(hits, key=lambda h: (-head_prec(h[1]), -h[0]))
    score = hits[0][0]
    hp = head_prec(hits[0][1])

    if score < 0.45 or (score < CONFIDENT and hp < 0.28):
        return dict(status="escalated", sources=[], score=score, mode="threshold", unverified=False,
                    reason="Closest match was too weak to stand behind — escalate rather than guess.",
                    answer=(f"{name} hasn't told me this exact case clearly enough, so I won't guess. "
                            f"Please ask {obj} directly, or try a clearer burger/pasta question."))

    ctx = [h for h in hits if h[0] >= max(0.45, 0.75 * score)][:3] or hits[:1]
    top = ctx[0][1]
    status = "confident" if (score >= CONFIDENT or hp >= 0.5) and top.get("confidence") == "documented" else "qualified"
    text, mode, reason = None, "verbatim", ""
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
        text = top["text"]
    if status == "qualified" and hp < 0.4:
        return dict(status="escalated", sources=[], score=score, mode="threshold", unverified=False,
                    reason="Closest match was too weak to stand behind — escalate rather than guess.",
                    answer=(f"{name} hasn't told me this exact case clearly enough, so I won't guess. "
                            f"Please ask {obj} directly, or try a clearer burger/pasta question."))
    if status == "qualified":
        reason = (f"Closest documented match (score {score:.2f}) — {name} did not address this exact wording; "
                  f"treat as qualified guidance, not a confident claim.")
    if BRIEF_MODE and len(text) > 320:
        text = text[:320].rsplit(" ", 1)[0] + "…"
    if greet:
        text = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + text
    return dict(status=status, answer=text, score=score, mode=mode, reason=reason,
                unverified=any(not d.get("verified", False) for _, d in ctx),
                sources=[dict(id=d["id"], kind=d["kind"], source=d["source"], text=d["text"], score=s) for s, d in ctx])
