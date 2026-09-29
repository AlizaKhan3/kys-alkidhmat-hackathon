#!/usr/bin/env python3
"""Rebuild knowledge/kb.json from chef-provided PDF extract + EN/RU interview transcripts.
Only chef-authored text is stored — never invent measurements she said she would share later."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PDF = "Smash & Sauce Complete Operations Manual (chef-provided PDF, with consent)"
SRC_EN = "Chef interview transcript — Smash_and_Sauce_Kitchen_cleaned.txt (with consent)"
SRC_RU = "Chef interview transcript — samshandsaucekitchen_romanurdu.txt (with consent)"
SRC_BURGER = "Chef recipe — Burger_Recipe.txt (with consent)"
SRC_ALFREDO = "Chef recipe — CREAMY CHICKEN ALFREDO PASTA RECIPE.txt (with consent)"
SRC_EXTRA = "Chef Q&A — extra Question_Answers.txt (with consent)"


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
         "For the burger patty we use beef mince that is 80% meat and 20% fat from our vendor. For 1 kg of meat we add: 1½ teaspoons black pepper (teaspoon, not tablespoon), 2 tablespoons ginger-garlic paste, 1 to 1½ tablespoons butter (Nurpur/Milkpack) for a juicier patty, optional ½ teaspoon red chilli powder if you want it spicy, and optionally Shan Keema Masala for a spicier different taste. Vendor meat balls are around 80 g; after our spices we re-weigh each patty to 70–80 g.",
         "Beef mince 80/20. 1 kg par: 1½ tsp black pepper, 2 tbsp ginger-garlic paste, 1–1½ tbsp butter, optional ½ tsp red chilli, optional Shan Keema Masala. Patty 70–80 g.",
         ["patty", "mixture", "butter", "garlic", "ginger", "chilli", "beef", "seasoning", "kilogram", "80", "20", "keema", "nurpur"]),
        ("I11", "burger",
         "What goes into your burger sauce?",
         "Burger sauce mein kya kya hai?",
         "For the burger sauce: 3 tablespoons mayonnaise, 1 tablespoon ketchup, 1½ tablespoons barbecue sauce, ½ tablespoon mustard sauce, 1 tablespoon Worcestershire sauce, ½ teaspoon or slightly less paprika powder, ½ teaspoon or slightly less black pepper, and a pinch of salt. Mix all together — the burger sauce is ready.",
         "3 tbsp mayo, 1 tbsp ketchup, 1½ tbsp BBQ, ½ tbsp mustard, 1 tbsp Worcestershire, paprika, black pepper, pinch salt — mix.",
         ["burger", "sauce", "mayonnaise", "bbq", "mustard", "worcestershire", "ketchup", "paprika", "tablespoon"]),
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
         "Cut cucumber into round slices. For the pickling liquid: 1½ to 2 cups water, 4 spoons vinegar, juice of 1 complete lemon, 3 teaspoons sugar, 1 teaspoon salt — stir together, add cucumber, boil approximately 15–18 minutes. When the cucumber colour darkens slightly, close the flame. Keep on low flame around 3–20 minutes total as needed.",
         "Kheera round slices; 1½–2 cups pani, 4 spoons vinegar, 1 lemon juice, 3 tsp sugar, 1 tsp salt; boil 15–18 min; low flame.",
         ["pickle", "pickles", "cucumber", "vinegar", "lemon", "sugar", "salt", "boil", "15", "18"]),
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
            "chef_action": "Sometimes the patty breaks while frying because too much butter was added to the mixture, or because too much raw papaya paste was used to tenderize quickly — excess papaya releases water and weakens the patty. Handle the patty gently and avoid flipping until the bottom is properly cooked. Use controlled butter and only a small amount of papaya paste. We hit this problem at the Habitt stall.",
            "confidence": "documented",
            "fallback_escalate": True,
            "source": SRC_EN,
            "verified": True,
        },
        {
            "id": "R41",
            "category": "pasta",
            "condition": "pasta sauce became too thick",
            "tags": ["thick", "thickened", "too thick", "sauce thick", "stiff sauce"],
            "chef_action": "Add a little water and mix well until you get the desired consistency.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R42",
            "category": "pasta",
            "condition": "pasta is sticky",
            "tags": ["sticky", "sticking", "clump", "clumps", "stuck together"],
            "chef_action": "Wash the boiled pasta with cold water and add a little oil to prevent it from sticking.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R43",
            "category": "pasta",
            "condition": "pasta sauce is too watery",
            "tags": ["watery", "thin sauce", "runny", "too much water", "soupy"],
            "chef_action": "Cook it for a little longer on medium heat so the excess water can evaporate and the sauce becomes thicker. If you added too much water, let the sauce cook uncovered on medium heat until the extra water evaporates.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R44",
            "category": "pasta",
            "condition": "sauce is too salty",
            "tags": ["salty", "too much salt", "oversalted"],
            "chef_action": "Add a little more unsalted sauce or other ingredients to balance the saltiness.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R45",
            "category": "pasta",
            "condition": "chicken is still raw",
            "tags": ["raw chicken", "undercooked", "pink chicken", "not cooked"],
            "chef_action": "Cook it for another 10 minutes. You can add a little water and continue cooking until the chicken is completely cooked. Make sure the chicken is no longer raw or pink inside before serving.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R46",
            "category": "burger",
            "condition": "burger patty is too dry",
            "tags": ["dry", "dry patty", "overcooked patty"],
            "chef_action": "Avoid overcooking the patty and make sure it is cooked for the recommended time — each side approximately 8–10 minutes. Add about ½ to 1 teaspoon of butter to the pan when cooking.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
        {
            "id": "R47",
            "category": "burger",
            "condition": "patty sticks to the pan",
            "tags": ["sticking", "sticks", "sticky pan", "won't flip"],
            "chef_action": "Let the bottom cook properly before trying to flip it. Do not force the patty while it is still sticking. Flip only when the bottom is properly cooked and is no longer sticky to the pan.",
            "confidence": "documented",
            "fallback_escalate": False,
            "source": SRC_EXTRA,
            "verified": True,
        },
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


def _sort_key(eid):
    m = re.match(r"([A-Za-z]+)(\d+)", eid)
    if not m:
        return (99, 0)
    order = {"Q": 0, "I": 1, "BR": 2, "AP": 3, "XQ": 4, "M": 5, "QR": 6}.get(m.group(1), 9)
    return (order, int(m.group(2)))


def burger_recipe_entries():
    """Full measured burger recipe from Burger_Recipe.txt."""
    path = ROOT / "Burger_Recipe.txt"
    if not path.exists():
        return []
    chunks = [
        ("BR01", "burger", "What is the full beef patty recipe for 1 kg of meat?",
         "For the burger patty we use beef mince that is 80% meat and 20% fat from the vendor. For 1 kg of meat add: 1½ teaspoons black pepper (teaspoon, not tablespoon), 2 tablespoons ginger-garlic paste, 1 to 1½ tablespoons butter (Nurpur/Milkpack) for juicier patties, optional ½ teaspoon red chilli powder, and optionally Shan Keema Masala for a spicier taste. Vendor balls are ~80 g; after spices re-weigh each patty to 70–80 g.",
         ["patty", "mince", "80", "20", "kilogram", "pepper", "ginger", "garlic", "butter", "nurpur", "keema", "weight", "70", "80"]),
        ("BR02", "burger", "What are the exact burger sauce measurements?",
         "For the burger sauce: 3 tablespoons mayonnaise, 1 tablespoon ketchup, 1½ tablespoons barbecue sauce, ½ tablespoon mustard sauce, 1 tablespoon Worcestershire sauce, ½ teaspoon or slightly less paprika powder, ½ teaspoon or slightly less black pepper, and a pinch of salt. Mix all ingredients together.",
         ["burger", "sauce", "mayonnaise", "ketchup", "barbecue", "mustard", "worcestershire", "paprika", "tablespoon"]),
        ("BR03", "burger", "How do you prepare iceberg lettuce for burgers?",
         "Wash the iceberg lettuce once, dry it properly, then chop it.",
         ["lettuce", "iceberg", "wash", "dry", "chop"]),
        ("BR04", "burger", "How do you make caramelized onions for burgers?",
         "Take one onion and cut into round slices. Add 1 to 1½ tablespoons butter to a pan and caramelize on low flame until slightly sweet — never high heat or they burn and taste bitter. Caramelized onions should always be cooked on low flame.",
         ["caramelized", "onions", "butter", "low", "flame", "sweet", "bitter"]),
        ("BR05", "burger", "What is the full pickle recipe with boiling times?",
         "Cut cucumber into round slices. Pickling liquid: 1½ to 2 cups water, 4 spoons vinegar, juice of 1 complete lemon, 3 teaspoons sugar, 1 teaspoon salt — stir, add cucumber, boil approximately 15–18 minutes until colour darkens slightly, then close flame. Keep on low flame around 3–20 minutes as needed.",
         ["pickle", "pickles", "cucumber", "vinegar", "lemon", "boil", "15", "18", "sugar"]),
        ("BR06", "burger", "How do you toast burger buns?",
         "Apply a little butter to the bun halves and toast them slightly in a pan, then use for assembly.",
         ["bun", "toast", "butter", "pan"]),
        ("BR07", "burger", "How do you cook the patty and melt cheese?",
         "Add 1 to 2 teaspoons butter to the pan. Place the meat ball on the butter, smash once only to form the patty — do not repeatedly press. Do not flip while the bottom is still sticky; wait until properly cooked then flip. Each side takes approximately 8–10 minutes. Place cheese on the cooked patty; it melts in approximately 3–4 minutes.",
         ["cook", "patty", "smash", "flip", "cheese", "melt", "8", "10", "minutes", "sticky", "butter"]),
        ("BR08", "burger", "What is the burger assembly order?",
         "1) Bottom toasted bun with burger sauce. 2) Iceberg lettuce. 3) Caramelized onions. 4) Cheese-covered patty. 5) Pickles on top. 6) Another layer of sauce. 7) Top bun. Ready to serve.",
         ["assembly", "assemble", "order", "bottom", "lettuce", "onions", "pickles", "sauce", "top"]),
    ]
    return [entry(eid, cat, q, ans, SRC_BURGER, extra_tags=xtags) for eid, cat, q, ans, xtags in chunks]


def alfredo_recipe_entries():
    """Creamy chicken Alfredo from chef recipe txt."""
    path = ROOT / "CREAMY CHICKEN ALFREDO PASTA RECIPE.txt"
    if not path.exists():
        return []
    chunks = [
        ("AP01", "pasta", "How do you boil pasta for creamy chicken Alfredo?",
         "Add water to a pot on medium flame with 1½ teaspoons salt and 2 tablespoons oil. Bring to a proper boil, add 1 packet pasta, cook until boiled but not overcooked. Strain, immediately wash with cold water, add a small amount of oil and mix gently so pasta does not stick. Keep aside until sauce and chicken are ready.",
         ["boil", "pasta", "salt", "oil", "cold", "water", "strain", "packet", "overcook"]),
        ("AP02", "pasta", "How do you make the creamy Alfredo sauce?",
         "Mix in a bowl: 2 cups milk, 1 packet cream, 1 tbsp chicken powder, 1 tsp salt, 1 tsp black pepper, 1 tsp chilli flakes, 1 tsp organic leaves, 1 tsp mixed herbs, slightly less than 1 tsp rosemary leaves. On low flame: 1 tbsp butter, 1 tbsp chopped garlic (sauté lightly, do not brown), add flour/maida and mix, gradually add milk-cream mixture while mixing to avoid lumps. Cook on low ~15 minutes until creamy and thick. Add 2–4 slices cheddar cheese until melted. Taste and adjust spices.",
         ["alfredo", "sauce", "cream", "milk", "garlic", "maida", "flour", "cheddar", "rosemary", "herbs", "15", "minutes"]),
        ("AP03", "pasta", "How do you marinate and cook chicken for Alfredo pasta (1 kg)?",
         "For 1 kg chicken marinate with: 1 tbsp garlic paste, 2 tsp chicken tikka powder, ½ tsp oregano, ½ tsp mixed herbs, ½ tsp rosemary, 1 tsp chicken powder, 1 tbsp vinegar, 1 tbsp chilli sauce, 1 tbsp soy sauce, ½ tsp chilli flakes, 1 tsp black pepper, less than ½ tsp salt. Mix thoroughly, marinate 15 minutes. Cook on low flame ~15 minutes; add remaining marinade mixed with a little water and continue until fully cooked.",
         ["chicken", "marinate", "tikka", "vinegar", "soy", "oregano", "rosemary", "15", "minutes", "kilogram"]),
        ("AP04", "pasta", "How do you assemble creamy chicken Alfredo pasta?",
         "Add boiled pasta to the Alfredo sauce and mix until evenly coated. Add cooked chicken and mix carefully. Cook pasta, sauce, and chicken together ~10 minutes on low flame, stirring gently. If pasta is already soft from boiling, reduce final cooking time — do not cook full 10 minutes or it becomes mushy. Final pasta should be creamy, well-coated, and not mushy.",
         ["assembly", "assemble", "combine", "10", "minutes", "mushy", "soft", "coated", "creamy"]),
    ]
    return [entry(eid, cat, q, ans, SRC_ALFREDO, extra_tags=xtags) for eid, cat, q, ans, xtags in chunks]


def extra_qa_entries():
    """Parse extra Question_Answers.txt (Q: / A: blocks)."""
    path = ROOT / "extra Question_Answers.txt"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", text)
    out = []
    n = 0
    for block in blocks:
        m = re.match(r"Q:\s*(.+?)\s*\nA:\s*(.+)", block.strip(), re.S)
        if not m:
            continue
        n += 1
        q, ans = m.group(1).strip(), m.group(2).strip()
        cat = "general"
        ql = q.lower()
        if any(w in ql for w in ("burger", "patty", "bun", "pickle")):
            cat = "burger"
        elif any(w in ql for w in ("pasta", "sauce", "chicken", "maida", "aata")):
            cat = "pasta"
        elif "loss" in ql:
            cat = "brand"
        out.append(entry(f"XQ{n:02d}", cat, q, ans, SRC_EXTRA))
    return out


def escalation():
    return [
        {
            "id": "E01",
            "topic": "Allergies / severe dietary",
            "pattern": "allerg|anaphyla|celiac|coeliac|intoleran|nut allerg|dairy allerg|peanut|\\bnuts?\\b.*\\b(allerg|safe)|gluten.?free|severe diet",
            "reason": "This query involves medical health and severe dietary allergens. The Stand-In cannot authorize dietary safety. Please speak directly with Chef Nisa before placing this order.",
        },
        {
            "id": "E02",
            "topic": "Food safety limits",
            "pattern": "food poison|safe to eat|expired|spoil|bacteria|salmonella|e\\.? ?coli|reheat old|leftover overnight|left out overnight",
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
            "reason": "Legal and business decisions are for Chef Nisa herself.",
        },
        {
            "id": "E05",
            "topic": "Off-menu / outside smash burgers, Alfredo pasta & documented sides",
            "pattern": "steaks?|zinger|broasts?|broasted|(chicke?n|chikcen|chiken|fish|mutton|lamb|turkey|veg|paneer)\\s*-?\\s*burgers?|fried\\s*chicke?n|pizza|biryani|dessert|cake|soup|salad|sushi|lamb\\b|mutton|karahi|curry|shawarma|\\bnuggets?\\b|\\bwraps\\b|off[- ]?menu",
            "reason": "Smash & Sauce specializes exclusively in handcrafted Smash Beef Burgers and Signature Alfredo Penne Pasta. We do not prepare off-menu items, steaks, or fried chicken burgers.",
        },
        {
            "id": "E06",
            "topic": "Secret / proprietary blends only",
            "pattern": "secret spice|proprietary|exact spice blend|reveal.*(spice|recipe)|give.*(spice|brine) recipe|alfredo.*secret|never disclose.*spice",
            "reason": "Proprietary spice blends and unpublished secret recipes are not in the stand-in knowledge base. Ask Chef Nisa directly — the stand-in will not invent them.",
        },
        {
            "id": "E07",
            "topic": "Outside kitchen knowledge",
            "pattern": "quaid|jinnah|who (was|is) (the )?(president|founder|prime minister)|history homework|geography|math homework|unrelated to (food|recipe|kitchen|burger|pasta)",
            "reason": "That's outside Chef Nisa's documented kitchen knowledge. I'll refer you to her rather than guess.",
        },
    ]


def main():
    pdf_entries, pdf_rules, pdf_prefs, _ = load_pdf_entries()
    # Dedup by id — interview I* added fresh; recipe + extra Q&A merged in
    by_id = {e["id"]: e for e in pdf_entries}
    for e in interview_chunks():
        by_id[e["id"]] = e
    for e in burger_recipe_entries() + alfredo_recipe_entries() + extra_qa_entries():
        by_id[e["id"]] = e
    interviews = sorted(by_id.values(), key=lambda e: _sort_key(e["id"]))

    rules_by = {r["id"]: r for r in pdf_rules}
    for r in extra_rules():
        rules_by[r["id"]] = r
    prefs_by = {p["id"]: p for p in pdf_prefs}
    for p in extra_prefs():
        prefs_by[p["id"]] = p

    kb = {
        "chef_profile": {
            "name": "Nisa",
            "kitchen": "Smash & Sauce Kitchen",
            "specialty": "Smash beef burgers, Alfredo/pasta sauces, homemade pickles & masala fries",
            "pronouns": "she/her",
            "relationship": "Aunt of Laiba",
            "bio": "Chef Nisa of Smash & Sauce Kitchen — aunt of Laiba. Family 50/50 kitchen partnership (investment + cooking/orders). Pasta cook for 4–5 years; beef burgers for about 1 year. Home-based kitchen balancing university-day lunchtime orders.",
            "consent_confirmed": True,
            "consent_note": "Chef Nisa (Laiba's aunt) provided the Operations Manual PDF, EN/RU interview transcripts, Burger_Recipe.txt, CREAMY CHICKEN ALFREDO PASTA RECIPE.txt, and extra Question_Answers.txt with consent. Knowledge is limited to those documents; proprietary secret blends are escalated.",
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
