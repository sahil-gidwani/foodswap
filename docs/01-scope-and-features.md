# 01 · Scope and features

**Use:** live (update when scope changes, and log the change in [decisions.md](decisions.md)).
**Read by:** everyone.
**Last updated:** 2026-11-10.

## 1. What FoodSwap is

FoodSwap finds substitutes for a packaged food. The user picks a reference product, for example a specific cereal, and types a request such as "a similar cereal with less sugar, more protein, and no peanuts". FoodSwap then:

1. parses the request into hard constraints (things a result must satisfy), soft goals (directions to move in) and product-type terms;
2. retrieves comparable products with lexical and dense search;
3. removes every candidate that violates a hard constraint, or for which the data cannot show that it satisfies one;
4. ranks the rest by relevance, similarity to the reference product and nutrient improvement;
5. removes near-duplicates and diversifies the top results;
6. explains each result, and each rejection, using values from the product record.

FoodSwap does not certify that a food is safe for anyone. "Passes the peanut constraint" means "no peanut is declared in the record we hold", and every result says so.

## 2. Goals

| ID | Goal |
|---|---|
| G1 | A working substitute search over the US-market slice of Open Food Facts (hundreds of thousands of products, not 400). |
| G2 | Hard constraints enforced symbolically, with a recorded reason and evidence source for every verdict, and abstention when evidence is missing. |
| G3 | A transparent ranking that a reader can recompute by hand from the displayed score components. |
| G4 | An evaluation that honors every commitment in the proposal and holds up to a grader's scrutiny (blind labels, a sealed held-out set, significance tests). |
| G5 | Four deliverables on time: demo video, live demo, written report, code repository with README. |

## 3. Non-goals

- Medical, dietary or allergy advice, and any statement that a product is "healthy" or "safe".
- Personalization from user history, accounts, or stored health data.
- Recipe or ingredient substitution ("what can I use instead of butter"). FoodSwap substitutes packaged products for packaged products.
- Markets other than the US and languages other than English (documented as future work).
- Price and store availability.
- Generated free-text answers. Explanations are templates filled from data.
- A hosted, always-on deployment. The demo runs on a laptop.

## 4. Example requests

| Request | Hard constraints | Soft goals | Type terms |
|---|---|---|---|
| "a similar cereal with less sugar, more protein, and no peanuts" | exclude allergen: peanuts | sugars ↓, proteins ↑ | cereal |
| "yogurt without gelatin, under 8 g sugar" | exclude ingredient: gelatin; sugars ≤ 8 g per 100 g | none | yogurt |
| "something like this but gluten-free" | exclude allergen: gluten | none | (from the reference product's category) |
| "nut-free granola bar with more fiber" | exclude allergen: peanuts and tree nuts (the stricter reading, stated to the user) | fiber ↑ | granola bar |
| "a healthier soda" | none | none: "healthier" is unsupported and triggers a clarification asking which nutrients matter | soda |
| "low sodium crackers, at least 3 g protein" | proteins ≥ 3 g per 100 g | sodium ↓ ("low" without a number is a direction, see [07](07-constraints-and-safety.md)) | crackers |

## 5. Research questions

Each question maps to systems and metrics defined in [09-evaluation.md](09-evaluation.md).

| ID | Question | Compared | Main metrics |
|---|---|---|---|
| RQ1 | Does keeping negated terms ("no peanuts") in the retrieval query pull excluded products into the top results, and does removing them fix it? | B1 and hybrid retrieval, negated terms kept vs. dropped | contamination@10, nDCG@5 |
| RQ2 | Does adding dense retrieval and rank fusion improve on BM25 when both use the same filters? | P1 vs. B2 | nDCG@5, P@5, recall@100 |
| RQ3 | Does scoring by relevance, reference similarity and nutrient improvement beat filter-then-sort? | P2 vs. B2 (primary), P2 vs. P1, X1, X2 | nDCG@5, preference satisfaction@5 |
| RQ4 | How often does each system show a product that violates a hard constraint, and what does rejecting unknown evidence cost in coverage? | all systems | violations@5, coverage, unknown-rejection rate |
| RQ5 | Does diversification reduce redundancy at an acceptable relevance cost? | P2 with and without MMR | intra-list distance@5, distinct brands@5, nDCG@5 |
| RQ6 | What does the system cost at US scale? | P2 stages | latency p50/p95 per stage, index size, build time |

## 6. Changes from the proposal

The proposal was submitted and may be what a grader holds us to, so every deviation is deliberate and logged.

| Proposal | Now | Why | Decision |
|---|---|---|---|
| About 400 products sampled through the OFF search API | The full US-market corpus built from OFF's Parquet dump. The 4×100 set survives as a test fixture. | The search API allows 10 requests a minute and returned HTTP 503 on 18 of 32 polite requests on 2026-11-09. OFF asks bulk users to take the dumps. | D-001, D-002 |
| `rank-bm25` | `bm25s`, three fielded indexes combined by a weighted sum | `rank-bm25` has had no release since 2022 and is far slower. | D-003, D-005 |
| OpenAI `text-embedding-3-small` | A local open model (`BAAI/bge-small-en-v1.5`); OpenAI stays as an optional comparison (S9) | Local-first, reproducible, no key needed to rebuild. | D-004 |
| Reject allergens found in tags, trace tags or ingredient text | The same sources plus inference from parsed ingredients through the OFF taxonomy, expressed as pass / fail / unknown with a recorded reason | Tags over-report and under-report (see [02](02-data-sources.md#28-data-quality-observed-first-hand)). | D-007 |
| B3: OFF's live structured search | The same baseline, fetched once from OFF's Elasticsearch-based search service and cached | The older endpoint is unreliable; a cached run is reproducible. | D-010 |
| Five systems | Seven: two extra config-only baselines (X1 nearest neighbours of the reference; X2 same category with a better Nutri-Score) | Near-free, and they are the comparisons a reader will ask for. X2 is what Yuka-style apps do. | D-011 |
| Graders give one 0–2 grade | Graders give a 0–2 substitutability grade and a separate exclusion-status flag | Without a human flag, the full system would score zero violations by construction. | D-012 |
| Metrics as listed | The same, plus first-stage recall@100, per-stage latency, corpus and index statistics, randomization tests and a stated minimum detectable effect | Rigor a grader expects from an IR project. | D-014 |

## 7. Tiers and budget

Four people at 12–18 focused hours a week gives 96–144 person-hours before Monday Nov 23. Core is estimated at about 138 hours, so it fits only near the top of that range. That is why everything else is tiered.

| Tier | Meaning | Size |
|---|---|---|
| **Core** | Committed. Submittable on Sunday Nov 22. | ~138 h |
| **Should** | Done in priority order S1 to S9, and only after the owner's Core work is finished. | ~31 h |
| **Stretch** | Attempted only after results are frozen (Nov 21). | not estimated |
| **Later** | Out of scope for this deadline. Documented so the report's future-work section is concrete. | not estimated |

"Go all out" is spent on corpus scale and evaluation rigor. It is not spent on more models, because every extra system that enters the pool adds items for two people to label by hand.

## 8. Feature catalogue

Task IDs refer to [10-plan.md](10-plan.md). Features with no task are not scheduled.

### 8.1 Data

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-D1 | US-market corpus from the OFF Parquet dump, with a manifest (revision, checksum, row counts) | Core | T2.1, T2.2 | |
| F-D2 | Canonical schema: English text fields, per-100 nutrient columns, g/ml basis | Core | T2.2 | [03](03-data-pipeline.md) |
| F-D3 | Quality flags and a "searchable" gate | Core | T2.3 | Flag and exclude, never repair |
| F-D4 | Taxonomy module: ancestor closure, comparison category | Core | T2.4 | |
| F-D5 | Product families (same product in several sizes) by exact key | Core | T2.5 | |
| F-D6 | Missingness and coverage audit | Core | T2.6 | Promised in the proposal |
| F-D7 | 20K sample corpus and the 4×100 pilot fixture | Core | T2.2 | Sample exists Tue Nov 10 |
| F-D8 | Within-category nutrient percentiles | Core | T3.3 | Input to the score term N |
| F-D9 | Released test collection (scenarios, rubric, labels in TREC format) under ODbL | Core | T8.4 | |
| F-D10 | Corpora at 10K / 100K / full for scaling curves | Should | S6 | |
| F-D11 | Cached thumbnails for scripted demo scenarios | Should | S4 | Image URLs need the network |
| F-D12 | Fuzzy product families (MinHash over names and ingredients) | Later | | Exact key is enough; fuzzy clustering is a rabbit hole |
| F-D13 | USDA FoodData Central join on barcode | Later | | Needs GTIN normalization and a conflict policy for little new information |
| F-D14 | Category imputation for uncategorized products | Later | | Robotoff predictions or our own classifier |
| F-D15 | Global, multilingual corpus | Later | | |
| F-D16 | Price data (GroceryDB, Open Prices) | Later | | Open Prices has thin US coverage |

### 8.2 Query understanding

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-Q1 | Exclusions with negation scope ("no peanuts or tree nuts") | Core | T4.1 | |
| F-Q2 | Soft nutrient goals (less / more / low / high) | Core | T4.1 | |
| F-Q3 | Numeric limits per 100 g or 100 ml | Core | T4.1 | |
| F-Q4 | Type terms and query formulation, falling back to the reference's category | Core | T4.1 | Negated terms never reach the query |
| F-Q5 | Clarifications for ambiguous or unsupported requests | Core | T4.1 | |
| F-Q6 | "Gluten-free", "dairy-free", "nut-free" mapped to allergen exclusions | Core | T4.1 | Mapping only |
| F-Q7 | 30-case regression suite | Core | T4.1 | |
| F-Q8 | Parser suite of ~150 annotated requests with slot-level P/R/F1 | Should | S5 | Half written by non-authors |
| F-Q9 | Vegan and vegetarian | Should | S7 | |
| F-Q10 | Claim words mapped to thresholds ("sugar-free" as ≤ 0.5 g per 100 g) | Stretch | | In Core these produce a clarification that proposes the number |
| F-Q11 | Brand preferences ("a different brand") | Stretch | | |
| F-Q12 | Per-serving limits | Stretch | | Serving size is free text in the data |
| F-Q13 | Local-LLM parser compared with the rules | Stretch | | |
| F-Q14 | Spelling correction | Later | | |
| F-Q15 | Conversational critiquing ("even less sugar") | Later | | |

### 8.3 Constraints and safety

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-C1 | Vocabulary: the nine US major allergens plus gluten, and molluscs via "shellfish" | Core | T3.1 | 11 entries |
| F-C2 | Evidence builder: verdict and source bitmask per product and allergen | Core | T3.2 | |
| F-C3 | Masks applied inside search; a reason on every candidate | Core | T3.2, T5.3 | |
| F-C4 | Basic ingredient exclusion (tag or text match) | Core | T3.2 | |
| F-C5 | Numeric nutrient verdicts (missing value is unknown) | Core | T3.3 | |
| F-C6 | Category compatibility through the comparison category | Core | T2.4 | |
| F-C7 | Unknown means ineligible; rejected items listed with reasons | Core | T7.1 | |
| F-C8 | Golden tests (Nutella, Cheerios, cocoa butter and others) | Core | T3.2 | |
| F-C9 | Taxonomy-expanded ingredient exclusions | Should | S7 | |
| F-C10 | Hand audit of ~100 verdicts against label photos | Should | S2 | No published audit of OFF allergen data exists |
| F-C11 | Sensitivity of coverage to the evidence-sufficiency threshold | Should | S8 | |
| F-C12 | "May contain is acceptable" preference mode | Stretch | | Default stays strict |
| F-C13 | The other EU allergens (celery, mustard, lupin, molluscs, sulphites) | Stretch | | Vocabulary extension |
| F-C14 | Relaxation suggestions for over-constrained requests (soft goals only) | Stretch | | Core shows counts and reasons |
| F-C15 | FDA per-serving nutrient claims | Later | | Defined per reference amount; FDA has no "low sugar" |

### 8.4 Retrieval

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-R1 | Fielded BM25: three `bm25s` indexes, weighted sum | Core | T5.1 | Not BM25F, and the report says so |
| F-R2 | Dense index with `bge-small-en-v1.5`, exact masked search | Core | T5.2 | |
| F-R3 | Reciprocal Rank Fusion | Core | T5.3 | |
| F-R4 | Pipeline with one settings dict per system; run and trace writer | Core | T5.3 | |
| F-R5 | B3 adapter over cached OFF search responses | Core | T6.2 | |
| F-R6 | Reference-product lookup by name, brand or typed barcode | Core | T7.1 | Text search, pick from the top 20 |
| F-R7 | Convex-combination fusion compared with RRF | Should | S3 | |
| F-R8 | A second embedding model on at most 100K products | Should | S9 | The proposal's OpenAI model is the natural pick |
| F-R9 | Scaling curve: index size, build time, latency per stage | Should | S6 | |
| F-R10 | Cross-encoder reranking | Stretch | | Adds unjudged items |
| F-R11 | Approximate (HNSW) vs. exact vector search | Stretch | | |
| F-R12 | Synonym expansion from the taxonomy | Stretch | | |
| F-R13 | True BM25F | Later | | |
| F-R14 | Learned-sparse and late-interaction retrieval | Later | | See [12](12-methods-survey.md) |
| F-R15 | A search-engine backend (OpenSearch, Qdrant, LanceDB) | Later | | |
| F-R16 | Pseudo-relevance feedback | Later | | Tends to drift on short product text |
| F-R17 | Image search | Later | | |

### 8.5 Ranking and diversity

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-K1 | Score `S = αR + βC + γN` with a visible breakdown | Core | T5.4 | |
| F-K2 | Nutrient improvement N from within-category percentiles | Core | T3.3, T5.4 | |
| F-K3 | Weights tuned on dev scenarios by grid search | Core | T5.4 | Never on held-out |
| F-K4 | MMR over product families; the reference's own family is never returned | Core | T5.4 | |
| F-K5 | Flags for regressions on nutrients the user did not mention | Core | T5.5 | Explanation only, no score effect |
| F-K6 | Sensitivity plots for weights and the RRF constant | Should | S8 | |
| F-K7 | Brand cap in the top results | Stretch | | |
| F-K8 | A guardrail penalty term for regressions | Stretch | | Changes the promised formula |
| F-K9 | Pareto (skyline) view of similarity vs. improvement | Later | | |
| F-K10 | Learning to rank | Later | | Needs a few hundred labelled queries |
| F-K11 | An LLM-only reranking baseline | Later | | Adds labeling; interesting future comparison |

### 8.6 Explanations and UI

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-U1 | Template explanations with a test that every number matches the record | Core | T5.5 | |
| F-U2 | Search page: reference lookup, request box, parsed chips, result cards | Core | T7.1 | |
| F-U3 | "Why not" drawer: rejected candidates grouped by reason | Core | T7.1 | |
| F-U4 | System comparison view | Core | T7.1 | Degrades to a dropdown |
| F-U5 | Attribution, snapshot date, verify-on-package notice | Core | T7.1 | |
| F-U6 | Labeling page for assessors | Core | T6.3 | |
| F-U7 | Demo hardening: warm query under 1 s, runs offline | Core | T7.2 | |
| F-U8 | Editable chips (one-way override) and thumbnails | Should | S4 | |
| F-U9 | Facets and sorting | Stretch | | |
| F-U10 | Weight sliders for α, β, γ | Stretch | | |
| F-U11 | Side-by-side compare of two or three products | Stretch | | |
| F-U12 | Camera barcode scanning | Later | | Native dependencies and demo risk |
| F-U13 | Saved dietary profile | Later | | |
| F-U14 | Generated summaries | Later | | Conflicts with the no-generated-claims rule |

### 8.7 Evaluation

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-E1 | 32 scenarios, 12 dev and 20 held-out, held-out sealed | Core | T6.1 | |
| F-E2 | Seven systems, three ablations and the negation experiment as settings dicts | Core | T5.3, T5.6 | |
| F-E3 | Pooling, blind double labeling, weighted κ, adjudication | Core | T6.3–T6.5 | |
| F-E4 | Metrics harness | Core | T6.6 | |
| F-E5 | Randomization tests, bootstrap intervals, Holm correction, minimum detectable effect | Core | T6.6 | |
| F-E6 | Corpus and index statistics | Core | T2.6, T6.6 | |
| F-E7 | Breakdowns by category and constraint type; three to five failure cases | Core | T8.1 | |
| F-E8 | 300–500 template-generated scenarios for automatic metrics, with paraphrase robustness | Should | S1 | |
| F-E9 | Parser evaluation | Should | S5 | |
| F-E10 | LLM-as-judge extension, validated against human labels | Stretch | | |
| F-E11 | User study | Later | | Needs an IRB determination |

### 8.8 Infrastructure and deliverables

| ID | Feature | Tier | Tasks | Notes |
|---|---|---|---|---|
| F-I1 | Project skeleton: package, pinned requirements, data download | Core | T1.1 | Done Nov 14 |
| F-I2 | Written report | Core | T8.1 | |
| F-I3 | Demo video, 3–4 minutes | Core | T8.2 | |
| F-I4 | Slides and two rehearsals | Core | T8.3 | |
| F-I5 | README, reproducibility targets, attribution | Core | T8.4 | |
| F-I6 | Continuous integration | Stretch | | |
| F-I7 | Hosted demo | Later | | Free tiers have tight memory limits |

## 9. Cut order

If the team falls behind, drop or degrade in this order:

1. Everything in Stretch.
2. Should items from the bottom: S9 first, S1 last.
3. Core, degraded but not dropped:
   1. MMR becomes an ablation measured by automatic metrics only (not pooled, off in the UI).
   2. The two extra baselines X1 and X2 are measured by automatic metrics only.
   3. The corpus falls back to the four proposal categories within the US slice.
   4. The side-by-side comparison becomes a system dropdown.
   5. Dev labeling shrinks to 8 scenarios and a coarse weight grid.
   6. B3 becomes whatever was cached, with documented limits.
   7. The held-out set shrinks from 20 to 16 scenarios, disclosed in the report. Last resort.

Never dropped:

- Three-valued evidence, with unknown meaning ineligible and a reason on every candidate. This is the thesis and the safety property.
- The blind, double-labeled, held-out comparison of B1, B2, P1 and P2 with κ. Shrink the scenario count before weakening the protocol.
- The negation kept-vs-dropped result.
- The frozen data snapshot and the scripts that regenerate every reported number.
- The missingness audit and the no-certification disclaimer.
- One full rehearsal and an offline fallback recording.
