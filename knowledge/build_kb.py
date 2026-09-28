#!/usr/bin/env python3
"""Rebuild knowledge/kb.json from chef-provided PDF extract + EN/RU interview transcripts.
Only chef-authored text is stored — never invent measurements she said she would share later."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PDF = "Smash & Sauce Complete Operations Manual (chef-provided PDF, with consent)"
SRC_EN = "Chef interview transcript — Smash_and_Sauce_Kitchen_cleaned.txt (with consent)"
SRC_RU = "Chef interview transcript — samshandsaucekitchen_romanurdu.txt (with consent)"


def tags(*parts, limit=20):
    stop = set(
        "the a an is are do you your i to of for in on it how what when why my me and or with be if can "
        "should does did that this so we went wrong tell about please give say kab kya hai hain se ke ki "
        "ko aur mein par bhi toh jo ye woh hum".split()
    )
    out = []
    for w in re.findall(r"[a-z0-9%°]+", " ".join(parts).lower()):
        if w in stop or len(w) < 3:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def entry(eid, category, question, answer, source, *, question_ru="", answer_ru="", extra_tags=None, confidence="documented"):
    t = tags(question, question_ru, answer[:240], *(extra_tags or []))
    if extra_tags:
        t = list(dict.fromkeys(list(extra_tags) + t))[:22]
    e = {
        "id": eid,
        "category": category,
        "question": question,
        "tags": t,
        "chef_answer": answer.strip(),
        "source": source,
        "confidence": confidence,
        "verified": True,
    }
    if question_ru:
        e["question_ru"] = question_ru.strip()
    if answer_ru:
        e["chef_answer_ru"] = answer_ru.strip()
    return e


def load_pdf_entries():
    """Reuse previously structured Q01–Q32 / M / QR from current kb if present; else empty."""
    path = ROOT / "knowledge" / "kb.json"
    if not path.exists():
        return [], [], [], []
    old = json.loads(path.read_text(encoding="utf-8"))
    # Refresh source + consent provenance on PDF rows
    interviews, rules, prefs = [], [], []
    for e in old.get("interview_entries", []):
        if e["id"].startswith(("Q", "M", "QR")):
            e = dict(e)
            e["source"] = SRC_PDF
            e["verified"] = True
            e["confidence"] = e.get("confidence", "documented")
            interviews.append(e)
    for r in old.get("rules", []):
        r = dict(r)
        r["source"] = SRC_PDF
        r["verified"] = True
        rules.append(r)
    for p in old.get("preferences", []):
        if p["id"] in ("F01", "F02"):
            p = dict(p)
            p["source"] = SRC_PDF
            p["verified"] = True
            prefs.append(p)
    esc = old.get("escalation_topics", [])
    return interviews, rules, prefs, esc


def interview_chunks():
    """Narrative chunks from the chef's spoken interview (EN + aligned RU)."""
    chunks = [
        ("I01", "brand",
         "Who are you and why did you start Smash & Sauce Kitchen?",
         "Aap kaun hain aur Smash & Sauce Kitchen kyun start kiya?",
         "I'm a university student and I started my own small food business called Smash & Sauce Kitchen because I've always had a huge passion for cooking. I especially love making pasta — I've been making it for around four to five years and Alhamdulillah I've received really good reviews. I also really enjoy making beef burgers; it's been almost one year since I started making them.",
         "Main basically ek university student hoon, aur maine apna khud ka small food business start kiya hai jiska naam Smash & Sauce Kitchen hai, kyun ke mujhe hamesha se cooking ka bohat zyada shauq raha hai. Mujhe especially pasta banana bohat pasand hai — around four to five years; beef burgers almost one year.",
         ["university", "student", "passion", "pasta", "burger", "smash", "sauce", "kitchen", "shauq"]),
        ("I02", "brand",
         "How is the business structured with your aunt?",
         "Aapki aunt ke saath partnership kaise hai?",
         "I started this business with my aunt, and we are 50-50 partners. She mainly invests in the business, while I handle the actual work and operations, especially the cooking and orders.",
         "Maine ye business apni aunt ke saath start kiya hai, aur hum 50-50 partners hain. Woh mainly investment karti hain, jabke main cooking aur orders handle karti hoon.",
         ["aunt", "partner", "50", "50-50", "investment", "operations"]),
        ("I03", "operations",
         "How many orders did you get when you first started?",
         "Shuru mein kitne orders milte the?",
         "When we first started, we used to get around two to three orders a week. Within our first one and a half months, we completed around 20 orders. We also tried getting some reviews from local people.",
         "Shuru mein week mein around two to three orders milte the. First one and a half months ke andar around 20 orders complete kiye.",
         ["orders", "week", "twenty", "reviews", "started"]),
        ("I04", "inventory",
         "Where do you buy ingredients now versus when you started?",
         "Ingredients kahan se khareedte ho?",
         "When we first started, we used to buy almost everything from supermarkets like Imtiaz, Naheed, and Chase. Now that the business is more organized, we buy ingredients from specific brands and vendors. For burgers we usually use Dawn and Bake Parlour products. For pasta we use Bake Parlour and Reggia. For chicken and meat we have our own vendor. For fries we initially used normal potatoes, but now we use 9mm potatoes.",
         "Pehle Imtiaz, Naheed aur Chase se; ab specific brands. Burgers: Dawn aur Bake Parlour. Pasta: Bake Parlour aur Reggia. Meat/chicken: apna vendor. Fries: ab 9mm potatoes.",
         ["imtiaz", "naheed", "chase", "dawn", "bake", "parlour", "reggia", "vendor", "fries", "9mm"]),
        ("I05", "menu",
         "What packaging, starting prices, and fries do you offer?",
         "Packaging, prices aur fries kya hain?",
         "For burger packaging we use foil paper, and for pasta we have 500 ml and 1000 ml boxes. Our beef burgers start from around Rs. 750, while our 500 ml pasta is Rs. 699. We also offer homemade masala fries.",
         "Burger packaging foil paper; pasta 500 ml aur 1000 ml boxes. Beef burgers around Rs. 750 se; 500 ml pasta Rs. 699. Homemade masala fries bhi offer karte hain.",
         ["foil", "500", "1000", "750", "699", "masala", "fries", "price", "packaging"]),
        ("I06", "operations",
         "What is the biggest challenge managing university and lunchtime orders?",
         "University aur lunchtime orders ka sabse bara challenge kya hai?",
         "I'm a university student and usually my classes are from around 9 to 2 or sometimes 9 to 3. The biggest problem is lunchtime orders when I'm not at home. If the order is pre-booked, I usually prepare things the night before. If an order arrives at that exact time, my sister or someone from my family receives it on WhatsApp or our business number. But I'm usually the one who prepares the food — pasta sauces and burger sauce are hard for my aunt to make exactly the way I do, so I often call and explain step by step. Even a small difference in quantity, sauce, or cooking time can change the taste. Consistency matters.",
         "Classes usually 9 se 2 ya 9 se 3. Lunchtime par ghar nahi hoti. Pre-booked ho to raat ko prepare. Warna sister/family WhatsApp se order leti hai. Sauce exactly meri tarah banana aunt ke liye mushkil; call par step-by-step. Consistency important hai.",
         ["university", "classes", "lunchtime", "whatsapp", "sister", "aunt", "consistency", "pre-booked"]),
        ("I07", "brand",
         "How did your first investment go?",
         "Pehli investment kaise rahi?",
         "When we made our first investment, we did not face any loss. Around one month and fifteen days later, we were able to recover around 40% of the amount that we had invested. We also had a separate amount set aside for resale and other related expenses, so overall our first investment worked out fine and we did not consider it a loss.",
         "Pehli investment par loss nahi hua. Around one month and fifteen days baad invested amount ka around 40% recover ho gaya.",
         ["investment", "loss", "recover", "40", "first"]),
        ("I08", "brand",
         "What happened at the Habitt stall?",
         "Habitt stall par kya hua?",
         "The major loss we experienced was during our Habitt stall. We made a separate investment for stock, preparation, and stall expenses, but sales were not enough to cover it, so a significant amount became a loss. There were also issues with inaccurate information and guidance from the organizers. It was my first proper food stall, so despite the loss I learned about event planning, estimating sales, managing stock, organizers' requirements, calculating investment beforehand, and not over-preparing or over-investing without a realistic sales estimate.",
         "Major loss Habitt stall par hua — sales investment cover nahi kar saki. Organizers ki guidance accurate nahi thi. Seekha: event planning, sales estimate, stock, over-invest na karna.",
         ["habitt", "stall", "loss", "sales", "organizers", "event"]),
        ("I09", "operations",
         "Where do your early orders come from, and what are you working on now?",
         "Orders kahan se aate hain?",
         "When we first started, most orders came from people we already knew — mainly immediate family, friends, and people connected to them. Getting orders from completely new customers was much less common. We're now trying to reach people outside our immediate circle and build a customer base that returns because they like the food. Customer reviews and feedback matter because for a small home-based food business, building trust with people who don't personally know you takes time.",
         "Shuru mein zyada orders family/friends se. Ab circle se bahar reach aur repeat customers. Reviews/feedback important hain.",
         ["customers", "family", "friends", "reviews", "trust", "home-based"]),
        ("I10", "burger",
         "How do you prepare your beef patty mixture?",
         "Beef patty mixture kaise banati ho?",
         "For our patty we use our own meat mixture and prepare it according to the quantity we need. We start with butter, then add garlic and ginger paste along with our other basic seasonings. We keep the base relatively simple to maintain the original beef flavour. Because some customers prefer a slightly spicy patty, we add a small amount of red chilli according to the quantity of meat — for example, when preparing one kilogram of meat, we add a controlled amount of red chilli. We also add butter to the mixture in the required quantity. Exact recipe and measurements for one kilogram of meat were to be shared separately and are not in this interview transcript.",
         "Apna meat mixture; butter, garlic-ginger paste, basic seasonings. Beef flavour simple. 1 kg meat par controlled red chilli. Exact 1 kg measurements is interview mein fully detailed nahi — alag se share karne wali thin.",
         ["patty", "mixture", "butter", "garlic", "ginger", "chilli", "beef", "seasoning", "kilogram"]),
        ("I11", "burger",
         "What goes into your burger sauce?",
         "Burger sauce mein kya kya hai?",
         "For our burger sauce we use mayonnaise, Dippit BBQ sauce, mustard sauce, Worcestershire sauce, and tomato ketchup. Brands matter — low-quality brands change the taste significantly. I tried wholesale products to reduce cost, but the taste wasn't what I wanted to sell, so we switched to ingredients that create the flavour we want. Apart from barbecue sauce we also use mustard sauce, rosemary sauce, chilli sauce, paprika powder, rosemary, and black pepper. These ingredients together make up our burger sauce. Exact quantities and the complete measured process were to be discussed separately and are not fully specified in this transcript.",
         "Mayonnaise, Dippit BBQ, mustard, Worcestershire, tomato ketchup; mustard, rosemary sauce, chilli sauce, paprika, rosemary, black pepper. Exact quantities is transcript mein fully nahi.",
         ["burger", "sauce", "mayonnaise", "dippit", "bbq", "mustard", "worcestershire", "ketchup", "paprika", "rosemary"]),
        ("I12", "pasta",
         "How do you cook pasta and what is in the pasta sauce?",
         "Pasta aur pasta sauce kaise banta hai?",
         "For pasta we usually boil it for around 8–10 minutes, depending on the type and brand. We use Bake Parlour and Reggia pasta. For our pasta sauce we use cheddar cheese — specifically Adam's cheese — along with cream, milk, and butter. We also use all-purpose milk. Ingredient quality matters because changing the brand or using a lower-quality product affects taste and consistency.",
         "Pasta usually 8–10 minutes boil; Bake Parlour aur Reggia. Sauce: Adam's cheddar, cream, milk, butter, all-purpose milk.",
         ["pasta", "boil", "8", "10", "adams", "cheddar", "cream", "milk", "butter", "reggia", "bake"]),
        ("I13", "troubleshooting",
         "Why does the patty sometimes break while frying, and how do you prevent it?",
         "Patty fry karte waqt break kyun hoti hai?",
         "Sometimes our patty breaks while frying. One reason is accidentally adding too much butter to the patty mixture. Another is when we need to prepare the meat quickly and use a small amount of raw papaya paste to tenderize — if too much raw papaya paste is added, the mixture can release water, and that excess moisture makes the patty weak so it breaks while frying. We experienced this exact problem at our Habitt stall.",
         "Zyada butter ya zyada raw papaya paste se mixture pani chhor sakta hai; excess moisture se patty fry mein break hoti hai. Habitt stall par ye problem aayi thi.",
         ["break", "breaking", "butter", "papaya", "moisture", "tenderize", "frying", "habitt"]),
        ("I14", "burger",
         "What cheese do you use for burgers and pasta, and how long does burger cheese take to melt?",
         "Cheese kaunsi use karti ho?",
         "For our burgers we use Adam's burger cheese. I prefer Adam's because of its quality and melting consistency. Usually it takes around five minutes for the cheese to melt properly, depending on how we're preparing the burger. For our pasta we also use Adam's cheddar cheese.",
         "Burgers: Adam's burger cheese — usually around five minutes melt. Pasta: Adam's cheddar.",
         ["adams", "cheese", "melt", "five", "minutes", "cheddar", "burger"]),
        ("I15", "pasta",
         "How do you marinate the chicken?",
         "Chicken kaise marinate karti ho?",
         "For the chicken we usually marinate it properly before preparing it. For the marinade we use Shan Chicken Tikka Powder, along with chicken powder, chilli sauce, soy sauce, black pepper, a little salt, chilli flakes, and oregano. Depending on what we're preparing, we also use different seasoning mixes — sometimes Rosemary products or Falak products. Exact ingredients and quantities can vary depending on the recipe.",
         "Marinade: Shan Chicken Tikka Powder, chicken powder, chilli sauce, soy sauce, black pepper, thoda salt, chilli flakes, oregano. Kabhi Rosemary ya Falak products. Exact quantities recipe ke hisaab se vary.",
         ["chicken", "marinate", "shan", "tikka", "soy", "oregano", "falak", "rosemary"]),
        ("I16", "burger",
         "How do you make your homemade pickles?",
         "Homemade pickles kaise bante hain?",
         "We take cucumber and slice it properly. Then in around one cup of hot water we add approximately 3–4 tablespoons of vinegar, one small lemon, 2 tablespoons of sugar, and half a teaspoon of salt. We put the sliced cucumbers into this mixture and leave them for around 30 minutes. After that we let the pickles cool down in the same liquid. Once cooled, we store them in the refrigerator. Keeping them refrigerated helps preserve them properly.",
         "Kheera slice; ~1 cup garam pani mein 3–4 tbsp vinegar, 1 chhota lemon, 2 tbsp sugar, half tsp salt; 30 minutes; thanda karke fridge mein store.",
         ["pickle", "pickles", "cucumber", "vinegar", "lemon", "sugar", "salt", "30", "refrigerator"]),
        ("I17", "brand",
         "What have you learned overall running Smash & Sauce Kitchen?",
         "Is business se kya seekha?",
         "Overall, from our first investment and the loss we experienced, to understanding ingredients, recipes, storage, food preparation, and the challenges at our Habitt stall — every experience has taught us something new. That's one of the most interesting parts of running a small food business: you learn something from almost every order. I also keep track of our expenses and losses in a diary.",
         "Har experience se seekha — investment, Habitt stall, ingredients, consistency. Expenses/losses diary mein track karti hoon.",
         ["learning", "diary", "expenses", "losses", "experience"]),
    ]
    out = []
    for eid, cat, q, qru, ans, ansru, xtags in chunks:
        out.append(entry(eid, cat, q, ans, SRC_EN, question_ru=qru, answer_ru=ansru, extra_tags=xtags))
    return out


def extra_rules():
    return [
        {
            "id": "R40",
            "category": "burger",
            "condition": "patty breaks while frying",
            "tags": ["break", "breaking", "crumbly", "falls", "apart", "papaya", "butter", "moisture"],
            "chef_action": "Sometimes the patty breaks while frying because too much butter was added to the mixture, or because too much raw papaya paste was used to tenderize quickly — excess papaya releases water and weakens the patty. Use controlled butter and only a small amount of papaya paste. We hit this problem at the Habitt stall.",
            "confidence": "documented",
            "fallback_escalate": True,
            "source": SRC_EN,
            "verified": True,
        }
    ]


def extra_prefs():
    return [
        {
            "id": "F03",
            "category": "general",
            "item": "Brand and ingredient quality stance",
            "tags": ["brand", "quality", "wholesale", "cost", "taste"],
            "chef_stance": "Brands make a big difference. Low-quality or cheap wholesale sauces can change the taste significantly; she tried reducing cost that way and rejected it because it wasn't what she wanted to sell. Prefer Adam's cheese, Dawn/Bake Parlour burger products, Bake Parlour/Reggia pasta, and trusted meat vendors.",
            "confidence": "documented",
            "verified": True,
            "source": SRC_EN,
        },
        {
            "id": "F04",
            "category": "operations",
            "item": "Habitt stall lesson — never over-invest without sales estimate",
            "tags": ["habitt", "stall", "over-invest", "sales", "estimate"],
            "chef_stance": "Do not over-prepare or over-invest for an event without a realistic estimate of expected sales. Calculate investment beforehand and verify organizer guidance.",
            "confidence": "documented",
            "verified": True,
            "source": SRC_EN,
        },
    ]


def escalation():
    return [
        {
            "id": "E01",
            "topic": "Allergies / severe dietary",
            "pattern": "allerg|anaphyla|celiac|coeliac|intoleran|nut allerg|dairy allerg|peanut|gluten.?free medical|severe diet",
            "reason": "This query involves medical health and severe dietary allergens. The Stand-In cannot authorize dietary safety. Please speak directly with the chef/owner before placing this order.",
        },
        {
            "id": "E02",
            "topic": "Food safety limits",
            "pattern": "food poison|safe to eat|expired|spoil|bacteria|salmonella|e\\.? ?coli|internal temp|reheat old|leftover overnight",
            "reason": "Food-safety limits must come from the chef or a food-safety officer, not from the stand-in.",
        },
        {
            "id": "E03",
            "topic": "Medical",
            "pattern": "doctor|sick|\\bill\\b|illness|vomit|pregnan|diabet|medic|diet plan|calorie|weight loss",
            "reason": "This is medical territory. Please ask a doctor or the chef in person.",
        },
        {
            "id": "E04",
            "topic": "Legal / business disputes",
            "pattern": "lawsuit|legal|licen[cs]e|insurance|refund|complain|\\bsue\\b",
            "reason": "Legal and business decisions are for the chef/owner herself.",
        },
        {
            "id": "E05",
            "topic": "Off-menu / outside smash burgers, Alfredo pasta & documented sides",
            "pattern": "steak|zinger|broast|chicken burger|fried chicken|pizza|biryani|dessert|cake|soup|salad|sushi|lamb|mutton|karahi|curry|shawarma|\\bnuggets?\\b|\\bwraps\\b",
            "reason": "Smash & Sauce Kitchen specializes in handcrafted smash beef burgers, signature Alfredo/pasta, and documented sides like masala fries. Off-menu steaks or fried chicken burgers are not prepared.",
        },
        {
            "id": "E06",
            "topic": "Secret / unpublished exact recipes",
            "pattern": "secret spice|proprietary|pickle brine recipe|exact spice blend|reveal.*(spice|recipe)|give.*(spice|brine) recipe|exact\\s+(grams?|measurements?|quantit\\w*)|full recipe with (grams?|quantit)|1\\s*kg (patty|meat).*(recipe|measure|quantit|grams?)|(patty|sauce).*(exact|precise).*(grams?|measure|quantit)",
            "reason": "Exact measured recipes she said she would share separately (e.g. full 1 kg patty mix quantities, full burger-sauce gram sheet, proprietary Alfredo spices) are not fully in the stand-in knowledge base. Ask the chef/owner directly — the stand-in will not invent numbers.",
        },
    ]


def main():
    pdf_entries, pdf_rules, pdf_prefs, _ = load_pdf_entries()
    # Dedup by id — interview I* added fresh
    by_id = {e["id"]: e for e in pdf_entries}
    for e in interview_chunks():
        by_id[e["id"]] = e
    interviews = sorted(by_id.values(), key=lambda e: (
        {"Q": 0, "I": 1, "M": 2, "QR": 3}.get(re.match(r"[A-Za-z]+", e["id"]).group(), 9),
        int(re.search(r"\d+", e["id"]).group()),
    ))

    rules_by = {r["id"]: r for r in pdf_rules}
    for r in extra_rules():
        rules_by[r["id"]] = r
    prefs_by = {p["id"]: p for p in pdf_prefs}
    for p in extra_prefs():
        prefs_by[p["id"]] = p

    kb = {
        "chef_profile": {
            "name": "Smash & Sauce Kitchen Chef",
            "kitchen": "Smash & Sauce Kitchen",
            "specialty": "Smash beef burgers, Alfredo/pasta sauces, homemade pickles & masala fries",
            "pronouns": "she/her",
            "bio": "University student and chef-operator of Smash & Sauce Kitchen; 50/50 partner with her aunt (aunt invests; she runs cooking and orders). Pasta cook for 4–5 years; beef burgers for about 1 year. Home-based kitchen balancing classes (~9–2/9–3) with lunchtime orders.",
            "consent_confirmed": True,
            "consent_note": "Chef provided the Operations Manual PDF plus English and Roman Urdu interview transcripts with consent for this stand-in. Knowledge is limited to those documents; unpublished exact gram sheets she mentioned separately are escalated.",
        },
        "interview_entries": interviews,
        "rules": list(rules_by.values()),
        "preferences": list(prefs_by.values()),
        "escalation_topics": escalation(),
    }
    out = ROOT / "knowledge" / "kb.json"
    out.write_text(json.dumps(kb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"entries={len(interviews)} rules={len(kb['rules'])} prefs={len(kb['preferences'])} esc={len(kb['escalation_topics'])}")
    print("consent", kb["chef_profile"]["consent_confirmed"], "pronouns", kb["chef_profile"]["pronouns"])


if __name__ == "__main__":
    main()
