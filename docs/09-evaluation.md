# 09 · Evaluation

**Use:** live until the system freeze on Tue Nov 17; after that, sections 3–9 are frozen and serve as the pre-registered protocol.
**Read by:** everyone. EVAL owns this document.
**Last updated:** 2026-11-10.

## 1. Principles

1. **Honor the proposal.** Every commitment in the submitted proposal is kept: 32 scenarios (12 dev, 20 held-out); systems B1, B2, B3, P1, P2; the negation experiment; two independent graders on pooled, shuffled top-10 results with a 0–2 rubric; adjudication and weighted Cohen's κ; Precision@5, nDCG@5, hard-constraint violations, scenarios with five eligible candidates, diversity and latency; ablations of semantic search, nutrition ranking and MMR with paired differences.
2. **Blind and sealed.**
   - The two people who build the ranker and the parser (RANK, QUX) never label and never see the held-out requests.
   - The assessors (DATA, EVAL) never see which system produced an item.
3. **Freeze before looking.** Systems are frozen and tagged before held-out runs are generated. The primary comparison is declared in advance.
4. **Humans judge what only humans can judge.**
   - Assessors judge substitutability, plus whether the record shows a violated exclusion.
   - Nutrient improvement is computed from data, so it cannot drift between judges.
5. **Report uncertainty.** Twenty held-out scenarios give limited statistical power. The report states the minimum detectable effect and calls smaller differences inconclusive.

## 2. Research questions

| RQ | Question | Systems | Primary metric | Secondary metrics |
|---|---|---|---|---|
| RQ1 | Do negated terms left in the query pull excluded products into the results, and does dropping them fix it? | 2×2 negation grid; B1 vs. N1 | contamination@10 | nDCG@5 (B1 vs. N1) |
| RQ2 | Does hybrid retrieval with fusion beat BM25 under the same filters? | P1 vs. B2 | nDCG@5 | P@5, recall@100 per channel |
| RQ3 | Does the transparent score beat filter-then-sort, and the common "better Nutri-Score" heuristic? | P2 vs. B2 (primary), P2 vs. P1, P2 vs. X2, A1, A2 | nDCG@5 | preference satisfaction@5, P@5 |
| RQ4 | How often does each system show a violating product, and what does rejecting unknown evidence cost? | all; U1 | violations@5 | coverage, unknown@5, unknown-rejection rate |
| RQ5 | Does MMR reduce redundancy at acceptable cost? | P2 vs. A3 | ILD@5 | distinct brands@5, distinct families@5, nDCG@5 |
| RQ6 | What does it cost to run at US scale? | P2 stages | latency p50/p95 | index size, build time, memory |

## 3. Systems

| ID | System | Query | Eligibility mask | Ordering | Pooled | Origin |
|---|---|---|---|---|---|---|
| **B1** | BM25 only | raw request + reference name (negated terms included) | searchable | fielded BM25 | depth 10 | proposal |
| **B2** | BM25 + filters + nutrient sort | parsed | category + hard constraints | top 50 by BM25, sorted by N (BM25 breaks ties) | depth 10 | proposal |
| **B3** | OFF's live search | scenario translated into OFF's search syntax (section 4.3) | OFF filters where expressible | OFF's order, cached | depth 10 | proposal |
| **P1** | Hybrid + B2's filters and sorting | parsed | as B2 | top 50 by RRF(BM25, dense), sorted by N | depth 10 | proposal |
| **P2** | Full FoodSwap | parsed | as B2 | S = αR + βC + γN, families collapsed, MMR | depth 10 | proposal |
| X1 | Reference neighbours | none (reference only) | as B2 | C only | depth 5 | new |
| X2 | Same category, better Nutri-Score | none | as B2 | products with a better Nutri-Score grade than the reference first, then by scans | depth 5 | new; what Yuka-style apps do |
| A1 | P2 without semantic search | parsed | as B2 | dense channel off, β = 0 | depth 5 | proposal ablation |
| A2 | P2 without nutrition ranking | parsed | as B2 | γ = 0 | depth 5 | proposal ablation |
| A3 | P2 without MMR | parsed | as B2 | MMR off (families still collapsed) | depth 5 | proposal ablation |
| N1 | B1 with negated terms dropped | raw request minus negated terms + reference name | searchable | fielded BM25 | depth 5 | proposal negation test |
| U1 | P2 with unknown evidence allowed | parsed | category + hard constraints, UNKNOWN passes | as P2 | automatic only | new |
| NEG | 2×2 grid: {BM25, hybrid} × {negated terms kept, dropped} | | category only, no constraint mask | relevance | automatic only | proposal negation test |

Notes:

- **Weights.** For A1 and A2 the remaining weights are renormalized from P2's tuned values. N is the nutrient-improvement term ([06](06-retrieval-and-ranking.md#62-nutrient-improvement-n)).
- **Shared rules.** Every system removes the reference product's own family and breaks ties by scans, then barcode.
- **B2's depth.** B2 and P1 sort only the top 50 by relevance. Without that limit they would return the same lowest-sugar products for every request.
- **X1 and X2** apply the same mask as P2, so they differ from it only in ordering.

## 4. Scenarios

### 4.1 Design

There are 32 scenarios: 8 for each of the proposal's four categories (breakfast cereals, yogurts, snacks, beverages). Each category has 3 dev and 5 held-out scenarios.

| Type | Request shape | Example | Dev | Held-out |
|---|---|---|---|---|
| R1 | Soft goals only | "a similar cereal with less sugar and more fiber" | 2 | 4 (one per category) |
| R2 | One exclusion + soft goals | "no peanuts, less sugar" | 3 | 4 |
| R3 | Several hard constraints + soft goals | "no milk or soy, under 8 g sugar, more protein" | 3 | 4 |
| R4 | Tricky phrasing | "nut-free", "no peanuts but almonds are fine", "dairy-free" | 2 | 4 |
| R5 | Hard case | an ingredient exclusion (gelatin, palm oil), a reference with incomplete data, or a likely over-constrained request | 2 | 4 |

Rules for choosing references:

- Searchable, and with the nutrients each request mentions.
- Popular (scanned often) but spread over many brands.
- Chosen before any system is run on them.
- The reason each reference was chosen is recorded.

### 4.2 Format and sealing

`eval/scenarios/{dev,heldout}.jsonl`:

```json
{"id": "H07", "split": "heldout", "category": "en:yogurts", "type": "R5",
 "reference_code": "…", "request": "a similar yogurt without gelatin, under 8 g sugar",
 "gold_parse": {"hard": [["exclude_ingredient", "en:gelatin"], ["nutrient_max", "sugars", 8.0]],
                "goals": [], "type_category": "en:yogurts"},
 "b3_query": "…", "notes": "…"}
```

- **Writers.** EVAL writes the scenarios on Nov 10–12, with DATA's help finding references.
- **Sealing.** The held-out file stays outside the repository (in EVAL's private storage) until the system freeze, and is committed with the `eval-v1` tag.
- **Dev file.** The dev file is shared from the start.

### 4.3 Baseline B3

EVAL translates each scenario into the query language of OFF's search service ([02](02-data-sources.md#25-the-newer-search-service-used-for-baseline-b3)), records the query in `b3_query`, fetches once on Thu Nov 12, and stores the raw response under `eval/b3_cache/`.

| Scenario element | Translation | Expressible? |
|---|---|---|
| US market | `countries_tags:"en:united-states"` | yes |
| Product type | category tag filter, or the type words as full text | yes |
| Allergen exclusion | `NOT allergens_tags:"en:peanuts" AND NOT traces_tags:"en:peanuts"` | yes, but tags only: no ingredient inference |
| Numeric limit | `nutriments.sugars_100g:[* TO 8]` | yes |
| Soft goal | sort by the nutrient, if the service supports it | to be checked; documented |
| Similarity to the reference | none | no |
| Unknown evidence rejected | none | no (a missing tag looks like "no allergen") |

The table of what B3 cannot express goes in the report. B3 items outside our corpus are fetched once through the product API and cached, so they can be labeled, and our evidence code runs on those records too.

## 5. Rubric

Every pooled item gets two fields.

### 5.1 Substitutability (0–2)

Judge it against the reference product and the kind of product the request names. Ignore nutrition, and ignore whether hard constraints are met (the second field covers those).

| Grade | Meaning | Anchors (expanded with real products during calibration) |
|---|---|---|
| **2** Direct substitute | The same kind of product, used the same way. Someone replacing the reference would accept it as the same kind of thing; flavour variants count. | Another ready-to-eat breakfast cereal for a cereal; another cup yogurt for a cup yogurt |
| **1** Partial substitute | Related, and could stand in with a compromise in form, format or use | Hot oatmeal or a cereal bar for a cold cereal; a drinkable yogurt for a cup yogurt; flavoured sparkling water for a soda |
| **0** Not a substitute | A different kind of product or use, or not identifiable from its record | Cookies for a cereal; a dessert for a yogurt |

Rule for exclusions that define a product: if the request excludes something that defines the reference's kind (for example "no milk" for a dairy yogurt), the closest kind that satisfies the request counts as direct (a plant-based yogurt alternative is a 2).

### 5.2 Exclusion status

Asked only for scenarios with hard constraints, and judged from the record shown.

| Value | Meaning |
|---|---|
| satisfied | The record lists ingredients and shows no excluded item, no matching "may contain" statement, and values within any limits |
| violated | The record shows an excluded item (in ingredients, allergens or "may contain"), or a value outside a limit |
| cannot tell | No ingredient list, unreadable or non-English text, or a missing value |

### 5.3 Gain

- **Strict (primary):** gain = substitutability if the exclusion status is satisfied (or the scenario has no hard constraints); otherwise 0.
- **Lenient (reported):** "cannot tell" counts as satisfied.

The human exclusion flag keeps the violation metric independent of our evidence engine. Our engine would otherwise score itself perfect by construction. Assessors see the same record as the engine, so the flag catches engine errors (lexicon gaps, taxonomy gaps) but not record errors; the label-photo audit (S2) addresses record errors.

## 6. Pooling and labeling protocol

### 6.1 Pools

**Held-out pool.**

- Contents: the union of the top 10 from B1, B2, B3, P1 and P2, plus the top 5 from X1, X2, A1, A2, A3 and N1.
- **Families.** Returned barcodes are mapped to product families, and each family is labeled once. B3 items outside the corpus are labeled by barcode.
- **Order.** Items are shuffled per scenario and assessor, with a recorded seed. No ranks, scores or system names are shown.
- **Expected size.** 25–35 items per scenario, so 500–700 judgments per assessor, about 4–5 hours at 25 seconds each.
- **Budget rule.** If the pool exceeds 700 judgments per assessor, X1, X2 and N1 drop to automatic metrics only. This matches the cut order in [01](01-scope-and-features.md#9-cut-order).

**Dev pool.** The union of:

- the top 10 from B1, B2, P1 and P2 at default weights;
- the top 5 from P2 at seven weight settings: the three corners of the (α, β, γ) simplex, the three edge midpoints and the centre.

That gives the tuner judged items across the weight space.

### 6.2 Steps

| Step | When | Who | What |
|---|---|---|---|
| Calibration | Sun Nov 15 | DATA, EVAL | Both label the 3 pilot dev scenarios independently, compute κ, meet for 30 minutes, and revise the rubric anchors once (changes logged) |
| Dev labeling | Sun–Mon Nov 15–16 | DATA, EVAL | The other 9 dev scenarios, split between the two assessors (single-labeled); used for tuning |
| Freeze | Tue Nov 17 | RANK, EVAL | Systems tagged `eval-v1`; EVAL generates held-out runs and the pool |
| Held-out labeling | Wed–Fri Nov 18–20 | DATA, EVAL | Both label all 20 scenarios independently and blind |
| Agreement | Fri Nov 20 | EVAL | Agreement statistics computed before adjudication |
| Adjudication | Fri Nov 20 | DATA, EVAL | Each disagreement discussed to a consensus label. If still unresolved, the lower substitutability grade is taken and exclusion status becomes "cannot tell". Notes are kept. |
| Qrels | Fri Nov 20 | EVAL | Consensus labels written to `qrels/heldout.txt` (TREC format, graded) and the exclusion status to a sidecar file |

### 6.3 Agreement

- **Substitutability:** quadratic-weighted Cohen's κ, plus the 3×3 confusion matrix.
- **Exclusion status:** Cohen's κ and raw agreement. When one category dominates, κ is unstable, so also report Gwet's AC1.
- **Targets:** κ_w ≥ 0.6 after calibration. If pilot κ_w is below 0.5, add anchors and run one more calibration round before dev labeling continues.

## 7. Metrics

| Metric | Definition | RQ |
|---|---|---|
| **nDCG@5** (primary), nDCG@10 | Strict gains (0/1/2), log2 discount, ideal ranking from all judged items in the scenario | RQ2, RQ3 |
| P@5 | Share of the top 5 with gain 2 | RQ2, RQ3 |
| **Violations@5** | Share of scenarios with at least one top-5 item violating a constraint. Two columns: human consensus flag, and engine FAIL verdict | RQ4 |
| Violation rate@5 | Share of top-5 items violating a constraint | RQ4 |
| Unknown@5 | Share of top-5 items with UNKNOWN evidence (engine) | RQ4 |
| **Coverage** | Share of scenarios with at least 5 eligible results (the proposal's "scenarios with five eligible candidates") | RQ4 |
| Unknown-rejection rate | Share of in-category products rejected as UNKNOWN for the scenario's constraints | RQ4 |
| Preference satisfaction@5 | Mean over top-5 items of the share of requested soft goals improved relative to the reference (from data) | RQ3 |
| **Contamination@10** | Share of top-10 items that FAIL a requested exclusion (engine verdict), in systems without the constraint mask | RQ1 |
| ILD@5 | Intra-list distance: 1 − mean pairwise cosine of document embeddings among the top 5 | RQ5 |
| Distinct brands@5, distinct families@5 | Counts in the top 5 | RQ5 |
| Recall@100 | For each first-stage channel, share of consensus-relevant items (gain ≥ 1) found in its top 100 within the mask. Pool-based, so relative to what pooled systems found | RQ2 |
| Judged@5 | Share of the top 5 that has a label; reported for any run added after pooling | all |
| Latency | p50 and p95 per stage and in total, warm and cold, three runs over all scenarios | RQ6 |
| Corpus and index statistics | Documents, vocabulary per field, index sizes, build times, memory | RQ6 |

Tooling: `ir-measures` for the standard metrics; our own small module for the project-specific ones.

## 8. Statistics

- **Unit of analysis:** the scenario. Each system has one value per scenario.
- **Planned comparisons on held-out nDCG@5:**

| ID | Comparison | Question |
|---|---|---|
| C1 | **P2 vs. B2 (primary)** | Is the transparent score better than filter-then-sort? |
| C2 | P1 vs. B2 | Does hybrid retrieval help? |
| C3 | P2 vs. P1 | Does the score help over hybrid plus sort? |
| C4 | P2 vs. X2 | Better than "same category, better Nutri-Score"? |
| C5 | P2 vs. A1 | Contribution of semantic search |
| C6 | P2 vs. A2 | Contribution of nutrition ranking |
| C7 | P2 vs. A3 | Cost or benefit of MMR |

- **Test:** two-sided paired randomization test (sign flips of per-scenario differences, 10,000 permutations). Smucker, Allan and Carterette (CIKM 2007) and Urbano, Lima and Hanjalić (SIGIR 2019) support randomization or t-tests over sign and Wilcoxon tests for IR evaluation.
- **Multiple comparisons:** Holm–Bonferroni across C1–C7 (Carterette, TOIS 2012). Adjusted p-values are reported.
- **Effect size:** mean difference with a 95% bootstrap interval (10,000 resamples of scenarios, percentile method), plus the number of scenarios better, worse and tied.
- **Minimum detectable effect, stated before unsealing.** From the standard deviation s of per-scenario differences in C1 on dev, with n = 20, α = 0.05 two-sided and 80% power:

```
MDE ≈ (z_0.975 + z_0.80) · s / √n = (1.96 + 0.84) · s / √20 ≈ 0.63 · s
```

  With t quantiles for 19 degrees of freedom the factor is about 0.66. Differences smaller than the MDE are reported as inconclusive, not as "no effect".

- **Descriptive only:** violations, coverage and unknown@5. They are often exactly zero for masked systems, and comparisons with zero variance are not tested.
- **No tuning on held-out.** Dev and held-out results are reported separately. Exploratory analyses (per category, per request type) are labeled exploratory and carry no p-values.

**Pre-registration.** At the freeze, EVAL commits `reports/preregistration.md` containing:

- the frozen settings of every system and the git commit;
- the planned comparisons;
- the primary metric;
- the MDE;
- the date.

## 9. Component evaluations

| Evaluation | Tier | What is reported |
|---|---|---|
| Parser regression suite (30 cases) | Core | Pass rate; the "no negated term in the query" property |
| Parser test set (~150 requests, half written by non-authors) | Should (S5) | Slot-level precision, recall and F1 for exclusions, limits, goals and type; exact match; downstream ranking changes when the gold parse replaces the predicted one |
| Evidence audit (~100 verdicts against label photos) | Should (S2) | False-pass and false-fail rates with Clopper–Pearson intervals; how often tags over- and under-report |
| Template scenarios (300–500) | Should (S1) | Contamination@10 (the negation experiment at scale), coverage, unknown-rejection rate, preference satisfaction, ILD, latency. **Not used for relevance claims:** template requests flatter the rule parser, and P2's engine violations are zero by construction. |
| Paraphrase robustness | Should (S1) | Rank-biased overlap (p = 0.9) between rankings for 2–3 hand-written paraphrases of 20 requests (Webber, Moffat and Zobel, TOIS 2010) |
| Fusion: RRF vs. convex combination | Should (S3) | Dev-tuned λ; held-out nDCG@5 with judged@5 |
| Scaling | Should (S6) | Index build time, size on disk, memory and latency per stage at 10K, 100K and full corpus |
| Sensitivity | Should (S8) | nDCG@5 over the weight simplex; RRF k; coverage vs. θ (evidence sufficiency) |
| Second embedding model | Should (S9) | On ≤100K products; dev nDCG@5 and judged@5; cost and time |

## 10. Optional: LLM as a second judge (Stretch)

Only after results are frozen, and only to add depth or scenarios. LLM labels never feed tuning.

Protocol, following the cautions in the literature ([13](13-related-work.md#9-evaluation-methodology)):

1. **Prompt.** A UMBRELA-style prompt (Upadhyay et al., 2024), adapted to the substitutability rubric, frozen before use.
2. **Model.** Any model not used inside FoodSwap. Core uses no LLM, so this is easy.
3. **Agreement.** Measured against human consensus on every human-labeled pair: κ_w, AC1 and the confusion matrix.
4. **Ranking agreement.** System rankings compared under human vs. LLM labels with Kendall's τ, plus the number of system pairs whose order flips. With fewer than ten systems τ is coarse.
5. **Gullibility probe.** Insert irrelevant products whose names are stuffed with reference terms, since LLM judges are known to be fooled by keyword stuffing (Alaofi et al., 2024).
6. **Reporting.** LLM-judged results are reported separately and clearly labeled.

## 11. Threats to validity

| Threat | Mitigation |
|---|---|
| Assessors are team members | Blind pools; builders never label; rubric anchors; κ reported before adjudication |
| Scenarios written by the team may favour the parser | Held-out written by EVAL and DATA, never seen by QUX; S5 uses requests written by non-authors |
| Few held-out scenarios | Paired tests, intervals, MDE stated, no claims below it |
| Engine and assessors read the same, possibly wrong, record | S2 audits records against package photos; "PASS" is worded as "not declared" |
| Pool bias against runs added later | Judged@5 for every later run; condensed-list check (unjudged removed) as a robustness view |
| Recall is pool-based | Stated where reported |
| B3 is our translation of each scenario | The query is recorded and its limits tabulated; local baselines make no claim about OFF's production system |
| Tuning leakage | Weights tuned on dev only; freeze before held-out runs; pre-registration note |
| US, English, crowd-sourced data | Stated as scope, not as a general claim |

## 12. Released artifacts

Published with the repository, under ODbL with OFF attribution:

- scenarios (dev and held-out, after the freeze);
- the rubric and anchors;
- consensus qrels and exclusion flags;
- per-assessor raw labels (anonymized as A and B);
- the frozen run files;
- the scripts that regenerate every table.

Together these form a small reusable test collection for constraint-aware substitution.
