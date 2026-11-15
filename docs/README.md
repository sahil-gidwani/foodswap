# FoodSwap planning documents

FoodSwap finds substitutes for a packaged food. A user picks a reference product, for example a specific cereal, and types a request such as "a similar cereal with less sugar, more protein, and no peanuts". FoodSwap separates what must be avoided from what is preferred, retrieves comparable products with lexical and dense search, removes anything that violates a hard constraint or cannot be verified, ranks the rest by relevance, similarity to the reference and nutrient improvement, and explains every result and every rejection from the product record.

It is a four-person Information Storage and Retrieval project built on [Open Food Facts](https://world.openfoodfacts.org). The original proposal is [proposal.pdf](proposal.pdf). These documents turn that proposal into a plan.

**New to the project?** Start with the explainers, which use real examples:

1. [The data, the taxonomies and the code](explainers/01-data-and-code.md)
2. [How we clean the data](explainers/02-data-cleaning.md)

**Status (2026-11-10):** planning complete. Every decision in [decisions.md](decisions.md) is *Proposed* until the team confirms it at kickoff. Start with [10-plan.md §3.4, "First 48 hours"](10-plan.md#34-first-48-hours).

## At a glance

| | |
|---|---|
| Data | Open Food Facts Parquet export: 4.9M products, about 1.0M sold in the US, filtered to a searchable US corpus |
| Pipeline | Rule-based parser → constraint mask from three-valued evidence → fielded BM25 + dense retrieval → reciprocal rank fusion → S = αR + βC + γN → family collapse and MMR → template explanations |
| Systems | 5 from the proposal (B1, B2, B3, P1, P2), 2 extra baselines, 3 ablations, a negation experiment |
| Evaluation | 32 scenarios (12 dev, 20 held-out), blind double labeling, κ, nDCG@5, violations, coverage, paired randomization tests |
| Stack | Python 3.13, DuckDB, `bm25s`, sentence-transformers (`bge-small-en-v1.5`), NumPy, Streamlit |
| Target | Submittable on Sun Nov 22, 2026, with buffer to Nov 30 |
| Deliverables | Report, 3–4 min video, live demo, code repository |

## Documents

| Doc | What it holds | Use |
|---|---|---|
| [01-scope-and-features.md](01-scope-and-features.md) | Goals, non-goals, research questions, changes from the proposal, the full feature catalogue with tiers, the cut order | live (via decisions) |
| [02-data-sources.md](02-data-sources.md) | Every data source researched, the US slice, observed data-quality problems, regulatory thresholds, licensing | reference |
| [03-data-pipeline.md](03-data-pipeline.md) | Canonical schema, extraction, quality gates, product families, storage layout, the missingness audit | design |
| [04-architecture.md](04-architecture.md) | Components, interfaces, "a system is a config", artifacts, performance budget, stack | design |
| [05-query-understanding.md](05-query-understanding.md) | Request language, negation scope, ambiguity and conflicts, clarifications, query formulation | design |
| [06-retrieval-and-ranking.md](06-retrieval-and-ranking.md) | Fielded BM25, dense retrieval, fusion, the scoring formula, nutrient improvement, diversity | design |
| [07-constraints-and-safety.md](07-constraints-and-safety.md) | Allergen vocabulary, evidence rules, unknown policy, wording rules, ethics | design (safety-critical) |
| [08-explanations-and-ui.md](08-explanations-and-ui.md) | Explanation templates, screens, the labeling page, demo mode | design |
| [09-evaluation.md](09-evaluation.md) | Systems, scenarios, rubric, pooling, metrics, statistics, threats to validity | **live** until the freeze |
| [10-plan.md](10-plan.md) | Roles, schedule and freezes, every task with hours and acceptance criteria, risks | **live** |
| [11-deliverables.md](11-deliverables.md) | Report outline, video storyboard, demo runbook, slides, repository checklist | reference |
| [12-methods-survey.md](12-methods-survey.md) | Every method and tool considered, with versions and a verdict | reference |
| [13-related-work.md](13-related-work.md) | Literature, existing products, positioning, evaluation methodology | reference |
| [decisions.md](decisions.md) | Append-only decision log | **live** |

## Who reads what

| Role | Must read | Skim |
|---|---|---|
| Everyone | this page, [01](01-scope-and-features.md), [10](10-plan.md), [decisions](decisions.md), [07 §1 and §8](07-constraints-and-safety.md) | [09](09-evaluation.md) |
| DATA (corpus, audit, assessor) | [02](02-data-sources.md), [03](03-data-pipeline.md), [09 §5–6](09-evaluation.md#5-rubric) | [07](07-constraints-and-safety.md) |
| RANK (tech lead, retrieval, metrics) | [04](04-architecture.md), [06](06-retrieval-and-ranking.md), [09 §7–8](09-evaluation.md#7-metrics) | [12](12-methods-survey.md) |
| QUX (parser, evidence, UI) | [05](05-query-understanding.md), [07](07-constraints-and-safety.md), [08](08-explanations-and-ui.md) | [04](04-architecture.md) |
| EVAL (scenarios, labels, report) | [09](09-evaluation.md), [11](11-deliverables.md), [13](13-related-work.md) | [05](05-query-understanding.md) |

## Conventions

**Tiers:**

| Tier | Meaning |
|---|---|
| **Core** | Committed; submittable on Nov 22 |
| **Should** | Done in order S1–S9 once the owner's Core work is finished |
| **Stretch** | Only after results are frozen |
| **Later** | Future work, documented with reasons |

**IDs used across the documents:**

| Prefix | Meaning | Defined in |
|---|---|---|
| G1–G5 | Goals | [01 §2](01-scope-and-features.md#2-goals) |
| RQ1–RQ6 | Research questions | [01 §5](01-scope-and-features.md#5-research-questions) |
| F-… | Features (F-D data, F-Q query, F-C constraints, F-R retrieval, F-K ranking, F-U UI, F-E evaluation, F-I infrastructure) | [01 §8](01-scope-and-features.md#8-feature-catalogue) |
| T1.1–T8.4 | Core tasks | [10 §4](10-plan.md#4-core-tasks-1375-h) |
| S1–S9 | Should tasks | [10 §5](10-plan.md#5-should-tasks-31-h) |
| M1–M5 | Milestones | [10 §3](10-plan.md#31-milestones-and-freezes) |
| B1–B3, P1, P2, X1, X2, A1–A3, N1, U1, NEG | Systems | [09 §3](09-evaluation.md#3-systems) |
| C1–C7 | Planned statistical comparisons | [09 §8](09-evaluation.md#8-statistics) |
| D-001… | Decisions | [decisions.md](decisions.md) |

**Sources:** facts about external data, libraries and papers were checked on 2026-11-09 and carry links. Anything that could not be confirmed is marked *(unverified)*.

**Changing these documents:** after Nov 10 only 09, 10 and the decision log are edited directly. Anything else changes through a new entry in [decisions.md](decisions.md) first.

## Data attribution

FoodSwap uses data from Open Food Facts, available under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/). Product images are under CC BY-SA. FoodSwap is a research prototype and gives no medical or allergy advice.
