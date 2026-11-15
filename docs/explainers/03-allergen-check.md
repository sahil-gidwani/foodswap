# The allergen check

The third primer for the team, after [01](01-data-and-code.md) (the data and taxonomies) and [02](02-data-cleaning.md) (cleaning). This one explains the allergen check in `foodswap/allergens.py`: why we need it, where it is used, how it decides, and how we know it works.

**State as of Nov 14.** The check runs inside `python -m foodswap.data build`. Every one of the 349,308 products gets a verdict for each of 11 allergens. Tests: `python -m pytest`.

## 1. Why we need it

A substitute search has to do two things ordinary search can't.

1. **Honour "no peanuts".** Search engines, keyword or AI, treat "no peanuts" as a request *for* peanuts, because they look for products that mention peanuts. Research on modern search systems shows the same failure (NevIR, ExcluIR; see the [related work](../13-related-work.md)). So exclusions can't be left to the search engine. They have to be a separate filter.
2. **Know which products contain peanuts.** The data's own allergen fields aren't reliable enough:
   - Nutella's tags miss milk and soy, even though both are ingredients.
   - Many products have an empty allergen list simply because nobody filled it in.

   So we work out our own answer from all the evidence, and we refuse to guess when the record is incomplete.

This is the safety part of the project. It is also what separates FoodSwap from apps like Yuka, which suggest "same category, better score" with no notion of what you must avoid.

## 2. Where it is used

**The search filter.** When a request excludes an allergen, only products that pass become candidates. For "a cereal like Cheerios, with no peanuts":

| Extruded cereals (Cheerios' comparison group) | Products |
|---|---|
| Total | 286 |
| Don't declare peanuts → shown | 229 |
| Can't verify → hidden | 48 |
| Contain peanuts → hidden | 9 |

Add "less sugar", and 18 cereals qualify on sugar, but only 9 get through. Magic Spoon "Peanut Butter" is removed, along with 8 that can't be verified. One of the 9 peanut products, Sainsbury's Oats & Honey, was caught only by reading its ingredient text; its allergen tags didn't mention peanuts.

**The app's explanations.** Every result says what was checked: "✓ No peanut declared (allergen list, ingredients checked)". The "why were others excluded?" panel reads the same verdicts:

- "Magic Spoon Peanut Butter: contains peanuts (allergen list, ingredients)"
- "8 cereals couldn't be verified: no English ingredient list"

**The evaluation**, where the headline results come from:

- **Safety violations:** how often each system shows a product containing the excluded allergen.
- **Coverage:** how often at least 5 safe options remain, the cost of being strict.
- **The "no peanuts" experiment** from the proposal: how much harm it does to leave the excluded word in the search query.

**The demo.** The side-by-side page marks the baseline's results that contain the excluded allergen.

**Why compute it in advance.** Reading 349,000 ingredient lists on every search would be slow. Doing it once during the build turns each search's filter into a column lookup that takes milliseconds. It also means the app, the evaluation and every system we compare use exactly the same verdicts.

## 3. The three verdicts

| Verdict | Meaning | In search |
|---|---|---|
| **FAIL** | Something in the record mentions the allergen | Excluded, with the evidence shown |
| **PASS** | Nothing mentions it, and the ingredient list is good enough to trust | Eligible |
| **UNKNOWN** | Nothing mentions it, but the record is too incomplete to be sure | Also excluded |

Why not just yes or no? Missing data is extremely common. If "nothing mentions peanuts" counted as safe, a product with no ingredient list at all would pass a peanut check. The proposal promised that missing evidence means rejection, and Open Food Facts' own app makes the same distinction.

**PASS means "not declared in this record", never "safe".**

## 4. How it decides

### 4.1 The allergen list

`ALLERGENS` covers 11 allergens: the FDA's nine US major allergens (milk, eggs, fish, crustaceans, tree nuts, peanuts, wheat, soybeans, sesame), plus gluten (people ask for gluten-free), plus molluscs (so "shellfish" can mean both shellfish groups).

Each entry has up to four parts:

| Part | What it is | Example (milk) |
|---|---|---|
| `tags` | The Open Food Facts allergen IDs that mean this allergen | `en:milk` |
| `root` | Wheat only: any ingredient under `en:wheat` in the taxonomy (Open Food Facts has no wheat allergen ID, only gluten) | n/a |
| `words` | What to look for in the ingredient text | milk, cream, butter, cheese, whey, casein, … |
| `not` | Phrases that contain a word but aren't the allergen | coconut milk, almond butter, cream of tartar, … |

### 4.2 Four places evidence can come from

`check()` looks in four places. **Any one of them is enough to FAIL.**

**1. The allergen list** (`allergen_tags`). The product declares it. This sometimes over-reports, because "may contain" items get entered as allergens. We accept that: wrongly excluding a product is safe, wrongly including one isn't.

**2. The "may contain" list** (`trace_tags`). Counted as FAIL, since someone avoiding peanuts usually avoids "may contain peanuts" too. Only 5,802 US products have any "may contain" data, so for US products the ingredient list is the main evidence.

**3. Ingredients, through the taxonomy.** This is the key source. Only 76 nodes in the ingredient taxonomy declare an allergen; everything else inherits it from a parent. `ingredient_allergens()` walks up every ingredient's parents once (`ancestors()`) and records what it inherits:

```
whey        → dairy (milk)      → whey means milk
wheat flour → wheat (the root)  → wheat flour means wheat and gluten
barley      (gluten)            → barley means gluten, but not wheat
oat                             → nothing
```

That gives 1,382 ingredients that carry an allergen. Without this step, whey, casein and milk powder would all look milk-free.

**4. The ingredient text.** Open Food Facts' ingredient parsing misses things, so we also search the printed list. The text is prepared in four steps:

1. **Lower-case** everything.
2. **Replace free-from claims** with a placeholder (`FREE_FROM`). "Gluten-free" or "peanut free facility" says something is absent; it isn't an ingredient. The placeholder also stops "gluten free flour" from turning into plain "flour".
3. **Remove the exceptions,** so "coconut milk" disappears before "milk" is searched for.
4. **Search for whole words, plurals included** (`phrases()`). "egg" matches "eggs" but not "eggplant", and "nut" doesn't match "coconut", "nutmeg" or "doughnut".

Two refinements came from checking real records:

- **Prefix words.** A trailing `*` (`soy*`, `milk*`, `peanut*`) also matches longer words, because many records run words together: "soybeanoil", "milkpowder", "peanutbutter".
- **Plain flour is wheat** (`PLAIN_FLOUR`, plus phrases like "enriched flour"). On US labels, flour with no grain named is wheat flour by definition. Open Food Facts files plain "flour" as generic, not under wheat, so without this rule "flour, sugar, eggs" passed the wheat check. "Rice flour", "mustard flour" and "gluten free flour blend" don't match.

### 4.3 When a PASS is allowed

If no source mentions the allergen, `ingredients_problem()` checks whether the ingredient list is good enough to trust:

| Problem | Meaning | Verdict |
|---|---|---|
| `no_ingredients` | No English ingredient list | UNKNOWN |
| `not_parsed` | Open Food Facts couldn't split it into ingredients | UNKNOWN |
| `low_recognition` | Under 80% of the ingredients recognized | UNKNOWN |
| none of these | | **PASS** |

**Why 80%:** an unrecognized ingredient could be the allergen under a name we don't know. The threshold is a safety setting, not something to tune for better scores. Of the 307,604 products with an English ingredient list, 245,620 meet it.

**Evidence beats missing information.** A product with no ingredient list but "peanuts" in its allergen list is FAIL, not UNKNOWN.

### 4.4 Deliberately conservative choices

Each of these can wrongly exclude a product, but none can wrongly include one:

- **A gluten tag counts as possible wheat:** the gluten might come from barley, but the tag doesn't say which grain.
- **Generic "nuts" counts as tree nuts:** "may contain nuts" usually means tree nuts.
- **Pine, shea and kola nuts count as tree nuts,** because the FDA's tree-nut list has included them. Coconut doesn't; Open Food Facts files it as a fruit.
- **Soya oil counts as soy,** following the taxonomy, even though US law exempts highly refined oils.

## 5. What gets stored

`add_verdicts()` adds these columns to `products.parquet` and the sample:

| Column | Meaning |
|---|---|
| `ingredients_check` | `ok`, or which problem applies |
| `allergen_peanuts`, `allergen_milk`, … | 0 FAIL, 1 PASS, 2 UNKNOWN |
| `allergen_peanuts_sources`, … | For a FAIL, which sources fired, such as `allergen list+ingredient+ingredient text` |

The detailed evidence (which tag, which ingredient, which word) isn't stored. `check()` recomputes it for the few products shown on screen, so the stored verdict and the displayed explanation can never disagree.

## 6. How we know it works

**1. Real products.**

| Product | Result |
|---|---|
| Nutella (allergen tags list only nuts) | Fails milk ("skimmed milk powder") and soy ("lecithins (soya)") |
| Cheerios | Passes peanuts, milk, gluten, wheat and tree nuts |
| Magic Spoon "Peanut Butter" | Fails peanuts with evidence from three sources |

**2. Hunting for misses.** We searched the ingredient lists of every product that passed for anything allergen-like. That found:

- soy words run together ("soymilk", "soybeanoil");
- "lysozyme", a preservative made from egg;
- "whitefish roe";
- plain "flour, sugar, …" passing wheat.

All are fixed.

**3. Hunting for false alarms.** We looked at what triggered every fail that rested on the ingredient text alone. That found almond, cashew and sunflower butter failing milk, and soy nuts and corn nuts failing tree nuts. All are fixed. About 750 dairy-free products now correctly pass milk.

**4. Tests.** 36 tests in `tests/test_allergens.py` lock in every rule and lookalike. They use a tiny hand-made taxonomy, so they run in under a second without the data.

## 7. Results

| Allergen | FAIL | PASS | UNKNOWN |
|---|---|---|---|
| milk | 102,537 | 154,646 | 92,125 (26%) |
| eggs | 31,430 | 216,596 | 101,282 (29%) |
| fish | 6,129 | 241,143 | 102,036 (29%) |
| crustaceans | 2,985 | 243,463 | 102,860 (29%) |
| molluscs | 1,055 | 244,804 | 103,449 (30%) |
| tree nuts | 25,823 | 223,524 | 99,961 (29%) |
| peanuts | 16,286 | 231,283 | 101,739 (29%) |
| wheat | 76,100 | 175,238 | 97,970 (28%) |
| gluten | 77,150 | 174,440 | 97,718 (28%) |
| soybeans | 88,715 | 163,931 | 96,662 (28%) |
| sesame | 9,138 | 237,598 | 102,572 (29%) |

Roughly 26–30% of products can't be verified for any given allergen. That is the price of never treating missing data as safe, and the report will show it.

## 8. What it can't catch

- **Records that are simply wrong,** for example an ingredient missing from the label entry. The optional photo audit addresses this.
- **Ingredient text in another language** that slipped through the English check. We saw a couple of German ones.
- **Missing "may contain" statements.** They are voluntary on US labels, so their absence proves nothing.

## 9. Try it

```python
import json

import pandas as pd

from foodswap import allergens

products = pd.read_parquet("data/corpus/products.parquet")
carried = allergens.ingredient_allergens(json.load(open("data/raw/taxonomies/ingredients.json")))

cheerios = products[products.code == "0016000170032"].iloc[0]
cereals = products[(products.comparison_category == cheerios.comparison_category)
                   & (products.family_id != cheerios.family_id)]
print(cereals.allergen_peanuts.map({0: "FAIL", 1: "PASS", 2: "UNKNOWN"}).value_counts())

peanut_butter = cereals[cereals.name == "Peanut Butter"].iloc[0]
print(allergens.check(peanut_butter, "peanuts", carried))
```

Output:

```
allergen_peanuts
PASS       229
UNKNOWN     48
FAIL         9

(<Verdict.FAIL: 0>, [('allergen list', 'en:peanuts'), ('ingredient', 'en:peanut-oil'),
  ('ingredient', 'en:peanut-flour'), ('ingredient', 'en:peanut'),
  ('ingredient text', 'peanut'), ('ingredient text', 'peanut'), ('ingredient text', 'peanut')])
```

The full design is in [constraints and safety](../07-constraints-and-safety.md).
