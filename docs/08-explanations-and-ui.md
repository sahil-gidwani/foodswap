# 08 · Explanations and UI

**Use:** design.
**Read by:** QUX role (owner); EVAL for the labeling page; everyone before recording the video.
**Last updated:** 2026-11-10.

## 1. Principles

- **Templates only.** Every explanation is a fixed template filled with values from the product record. Generated text is out of scope: generated explanations can read well and still be wrong (Turpin et al., NeurIPS 2023; Kabongo and Guigue, 2025).
- **Help users judge, not persuade.** Explanations should help a user estimate whether a product suits them, not oversell it (Bilgic and Mooney, 2005). Of the aims in Tintarev and Masthoff's framework, FoodSwap targets transparency, scrutability and effectiveness, not persuasiveness.
- **Every number is checkable.** A test recomputes each displayed number from the record (section 7).
- **Uncertainty is visible.** "Cannot verify" is a first-class outcome with counts, not a footnote.

## 2. Explanation templates

| Situation | Template | Example |
|---|---|---|
| Allergen PASS | ✓ No {item} declared ({sources checked}) | ✓ No peanut declared (allergen tags, traces and ingredient list checked) |
| Allergen FAIL | ✗ Contains {item}: {evidence} | ✗ Contains milk: ingredient "skimmed milk powder" |
| Trace FAIL | ✗ May contain {item} (label statement) | ✗ May contain peanut (label statement) |
| UNKNOWN, no ingredients | ? Cannot verify {item}: no English ingredient list | |
| UNKNOWN, low recognition | ? Cannot verify {item}: {k} of {n} ingredients not recognized | ? Cannot verify milk: 4 of 11 ingredients not recognized |
| Numeric PASS | ✓ {Nutrient} {v} g per 100 {basis} (your limit: {L} g) | ✓ Sugars 6.0 g per 100 g (your limit: 8 g) |
| Numeric FAIL | ✗ {Nutrient} {v} g per 100 {basis} is above your limit of {L} g | |
| Numeric UNKNOWN | ? {Nutrient} not reported | |
| Goal met | {Nutrient}: {v_p} vs {v_o} per 100 {basis} ({p}% {less/more} than {reference}) | Sugars: 3.0 g vs 5.1 g per 100 g (41% less than Cheerios) |
| Goal not met | {Nutrient}: {v_p} vs {v_o} per 100 {basis}, not {lower/higher} than {reference} | |
| Unmentioned regression | Note: {nutrient} {v_p} vs {v_o} per 100 {basis}, higher than {reference} | Note: sodium 700 mg vs 487 mg per 100 g, higher than Cheerios |
| Similarity | Same category: {category} · shares {m} ingredients with {reference} | Same category: Breakfast cereals · shares 4 ingredients with Cheerios |
| Family | Also sold in {n} other sizes | |
| OFF scores | Nutri-Score {grade} · NOVA group {g}, as computed by Open Food Facts | |

Formatting rules:

- **Grams:** one decimal place below 10 g, whole numbers from 10 g up.
- **Sodium:** in mg.
- **Percentages:** whole numbers, computed as (v_o − v_p) / v_o. When v_o is 0, show values only.
- **Sources:** "{sources checked}" lists only the sources that exist on that record. A product with no trace information says "allergen tags and ingredient list checked".
- **Ingredient overlap:** shown as a separate, literal fact (the shared canonical ingredient ids). It complements the embedding-based similarity score C rather than claiming to explain it.

## 3. Why-not drawer

Under the results, a collapsed section titled "Why were other products excluded?":

```
Breakfast cereals in this snapshot: {in_category}
  eligible for your request:       {eligible}
  contain or may contain peanut:   {failed_peanuts}   e.g. {up to 5 product names}
  cannot verify peanut:            {unknown_peanuts}  ({no_ingredients} have no English ingredient list)
  above your sugar limit:          {failed_sugars}
```

Below the counts, the top 50 candidates by relevance that were rejected, grouped by reason, each with its evidence line and a link to its OFF record.

**When fewer than five products are eligible**, a banner replaces silence:

> Only {n} breakfast cereals satisfy all your constraints with verifiable data. {u} more could not be verified and {f} contain or may contain peanut.

Offering to search the parent category is Stretch (F-C14). Soft goals never remove products, so they are never the cause.

## 4. Screens

### 4.1 Search (`app.py`)

```
┌ FoodSwap ──────────────────────────────────────────────────────────────┐
│ Reference product   [ cheerios                              ] [Find]    │
│   ● Cheerios · General Mills · 18 oz · 0016000170032                    │
│     Breakfast cereals · sugars 5.1 g · protein 12.8 g per 100 g         │
│                                                                         │
│ What would you like instead?                                            │
│ [ a similar cereal with less sugar, more protein, and no peanuts ] [Go] │
│ Must:  (no peanut)          Prefer:  (sugar ↓) (protein ↑)              │
│                                                                         │
│ {eligible} of {in_category} breakfast cereals are eligible · details ▸  │
│ ─────────────────────────────────────────────────────────────────────── │
│ 1  {Product name} · {Brand}                         View on OFF ↗       │
│    ✓ No peanut declared (allergen tags, traces, ingredient list)        │
│    Sugars: {x} g vs 5.1 g per 100 g ({p}% less than Cheerios)           │
│    Protein: {y} g vs 12.8 g per 100 g ({q}% more than Cheerios)         │
│    Same category: Breakfast cereals · shares {m} ingredients            │
│    ▸ Score breakdown   ▸ Also sold in {n} other sizes                   │
│ 2  ...                                                                  │
│ ▸ Why were other products excluded?                                     │
│ ─────────────────────────────────────────────────────────────────────── │
│ Contains data from Open Food Facts (ODbL), snapshot {date}. Not allergy │
│ advice: always read the package.                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

Values in braces are placeholders. The Cheerios numbers are real values from a probe.

| Element | Behaviour | Tier |
|---|---|---|
| Reference lookup | Text input searched against the name field (BM25), top 20 shown as a pick list. A typed barcode matches exactly. A single select box over hundreds of thousands of products would not work. | Core |
| Reference card | Name, brand, size, category, key nutrients, declared allergens | Core |
| Request box | With three clickable example requests | Core |
| Parsed chips | Read-only, grouped "Must" (hard) and "Prefer" (soft), with words highlighted in the request | Core |
| Editable chips | Removing a chip reruns the search without it (one-way override; the request text is not rewritten) | Should (S4) |
| Clarification panel | Message and suggested rewrites | Core |
| Result cards | Top five, "show ten" toggle; template lines from section 2 | Core |
| Score breakdown | R, C, N, their weights and S, as a small table | Core |
| Thumbnails | From a local cache only | Should (S4) |
| Footer | Attribution, snapshot date, disclaimer | Core |
| Facets, weight sliders, product compare | | Stretch |

### 4.2 Compare systems (`pages/compare.py`)

The same reference and request run through two systems side by side, defaulting to B1 against P2. Items that violate a constraint are marked "✗ contains peanut (ingredient list)", and unverifiable ones "? cannot verify". This is the demo's key visual: the keyword baseline returns peanut products for "no peanuts".

If time runs short, it degrades to a system dropdown on the search page (cut order, [01](01-scope-and-features.md#9-cut-order)).

### 4.3 Labeling (`pages/label.py`)

Used by the two assessors ([09](09-evaluation.md#6-pooling-and-labeling-protocol)).

```
Scenario H07 · item 14 of 31                          assessor: A   [save] [next →]
Reference: {name} · {brand} · {category}
Request:   "a similar yogurt without gelatin, under 8 g sugar"
────────────────────────────────────────────────────────────────────────────────
Candidate: {name} · {brand} · {category}
Ingredients:        {English ingredient text}
Allergens declared: {list}      May contain: {list}
▸ Nutrition per 100 g (candidate vs reference)
────────────────────────────────────────────────────────────────────────────────
Substitutability:     ( ) 0 not a substitute   ( ) 1 partial   ( ) 2 direct
Exclusions (gelatin): ( ) satisfied   ( ) violated   ( ) cannot tell
Note: [                                                   ]
```

Requirements:

- No system names, ranks or scores are shown, and items are shuffled per scenario and assessor with a recorded seed.
- The exclusion field appears only for scenarios with hard constraints.
- The rubric, with anchored examples, is one click away.
- Nutrition is collapsed: substitutability is judged on what the product is and how it is used, and nutrient changes are scored from data instead ([09](09-evaluation.md#5-rubric)).
- Labels are appended to `eval/labels/<assessor>.jsonl` after each item, so a crash loses nothing and work can resume.
- Items returned only by B3 that are outside our corpus are displayed from the cached OFF record.

### 4.4 Results page (optional, Stretch)

A page that reads `reports/` and shows the evaluation tables and figures. Useful for the presentation, but the slides can carry the same content.

## 5. Streamlit implementation notes

- Load the corpus, indexes and model once with `st.cache_resource`. The cold-start target is under 20 seconds ([04](04-architecture.md#7-performance-budget)).
- Keep the selected reference and the last response in `st.session_state`; put the request box in a form so typing does not rerun searches.
- Avoid two-way sync between the request text and the chips; it fights Streamlit's rerun model. Chips are derived from the parse, and removing one is an override on top of the parse.
- The app is a thin client of `Pipeline.search()`. It contains no ranking logic ([04](04-architecture.md#2-five-rules)).

## 6. Demo mode

- `FOODSWAP_DEMO=1` adds a sidebar with the six scripted demo scenarios ([11](11-deliverables.md#3-live-demo-runbook)).
- Thumbnails for those scenarios are cached under `data/demo_images/`.
- Offline mode never fetches anything; "View on OFF" links stay visible but are not needed.
- A warm-up query runs at startup, so the first visible query is warm.

## 7. Tests

- **Faithfulness test (Core, T5.5):** for 1,000 random reference-candidate pairs, parse every number out of the rendered explanation and compare it with the value recomputed from the record and the formatting rules.
- **Wording lint:** a test fails if any template or UI string contains "safe", "healthy", "healthier" or "recommended".
- **Accessibility:** verdicts use an icon and words, never color alone.
