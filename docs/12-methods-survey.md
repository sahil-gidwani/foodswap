# 12 · Methods and tools survey

**Use:** reference. It records what was considered and why each choice was made, so the report's method section and the Q&A can cite it.
**Read by:** RANK and QUX before building; anyone asked "why not X?".
**Checked:** 2026-11-09, against PyPI, GitHub, model cards and official documentation. *(unverified)* marks facts taken from secondary sources, search snippets or memory.

**Verdicts:** **Core** (we build it), **Should**, **Stretch**, **Later** (future work), **Rejected** (with a reason). The scope tiers are defined in [01](01-scope-and-features.md#7-tiers-and-budget).

## 1. Lexical retrieval libraries

| Tool | Version, date | What matters for us | Verdict |
|---|---|---|---|
| [`bm25s`](https://github.com/xhluca/bm25s) | 0.3.16, 2026-10-28; MIT; very active | Fast sparse-matrix BM25. Variants: Lucene (default), Robertson, ATIRE, BM25L, BM25+. Stemming via PyStemmer, memory-mapped loading, numba backend. Reported 20× to 400× more queries per second than `rank-bm25` on BEIR sets. `get_scores` returns a score per document (checked in source). One text field per index, no BM25F. | **Core** |
| [`rank-bm25`](https://pypi.org/project/rank-bm25/) | 0.2.2, 2022-02-16 | Unmaintained, pure-Python scoring | Rejected (it was the proposal's choice; see D-003) |
| [PyTerrier](https://pyterrier.readthedocs.io/en/latest/) | `pyterrier` 1.1.2, 2026-07-19 | Java now optional ("Java 11 or newer is required for some functionality"). Terrier offers true BM25F and RM3/Bo1. `pt.Experiment` gives baselines, t-tests or Wilcoxon, and Bonferroni or Holm–Šidák correction. The PISA backend is Linux-only. | Later (a BM25F / PRF comparison) |
| [Pyserini](https://pypi.org/project/pyserini/) | 2.4.0, 2026-08-27 | Lucene reference implementation; needs Java 21 (the team laptop has Java 17) | Rejected for now |
| [tantivy-py](https://pypi.org/project/tantivy/) | 0.27.0, 2026-10-22 | Rust Lucene-like engine; field boosts | Rejected (no advantage over `bm25s` here) |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | built into Python | `bm25()` with per-column weights applied before saturation, but one length normalization per row; k1 and b fixed at 1.2 and 0.75; prefix and trigram indexes for type-ahead | Later (single-file storage story) |
| [DuckDB full-text search](https://duckdb.org/docs/2.0/core_extensions/full_text_search.html) | DuckDB 2.0 | `match_bm25` with stemming; restricts fields but has no per-field weights; the index does not update when the table changes | Rejected (fine for exploration only) |
| Elasticsearch 9.x | 9.5.6 | `combined_fields` is BM25F-like. RRF and linear retrievers require a paid licence, per an Elastic staff statement *(unverified in the licence matrix)*. | Later |
| OpenSearch 3.x | 3.9.0 | Free hybrid query with normalization and RRF processors | Later |
| Vespa, Typesense, Meilisearch | pyvespa 1.2.10; Typesense 30.2; Meilisearch 1.56.2 | Powerful engines, but Docker services that hide the scoring we want to show | Later |

### Field weighting

| Approach | Where it exists | Our use |
|---|---|---|
| True BM25F (frequencies combined across fields before saturation) | Terrier BM25F; approximately Elasticsearch `combined_fields` | Later |
| BM25F-like weighted frequency with one length normalization | SQLite FTS5 `bm25()` weights | Later |
| Weighted sum of per-field BM25 scores | Lucene `multi_match`, Pyserini field boosts, tantivy boosts; `bm25s` with one index per field | **Core** ([06](06-retrieval-and-ranking.md#3-lexical-retrieval-fielded-bm25)) |

### Query expansion, spelling and type-ahead

- **Pseudo-relevance feedback** (RM3, Bo1) exists in PyTerrier and Pyserini. On short product documents it tends to drift into brand names. Verdict: Later.
- **Spelling and fuzzy matching:** `symspellpy` 6.10.2 and `RapidFuzz` 3.14.6 (MIT). RapidFuzz is used for fuzzy reference lookup. Spelling correction is Later.
- **Gazetteers:** `pyahocorasick` 2.3.1 for fast multi-pattern matching in the parser (**Core**, or plain dictionaries if fast enough).
- **Type-ahead for the reference product** is a text search over the name field showing the top 20, ranked by BM25 then scan count (**Core**). Prefix indexes such as FTS5 `prefix=` are Later.

## 2. Dense retrieval

### 2.1 Open embedding models

| Model | Size | Dims | Max tokens | Licence | Notes | Verdict |
|---|---|---|---|---|---|---|
| [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) | 33.4M | 384 | 512 | MIT | Query prefix "Represent this sentence for searching relevant passages:"; none for passages. Scores are skewed high, so use their order. | **Core** |
| [`ibm-granite/granite-embedding-small-english-r2`](https://huggingface.co/ibm-granite/granite-embedding-english-r2) | 47M | 384 | 8192 | Apache-2.0 | No prefixes | Core alternative (day-one bake-off if wanted) |
| [`Alibaba-NLP/gte-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-modernbert-base) | 149M | 768 | 8192 | Apache-2.0 | BEIR 55.33 (model card) | Should (S9 candidate) |
| [`Qwen/Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 0.6B | up to 1024 (Matryoshka) | 32K | Apache-2.0 | Instruction-aware queries; MTEB English v2 70.70 (model card) | Should (S9 candidate) |
| `google/embeddinggemma-2` | 740M total, 270M text path | 768 (Matryoshka) | 8K | Apache-2.0 | Released 2026-10-06 ([Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/)); multimodal | Later |
| [`google/embeddinggemma-300m`](https://huggingface.co/google/embeddinggemma-300m) | ~300M | 768 | 2048 | Gemma terms | | Rejected (licence terms; the newer version is Apache) |
| [`nomic-ai/nomic-embed-text-v2-moe`](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe) | 475M total | 768 | 512 | Apache-2.0 | Prefixes required | Later |
| [`jinaai/jina-embeddings-v5-text-small`](https://huggingface.co/jinaai/jina-embeddings-v5-text-small) | 677M | 1024 | 32K | **CC BY-NC 4.0** | Strong scores, but non-commercial | Rejected (licence) |
| [`sentence-transformers/static-retrieval-mrl-en-v1`](https://huggingface.co/sentence-transformers/static-retrieval-mrl-en-v1) | static | 1024 | — | Apache-2.0 | Static embeddings, roughly 400× faster on CPU, about 87% of a small transformer's quality (model card) | Later (a speed baseline) |
| `BAAI/bge-m3` | 568M | 1024 + sparse + multi-vector | 8192 | MIT *(unverified this session)* | One model gives dense, sparse and late-interaction outputs | Later |

The live MTEB leaderboard did not render when checked, so the scores above are self-reported on model cards.

### 2.2 Hosted embedding APIs

| Provider | Model | Price per 1M tokens | Notes |
|---|---|---|---|
| [OpenAI](https://developers.openai.com/api/docs/pricing) | `text-embedding-3-small` / `-large` | $0.02 / $0.13 | Still the current generation. The proposal's model. **Should (S9)**: about $1 for 50M tokens. |
| [Voyage](https://docs.voyageai.com/docs/pricing) | `voyage-4-lite` / `voyage-4` / `voyage-4-large` | $0.02 / $0.06 / $0.12 | 200M free tokens; batch 33% cheaper |
| [Google](https://aistudio.google.com/docs/embeddings) | `gemini-embedding-2` | $0.20 (text) | Multimodal; batch 50% off |
| [Cohere](https://docs.cohere.com/docs/cohere-embed) | `embed-v5.0` | not listed on the pricing page | |

Hosted models are a comparison, never a dependency (local-first, D-004).

### 2.3 E-commerce and image models

| Model | What it is | Verdict |
|---|---|---|
| [`Marqo/marqo-ecommerce-embeddings-B`](https://huggingface.co/Marqo/marqo-ecommerce-embeddings-B) | 203M, Apache-2.0, text and image embeddings tuned for e-commerce | Later (image search) |
| [SigLIP 2](https://huggingface.co/google/siglip2-base-patch16-224) | Apache-2.0 image-text models | Later |
| `jina-clip-v2` | Non-commercial licence | Rejected |

### 2.4 Known weaknesses that shape the design

- **Negation and exclusion:** NevIR, ExcluIR, BoolQuestions, QUEST.
- **Numeric conditions:** NumConQ reports dense retrievers satisfying numeric constraints about 16% of the time.
- **Instruction following:** FollowIR, Promptriever.

All are summarized with citations in [13](13-related-work.md#5-constraints-and-negation-in-retrieval). Design consequence: exclusions and numeric limits are enforced symbolically, never through the query embedding.

### 2.5 Practical notes

- sentence-transformers is at 6.2.0 (2026-10-21). Version 6 added `MultiVectorEncoder` for late-interaction models and requires transformers v5.
- On Apple Silicon the torch backend uses the GPU through MPS automatically. ONNX and OpenVINO backends exist.
- No trustworthy throughput figures for small models on M-series chips were found. Measure on 10K products before the full run (T5.2).

## 3. Learned sparse and late interaction

| Method | Status | Verdict for short product text |
|---|---|---|
| [SPLADE-v3](https://huggingface.co/naver/splade-v3) | CC BY-NC-SA 4.0, gated | Rejected (licence) |
| OpenSearch `neural-sparse-encoding-doc-v3-gte` | Apache-2.0; documents encoded once, queries need only a tokenizer *(unverified via sbert docs)* | Later: the cheapest way to add vocabulary expansion ("granola" ↔ "muesli") |
| BGE-M3 sparse head | MIT | Later |
| Qdrant miniCOIL / BM42 | In fastembed | Rejected (only useful with Qdrant) |
| [`answerdotai/answerai-colbert-small-v1`](https://huggingface.co/answerdotai/answerai-colbert-small-v1) | 33M, Apache-2.0 | Later: as a reranker; late interaction does better than single-vector models on NevIR |
| [`lightonai/GTE-ModernColBERT-v1`](https://huggingface.co/lightonai/GTE-ModernColBERT-v1) | 149M, Apache-2.0 | Later |
| [PyLate](https://github.com/lightonai/pylate) | 1.6.0, MIT; PLAID / WARP indexes | The library to use if late interaction is tried |
| RAGatouille | 0.0.9.post2, appears stalled | Rejected |
| MUVERA (NeurIPS 2024) | Turns multi-vector sets into single vectors for standard ANN | Background only |

## 4. Vector storage and hybrid engines

| Option | Version | Hybrid lexical + vector | Filtering | Verdict |
|---|---|---|---|---|
| NumPy exact search | — | Our own fusion | Exact: mask, then top-k | **Core** |
| [FAISS](https://pypi.org/project/faiss-cpu/) (`faiss-cpu`) | 1.15.1, macOS arm64 wheels | No | ID selector | Stretch (HNSW vs. exact, F-R11) |
| [USearch](https://pypi.org/project/usearch/) | 2.26.6, Apache-2.0 | No | Predicate callback | Alternative to FAISS |
| hnswlib | 0.8.0, last release 2023-12 | No | Callback | Rejected (stale) |
| ScaNN | 1.4.2 | No | — | Rejected (Linux-only wheels) |
| [sqlite-vec](https://github.com/asg017/sqlite-vec) | 0.1.9, pre-1.0 | With FTS5 in the same file | Metadata columns | Later |
| [DuckDB vss](https://duckdb.org/docs/2.0/core_extensions/vss.html) | experimental | With DuckDB FTS | Undocumented | Rejected (experimental persistence) |
| [LanceDB](https://docs.lancedb.com/search/hybrid-search) | 0.41.0, Apache-2.0, embedded | Yes (RRF by default) | Pre-filter by default | Later (embedded alternative) |
| [Qdrant](https://qdrant.tech/documentation/search/hybrid-queries/) | 1.20.0 | Dense + sparse + BM25; fusion by RRF (configurable k, weighted since 1.17) or DBSF | Filterable HNSW with ACORN-style traversal | Later |
| Weaviate | embedded mode "experimental" | BM25F + vector with `alpha` | Pre-filter *(unverified)* | Rejected for laptops |
| Milvus Lite, Chroma | 3.2.2; 1.5.9 | Partial | Scalar filters | Rejected |
| pgvector (+ pg_textsearch or ParadeDB) | 0.8.7 | Through SQL | Iterative index scans since 0.8 | Later (a Postgres story) |
| Elasticsearch 9.x | 9.5.6 | `rrf` and `linear` retrievers (paid licence) | ACORN filtered kNN; BBQ quantization | Later |
| OpenSearch 3.x | 3.9.0 | Free normalization and RRF processors | | Later |

**When does exact search stop being enough?** These are estimates, memory-bandwidth-bound on an M-series laptop *(unverified)*:

| Corpus | Vector data | Time per query |
|---|---|---|
| 100K × 384, fp32 | about 150 MB | a few milliseconds |
| 1M × 768, fp32 | about 3 GB | tens of milliseconds; fp16 halves the memory |

Our full US corpus at 384 dimensions sits comfortably inside the exact range. Exact search also makes filtered retrieval trivially correct.

**Filtered approximate search** is an active research area, which is worth one paragraph in the report:

- **ACORN** (Patel et al., SIGMOD 2024) handles arbitrary predicates during graph traversal.
- **Filtered-DiskANN** (Gollapudi et al., WWW 2023 *(venue unverified)*) builds label filters into the graph.
- Elasticsearch 9.1 and Qdrant ship ACORN-style traversal.

## 5. Fusion

| Method | Notes | Verdict |
|---|---|---|
| Reciprocal Rank Fusion (Cormack, Clarke and Büttcher, SIGIR 2009) | Rank-based, no calibration, k = 60 in the paper. Engine defaults differ (OpenSearch 60, Qdrant 2), so state k. | **Core** |
| Convex combination of normalized scores | Bruch, Gai and Ingber ([ACM TOIS](https://doi.org/10.1145/3596512); [arXiv 2210.11934](https://arxiv.org/abs/2210.11934)): beats RRF in and out of domain; RRF is sensitive to k; largely insensitive to the normalization choice; needs only a few labelled queries to tune | **Should (S3)** |
| Distribution-based score fusion (DBSF) | Normalize by mean ± 3σ, then sum (Qdrant) | Later |
| CombSUM, CombMNZ, Borda, Condorcet, probabilistic fusion | All implemented in [`ranx`](https://amenra.github.io/ranx/fusion/) 0.3.21, with a grid optimizer | Later (a quick robustness check if time allows) |
| Learned fusion | Features into a learning-to-rank model | Later |

## 6. Re-ranking

### 6.1 Cross-encoders

| Model | Size | Licence | Verdict |
|---|---|---|---|
| `cross-encoder/ms-marco-MiniLM-L6-v2` | 22M | Apache-2.0 *(unverified)* | Stretch (fast baseline) |
| [`Alibaba-NLP/gte-reranker-modernbert-base`](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base) | 149M | Apache-2.0 | Stretch (preferred) |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | 0.6B | Apache-2.0 | Later |
| [`Qwen/Qwen3-Reranker-0.6B`](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | 0.6B | Apache-2.0 | Later (instruction-aware; scores 5.41 on FollowIR per its card) |
| [`mixedbread-ai/mxbai-rerank-base-v2`](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 0.5B | Apache-2.0 | Later |
| [`jinaai/jina-reranker-v3.5`](https://huggingface.co/jinaai/jina-reranker-v3.5) | 0.6B | CC BY-NC 4.0 | Rejected (licence) |
| [FlashRank](https://pypi.org/project/FlashRank/) | ONNX, no torch; includes a cross-encoder fine-tuned on Amazon's ESCI shopping data | — | Later (interesting for product search) |

Hosted rerankers (Cohere Rerank v5, Voyage `rerank-3`) are Later.

Why reranking is Stretch rather than Core: it changes the top 10, which means more items to label. Its known strength, better negation handling than bi-encoders, matters less here because exclusions are enforced symbolically.

### 6.2 LLM rerankers

- **Methods:** RankGPT (Sun et al., [EMNLP 2023](https://aclanthology.org/2023.emnlp-main.923/)), setwise prompting (Zhuang et al., SIGIR 2024), FIRST (Reddy et al., [EMNLP 2024](https://aclanthology.org/2024.emnlp-main.491/)).
- **Libraries:** [`rank_llm`](https://github.com/castorini/rank_llm) 0.26.0 bundles them. The `rerankers` library (0.10.0) has had no release in about 18 months.
- **What the evidence says:** a reproduction of NevIR (SIGIR 2025) found listwise LLM rerankers the best family on negation but still below humans *(from search results)*.
- **Verdict:** Later. They are better used as an offline relevance labeler than in the live path.

### 6.3 Learning to rank

- **Libraries:** LightGBM 4.7.0 (`LGBMRanker`, objective `lambdarank`) and XGBoost 3.4.1 (`XGBRanker`, objective `rank:ndcg`; training data must be sorted by query id).
- **Features it would use:** per-field BM25, dense cosine, reference similarity, per-nutrient deltas, Nutri-Score and NOVA, evidence completeness, scans.
- **Verdict:** Later. With 12 dev scenarios a learned ranker would overfit; it needs a few hundred labelled queries. LLM-generated labels could supply them, which is the future-work story (Thomas et al., SIGIR 2024).
- **Cascade ranking references:** Wang, Lin and Metzler (SIGIR 2011); Liu et al., "Cascade Ranking for Operational E-commerce Search" (KDD 2017).

## 7. Query understanding

### 7.1 Rule-based tools

| Tool | Version | Use | Verdict |
|---|---|---|---|
| Python regular expressions and gazetteers | — | The parser in [05](05-query-understanding.md) | **Core** |
| [`pyahocorasick`](https://pypi.org/project/pyahocorasick/) | 2.3.1 | Multi-pattern matching over taxonomy names | Core (if needed for speed) |
| [spaCy](https://pypi.org/project/spacy/) | 3.8.18; supports Python 3.13 | `Matcher` and `DependencyMatcher` for richer patterns | Later |
| [negspacy](https://pypi.org/project/negspacy/) | 1.1.0 | NegEx-style negation scope from clinical NLP | Later (our scope rules are simpler and tested) |
| [quantulum3](https://pypi.org/project/quantulum3/) | 0.10.0 | Quantity and unit extraction | Later (our numeric patterns are few) |

### 7.2 LLM-based parsing (Stretch, F-Q13)

| Option | What it offers |
|---|---|
| [Ollama](https://docs.ollama.com/capabilities/structured-outputs) | JSON-schema-constrained output from local models |
| [Outlines](https://pypi.org/project/outlines/) 1.3.3; [Instructor](https://pypi.org/project/instructor/) 1.17.0 | Structured generation and validation |
| Hosted structured outputs (Anthropic, OpenAI, Google) | JSON-schema outputs. Anthropic's documentation notes that numeric minimum and maximum constraints are not enforced, so validate afterwards. |

- **Small local models** that fit a 16 GB laptop are reported in the news, for example the Qwen3.5 small series (March 2026) and Gemma 4 (April 2026) *(confirm on the model cards before use)*.
- **Evaluation gap:** no rigorous benchmark of text-to-filter parsing was found, and LLMs are known to invent filter values that are not in the vocabulary. Our slot-level parser evaluation (S5) is a small contribution here.

### 7.3 E-commerce query-understanding literature

- QueryNER (LREC-COLING 2024): segmenting shopping queries into 17 entity types.
- The ESCI paper deliberately samples negation queries such as "energy bar without nuts" as a hard subset.
- The TREC 2023 Product Search track found traditional lexical systems highly effective, often better than single-stage dense runs.
- WANDS (Wayfair, ECIR 2022): 480 queries with 233K labels.
- LLM query rewriting for the long tail, e.g. BEQUE (WWW 2024 companion).

Details and links are in [13](13-related-work.md#3-substitute-recommendation-in-e-commerce-and-grocery).

## 8. Diversification

| Method | Notes | Verdict |
|---|---|---|
| Collapse near-duplicate families | Exact key ([03](03-data-pipeline.md#51-product-families)) | **Core** |
| MMR (Carbonell and Goldstein, SIGIR 1998) | One parameter λ; embedding similarity | **Core** |
| Brand cap | At most two per brand in the top five | Stretch |
| xQuAD, IA-Select, PM-2 | Need explicit subtopics or intents | Later |
| DPP with fast greedy MAP inference (Chen, Zhang and Zhou, NeurIPS 2018) | Elegant, but needs a quality-diversity kernel | Later |
| MinHash / LSH (`datasketch` 2.0.0) | Fuzzy duplicates. The new default hash scheme invalidates old sketches. | Later (F-D12) |

**Metrics:**

- **Intra-list distance and distinct brands or families** are computed ourselves (**Core**).
- **α-nDCG, ERR-IA and subtopic recall** exist in `ir-measures` but need subtopics we do not have (Later).

## 9. Evaluation tooling

| Tool | Version | Use | Verdict |
|---|---|---|---|
| [`ir-measures`](https://ir-measur.es/en/latest/measures.html) | 0.4.3 (2025-11-25) | Standard metrics and naming; Judged@k; diversity measures via pyndeval | **Core** |
| [`ranx`](https://pypi.org/project/ranx/) | 0.3.21 (2025-08-07) | Metrics, 25 fusion methods, Fisher randomization and Tukey HSD tests, LaTeX table export | Core cross-check |
| `pytrec_eval` | last push Oct 2023 | trec_eval in Python; custom gains | Backend only |
| PyTerrier `pt.Experiment` | 1.1.2 | Experiment tables with significance and correction | Later |
| Our statistics module | — | Paired randomization, bootstrap intervals, Holm, MDE | **Core** (T6.6) |

**Annotation tools:**

| Tool | Status | Verdict |
|---|---|---|
| Custom Streamlit labeling page | Shows product cards beside the reference, hides provenance, writes JSONL | **Core** (T6.3) |
| Label Studio | 1.23.2 (Sep 2026), active | Rejected: setup cost for two assessors |
| Argilla | Last release v2.8.0 (Mar 2025) | Rejected |
| doccano | v1.8.5 (Jan 2026) | Rejected: text-centric |
| Google Sheets | — | Fallback if the labeling page fails |
