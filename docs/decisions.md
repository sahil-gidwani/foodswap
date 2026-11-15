# Decision log

**Use:** live and append-only. Never edit an accepted decision; add a new entry that supersedes it.
**Read by:** everyone at kickoff (T1.2), when each "Proposed" decision is accepted, changed or rejected.

Each entry records the context, the decision and its consequences. Entries D-001 to D-021 were proposed on 2026-11-10 from the planning research and are waiting for team confirmation.

| ID | Decision | Status | Owner |
|---|---|---|---|
| D-001 | Use the OFF bulk dump, not the search API | Proposed | DATA |
| D-002 | Corpus scope: US market, English, canonical category, quality gates | Proposed | DATA |
| D-003 | `bm25s` replaces `rank-bm25` | Proposed | RANK |
| D-004 | Local embedding model; hosted models only as comparisons | Proposed | RANK |
| D-005 | Fielded BM25 as a weighted sum, not BM25F | Proposed | RANK |
| D-006 | Exhaustive masked search; exact vectors | Proposed | RANK |
| D-007 | Three-valued evidence; unknown is ineligible | Proposed | QUX |
| D-008 | Allergen vocabulary and ambiguity defaults | Proposed | EVAL |
| D-009 | "Low X" is a direction; numbers are limits | Proposed | QUX |
| D-010 | B3 through OFF's search service, fetched once | Proposed | EVAL |
| D-011 | Two extra baselines, X1 and X2 | Proposed | RANK |
| D-012 | Two-field rubric with strict gain | Proposed | EVAL |
| D-013 | Builders never label; held-out sealed | Proposed | EVAL |
| D-014 | Statistics plan and extra metrics | Proposed | EVAL |
| D-015 | Score normalization and candidate depth | Proposed | RANK |
| D-016 | Definition of nutrient improvement N | Proposed | RANK |
| D-017 | Product families by exact key | Proposed | DATA |
| D-018 | Streamlit only; core independent of UI; no hosting | Proposed | QUX |
| D-019 | Python 3.13, a virtual environment and pinned requirements | Proposed | RANK |
| D-020 | Licensing: GPL code, ODbL data, no proprietary data | Proposed | DATA |
| D-021 | Fifteen planning docs; three stay live | Proposed | EVAL |

---

### D-001 · Use the OFF bulk dump, not the search API

- **Context.** The proposal sampled about 400 products through OFF's search API. That API allows 10 searches a minute per IP and asks bulk users to download the exports. In probes on 2026-11-09, 18 of 32 polite search requests (8 per minute) returned HTTP 503.
- **Decision.** Download the Parquet export (`food.parquet`, 8.0 GB, 4.9M products) from Hugging Face once, pin the revision, and build everything from it. The live API is used only for the cached B3 baseline and a handful of record lookups.
- **Consequences.** An 8 GB download and a DuckDB extraction step. The corpus is reproducible from the manifest. The proposal's "documented product-search API" route becomes a stated deviation.
- **Docs:** [02 §2.1](02-data-sources.md#21-bulk-exports), [03](03-data-pipeline.md).

### D-002 · Corpus scope

- **Context.** OFF lists about 1.0M products for the US. A sample showed non-English records under the US filter, vandalized records and free-text tags.
- **Decision.** The searchable corpus contains products sold in the US with an English name, a canonical category and passing sanity checks. Records are flagged and excluded, never repaired. The proposal's 4×100 set becomes a committed test fixture.
- **Consequences.** A corpus of several hundred thousand products *(to be measured)*. The audit reports every exclusion.
- **Docs:** [03 §4](03-data-pipeline.md#4-quality-checks-and-the-funnel).

### D-003 · `bm25s` replaces `rank-bm25`

- **Context.** `rank-bm25` (the proposal's choice) has had no release since 2022 and is far slower. `bm25s` 0.3.16 is maintained and fast, returns full score vectors and loads indexes memory-mapped.
- **Decision.** Use `bm25s`.
- **Consequences.** A stated deviation from the proposal. B1 stays "BM25 only".

### D-004 · Local embedding model

- **Context.** The team chose local-first. The proposal named OpenAI `text-embedding-3-small`.
- **Decision.** The default dense model is `BAAI/bge-small-en-v1.5` (33.4M parameters, 384 dimensions, MIT). `ibm-granite/granite-embedding-small-english-r2` (Apache-2.0) is the alternative if a day-one check prefers it. OpenAI is an optional comparison (S9, about $1).
- **Consequences.** No API key is needed to rebuild. A stated deviation from the proposal.

### D-005 · Fielded BM25 as a weighted sum

- **Context.** True BM25F needs a custom scorer or a Java toolkit. Most engines expose a weighted sum of per-field scores.
- **Decision.** Three `bm25s` indexes (name with brand, categories, ingredients), combined as a weighted sum. Field weights are tuned once on dev and shared by every system.
- **Consequences.** The report calls it fielded BM25, not BM25F. True BM25F is Later.

### D-006 · Exhaustive masked search

- **Context.** Filtering a short top-K list after retrieval can leave too few results, and the shortfall would be an artifact of the cutoff, not of the corpus.
- **Decision.** Every retriever scores the whole corpus, and the eligibility mask is applied before taking the top K. Vector search is exact (NumPy). Approximate search is a Stretch scaling experiment.
- **Consequences.** Coverage numbers are facts about the corpus. Latency is within budget at this scale *(to be measured)*.

### D-007 · Three-valued evidence

- **Context.** Allergen tags both over- and under-report: Nutella's tags miss milk and soy, and some cereals list "may contain" items as allergens. The proposal promised that missing or ambiguous evidence means rejection.
- **Decision.** For each product and constraint the verdict is FAIL, PASS or UNKNOWN.
  - **FAIL** if any of the allergen tags, trace tags, ingredient taxonomy or ingredient-text lexicon is positive.
  - **PASS** only with English ingredient text and at least 80% of ingredients recognized.
  - **UNKNOWN** otherwise, and UNKNOWN is ineligible.
  - Traces fail by default.
- **Consequences.** Lower coverage, reported as a result. "PASS" is always worded "not declared in this record".
- **Docs:** [07](07-constraints-and-safety.md).

### D-008 · Vocabulary and ambiguity defaults

- **Decision.** The vocabulary covers the nine US major allergens plus gluten, and molluscs through "shellfish". Ambiguous words get the stricter reading:
  - "nuts" means peanuts and tree nuts;
  - "shellfish" means crustaceans and molluscs;
  - a gluten tag counts as possible wheat.
- **Consequences.** Some products are rejected that strictly need not be. The UI explains each expansion.

### D-009 · Directions and limits

- **Context.** FDA defines no "low sugar" claim, and its other claims are per serving, which OFF's per-100 g data cannot apply reliably.
- **Decision.** "Low", "less", "high" and "more" are soft directions. Explicit numbers are hard limits per 100 g or 100 ml. Claim words like "sugar-free" produce a clarification that proposes a number.
- **Consequences.** Claim thresholds are Stretch (F-Q10).

### D-010 · B3 through OFF's search service

- **Context.** The older search endpoint is unreliable. OFF's Elasticsearch-based service supports tag filters and numeric ranges.
- **Decision.** EVAL translates each scenario into that service's query language, records the query, fetches once on Nov 12 and caches the response. What cannot be expressed is tabulated.
- **Consequences.** B3 is reproducible. It makes no claim about OFF's production ranking beyond the recorded queries.

### D-011 · Two extra baselines

- **Decision.** Add X1 (nearest neighbours of the reference only) and X2 (same category, better Nutri-Score, which is the logic of Yuka-style apps). Both are config-only and pooled at depth 5.
- **Consequences.** About 1.5 hours to build and 1.5 hours of extra labeling. They are the first runs demoted to automatic metrics if labeling runs short.

### D-012 · Two-field rubric with strict gain

- **Context.** If the system's own evidence engine decided violations, the full system would score zero violations by construction.
- **Decision.** Assessors give substitutability (0–2) and, for scenarios with hard constraints, an exclusion status read from the record (satisfied, violated, cannot tell). Gain is 0 unless the status is satisfied. Nutrient improvement is computed from data, not judged.
- **Docs:** [09 §5](09-evaluation.md#5-rubric).

### D-013 · Assessors and blinding

- **Decision.**
  - DATA and EVAL are the assessors.
  - RANK and QUX build the systems, never label, and never see held-out requests.
  - The held-out scenarios stay outside the repository until the system freeze.
- **Consequences.** The proposal's "two team members independently grade" becomes defensible.

### D-014 · Statistics plan and extra metrics

- **Decision.**
  - Seven planned comparisons on held-out nDCG@5, with P2 vs. B2 as the primary.
  - Paired randomization tests, Holm correction and 95% bootstrap intervals.
  - The minimum detectable effect is stated before unsealing, and a pre-registration note is committed at the freeze.
  - Added metrics: first-stage recall@100, per-stage latency, corpus and index statistics, contamination@10 and preference satisfaction@5.
- **Docs:** [09 §7–8](09-evaluation.md#7-metrics).

### D-015 · Score normalization and candidate depth

- **Decision.**
  - Candidates are the top 200 by R plus the top 200 by C.
  - R and C are min-max normalized over the candidate set; N is mapped from [−1, 1] to [0, 1].
  - B2 and P1 sort only the top 50 by relevance.
- **Consequences.** A product with a large nutrient improvement but no relevance cannot rise on N alone.

### D-016 · Definition of N

- **Decision.** N is the mean, over requested goals, of the signed change in within-category percentile between candidate and reference (same basis only).
  - A missing candidate value scores −1.
  - A missing reference value is compared with the category median.
  - With no goals, N = 0: there is no implicit "healthier".
- **Docs:** [06 §6.2](06-retrieval-and-ranking.md#62-nutrient-improvement-n).

### D-017 · Product families by exact key

- **Decision.** Products are grouped by normalized brand, normalized name and a rounded nutrient signature. One member per family is shown, and the reference's own family is never returned. Fuzzy matching is Later.

### D-018 · Streamlit only

- **Decision.** Streamlit is a thin client of `Pipeline.search()`, and the core never imports it. No hosted deployment; the demo runs on a laptop, offline.

### D-019 · Python 3.13, a virtual environment and pinned requirements

- **Decision.** Python 3.13 in a plain virtual environment, with exact versions in `requirements.txt`. No `pyproject.toml`, lockfile tool or Makefile: the code is a flat `foodswap/` package run with `python -m foodswap.<module>`, and each module, test folder or settings file is added only when real code needs it.

### D-020 · Licensing

- **Decision.**
  - Code stays GPL-3.0.
  - Fixtures, the released test collection and any published corpus or index are ODbL, with "Contains data from Open Food Facts, available under the Open Database License".
  - Images are credited under CC BY-SA.
  - No data from proprietary APIs enters the corpus.
- **Docs:** [02 §7](02-data-sources.md#7-licensing-and-attribution).

### D-021 · Documentation structure

- **Decision.** Fifteen planning documents. After Nov 10 only [09-evaluation.md](09-evaluation.md), [10-plan.md](10-plan.md) and this log stay live; the others change only through a logged decision. Tasks may be mirrored into GitHub issues using the IDs in [10](10-plan.md).
