# 05 · Query understanding

**Use:** design.
**Read by:** QUX role (owner); EVAL for scenario writing; RANK for section 6.
**Last updated:** 2026-11-10.

The parser turns a free-text request into a `ParsedRequest` ([04](04-architecture.md#4-core-types)): hard constraints, soft nutrient goals, product-type terms, residual terms, and clarifications. It is rule-based, deterministic and fast. Its single most important property: **a negated term never becomes a positive query term.** Dense and lexical retrievers both treat "no peanuts" as a request for peanuts; NevIR, ExcluIR and BoolQuestions show the same failure in neural retrievers ([13](13-related-work.md#5-constraints-and-negation-in-retrieval)).

## 1. What the parser outputs

For "a similar cereal with less sugar, more protein, and no peanuts":

| Field | Value |
|---|---|
| `type_terms` | `cereal` (resolves to `en:breakfast-cereals`) |
| `residual_terms` | `similar` is a stop word, so none |
| `hard` | `exclude_allergen(peanuts)` |
| `goals` | `sugars −1`, `proteins +1` |
| `negated_terms` | `peanuts` (kept only for the negation experiment) |
| `clarifications` | none |

## 2. Supported request language (Core)

### 2.1 Exclusions

| Pattern | Examples | Result |
|---|---|---|
| `no`, `without`, `free of`, `free from`, `avoid`, `exclude`, `not containing`, `allergic to`, `can't have` followed by a list | "no peanuts or tree nuts", "without milk, eggs and soy" | One exclusion per listed item |
| `X-free`, `X free` | "gluten-free", "nut free", "dairy-free" | Exclusion of X |
| `non-X` for allergen nouns | "non-dairy" | Exclusion of X |

Each listed item is resolved against two gazetteers, in this order:

1. **Allergen gazetteer**, from the vocabulary in [07](07-constraints-and-safety.md#2-vocabulary): "peanut", "peanuts", "groundnut" → `peanuts`; "dairy", "milk", "lactose" → `milk`; "nuts" → `peanuts` + `tree_nuts` (see 2.5).
2. **Ingredient gazetteer**, from English names and synonyms in the OFF ingredient taxonomy: "gelatin" → `en:gelatin`; "palm oil" → `en:palm-oil`; "high fructose corn syrup" → `en:glucose-fructose-syrup` if that is the taxonomy's id *(to confirm on the snapshot)*.

An item found in neither becomes an `unsupported_term` clarification, never a silent drop.

### 2.2 Negation scope

A negation cue applies to the coordinated list that follows it and stops at the first of:

- a clause boundary: sentence end, semicolon, "but", "with", "and" followed by a word that is not in either gazetteer;
- a goal cue ("less", "more", "low", "high") or a number;
- a type term ("no peanuts cereal" → scope ends before "cereal").

Examples:

| Request | Exclusions | Not excluded |
|---|---|---|
| "no peanuts or tree nuts, more fiber" | peanuts, tree nuts | (fiber is a goal) |
| "no peanuts but almonds are fine" | peanuts | almonds (a "but … fine / ok" clause adds nothing to the query) |
| "without sugar" | none | "sugar" is a nutrient, so this becomes a clarification proposing "sugars ≤ 0.5 g per 100 g" |
| "not too sweet" | none | unsupported phrasing; clarification proposes "less sugar" |
| "dairy-free yogurt with almonds" | milk | "almonds" becomes a residual term (a positive lexical preference, not a constraint) |

### 2.3 Soft nutrient goals

| Cue | Direction |
|---|---|
| less, lower, reduced, fewer, lighter, low, low in, cut | −1 |
| more, higher, extra, high, high in, rich in, packed with, added | +1 |

Nutrient lexicon:

| Words | Nutrient column |
|---|---|
| sugar, sugars, sweet | `sugars` |
| added sugar, added sugars | `added_sugars` |
| protein | `proteins` |
| fat, fats | `fat` |
| saturated fat, sat fat, saturates | `saturated_fat` |
| salt | `salt` |
| sodium | `sodium` |
| fiber, fibre | `fiber` |
| calories, calorie, kcal, energy | `energy_kcal` |
| carbs, carbohydrates | `carbohydrates` |

"Low X" and "high X" without a number are directions, not thresholds ([07](07-constraints-and-safety.md#5-numeric-and-claim-language)).

### 2.4 Numeric limits

| Pattern | Example | Result |
|---|---|---|
| `under / less than / below / at most / no more than / max` N unit X | "under 8 g sugar", "less than 140 mg sodium" | `nutrient_max(X, N)` |
| X `under / below` N unit | "sugar under 8 g" | same |
| `at least / over / more than / min` N unit X | "at least 10 g protein" | `nutrient_min(X, N)` |
| N`%` X | "less than 5% sugar" | `nutrient_max(sugars, 5)` (5% of 100 g is 5 g) |

- Units: `g`, `mg` (converted to g), `kcal` / `calories` for energy. A missing unit defaults to g, except for calories.
- Basis: limits are per 100 g, or per 100 ml for products measured in ml. "Per serving" triggers a clarification in Core, because serving sizes are free text in the data (F-Q12 is Stretch).

### 2.5 Ambiguity rules

| Input | Default | Shown to the user |
|---|---|---|
| "nuts", "nut-free" | peanuts **and** tree nuts | "Treating 'nuts' as peanuts and tree nuts." Each is a separate chip that can be removed (S4). |
| "shellfish" | crustaceans **and** molluscs | Molluscs are not a US major allergen; the note says so. |
| "dairy", "lactose" | milk | "Lactose-free products can still contain milk protein; we exclude all milk." |
| "gluten" | gluten | Wheat, barley and rye sources; see [07](07-constraints-and-safety.md#2-vocabulary). |
| "sugar" goal | total sugars | "Added sugar" must be said explicitly. |

The rule is: when in doubt, choose the stricter interpretation and say so.

### 2.6 Type terms and residual terms

- **Type terms** are matched against English category names and synonyms from the OFF category taxonomy, longest match first: "granola bar", "greek yogurt", "sparkling water". The best match sets `type_category`, which overrides the reference product's comparison category ([03](03-data-pipeline.md#52-comparison-category)).
- **Residual terms** are the remaining content words after removing stop words, cues, negated items, nutrient words and numbers: "chocolate", "almonds", "crunchy", "organic". They stay in the query as soft lexical preferences.
- Words that refer to the reference ("similar", "like this", "something like") are stop words.

### 2.7 Conflicts

| Conflict | Example | Behaviour |
|---|---|---|
| The same nutrient in both directions | "less sugar and more sugar" | Clarification; neither goal is applied |
| A limit and a goal on the same nutrient | "under 8 g sugar, less sugar" | Both kept; they agree |
| A type term that contains an excluded allergen | "nut-free peanut butter" | Clarification ("peanut butter contains peanuts; did you mean another spread?") |
| An exclusion the reference itself violates | "no milk" with a dairy yogurt reference | Allowed; the note says "your reference contains milk; showing non-dairy alternatives" |

## 3. Unsupported requests

The parser recognizes these and answers with a clarification listing what it can do, instead of guessing:

| Phrase | Status | Clarification |
|---|---|---|
| healthier, better for me, clean | Unsupported | "Which nutrients matter to you? e.g. less sugar, less sodium, more fiber." |
| vegan, vegetarian | Should (S7) | Until S7 lands: "Diet filters are not supported yet." |
| organic, kosher, halal, non-GMO | Later | Label-based filters are not supported |
| keto, low-FODMAP, paleo | Later | Diet definitions are not supported |
| cheaper, on sale, at Walmart | Out of scope | No price or store data |
| kid-friendly, tastes better | Out of scope | |
| sugar-free, fat-free, low-sodium as a hard claim | Stretch (F-Q10) | Core proposes the threshold as an editable limit: "sugar-free: sugars ≤ 0.5 g per 100 g?" |

## 4. Algorithm

1. **Normalize.** Lower-case, Unicode NFKC, unify dashes, split `X-free` into `X free`, keep digits and `%`.
2. **Tokenize** on whitespace and punctuation, keeping character offsets for spans.
3. **Gazetteer matching**, longest match first, over five lexicons: allergens, ingredients, nutrients, categories, cue words. Multi-word entries ("tree nuts", "saturated fat", "greek yogurt") win over their parts.
4. **Numbers.** Attach each number and unit to the nearest nutrient within three tokens and the nearest comparison word.
5. **Scopes.** For each negation cue, collect the following list items until a boundary (section 2.2).
6. **Assemble.** Build constraints, goals, type terms and residual terms.
7. **Validate.** Apply the conflict rules and ambiguity notes; add clarifications.
8. **Report.** Return the `ParsedRequest` with spans, so the UI can highlight which words produced which chip.

Gazetteers are generated at build time from the vocabulary file and the taxonomies, plus a short hand-written list in the parser module for cue words, nutrient words and stop words. The generated gazetteers are cached with the corpus.

## 5. Clarification behaviour

- A clarification never blocks the search when something useful can still be done. The results are shown with a notice ("ignored: 'healthier'") and the clarification options.
- A clarification blocks the search only when the request has no usable content at all.
- In the evaluation, every clarification is logged. A scenario where the gold parse needs no clarification but the parser asks for one counts as a parser error (S5).

## 6. Query formulation

The formulated text is what the BM25 and dense retrievers search for. It is built from the parse, not from the raw request.

| Case | Formulated text |
|---|---|
| Type terms present | type terms + residual terms |
| No type terms | English name of the comparison category + the reference's generic name (if any) + residual terms |

Rules:

- Negated terms and nutrient words are removed (`negated_terms: drop`). For the negation experiment, `negated_terms: keep` appends them back, which reproduces what a keyword engine does with the raw request.
- Systems with `query.mode: raw` (B1, N1) search the raw request text plus the reference product's name. That is what a plain keyword engine receives. N1 removes the negated spans the parser found from that raw text.
- The dense query gets the instruction prefix the model expects; for `bge-small-en-v1.5` that is "Represent this sentence for searching relevant passages: " (from the model card).

## 7. Tests

**Core (T4.1): a 30-case regression suite** covering each pattern above, including:

- negation scope across "or", "and" and commas;
- "no peanuts but almonds are fine";
- "nut-free" expansion;
- numeric limits with mg conversion and `%`;
- a conflict;
- every unsupported phrase in section 3;
- the property that no negated item ever appears in the formulated text.

**Should (S5): about 150 annotated requests.**

- Half are written by people who did not write the parser (EVAL and DATA), to avoid testing the rules on their own author's phrasing.
- Each has a gold parse.
- Report slot-level precision, recall and F1 for exclusions, limits, goals and type category, plus exact-match rate.
- Report the downstream effect: how many scenario rankings change when the gold parse replaces the predicted one.

**Stretch (F-Q13): a local LLM parser compared with the rules.** A small open model run locally through Ollama, with output constrained by a JSON schema, scored on the same 150 requests. The comparison is reported; the rule parser stays the default because its behaviour is inspectable and deterministic.
