"""Stand-In engine (stdlib only). Flow: manners -> escalation -> retrieval -> confidence -> phrasing.
Answers in English or Roman Urdu, matching the language of the question."""
import json, re, math, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = json.loads((ROOT / "knowledge" / "kb.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "system_prompt.md").read_text(encoding="utf-8")
STOP = set("the a an is are do you your i to of for in on it how what when why my me and or with be if can should does did that this so we went wrong tell about please give say s".split())
# Roman Urdu filler words (question words, verbs, particles) — carry no kitchen meaning.
STOP |= set("""kya kia kaise kese kaisay kaisy hai hain hay ho hota hoti hote ka ki ke ko se mein mai aur ya ye yeh
wo woh kab kyun kyu hum ham aap ap tum par pe bhi to tou na nahi nai raha rahi rahe rha rhi rhe gaya gayi gai gya
kar kr karo kare karein karun krun karna krna karte karti krte krti de dein do bata batao btao batayein bataen bataiye
ji apni apna apne hamara hamari hamare mujhe mjhe kuch koi jab tab abhi sirf bas wala wali wale lagta lagti chahiye
sakte sakti skte hi banate banati banta banti bnate banana bnana
hello hey salam assalam asalam alaikum walaikum aoa""".split())
# Words that only show up in Roman Urdu — one is enough to answer in Roman Urdu.
RU_MARKERS = set("""hai hain kya kia kaise kese kaisay kab kyun kyu kitna kitni kitne karun krun karein karna krna karte
karti krte krti mein nahi nai raha rahi rha rhi ho hota hoti hote gaya gayi gai gya ka ki ke ko se aur batao btao bataen
bataiye chahiye wala wali wale banate banati banta banti dalta dalte dalti rakhte hum toot""".split())
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
_WHO = re.compile(r"\b(who\s+are\s+you|what\s+are\s+you|introduce\s+yourself|your\s+name|are\s+you\s+(?:a\s+)?(?:bot|ai|robot|human|real|the\s+chef)|ap\s+kaun|aap\s+kaun|tum\s+kaun)\b", re.I)
_HOWARE = re.compile(r"\b(how\s+are\s+you|how(?:'s|s|\s+is)\s+it\s+going|what'?s\s+up|kaise\s+ho|kaisi\s+ho|kya\s+haal)\b", re.I)
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
    r"\b(burger|patty|smash|pasta|sauce|salt|fat|ratio|cook|fry|fries|grill|cheese|bun|steak|chicken|pickle|"
    r"onion|pyaaz|alfredo|penne|deal|price|order|allerg|gluten|recipe|temperature|season|oil|dough|noodle|meat|beef)",
    re.I,
)


def lang_of(q):
    return "ru" if any(w in RU_MARKERS for w in re.findall(r"[a-z]+", (q or "").lower())) else "en"


def toks(s):
    out = []
    for w in re.findall(r"[a-z0-9]+", s.lower()):
        if w in STOP:
            continue
        w = re.sub(r"([a-z])\1+", r"\1", w)  # daalte/dalte, pyaaz/pyaz spell the same
        out.append(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


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
        f"I'm the stand-in for {name} at {kitchen}, covering for her while she's not here. "
        f"I only speak from what she taught me about smash burgers and Alfredo pasta; "
        f"if she didn't say it, I'll send you back to her. You can ask in English or Roman Urdu."
    )

    if _SALAAM.search(q) and len(q) < 80:
        return _manners_reply(f"Wa alaikum assalam! {intro} What would you like to ask?")
    if _WHO.search(q):
        return _manners_reply(
            f"{intro} I'm not the chef herself and I'm not a free-roaming AI — "
            f"just her kitchen stand-in for the questions she prepared me for."
        )
    if _HOWARE.search(q) and len(q) < 60:
        return _manners_reply(
            f"I'm doing well, thank you — ready to help the kitchen while {name} is away. "
            f"Ask me anything she covered about burgers or pasta."
        )
    if _THANKS.search(q) and len(q) < 80:
        return _manners_reply(
            f"You're welcome. If something else comes up on burgers or pasta, I'm here — "
            f"and for anything she didn't teach me, please ask {name} directly."
        )
    if _BYE.search(q) and len(q) < 60:
        return _manners_reply(
            f"Take care! Come back anytime with a kitchen question — "
            f"and give {name} my regards when you see her."
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
    j = lambda *xs: " ".join(x for x in xs if x)
    for e in KB["interview_entries"]:
        out.append(dict(e, kind="interview", head=j(e["question"], e.get("question_ru"), *e.get("tags", [])),
                        body=j(e["chef_answer"], e.get("chef_answer_ru")),
                        text=e["chef_answer"], text_ru=e.get("chef_answer_ru") or e["chef_answer"]))
    for r in KB["rules"]:
        out.append(dict(r, kind="rule", head=j(r["condition"], r.get("condition_ru"), *r.get("tags", [])),
                        body=j(r["chef_action"], r.get("chef_action_ru")),
                        text=f"If {r['condition']}: {r['chef_action']}",
                        text_ru=f"Agar {r.get('condition_ru') or r['condition']}: {r.get('chef_action_ru') or r['chef_action']}",
                        source=r.get("source", "rule"), confidence=r.get("confidence", "documented")))
    for p in KB["preferences"]:
        out.append(dict(p, kind="preference", head=j(p["item"], p.get("item_ru"), *p.get("tags", [])),
                        body=j(p["chef_stance"], p.get("chef_stance_ru")),
                        text=f"{p['item']}: {p['chef_stance']}",
                        text_ru=f"{p.get('item_ru') or p['item']}: {p.get('chef_stance_ru') or p['chef_stance']}",
                        source=p.get("source", "preference"), confidence=p.get("confidence", "documented")))
    # Known holes in the interview: retrieved like everything else, but always hand back to the chef.
    for g in KB.get("documented_gaps", []):
        out.append(dict(g, kind="gap", head=j(g["question"], g.get("question_ru"), *g.get("tags", [])),
                        body="", text=g["reason"], text_ru=g.get("reason_ru") or g["reason"],
                        confidence="documented", verified=True))
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


def _llm(q, ctx, lang):
    """Free options only: local Ollama, or Groq free tier via GROQ_API_KEY. Returns None if unavailable."""
    key = "text_ru" if lang == "ru" else "text"
    ctx_txt = "\n".join(f"[{d['id']}] {d[key]}" for _, d in ctx)
    reply_in = "Reply in Roman Urdu." if lang == "ru" else "Reply in English."
    msgs = [{"role": "system", "content": PROMPT.replace("[Chef Name]", KB["chef_profile"]["name"])},
            {"role": "user", "content": f"RETRIEVED CHEF KNOWLEDGE:\n{ctx_txt}\n\nQUESTION: {q}\n\n{reply_in}"}]
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
    src = " ".join(d["text"] + " " + d["text_ru"] for _, d in ctx)
    return all(n in src for n in re.findall(r"\d+(?:\.\d+)?", text))


def ask(q, use_llm=True):
    q = (q or "").strip()
    name = KB["chef_profile"]["name"]
    manners = check_manners(q)
    if manners:
        return manners
    ru = lang_of(q) == "ru"
    txt = lambda d: d["text_ru"] if ru else d["text"]
    src = lambda s, d: dict(id=d["id"], kind=d["kind"], source=d["source"], text=txt(d), score=s)
    greet = bool(_SALAAM.search(q) or (_HELLO.search(q) and len(q) < 120))
    esc = check_escalation(q)
    if esc:
        reason = esc.get("reason_ru") if ru and esc.get("reason_ru") else esc["reason"]
        answer = esc.get("answer_ru" if ru else "answer") or (
            f"Yeh {name} khud dekhengi. {reason}" if ru else f"{name} would want to handle this herself. {reason}")
        return dict(status="escalated", reason=reason, sources=[], score=0, mode="rule", unverified=False, answer=answer)
    hits = retrieve(q)
    score = hits[0][0] if hits else 0
    if hits and score >= QUALIFIED and hits[0][1]["kind"] == "gap":
        gap = hits[0][1]
        ask_her = f"Please {name} se direct poochein." if ru else f"Please ask {name} directly."
        return dict(status="escalated", reason=txt(gap), score=score, mode="gap", unverified=False,
                    answer=f"{txt(gap)} {ask_her}", sources=[src(score, gap)])
    ctx = [h for h in hits if h[0] >= QUALIFIED and h[1]["kind"] != "gap"][:3]
    if not ctx:
        return dict(status="escalated", sources=[], score=score, mode="threshold", unverified=False,
                    reason=(f"Yeh baat {name} ke documented interview mein nahi hai." if ru
                            else f"Outside what {name} documented in her interview."),
                    answer=(f"{name} ne mujhe iske baare mein nahi bataya, is liye andaza lagana theek nahi. Please unse direct poochein." if ru
                            else f"{name} hasn't told me how she'd handle this, so I won't guess. Please ask her directly."))
    top = ctx[0][1]
    status = "confident" if score >= CONFIDENT and top["confidence"] == "documented" else "qualified"
    text, mode = None, "verbatim"
    if use_llm:
        text = _llm(q, ctx, "ru" if ru else "en")
        if text and _grounded(text, ctx):
            mode = "llm"
        else:
            text = None
    if not text:
        text = " ".join(txt(d) for _, d in ctx[:2 if status == "qualified" else 1])
    if status == "qualified":
        text += (f" (Note: {name} ne yeh exact case nahi bataya; yeh unki sab se qareeb documented baat hai.)" if ru
                 else f" (Heads-up: {name} didn't address this exact case; this is her closest documented guidance.)")
    if greet:
        text = ("Wa alaikum assalam! " if _SALAAM.search(q) else "Hello! ") + text
    return dict(status=status, answer=text, score=score, mode=mode, reason="",
                unverified=any(not d.get("verified", False) for _, d in ctx),
                sources=[src(s, d) for s, d in ctx])
