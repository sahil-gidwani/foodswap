# 06 · Retrieval and ranking

**Use:** design. Sections 2–5 (indexing, keyword and meaning-based search, fusion) are implemented in `foodswap/search.py`; scoring (section 6) and diversity (section 7) are next.
**Read by:** RANK role (owner); everyone for the scoring formula in section 6.
**Last updated:** 2026-11-14.

This document specifies how candidates are found and ordered once a request is parsed ([05](05-query-understanding.md)) and the eligibility mask is built ([07](07-constraints-and-safety.md)). The alternatives considered for each stage are in [12-methods-survey.md](12-methods-survey.md).

## 1. Stages

| Stage | Input | Output |
|---|---|---|
| Eligibility mask | parsed request, evidence, comparison category | boolean vector over the corpus |
| Lexical retrieval | formulated text | BM25 score for every document |
| Dense retrieval | formulated text | cosine score for every document |
| Fusion | the two score vectors restricted to the mask | fused relevance R |
| Candidate set | R and reference similarity C | top `depth` by R plus top `depth` by C |
| Final score | R, C, N | S per candidate |
| Diversity | ranked candidates | one product per family, then MMR |
| Output | top k | ranked list, why-not list, counts |

## 2. Document representations

Each product is indexed three times for BM25 and once for dense retrieval.

| Representation | Text | Notes |
|---|---|---|
| `name` field | product name + generic name + brand | The strongest signal of what the product is |
| `categories` field | English names of every canonical category on the product | OFF category tags already include ancestors; IDF down-weights generic ones such as "plant-based foods" |
| `ingredients` field | English ingredient text, with HTML markup such as `<span class="allergen">` removed | Long and noisy; low weight |
| Dense text | `{name}. {brand}. {deepest category name}. Ingredients: {first ~40 words}` | Kept short: a median of 74 tokens and at most 226 on a 1,000-product check, well under the model's 512-token limit |

Labels ("gluten-free", "organic") are not indexed in Core: constraints come from evidence, never from words that happen to match.

## 3. Lexical retrieval: fielded BM25

- Library: `bm25s`, one index per field, `method="lucene"`, `k1 = 1.2`, `b = 0.75`.
- Analyzer: lower-case, English stop words, Snowball stemming via PyStemmer. The same analyzer for documents and queries.
- Score: a weighted sum of per-field BM25 scores.

```
BM25_fielded(q, d) = Σ_f  w_f · BM25_f(q, d)        f ∈ {name, categories, ingredients}
```

Each field keeps its own IDF and length normalization. This is **not** BM25F, which combines term frequencies across fields before saturation; the report says so. The weighted sum is what most engines expose (Lucene `multi_match`, Pyserini field boosts), and true BM25F is listed under Later.

Field weights start at `name 1.0, categories 0.5, ingredients 0.3`. They are tuned once on the dev scenarios with a coarse grid and then **shared by every system**, so the BM25 baselines are tuned baselines, not straw men. The analyzer, `k1`, `b` and field weights are stated in the report.

`bm25s` `get_scores(query_tokens)` returns one score per document (checked in the library source on 2026-11-09), so the mask can be applied exactly afterwards. Documents that match no query term score 0.

## 4. Dense retrieval

- Model: `BAAI/bge-small-en-v1.5` (33.4M parameters, 384 dimensions, 512-token limit, MIT licence; from the model card).
- Documents are embedded without a prefix; queries get the instruction "Represent this sentence for searching relevant passages: ".
- Vectors are L2-normalized, stored as float16 on disk and float32 in memory, so cosine similarity is a dot product.
- Search is exact: one matrix-vector product over the corpus, then the mask.
- Measured throughput on the M4 laptop's GPU: about 400 products a second at batch size 64 in a short benchmark; the full corpus took 18 minutes (about 330 a second), and the 18K sample about a minute. Larger batches and shorter token limits were no faster.

The model card notes that BGE similarity scores are skewed toward high values, so only the order of scores is meaningful. That is one more reason to fuse by rank (RRF) by default and to min-max normalize before any weighted combination.

A second embedding model is Should (S9) and is compared on at most 100K products, because a larger encoder can take hours on a laptop and every extra model adds unjudged items. The proposal's OpenAI `text-embedding-3-small` is the natural second model (about $1 for the whole corpus at $0.02 per million tokens).

## 5. Fusion

**Default: Reciprocal Rank Fusion** (Cormack, Clarke and Büttcher, 2009), as in the proposal:

```
RRF(d) = Σ_c  1 / (k + rank_c(d))          c ∈ {lexical, dense},  k = 60
```

- Ranks are computed among eligible documents only.
- Each method contributes its top 1,000 eligible products; a product outside a method's top 1,000 gets nothing from it.
- A document with a zero BM25 score gets no lexical contribution.
- k = 60 is the value from the original paper. Defaults differ between engines (OpenSearch uses 60, Qdrant uses 2), so the report states it.

**Ablation (Should, S3): convex combination.**

```
CC(d) = λ · minmax(BM25_fielded(d)) + (1 − λ) · minmax(cos(d))
```

λ is tuned on dev. Bruch, Gai and Ingber (ACM TOIS) found that a tuned convex combination beats RRF in and out of domain, that RRF is sensitive to k, and that only a few labelled queries are needed to tune λ. Our dev set is small, so this is a real test of that claim at small scale.

**First checks on the 18K sample** (2026-11-14). Each method covers the other's blind spots:

| Query | Keyword search alone | Meaning-based search alone | Combined |
|---|---|---|---|
| "fizzy drink" | Bottled water: only "drink" matched | Sodas and sparkling drinks | Sodas and sparkling drinks |
| "peanut butter cereal" | Peanut butter jars and peanut butter cups | Peanut butter granola | Peanut butter cereals (Kashi, Kroger) on top |

"Peanut butter cereal" with peanuts excluded also exposed cut-off ingredient lists passing the peanut check, which led to the name rule in [07](07-constraints-and-safety.md#31-allergen-and-ingredient-exclusions). A query over the sample takes about 0.15 seconds.

## 6. Scoring

### 6.1 The formula

The proposal's transparent multi-criteria score:

```
S(p) = α · R(p) + β · C(p, o) + γ · N(p, o),     α + β + γ = 1,  α, β, γ ≥ 0
```

| Term | Meaning | Computed as | Normalization |
|---|---|---|---|
| R | relevance to the request | fused score from section 5 | min-max over the candidate set |
| C | similarity to the reference product o | cosine of the two document embeddings | min-max over the candidate set |
| N | nutrient improvement over o | section 6.2 | mapped from [−1, 1] to [0, 1] |

**Candidate set.** The top `depth` (default 200) eligible documents by R, plus the top `depth` by C. Taking candidates from both lists keeps products that are very similar to the reference even when the request text is generic. Scoring only these candidates, rather than every eligible product, stops an irrelevant product with a large nutrient improvement from rising on N alone.

### 6.2 Nutrient improvement N

For each requested goal g on nutrient n with direction d (−1 for less, +1 for more):

```
Δ_g(p, o) = d · ( P_c(v_p) − P_c(v_o) )          ∈ [−1, 1]
N(p, o)   = mean over goals of Δ_g(p, o)
```

- `P_c(v)` is the percentile of value v among searchable products in the comparison category c with the same basis (g or ml).
- `v_p` and `v_o` are the per-100 values of the candidate and the reference.

Why percentiles inside the category:

- A 5 g sugar difference means something different for soda than for granola.
- Percentiles are robust to outliers that survive the gates.
- They are easy to explain: "from the 80th to the 20th percentile for sugar among cereals".

Edge cases:

| Case | Rule | Shown to the user |
|---|---|---|
| No goals in the request | N = 0 for every candidate; the γ term drops out | Nothing: there is no implicit "healthier" |
| Candidate value missing | Δ_g = −1 | "sugar not reported" |
| Reference value missing | compare against the category median (P = 0.5) | "your reference does not report sugar; compared with the category median" |
| Comparison category too small for percentiles | use the parent category | |

**Unmentioned nutrients.** A candidate that is clearly worse than the reference on sugars, saturated fat or sodium, which the user did not mention, gets a visible note in its explanation: 25 or more percentile points worse. It does not change the score (F-K5). A guardrail penalty would change the promised formula, so it is Stretch (F-K8).

### 6.3 Tuning

- Weights are tuned on the 12 dev scenarios only, never on held-out.
- Grid: α, β, γ in steps of 0.1 on the simplex (66 settings).
- MMR λ in {0.5, 0.7, 0.9, 1.0}.
- Objective: mean nDCG@5 on dev, with unjudged items counted as 0.
- Guard: the chosen setting must have at least 80% of its top five judged. If not, its unjudged items are labeled in a short top-up session and the search is rerun.
- Report a sensitivity plot (S8). If the best setting lies on a corner of the simplex, say so: it means one signal dominates.

## 7. Diversity

1. **Collapse families.** Keep one member per product family: the member with the highest S, displayed with "also sold in N other sizes". The reference product's own family is always removed.
2. **MMR** (Carbonell and Goldstein, 1998) over the top 50 by S:

```
next = argmax_{p ∉ Sel}  [ λ · S(p) − (1 − λ) · max_{q ∈ Sel} cos(p, q) ]
```

Cosine similarity comes from the document embeddings, and λ is tuned as above.

A brand cap (at most two products per brand in the top five) is Stretch (F-K7). Diversity is measured as intra-list distance and distinct brands in the top five ([09](09-evaluation.md#7-metrics)).

## 8. How each system uses these stages

The full system matrix is in [09](09-evaluation.md#3-systems). In short:

| System | Query | Mask | Ordering |
|---|---|---|---|
| B1 | raw text + reference name | searchable only | fielded BM25 |
| B2 | parsed | category + hard constraints | top 50 by BM25, sorted by N |
| B3 | translated to OFF's search service | OFF filters | OFF's order (cached) |
| P1 | parsed | category + hard constraints | top 50 by RRF(BM25, dense), sorted by N |
| P2 | parsed | category + hard constraints | S over the candidate set, families collapsed, MMR |
| X1 | none (reference only) | category + hard constraints | C only |
| X2 | none | category + hard constraints | better Nutri-Score grade first, then scans |

Every system removes the reference product's own family and breaks ties by scan count, then barcode.

## 9. Why-not list and counts

The why-not list explains what was filtered out.

1. Run the same retrieval without the hard-constraint part of the mask, keeping the category and searchable parts.
2. Take the top 50 by R.
3. List the ineligible ones grouped by reason, with up to five examples each.
4. Show counts over the whole comparison category: in category, eligible, failed per constraint, unknown per constraint.

The counts are the honest answer to "why are there only three results?". See [08](08-explanations-and-ui.md#3-why-not-drawer).

## 10. Out of scope here, and why

| Method | Status | Reason |
|---|---|---|
| Cross-encoder reranking (`gte-reranker-modernbert-base`, `ms-marco-MiniLM-L6-v2`) | Stretch | Changes the top 10, so it needs more labels |
| Approximate vector search (HNSW via FAISS) | Stretch | Exact search is fast enough; worth showing only as a scaling curve |
| Taxonomy synonym expansion | Stretch | |
| True BM25F | Later | Needs a custom scorer; the weighted sum is the honest, common baseline |
| Learned sparse (SPLADE, OpenSearch inference-free encoders) and late interaction (ColBERT) | Later | Little gain expected on short product text, and negation is still unsolved |
| Learning to rank (LightGBM LambdaMART) | Later | Needs a few hundred labelled queries; we have 32 |
| Pseudo-relevance feedback (RM3) | Later | Tends to drift into brand names on short documents |
| An LLM reranking or LLM-only baseline | Later | Adds labeling. Also a known risk with exclusions: listwise LLM rerankers are better than bi-encoders on negation but still below humans (NevIR reproduction, SIGIR 2025). |
