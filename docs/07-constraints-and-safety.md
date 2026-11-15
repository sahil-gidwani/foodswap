# 07 · Constraints and safety

**Use:** design. This is the safety-critical part of the system; changes need a second reviewer and an entry in [decisions.md](decisions.md).
**Read by:** QUX role (owner of the evidence builder); EVAL (owner of the vocabulary, T3.1); everyone for sections 8–9.
**Last updated:** 2026-11-10.

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

The vocabulary (task T3.1, a Python dict next to the evidence code) maps what users say to what the data contains. Core covers the nine US major food allergens ([FDA](https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies)) plus gluten, and molluscs (reached only through "shellfish").

| Id | User words | OFF allergen tag | Ingredient taxonomy evidence | Text lexicon (examples) | Exceptions (must not match) |
|---|---|---|---|---|---|
| `milk` | milk, dairy, lactose, casein, whey | `en:milk` | ingredients whose `allergens` property is `en:milk` | milk, cream, butter, cheese, whey, casein, caseinate, lactose, yogurt, yoghurt, ghee, curd, buttermilk | coconut milk, almond milk, oat milk, soy milk, rice milk, cocoa butter, peanut butter, nut butter, apple butter, butternut, cream of tartar |
| `eggs` | egg, eggs | `en:eggs` | `allergens` = `en:eggs` | egg, albumen, albumin, ovalbumin, mayonnaise, meringue | eggplant |
| `fish` | fish | `en:fish` | `allergens` = `en:fish` | anchovy, cod, salmon, tuna, tilapia, pollock, sardine, fish sauce | shellfish |
| `crustaceans` | crustaceans, crustacean shellfish, shellfish | `en:crustaceans` | `allergens` = `en:crustaceans` | shrimp, prawn, crab, lobster, crayfish, krill | |
| `molluscs` | molluscs, mollusks, shellfish | `en:molluscs` | `allergens` = `en:molluscs` | clam, mussel, oyster, scallop, squid, octopus | |
| `tree_nuts` | tree nuts, nuts | `en:nuts` | `allergens` = `en:nuts` | almond, cashew, hazelnut, filbert, walnut, pecan, pistachio, macadamia, brazil nut, praline, marzipan | nutmeg, butternut, water chestnut, doughnut, donut |
| `peanuts` | peanut, peanuts, groundnut | `en:peanuts` | `allergens` = `en:peanuts` | peanut, groundnut, arachis | |
| `wheat` | wheat | none (OFF has no wheat node) | ingredients at or below `en:wheat` in the ingredient taxonomy; an `en:gluten` allergen or trace tag also counts (see note) | wheat, spelt, durum, semolina, farina, kamut, einkorn, emmer, bulgur, couscous, seitan | buckwheat |
| `gluten` | gluten | `en:gluten` | `allergens` = `en:gluten` | the wheat terms plus barley, rye, malt, triticale | buckwheat |
| `soybeans` | soy, soya, soybean | `en:soybeans` | `allergens` = `en:soybeans` | soy, soya, soybean, edamame, tofu, tempeh, miso | |
| `sesame` | sesame | `en:sesame-seeds` | `allergens` = `en:sesame-seeds` | sesame, tahini, benne | |

Notes:

- **Wheat.** A product tagged `en:gluten` may get its gluten from barley or rye rather than wheat. Core treats a gluten tag as possible wheat (FAIL with the detail "gluten declared; grain not identified"). This is conservative, and the audit counts how often it happens.
- **"Nuts"** expands to `peanuts` and `tree_nuts`; **"shellfish"** to `crustaceans` and `molluscs` ([05](05-query-understanding.md#25-ambiguity-rules)). Molluscs are not a US major allergen; the UI says so.
- Exception phrases are removed from the ingredient text before the lexicon runs, and every exception has a test.
- The other EU allergens (celery, mustard, lupin, sulphites) are Stretch (F-C13): one vocabulary entry each.

## 3. Evidence sources and the verdict rule

### 3.1 Allergen and ingredient exclusions

Each source sets one bit:

| Bit | Source | Positive when |
|---|---|---|
| 0 | `allergen_tag` | `allergen_tags` contains the item's OFF tag |
| 1 | `trace_tag` | `trace_tags` contains it ("may contain") |
| 2 | `ingredient_taxonomy` | an entry in `ingredient_tags` carries the allergen in its `allergens` property, directly or inherited through the ingredient taxonomy |
| 3 | `ingredient_text` | the English ingredient text matches the lexicon after exception phrases are removed |
| 4 | `label` | a free-from label is present (for example `en:no-gluten`); supporting evidence only |

The rule, in order:

1. **FAIL** if any of bits 0–3 is set. A "may contain" statement fails by default (the stricter reading; F-C12 adds an opt-in mode that accepts traces).
2. **PASS** if bits 0–3 are all clear **and** the product has English ingredient text **and** OFF recognized at least a share θ of its ingredients:

   ```
   recognized_share = (ingredients_n − unknown_ingredients_n) / ingredients_n   ≥   θ = 0.8
   ```

3. **UNKNOWN** otherwise, with a reason code:

| Reason code | Condition | Shown as |
|---|---|---|
| `no_ingredients` | no English ingredient text | "Cannot verify: no English ingredient list" |
| `no_parsed_ingredients` | `ingredients_n` missing or 0 | "Cannot verify: ingredient list not parsed" |
| `low_recognition` | recognized share below θ | "Cannot verify: {k} of {n} ingredients not recognized" |

Rules about conflicting sources:

- A free-from label never turns a positive source into a PASS. A conflict between a label and a tag is flagged for the audit.
- A free-from label alone, without an ingredient list, is not enough for PASS. The audit reports how many labelled products this rule rejects.
- θ = 0.8 is a safety parameter, not a tuning knob. Its effect on coverage is reported as a sensitivity curve (S8), and the default changes only through a logged decision.
- If a product's main language is not English, `ingredients_n` and `unknown_ingredients_n` describe OFF's parse of the main-language text, while our lexicon checks the English text. Both checks still have to pass.

**Ingredient exclusions that are not allergens** ("no gelatin", "no palm oil") use the same rule with bits 2 and 3:

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

## 4. Storage

`data/corpus/evidence.parquet`, built offline by the evidence step (T3.2):

| Column | Type | Meaning |
|---|---|---|
| `idx` | int32 | Row index |
| `has_en_ingredients` | bool | |
| `recognized_share` | float32 | NaN when not computable |
| `<item>_verdict` | int8 | 0 FAIL, 1 PASS, 2 UNKNOWN, one column per vocabulary item |
| `<item>_sources` | uint8 | Bitmask from section 3.1 |
| `<item>_reason` | uint8 | Reason code for UNKNOWN |

Human-readable details (for example 'ingredient "skimmed milk powder" maps to `en:milk`') are recomputed at display time, and only for the products on screen.

Ingredient exclusions outside the vocabulary are evaluated at query time:

- **Tags:** an ingredient-id → products posting list built with the corpus.
- **Text:** the BM25 ingredients index finds documents that contain the term, and the lexicon regex runs only on those.

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

Golden tests (T3.2) run on frozen copies of records captured from the pinned snapshot, so they work whether or not a record is in the US corpus. Expected verdicts are filled in by hand when fixtures are captured and checked by a second person.

| Case | Record | Expected |
|---|---|---|
| Allergen tags under-report | Nutella `3017624010701` (allergen tag lists only nuts) | `milk` FAIL via ingredients ("skimmed milk powder"); `soybeans` FAIL via trace tag and ingredients; `tree_nuts` FAIL via allergen tag |
| No English ingredients | Crownfield bran flakes `20621483` (Italian text) | Allergens without a positive tag → UNKNOWN (`no_ingredients`); `milk` and `peanuts` FAIL via tags |
| Allergen tags over-report | Nature's Path granola `0058449770565` | `peanuts` FAIL via allergen tag although the ingredient list has none (conservative) |
| Families | Cheerios `0016000275263`, `0016000170032` | Same family (T2.5) |
| Vandalized record | Cheerios `0016000275287` | Outside the searchable set (T2.3); non-canonical tag `en:Corn` dropped |

Synthetic records cover every rule:

| Record | Expected |
|---|---|
| Allergen tag only | FAIL |
| Trace tag only | FAIL |
| Ingredient tag whose taxonomy entry carries the allergen (e.g. whey → milk) | FAIL |
| Text match only ("contains peanut flour") | FAIL |
| No English text | UNKNOWN (`no_ingredients`) |
| English text, recognized share 0.5 | UNKNOWN (`low_recognition`) |
| Clean record, recognized share 1.0 | PASS |
| Free-from label plus a positive tag | FAIL, conflict flagged |
| Free-from label, no ingredient list | UNKNOWN |
| Sugar 8.0 g, limit ≤ 8 g / 8.01 g / missing | PASS / FAIL / UNKNOWN |
| "140 mg sodium" limit on a product with 0.15 g sodium | FAIL (unit conversion) |

Lexicon exceptions, each a test:

| Text | Must not match | Must match |
|---|---|---|
| "coconut milk", "almond milk", "oat milk" | milk | |
| "cocoa butter" | milk | |
| "peanut butter" | milk | peanuts |
| "nutmeg", "water chestnut", "doughnut" | tree nuts | |
| "butternut squash" | milk, tree nuts | |
| "eggplant" | eggs | |
| "buckwheat" | wheat, gluten | |
| "cream of tartar" | milk | |

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
