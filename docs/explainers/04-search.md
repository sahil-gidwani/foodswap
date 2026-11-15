# Search

The fourth primer for the team, after [01](01-data-and-code.md) (data and taxonomies), [02](02-data-cleaning.md) (cleaning) and [03](03-allergen-check.md) (the allergen check). This one explains `foodswap/search.py`: what search does, how its two methods work and are combined, what you can and can't search yet, and what it costs.

**State as of Nov 14.** All 349,308 products are indexed. A search takes 33–73 ms.

```
python -m foodswap.search build            # about 18 minutes; --sample builds the 18K sample in about a minute
python -m foodswap.search query "crunchy oat cereal" --exclude peanuts
```

## 1. The job

Search answers one question: **which products match what the person described?** For "crunchy oat cereal" it should return crunchy oat cereals, not oat milk or cereal bowls.

It doesn't know about a reference product or nutrition goals. Those belong to the next steps:

- **The request parser** turns a sentence into search words, exclusions and preferences.
- **Ranking** adds similarity to the reference product and nutrition improvement.

Search finds good candidates; ranking orders them.

## 2. The flow

```
query text ─┬─► keyword search (BM25)  ─► top 1,000 ─┐
            │                                        ├─► merge by rank (RRF) ─► top k
            └─► meaning-based search    ─► top 1,000 ─┘
                     ▲
excluded allergens ──┘  (applied to both, before anything is ranked)
```

## 3. Step 1: the allergen filter comes first

Before ranking anything, `eligible()` builds the **allowed list**: every product whose verdict is PASS for each excluded allergen. With "no peanuts", 231,163 of 349,308 products remain; FAIL and UNKNOWN are both out.

Both methods then rank only allowed products, across the whole corpus.

Why filter first: if we took the top 10 and filtered afterwards, a "no peanuts" search could end up with two results just because the top 10 happened to be mostly peanut products. Filtering first means "only 3 options exist" is a true statement about the data, not an artifact of where we cut.

## 4. Step 2a: keyword search (BM25)

BM25 is the classic search-engine scoring formula. It scores how well a product's words match the query's words, following three ideas:

1. **More matches score higher,** with diminishing returns: the fifth "oat" adds much less than the first.
2. **Rare words count more.** "Oat" appears on thousands of products and says little; "crunchy" is rarer and says more.
3. **Long text is discounted.** A match in a short name means more than the same word buried in a long ingredient list.

The query and the products are cleaned the same way:

- lower-cased;
- stopwords such as "the" and "with" removed;
- words reduced to their root, so "crunchy" becomes "crunchi" and "oats" becomes "oat", and variants match.

Each product is searched in three fields, and the scores are added with weights:

| Field | Contents | Weight |
|---|---|---|
| Name | name, generic name, brand | 1.0 |
| Categories | English names of all its categories ("Breakfast cereals", "Extruded cereals") | 0.5 |
| Ingredients | the ingredient list, with HTML markup removed | 0.3 |

A match in the name is the strongest sign of what a product is. These weights are starting values; we'll tune them once on the practice scenarios and then use the same ones for every system we compare.

Strengths and weaknesses:

- **Fast and precise.** "Cheerios" finds Cheerios, and "greek yogurt honey" finds exactly those words. Research on product search finds it hard to beat.
- **Matches words, not meaning.** "Fizzy drink" returned bottled water, because "drink" was the only word that matched.

## 5. Step 2b: meaning-based search (embeddings)

An **embedding model** turns text into a list of numbers, arranged so that texts with similar meaning get similar numbers. "Soda" and "fizzy drink" end up close together without sharing a word.

Ours is `bge-small-en-v1.5`: small (33 million parameters), free, MIT-licensed, and running on the laptop's GPU. It produces 384 numbers per text.

**Building:** each product becomes a short description, which the model converts into its 384 numbers. The result is saved once (about 270 MB for the full corpus). For example:

> Cheerios. General Mills. Extruded cereals. Ingredients: Whole Grain Oats, Corn Starch, Sugar, Salt, …

Descriptions average 74 tokens, far below the model's 512-token limit, so nothing is cut off.

**Searching:** the query is converted the same way, with a short instruction in front that this model expects for queries ("Represent this sentence for searching relevant passages:"). It's compared with every allowed product in one matrix multiplication, which measures how closely the two lists of numbers point in the same direction (cosine similarity). No approximate index is needed at this size; the comparison is exact.

Strengths and weaknesses:

- **Understands meaning.** "Fizzy drink" finds sodas; "peanut butter cereal" finds peanut butter granola; it tolerates typos like "chedar chese".
- **Fuzzier, and doesn't understand "no".** To this model, "no peanuts" sits close to "peanuts". That's exactly why exclusions are enforced by the allergen filter, never by search.

## 6. Step 3: merging the two lists (Reciprocal Rank Fusion)

The two methods score on different scales: BM25 might give 14.2, the embedding 0.83. So `rrf()` merges by **position in each list**. Each product earns `1 / (60 + its rank)` from each list it appears in, and the amounts are added:

| Product | Keyword rank | Meaning rank | Merged score |
|---|---|---|---|
| A | 1 | 3 | 1/61 + 1/63 = 0.0323 |
| B | 2 | not in its top 1,000 | 1/62 = 0.0161 |
| C | not in its top 1,000 | 1 | 1/61 = 0.0164 |

A wins because both methods agree. The 60 comes from the paper that proposed the method (Cormack, Clarke and Büttcher, 2009); it stops either list's first place from dominating. The proposal specified this method.

What merging fixed in practice, on the sample:

| Query | Keyword search alone | Meaning search alone | Merged |
|---|---|---|---|
| "fizzy drink" | Bottled water | Sodas and sparkling drinks | Sodas and sparkling drinks |
| "peanut butter cereal" | Peanut butter jars and cups | Peanut butter granola | Peanut butter cereals (Kashi, Kroger) on top |

## 7. What you can and can't search yet

**Works now** (real results on the sample):

| You type | You get |
|---|---|
| A kind of product: "crunchy oat cereal" | Crunchy oat cereals |
| A brand: "kellogg's" | Kellogg's products |
| A flavour or ingredient: "yogurt with blueberries" | Blueberry yogurts |
| Other words for the same thing: "fizzy drink" | Sodas and sparkling drinks |
| Small typos: "chedar chese crackers" | Cheese crackers |
| "cereal", with `exclude=["peanuts"]` | Cereals that all pass the peanut check |

**Doesn't work yet, and what fixes it:**

| You type | What happens | Fixed by |
|---|---|---|
| "cereal **no peanuts**" | **All five results contain peanuts**: "peanuts" is searched for, and "no" is ignored | The request parser turns "no peanuts" into the exclusion option |
| "cereal with **less sugar**" | Apple Jacks, Froot Loops, Frosted Flakes (27–37 g sugar per 100 g): the word "sugar" matches sugary cereals | Parser and ranking: "less sugar" becomes a nutrition goal |
| "something **like Cheerios**" | No notion of a reference product | Ranking adds similarity to the chosen product |
| "**under 8 g** sugar" | Numbers mean nothing to search | Parser: a hard limit checked against the nutrition data |
| "greek yogurt with honey", milk excluded | Five jars of honey: every dairy yogurt fails milk, and nothing keeps results to yogurts | Parser or reference product: limiting results to the yogurt category, which then shows plant-based yogurts |
| A barcode: "0016000170032" | Random products | The app's product picker looks barcodes up directly |

The first row is the core problem this project is about: plain search, keyword or AI, does the opposite of what you asked.

## 8. Building search exposed an allergen-check gap

"Peanut butter cereal" with peanuts excluded first returned Reese's cups and Hershey's Peanut Butter Blossoms. Their ingredient lists were cut off before the peanut part, so they had passed. The allergen check now also reads the product name: if the name mentions the allergen but the ingredients don't, the verdict is "can't verify" ([03 §4.3](03-allergen-check.md#43-when-a-pass-is-allowed)).

A later scare turned out fine. A product called "Jif" ranked first for that query, but Jif's 11 passing products are hazelnut spreads, almond butter bars and Jiffy biscuit mix. All 87 Jif peanut butters fail the check. Meaning-based search just associates the brand with peanut butter.

## 9. What it costs

| | Sample (18K) | Full corpus (349K) |
|---|---|---|
| Keyword indexes | under 1 second | 12 seconds |
| Embeddings | about 1 minute (the first run also downloads the model) | about 18 minutes, roughly 330–400 products a second on the M4's GPU |
| Index size on disk | small | 341 MB |
| Loading the indexes | a few seconds | about 4 seconds |
| One search | about 0.15 seconds | 33–73 ms |

The sample's per-search time includes more one-off overhead; both are fast enough for an interactive app.

## 10. Try it

```python
from foodswap.search import Search

search = Search("sample")   # "products" for the full corpus
results = search.search("crunchy oat cereal", exclude=["peanuts"], k=5)
print(results.attrs["eligible"], "eligible products")
print(results[["name", "brand", "keyword_rank", "dense_rank", "score"]].to_string(index=False))
```

Output:

```
11889 eligible products
                                                                           name       brand  keyword_rank  dense_rank    score
                                            Crunchy Almond Oatmeal Crisp Cereal         NaN             8           2 0.030835
                                                             Crunchy Honey Oats Great Value             7           5 0.030310
                                                     Raisin bran cereal crunchy    Foodhold             6          12 0.029040
                                                      Almond Crunchy Honey Oats Great Value            16           3 0.029031
Honey oat crunchy wheat, rice & corn flakes with oats & honey cereal, honey oat   Kellogg's             2          19 0.028787
```

The two rank columns show what merging does. No result is first in either list, but each ranks well in both, so they rise to the top. Results come back with `keyword=False` or `dense=False` too, for comparing the methods.

## 11. Tests

`tests/test_search.py` checks the logic that doesn't need the model:

- picking the best products within the allowed list;
- requiring a positive keyword score;
- an empty allowed list;
- the merge formula and its ordering.

`python -m pytest` runs them with the allergen tests (43 in total, under a second).

## 12. Next

The **request parser**, so a full sentence like "a similar cereal with less sugar, more protein, and no peanuts" becomes:

- search words: "cereal";
- exclusions: peanuts;
- preferences: less sugar, more protein.

How to build it reliably is still open; see the discussion of rules versus an AI model with guardrails.

The full design is in [retrieval and ranking](../06-retrieval-and-ranking.md).
