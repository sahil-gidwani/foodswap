# 07 · Constraints and safety

**Use:** design. This is the safety-critical part of the system; changes need a second reviewer and an entry in [decisions.md](decisions.md).
**Read by:** QUX role (owner of the evidence builder); EVAL (owner of the vocabulary, T3.1); everyone for sections 8–9.
**Last updated:** 2026-11-14. The allergen check is implemented in `foodswap/allergens.py` and runs inside `python -m foodswap.data build`; tests are in `tests/test_allergens.py`.

## 1. Principle

A hard constraint is something every result must satisfy: an excluded allergen, an excluded ingredient, or a numeric limit. For each product and constraint, FoodSwap records one of three verdicts with the evidence behind it:

| Verdict | Meaning | Effect |
|---|---|---|
| **FAIL** | At least one source in the record says the product contains, or may contain, the excluded item, or the value breaks the limit. | Not eligible. Listed in the why-not drawer with the evidence. |
| **PASS** | The record has enough information to check, and no source mentions the item. | Eligible. |
| **UNKNOWN** | The record does not have enough information to check. | **Not eligible** (default policy). Listed with the reason. |

"PASS" means **"not declared in the record we hold"**. It never means "safe". Records are crowd-sourced and can be incomplete, outdated or wrong, and in the US "may contain" statements are voluntary, so their absence proves nothing. Every place PASS appears in the UI says what was checked.

Why three values: the alternative, treating missing evidence as a pass, is the failure the proposal promised to avoid ("products with missing or ambiguous evidence will be rejected rather than deemed safe"). OFF's own preference matching makes the same distinction with its `unknown_match` status ([docs](https://openfoodfacts.github.io/openfoodfacts-server/dev/explain-personal-search)).

## 2. Vocabulary

The vocabulary (`ALLERGENS` in `foodswap/allergens.py`) maps each allergen to what the data contains. It covers the nine US major food allergens ([FDA](https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies)) plus gluten, and molluscs (reached only through "shellfish").

| Id | OFF allergen tag | Ingredient taxonomy evidence | Text words (a `*` also matches longer words) | Exceptions (must not match) |
|---|---|---|---|---|
| `milk` | `en:milk` | ingredients inheriting `allergens: en:milk` (whey, casein, milk powder, …) | milk\*, cream, butter, buttermilk, butterfat, butteroil, cheese, whey, casein, caseinate, lactose, lactalbumin, lactoglobulin, yogurt, ghee, curd, paneer | plant milks and creams (coconut, almond, oat, soy, rice, cashew, hemp, pea, flax, hazelnut, macadamia); plant, nut and seed butters (cocoa, cacao, shea, mango, coconut, peanut, almond, cashew, hazelnut, sunflower, soy, sesame, …); cream of tartar; bean curd |
| `eggs` | `en:eggs` | `allergens: en:eggs` | egg, albumen, albumin, ovalbumin, lysozyme, mayonnaise, meringue | (eggplant never matches "egg") |
| `fish` | `en:fish` | `allergens: en:fish` | fish, anchovy, cod, salmon, tuna, tilapia, pollock, sardine, haddock, trout, mackerel, herring, catfish, halibut, whitefish, lumpfish, monkfish, swordfish, bonito, hake, flounder, roe, caviar | (shellfish never matches "fish") |
| `crustaceans` | `en:crustaceans` | `allergens: en:crustaceans` | shrimp, prawn, crab, lobster, crayfish, crawfish, krill | |
| `molluscs` | `en:molluscs` | `allergens: en:molluscs` | clam, mussel, oyster, scallop, squid, octopus, calamari, snail, escargot, abalone | oyster mushroom |
| `tree_nuts` | `en:nuts` | `allergens: en:nuts` | nut, almond\*, cashew\*, hazelnut\*, filbert, walnut\*, pecan\*, pistachio\*, macadamia\*, chestnut, praline, marzipan | water chestnut, soy nut, corn nut, hemp nut, sunflower nut, tiger nut |
| `peanuts` | `en:peanuts` | `allergens: en:peanuts` | peanut\*, groundnut, ground nut, arachis | |
| `wheat` | `en:gluten` (possible wheat) | ingredients at or below `en:wheat` | wheat\*, spelt, durum, semolina, farina, kamut, einkorn, emmer, farro, bulgur, couscous, seitan, graham, triticale, **plain flour** (below) | (buckwheat never matches "wheat") |
| `gluten` | `en:gluten` | `allergens: en:gluten` (wheat, barley, rye, …) | gluten, the wheat words, barley, rye, malt, **plain flour** | (maltodextrin and maltose never match "malt") |
| `soybeans` | `en:soybeans` | `allergens: en:soybeans` | soy\*, edamame, tofu, tempeh, miso | |
| `sesame` | `en:sesame-seeds` | `allergens: en:sesame-seeds` | sesame\*, tahini, benne | |

How the text is searched:

- **Whole words, plurals included.** "egg" matches "eggs" but not "eggplant"; "fish" doesn't match "shellfish"; "nut" doesn't match "coconut", "nutmeg" or "doughnut".
- **Prefix words.** A trailing `*` also matches longer words, because many records run words together: "soybeanoil", "soylecithin", "milkpowder", "peanutbutter", "pistachionut", "sesameoil".
- **Exceptions** are removed from the text before the words are searched.
- **Free-from claims** ("gluten-free", "peanut free facility") are replaced by a placeholder before searching. A claim of absence is not an ingredient, and the placeholder stops "gluten free flour" from turning into plain "flour".
- **Plain flour is wheat.** On US labels, flour with no grain named is wheat flour. So "flour" listed on its own as an ingredient ("flour, sugar, …", "…: flour (…)"), and phrases such as "enriched flour", "bleached flour" and "all purpose flour", count as wheat and gluten. "Rice flour", "mustard flour" and "gluten free flour blend" don't. Open Food Facts files plain "flour" as a generic ingredient, not under wheat, so this rule has to live in the text search.

Notes:

- **Wheat.** A product tagged `en:gluten` may get its gluten from barley or rye rather than wheat. A gluten tag therefore counts as possible wheat. This is conservative; through the taxonomy, barley carries gluten but not wheat.
- **"Nuts"** expands to `peanuts` and `tree_nuts`, and **"shellfish"** to `crustaceans` and `molluscs` ([05](05-query-understanding.md#25-ambiguity-rules)). Molluscs are not a US major allergen; the UI says so.
- **Pine nut, shea nut and kola nut** count as tree nuts, because the FDA's tree-nut list has included them. Coconut does not: Open Food Facts files it under fruit.
- The other EU allergens (celery, mustard, lupin, sulphites) are Stretch (F-C13): one vocabulary entry each.

## 3. Evidence sources and the verdict rule

### 3.1 Allergen and ingredient exclusions

Four sources can show an allergen. The names below are what the code records as evidence:

| Source | Positive when |
|---|---|
| `allergen list` | `allergen_tags` contains the allergen's OFF tag |
| `may contain` | `trace_tags` contains it |
| `ingredient` | an entry in `ingredient_tags` carries the allergen, directly or inherited through the ingredient taxonomy. Only 76 ingredient nodes declare an allergen; 1,382 ingredients inherit one, for example whey → dairy → milk. |
| `ingredient text` | the English ingredient text matches the words, after exceptions and free-from claims are removed |

Free-from labels (`en:no-gluten` and similar) are not used as evidence. They never turn a positive source into a PASS, and they never stand in for a missing ingredient list.

The rule, in order:

1. **FAIL** if any source is positive. A "may contain" statement fails by default (the stricter reading; F-C12 adds an opt-in mode that accepts traces).
2. **PASS** if no source is positive **and** the product has English ingredient text **and** OFF recognized at least a share θ of its ingredients:

   ```
   recognized_share = (ingredients_n − unknown_ingredients_n) / ingredients_n   ≥   θ = 0.8
   ```

3. **UNKNOWN** otherwise, with a reason code:

| Reason code | Condition | Shown as |
|---|---|---|
| `no_ingredients` | no English ingredient text | "Cannot verify: no English ingredient list" |
| `not_parsed` | `ingredients_n` missing or 0 | "Cannot verify: ingredient list not parsed" |
| `low_recognition` | recognized share below θ | "Cannot verify: {k} of {n} ingredients not recognized" |

Rules about conflicting sources:

- θ = 0.8 is a safety parameter, not a tuning knob. Its effect on coverage is reported as a sensitivity curve (S8), and the default changes only through a logged decision.
- If a product's main language is not English, `ingredients_n` and `unknown_ingredients_n` describe OFF's parse of the main-language text, while our lexicon checks the English text. Both checks still have to pass.

**Ingredient exclusions that are not allergens** ("no gelatin", "no palm oil") use the same rule with the `ingredient` and `ingredient text` sources. They are checked at query time, since the list of possible ingredients is open:

- Core matches the exact ingredient id and its English names.
- Should (S7) also matches every descendant in the ingredient taxonomy, so "no palm oil" also catches "palm kernel oil" if the taxonomy places it below palm oil.

### 3.2 Numeric limits

| Condition | Verdict |
|---|---|
| Value present and within the limit | PASS ("Sugars 6.0 g per 100 g; limit 8 g") |
| Value present and outside the limit | FAIL |
| Value missing | UNKNOWN ("Sugars not reported") |

Limits apply per 100 g, or per 100 ml for products measured in ml. Numeric verdicts are computed at query time from the nutrient matrix.

### 3.3 Category compatibility

Category is not a verdict. Products outside the comparison category ([03](03-data-pipeline.md#52-comparison-category)) are simply not candidates; the UI shows how many products the category holds.

## 4. Storage and results

The verdicts are columns of `data/corpus/products.parquet` (and the sample), added during the build:

| Column | Meaning |
|---|---|
| `ingredients_check` | `ok`, or why the ingredient list can't support a PASS: `no_ingredients`, `not_parsed`, `low_recognition` |
| `allergen_<name>` | 0 FAIL, 1 PASS, 2 UNKNOWN, one column per allergen (`allergen_peanuts`, …) |
| `allergen_<name>_sources` | for a FAIL, which sources fired, joined by `+` (e.g. `allergen list+ingredient+ingredient text`) |

The detailed evidence (which tag, which ingredient, which words) is recomputed by `allergens.check()` at display time, only for the products on screen.

Results on the 2026-11-14 snapshot, 349,308 products:

| Allergen | FAIL | PASS | UNKNOWN |
|---|---|---|---|
| milk | 102,537 | 154,646 | 92,125 (26%) |
| eggs | 31,430 | 216,596 | 101,282 (29%) |
| fish | 6,129 | 241,143 | 102,036 (29%) |
| crustaceans | 2,985 | 243,463 | 102,860 (29%) |
| molluscs | 1,055 | 244,804 | 103,449 (30%) |
| tree_nuts | 25,823 | 223,524 | 99,961 (29%) |
| peanuts | 16,286 | 231,283 | 101,739 (29%) |
| wheat | 76,100 | 175,238 | 97,970 (28%) |
| gluten | 77,150 | 174,440 | 97,718 (28%) |
| soybeans | 88,715 | 163,931 | 96,662 (28%) |
| sesame | 9,138 | 237,598 | 102,572 (29%) |

Roughly 26–30% of products can't be verified for any given allergen. Mostly they have no English ingredient list, or Open Food Facts recognized less than 80% of the ingredients. That is the coverage cost of the conservative rule (section 6).

Ingredient exclusions outside the vocabulary are evaluated at query time, from `ingredient_tags` and the ingredient text.

## 5. Numeric and claim language

| User says | Core behaviour | Why |
|---|---|---|
| "less sugar", "low sugar", "lower sodium", "high protein" | Soft goal (direction only) | FDA defines no "low sugar" claim, and its other claims are per serving (reference amount), which our per-100 data cannot apply reliably |
| "under 8 g sugar", "at least 10 g protein" | Hard limit per 100 g or 100 ml | Explicit numbers are unambiguous |
| "sugar-free", "fat-free", "low-sodium" stated as a requirement | Clarification proposing a number, e.g. "sugar-free: sugars ≤ 0.5 g per 100 g?" (the EU per-100 g definition, which also matches FDA's 0.5 g) | Claim thresholds are Stretch (F-Q10) |

Reference thresholds for these proposals and for the report are listed in [02](02-data-sources.md#42-nutrient-claim-thresholds). Unit trap: OFF stores sodium in grams, while US rules are written in milligrams.

## 6. The cost of being conservative

Rejecting UNKNOWN lowers coverage, and the cost is a result to report, not a problem to hide (RQ4):

- The audit reports PASS / FAIL / UNKNOWN shares per allergen ([03](03-data-pipeline.md#7-the-missingness-and-coverage-audit)).
- The evaluation reports coverage (scenarios with at least five eligible results) and the unknown-rejection rate.
- An automatic-metrics ablation (U1, `unknown_policy: allow`) shows how many unverifiable products would otherwise reach the top five. It is never shown to users as a default.

If more than a quarter of dev scenarios end with fewer than five eligible results:

1. Report it as a finding.
2. Check that scenario references come from well-populated categories (scenarios are chosen before any system output is seen).
3. Look at the θ sensitivity curve.
4. Consider a "show unverified products" section (Stretch), off by default and visually separate from the results, under a warning.

The default policy is never relaxed silently.

**Fairness note.** Products from large brands tend to have more complete records (they are scanned more), so rejecting unknowns favours well-documented brands. The report states this.

## 7. Tests

`tests/test_allergens.py` (run with `python -m pytest`) uses a small hand-made taxonomy, so it needs no download. It checks:

- inheritance through the taxonomy (whey → milk; wheat flour → wheat and gluten; barley → gluten only; oats → nothing);
- that each source alone is enough to FAIL;
- that a clean record passes;
- that each kind of missing information gives UNKNOWN, never PASS, while positive evidence still gives FAIL;
- that a gluten tag counts as possible wheat;
- lookalikes that must not match: plant milks and butters, eggplant, coconut, nutmeg, doughnut, water chestnut, soy nuts, buckwheat, rice and mustard flour, "gluten free flour blend", maltodextrin, free-from claims, shellfish versus fish;
- real mentions that must match: "milkpowder", "butterfat", "lactalbumin", "lysozyme", "whitefish roe", "pistachionut", "peanutbutter", "soybeanoil", "sesameoil", "flour, sugar", "enriched bleached flour", malt vinegar.

Checks against real records, run on the 2026-11-14 snapshot:

| Record | Result |
|---|---|
| Nutella `3017624010701` (allergen tags list only nuts) | milk FAIL (may contain + "skimmed milk powder"); soy FAIL (may contain + "lecithins (soya)"); tree nuts FAIL (allergen list + "hazelnuts") |
| Cheerios `0016000170032` | PASS for peanuts, milk, gluten, wheat and tree nuts |
| Magic Spoon "Peanut Butter" cereal | peanuts FAIL (allergen list, peanut flour, peanut oil, text); milk FAIL (casein, whey protein) |

**How the word lists were tested.** We searched the ingredient text of every PASS product for allergen-like fragments, and every text-only FAIL for the words in front of the match. That surfaced:

- **misses:** "soymilk", "soybeanoil", "lysozyme", "whitefish roe", and plain "flour, sugar, …" passing wheat;
- **false alarms:** almond, cashew and sunflower butter failing milk; soy nuts and corn nuts failing tree nuts.

Each was fixed and has a test. Re-running the same searches finds none of them.

Should (S2) adds a hand audit of about 100 (product, allergen) verdicts stratified by verdict, checked against the ingredient-panel photos on OFF. It reports the false-pass rate with a confidence interval. With zero false passes in 100, the one-sided 95% upper bound is still about 3%. Products with photos are not a random sample, which the report states.

## 8. Wording rules and disclaimers

Explanations are filled-in templates ([08](08-explanations-and-ui.md#2-explanation-templates)). No text is generated, and no health claims are made.

| Never say | Say instead |
|---|---|
| safe, allergy-safe, safe for you | "No peanut declared in this record (allergen tags, traces and ingredients checked)" |
| peanut-free (as our claim) | "No peanut declared" |
| healthy, healthier, good for you | "6.0 g vs 14.0 g sugars per 100 g (57% less than {reference})" |
| recommended | "Matches your request" |
| Nutri-Score A means healthy | "Nutri-Score A, as computed by Open Food Facts" |

Nutri-Score is a European front-of-pack score and is not used on US packages; a tooltip says so.

**Persistent footer** in the app, video and slides:

> FoodSwap uses crowd-sourced data from Open Food Facts (snapshot {date}), available under the Open Database License. Records can be incomplete, outdated or wrong. "No peanut declared" means no peanut appears in the record we hold; it is not a guarantee. Always read the package. This is a research prototype, not medical or allergy advice.

## 9. Ethics and privacy

| Risk | Mitigation |
|---|---|
| A person with a severe allergy trusts a wrong PASS (bad record or a lexicon gap) | Traces fail by default; unknown is ineligible; evidence shown; disclaimer everywhere; audit (S2); framed as a research prototype |
| Nudging toward products on the strength of noisy nutrient data | Values and sources shown; quality gates; link to the OFF record; no claims |
| Over-trust in a polished UI | The "cannot verify" counts are always visible, not hidden in a menu |
| Uneven coverage across brands | Reported (section 6) |
| Data rights | ODbL attribution in the app, video, report and README; CC BY-SA credit for images |
| Privacy | No accounts and no stored requests. Timing logs record scenario ids, never free text. A user study (Later) would need an IRB determination and would use personas rather than participants' own allergy data. |

## 10. To verify on the snapshot

- Which ingredient-taxonomy entries carry each allergen property (for example oats and gluten).
- Whether refined soybean oil carries the soybeans property. US law (FALCPA) excludes highly refined oils from the definition of a major food allergen *(from memory; verify)*, so OFF may not flag it. Core follows the taxonomy and documents the choice.
- FDA's current list of tree nuts. FDA revised its allergen guidance in January 2025, reportedly narrowing the tree-nut list *(unverified)*. The lexicon follows OFF's `en:nuts` and adds only clear tree-nut names.
- The exact free-from label ids present in OFF (`en:no-gluten` is confirmed in probes; others to check).
