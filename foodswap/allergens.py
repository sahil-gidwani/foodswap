"""Does a product contain an allergen? For every product and allergen: FAIL, PASS or UNKNOWN, with the evidence.

FAIL     any source in the record mentions it: the allergen list, the "may contain" list,
         an ingredient that carries it in the ingredient taxonomy, or the ingredient text.
PASS     nothing mentions it, and the record has an English ingredient list that is mostly recognized.
UNKNOWN  nothing mentions it, but the record doesn't have enough information to be sure.

PASS means "not declared in this record", never "safe".
"""

import re

import pandas as pd

from foodswap.schema import Verdict

# A PASS needs at least this share of the ingredient list recognized by Open Food Facts.
MIN_RECOGNIZED = 0.8

WHEAT_WORDS = [
    "wheat*", "spelt", "durum", "semolina", "farina", "kamut", "einkorn", "emmer", "farro",
    "bulgur", "couscous", "seitan", "graham", "triticale",
    # On US labels, flour with no grain named is wheat flour.
    "enriched flour", "enriched bleached flour", "enriched unbleached flour", "bleached flour",
    "unbleached flour", "all purpose flour", "white flour", "plain flour", "self rising flour",
    "bread flour", "cake flour", "pastry flour",
]

# The same rule for "flour" listed on its own as an ingredient: "flour, sugar, ..." or "...: flour (...)".
PLAIN_FLOUR = re.compile(r"(?:^|[,(\[:;])\s*flour\b")

# "tags": Open Food Facts allergen ids that mean this allergen, whether in the product's allergen
#         list, its "may contain" list, or inherited by an ingredient through the taxonomy.
# "root": for wheat, which has no allergen id of its own: any ingredient under en:wheat.
# "words": searched for in the ingredient text as whole words, plurals included. A trailing *
#         also matches longer words, since many records run words together ("soybeanoil").
# "not": phrases that contain a word but aren't the allergen ("coconut milk" isn't milk).
ALLERGENS = {
    "milk": {
        "tags": ["en:milk"],
        "words": ["milk*", "cream", "butter", "buttermilk", "butterfat", "butteroil", "cheese", "whey",
                  "casein", "caseinate", "lactose", "lactalbumin", "lactoglobulin", "yogurt", "yoghurt",
                  "ghee", "curd", "paneer"],
        "not": [
            # plant milks and creams
            "coconut milk", "almond milk", "oat milk", "soy milk", "soya milk", "rice milk", "cashew milk",
            "hemp milk", "pea milk", "flax milk", "hazelnut milk", "macadamia milk", "coconut cream",
            "cashew cream",
            # plant, nut and seed butters
            "cocoa butter", "cacao butter", "shea butter", "mango butter", "coconut butter", "peanut butter",
            "nut butter", "almond butter", "cashew butter", "hazelnut butter", "pecan butter", "walnut butter",
            "pistachio butter", "macadamia butter", "seed butter", "sunflower butter", "soy butter",
            "sesame butter", "apple butter",
            "cream of tartar", "bean curd",
        ],
    },
    "eggs": {
        "tags": ["en:eggs"],
        "words": ["egg", "albumen", "albumin", "ovalbumin", "lysozyme", "mayonnaise", "meringue"],
        "not": [],
    },
    "fish": {
        "tags": ["en:fish"],
        "words": ["fish", "anchovy", "anchovies", "cod", "salmon", "tuna", "tilapia", "pollock",
                  "sardine", "haddock", "trout", "mackerel", "herring", "catfish", "halibut", "whitefish",
                  "lumpfish", "monkfish", "swordfish", "bonito", "hake", "flounder", "roe", "caviar"],
        "not": [],
    },
    "crustaceans": {
        "tags": ["en:crustaceans"],
        "words": ["shrimp", "prawn", "crab", "lobster", "crayfish", "crawfish", "krill"],
        "not": [],
    },
    "molluscs": {
        "tags": ["en:molluscs"],
        "words": ["clam", "mussel", "oyster", "scallop", "squid", "octopus", "calamari", "snail",
                  "escargot", "abalone"],
        "not": ["oyster mushroom"],
    },
    "tree_nuts": {
        "tags": ["en:nuts"],
        "words": ["nut", "almond*", "cashew*", "hazelnut*", "filbert", "walnut*", "pecan*", "pistachio*",
                  "macadamia*", "chestnut", "praline", "marzipan"],
        # Soy nuts, corn nuts and the like are not tree nuts.
        "not": ["water chestnut", "soy nut", "corn nut", "hemp nut", "sunflower nut", "tiger nut"],
    },
    "peanuts": {
        "tags": ["en:peanuts"],
        "words": ["peanut*", "groundnut", "ground nut", "arachis"],
        "not": [],
    },
    "wheat": {
        # A gluten tag may come from barley or rye rather than wheat; we treat it as possible wheat.
        "tags": ["en:gluten"],
        "root": "en:wheat",
        "words": WHEAT_WORDS,
        "plain_flour": True,
        "not": [],
    },
    "gluten": {
        "tags": ["en:gluten"],
        "words": ["gluten", *WHEAT_WORDS, "barley", "rye", "malt"],
        "plain_flour": True,
        "not": [],
    },
    "soybeans": {
        "tags": ["en:soybeans"],
        "words": ["soy*", "edamame", "tofu", "tempeh", "miso"],
        "not": [],
    },
    "sesame": {
        "tags": ["en:sesame-seeds"],
        "words": ["sesame*", "tahini", "benne"],
        "not": [],
    },
}

# "gluten-free", "peanut free": a claim that something is absent, not an ingredient. It is replaced
# by a placeholder word, so "gluten free flour" doesn't turn into plain "flour".
FREE_FROM = re.compile(r"\b\w+[- ]free\b")


def phrases(words):
    """One regex matching any of the words or phrases as whole words, plurals included."""
    alternatives = []
    for word in sorted(words, key=len, reverse=True):
        prefix = word.endswith("*")
        pattern = re.escape(word.rstrip("*")).replace(r"\ ", r"[\s-]+")
        alternatives.append(pattern + (r"\w*" if prefix else r"(?:e?s)?"))
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b")


PATTERNS = {
    name: (phrases(spec["words"]), phrases(spec["not"]) if spec["not"] else None)
    for name, spec in ALLERGENS.items()
}


def ingredient_allergens(ingredients):
    """Which allergens each ingredient carries, inherited through its parents (whey -> dairy -> milk)."""
    by_tag = {}
    for name, spec in ALLERGENS.items():
        if "root" not in spec:
            for tag in spec["tags"]:
                by_tag.setdefault(tag, set()).add(name)
    roots = {spec["root"]: name for name, spec in ALLERGENS.items() if "root" in spec}

    carried = {}
    for ingredient in ingredients:
        found = set()
        for ancestor in ancestors(ingredient, ingredients):
            if ancestor in roots:
                found.add(roots[ancestor])
            declared = ingredients[ancestor].get("allergens", {}).get("en", "")
            for tag in declared.split(","):
                found |= by_tag.get(tag.strip(), set())
        if found:
            carried[ingredient] = found
    return carried


def ancestors(node, taxonomy):
    """The node and everything above it; a node can have several parents."""
    seen, stack = set(), [node]
    while stack:
        current = stack.pop()
        if current in seen or current not in taxonomy:
            continue
        seen.add(current)
        stack.extend(taxonomy[current].get("parents", []))
    return seen


def ingredients_problem(product):
    """Why the ingredient list can't support a PASS, or None if it can."""
    text = product["ingredients_text"]
    if not isinstance(text, str) or not text.strip():
        return "no_ingredients"
    total, unknown = product["ingredients_n"], product["unknown_ingredients_n"]
    if pd.isna(total) or total == 0 or pd.isna(unknown):
        return "not_parsed"
    if (total - unknown) / total < MIN_RECOGNIZED:
        return "low_recognition"
    return None


def check(product, allergen, carried):
    """The verdict for one product and allergen, with every piece of evidence as (source, detail)."""
    spec = ALLERGENS[allergen]
    evidence = [("allergen list", t) for t in product["allergen_tags"] if t in spec["tags"]]
    evidence += [("may contain", t) for t in product["trace_tags"] if t in spec["tags"]]
    evidence += [("ingredient", t) for t in product["ingredient_tags"] if allergen in carried.get(t, ())]

    text = product["ingredients_text"]
    if isinstance(text, str):
        words, exceptions = PATTERNS[allergen]
        text = FREE_FROM.sub(" freefrom ", text.lower())
        if exceptions:
            text = exceptions.sub(" ", text)
        evidence += [("ingredient text", m.group(0)) for m in words.finditer(text)]
        if spec.get("plain_flour"):
            evidence += [("ingredient text", "flour") for _ in PLAIN_FLOUR.finditer(text)]

    if evidence:
        return Verdict.FAIL, evidence
    problem = ingredients_problem(product)
    return (Verdict.UNKNOWN, [("missing", problem)]) if problem else (Verdict.PASS, [])


def add_verdicts(df, ingredients):
    """Add allergen_<name> (0 FAIL, 1 PASS, 2 UNKNOWN) and allergen_<name>_sources for every allergen."""
    carried = ingredient_allergens(ingredients)
    fields = ["allergen_tags", "trace_tags", "ingredient_tags", "ingredients_text", "ingredients_n",
              "unknown_ingredients_n"]
    products = [dict(zip(fields, values)) for values in zip(*(df[f] for f in fields))]

    df["ingredients_check"] = [ingredients_problem(p) or "ok" for p in products]
    for allergen in ALLERGENS:
        results = [check(p, allergen, carried) for p in products]
        df[f"allergen_{allergen}"] = pd.array([int(v) for v, _ in results], dtype="int8")
        df[f"allergen_{allergen}_sources"] = [
            "+".join(sorted({source for source, _ in evidence})) if v == Verdict.FAIL else ""
            for v, evidence in results
        ]
    return ["ingredients_check"] + [
        column for a in ALLERGENS for column in (f"allergen_{a}", f"allergen_{a}_sources")
    ]
