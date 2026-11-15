# 03 · Data pipeline and storage

**Use:** design, implemented in `foodswap/data.py` (`python -m foodswap.data build`, about 15 seconds). Changes go through [decisions.md](decisions.md).
**Read by:** DATA role (owner); RANK and QUX for the schema in section 2.
**Last updated:** 2026-11-14 (first build).

This document specifies how the Open Food Facts dump becomes the corpus the search engine runs on. Sources are described in [02-data-sources.md](02-data-sources.md).

## 1. Principles

1. **Sample alongside.** Every build also writes an 18K-product sample, so development never waits on the full corpus.
2. **Exclude, never repair.** A record that fails a check is left out of the corpus and counted. We do not guess a corrected value. Repair is unbounded work and quietly changes the data we report on.
3. **Every exclusion is counted.** The pipeline emits a funnel (rows in, rows out, per gate). The funnel is a deliverable, not a log line.
4. **One row index.** After the corpus is frozen, the row position `idx` is the document id in every index and array. The barcode `code` is the external id used in run files and labels.
5. **One command, one snapshot.** `python -m foodswap.data build` goes from the raw Parquet to the corpus, and `build.json` records the SHA-256 of the dump it was built from.

## 2. Canonical schema

`data/corpus/products.parquet`, one row per product. This schema is the contract between roles.

### 2.1 Identity and text

| Column | Type | Derived from | Notes |
|---|---|---|---|
| (row position) | | | The document id in all indexes; not stored as a column |
| `code` | string | `code` | Barcode as stored by OFF, digits only |
| `name` | string | `product_name`: the `en` entry, else the main-language entry | Required |
| `generic_name` | string, nullable | `generic_name`, same rule | |
| `brand` | string, nullable | `brands` | First brand, trimmed. Missing for 36% of products. |
| `ingredients_text` | string, nullable | `ingredients_text`, same rule | Present for 88% of products |

### 2.2 Tags

| Column | Type | Derived from | Notes |
|---|---|---|---|
| `categories` | list<string> | `categories_tags` | Only ids that exist in the category taxonomy; at least one required |
| `category` | string | computed | Deepest category on the product |
| `comparison_category` | string | computed | See section 5.2 |
| `ingredient_tags` | list<string> | `ingredients_tags` | Canonical ids only |
| `ingredients_n`, `unknown_ingredients_n` | int32 | same-named columns | Inputs to the evidence-sufficiency rule |
| `allergen_tags`, `trace_tags` | list<string> | `allergens_tags`, `traces_tags` | Canonical ids only; non-canonical entries such as `en:Corn` are dropped |
| `label_tags` | list<string> | `labels_tags` | Canonical ids only |
| `analysis_tags` | list<string> | `ingredients_analysis_tags` | Vegan / vegetarian / palm-oil status (used by S7) |

### 2.3 Nutrition

Every nutrient in the dump becomes a column: 54 of them, from `energy_kcal`, `fat`, `sugars`, `proteins` and `sodium` to cholesterol, trans fat, vitamins, minerals and individual sugars. Dashes become underscores (`saturated-fat` → `saturated_fat`). Values are per 100 g, or per 100 ml for drinks, taken from the `100g` member of each `nutriments` entry. Masses are in grams, so sodium 0.487 means 487 mg.

Three kinds of entries are left out:

- scores and estimates that are not nutrients (Nutri-Score points, NOVA group, fruit and vegetable estimates);
- duplicates: energy in kJ, and `salt`, which is always sodium × 2.5;
- names used by fewer than 1% of products, which are mostly one-off typos such as `es-l-glutamine`.

The list is discovered from the data on each build and saved in `build.json`.

The eight **headline nutrients** are energy, fat, saturated fat, carbohydrates, sugars, fiber, protein and sodium. They are the numbers every label carries, used for the plausibility check (section 4) and for recognizing pack sizes (section 5.1).

| Column | Type | Notes |
|---|---|---|
| one column per nutrient | float | missing values are `NaN` |
| `basis` | string | `g` or `ml`. Two products are only ever compared on the same basis. |

Missing values are `NaN`, never zero. A blank on a label is not a zero.

### 2.4 Scores, popularity and provenance

| Column | Type | Derived from | Notes |
|---|---|---|---|
| `nutriscore_grade` | string, nullable | `nutriscore_grade` | `a`–`e`; other values become null. Computed by OFF. Used by baseline X2 and shown in the UI. |
| `nova_group` | int, nullable | `nova_group` | Shown in the UI only |
| `scans` | int | `unique_scans_n` (0 if missing) | Popularity; a tie-breaker |
| `last_modified_t` | int | `last_modified_t` | Shown as "record last edited" |
| `family_id` | int | computed | Section 5.1 |

Other files in `data/corpus/`:

- `sample.parquet`: the same columns for 18,293 products (section 3).
- `build.json`: the funnel (section 4), counts, and the SHA-256 of the dump it came from.
- Added by later steps: `evidence.parquet` ([07](07-constraints-and-safety.md#4-storage)) and the nutrient percentiles (section 5.3).

## 3. Extraction

One DuckDB query reads the US rows that are not obsolete and flattens them: the English entry of each multilingual field, one column per nutrient, plain tag lists. Two small SQL macros do the flattening (DuckDB 2.0 needs `lambda x: …`, and `"name"` and `"text"` are reserved words):

```sql
CREATE MACRO english(texts) AS coalesce(
    list_filter(texts, lambda x: x.lang = 'en'   AND trim(x."text") <> '')[1]."text",
    list_filter(texts, lambda x: x.lang = 'main' AND trim(x."text") <> '')[1]."text");
CREATE MACRO nutrient(values, n) AS list_filter(values, lambda x: x."name" = n)[1]."100g";
```

The rest of the cleaning runs in pandas on the roughly 370K rows that have an English name and at least one category tag.

The build also writes `sample.parquet`: the 5,000 most-scanned products in each of the four proposal categories (breakfast cereals, yogurts, snacks, beverages), 18,293 in total because cereals have fewer than 5,000 and some products sit in two categories. The sample keeps the full corpus's family ids and comparison categories.

**Basis.** Checked on the 2026-11-14 snapshot (US rows): neither field is reliable.

- `nutrition_data_per` records how values were *entered* (`100g` 560K, `serving` 327K, missing 115K, `100ml` only 66), not the basis of the stored per-100 values.
- `product_quantity_unit` is missing for 845K of 1.0M rows (`g` 137K, `ml` 20K).

So the fallback rule applies: products under `en:beverages` are `ml`, everything else `g`, unless `product_quantity_unit` says otherwise. The rule is stated in the report.

## 4. Quality checks and the funnel

Checks run in this order. Counts are from the build on the 2026-11-14 snapshot:

| Step | Rule | Products left |
|---|---|---|
| US products | `countries_tags` contains `en:united-states`, not obsolete | 1,002,000 |
| English | Main language is English and there is an English (or main-language) name | 960,992 |
| Has a category | At least one category the taxonomy knows; free-text categories are dropped | 367,436 |
| No OFF quality errors | `data_quality_errors_tags` is empty. These are OFF's own checks: energy not matching the macronutrients, totals over 105 g per 100 g, energy over 3,800 kJ | 349,527 |
| Plausible nutrition | No headline nutrient below 0 or above 105 g (labels round, so corn syrup can show 103 g of carbohydrate), and energy at most 900 kcal per 100 g. An impossible value in any other nutrient (184 products had impossible water values) blanks that value instead of dropping the product. | **349,308** |

What the numbers show:

- **Category is the expensive requirement:** it removes 62% of English-named US products. It stays, because without a category there is no way to decide what "the same kind of product" means. Category imputation (Robotoff predictions or our own classifier) is future work (F-D14).
- **The language check catches more than language.** It removes the vandalized Cheerios record (`0016000275287`, main language set to Latin) and the Italian bran flakes (`20621483`).
- **Incomplete products stay.** A product without English ingredients or without some nutrients is kept: it can still answer a request with no exclusions, and rejecting it for an exclusion is a result we count (the unknown-rejection rate), not hide.

Nutrient coverage in the corpus:

| Nutrient | Present |
|---|---|
| Energy, protein, fat | 95% |
| Sodium | 93% |
| Sugars | 92% |
| Saturated fat | 87% |
| Fiber | 80% |
| Added sugars | **20%** |

Requests about "added sugar" will therefore often meet "not reported".

## 5. Enrichment

### 5.1 Product families

A family is one product sold under several barcodes, typically different pack sizes. Without families, the top five fills with sizes of the same thing.

**Key (exact match):** normalized brand + normalized name + nutrient signature. **Unbranded products are never grouped.** Without a brand, "Extra Virgin Olive Oil" with olive oil's nutrition matched 72 different products in the first build.

- Normalized brand and name: lower-case, strip punctuation, collapse whitespace, remove size tokens ("18 oz", "510 g", "family size").
- Nutrient signature: the eight headline nutrients rounded to one decimal place, with missing values encoded as such. Vitamins are left out, because two people entering the same product often record different ones.

Result: 349,308 products form 337,242 families. Most families are single products; 9,867 have two members, and the largest are one brand's seltzer water or Diet Pepsi in many sizes (10–21 barcodes). Search results show one member per family and note how many other sizes exist.

Acceptance for T2.5: the two Cheerios records `0016000275263` and `0016000170032` share a family, and a reference product's own family is never returned as a substitute.

Fuzzy matching (edit distance, MinHash over ingredients) would merge more, and would also merge things that are different products. It is out of scope (F-D12).

### 5.2 Comparison category

The comparison category answers "which products are the same kind of thing as the reference". It is the most specific of the product's own categories that holds at least 30 families. Category depth is the longest path to the top of the taxonomy, since a category can have several parents. If none of a product's categories is that big, the one with the most families is used.

Example: a granola tagged `en:breakfast-cereals` → `en:mueslis` uses `en:mueslis` if that category has 30 or more families, and otherwise backs off to `en:breakfast-cereals`.

Coarse tagging limits this: 30,759 products are tagged only `en:snacks`, so plain "snacks" is their comparison category. A precisely tagged reference never compares against them, because they are not in its category.

A type term in the request overrides this: "a similar cereal" on a granola reference widens the scope to the category whose name matches "cereal". The override logic lives in query formulation ([05](05-query-understanding.md#6-query-formulation)).

### 5.3 Nutrient percentiles

For each nutrient and each category with enough products, store the empirical distribution of per-100 values over searchable products on the same basis. The score term N compares the percentile of the candidate with the percentile of the reference inside the comparison category ([06](06-retrieval-and-ranking.md#62-nutrient-improvement-n)). Percentiles are robust to the outliers that survive the gates and are easy to explain: "from the 80th percentile for sugar among cereals to the 20th".

## 6. Storage layout

```
data/                  (git-ignored)
  raw/                 food.parquet, taxonomies/*.json, REVISION, MANIFEST.json   (never edited)
  corpus/              products.parquet, sample.parquet, build.json; later evidence.parquet
  index/               BM25 and dense indexes (later)
  runs/                one folder per system run (later)
eval/                  scenarios/, b3_cache/, pools/, labels/, qrels/                (tracked)
reports/               data_audit.md, figures/                                       (generated)
```

`build.json` records the dump's SHA-256, so builds from the same snapshot are interchangeable and anything else is visibly different.

`MANIFEST.json` records the Hugging Face revision, the file's SHA-256, the total and US row counts, and the date it was checked.

## 7. The missingness and coverage audit

The proposal promised "a dataset and missingness report". Task T2.6 produces it from a script, so it can be regenerated after any change.

Contents of `reports/data_audit.md`:

1. **Funnel.** Rows at each stage: world, US, not obsolete, English name, canonical category, passing each sanity check, searchable. One figure.
2. **Field completeness by category.** For each of the proposal's four categories and for the corpus overall: share of searchable products with English ingredients, with each of the ten nutrients, with a Nutri-Score, with at least one allergen tag, with at least one trace tag.
3. **Evidence coverage.** For each allergen in the vocabulary: share of products with verdict pass, fail and unknown. This predicts how many scenarios can reach five eligible results.
4. **Families.** Number of families, distribution of family size, the largest families.
5. **Corpus statistics for the report.** Number of documents, mean and median field lengths in tokens, vocabulary size per field.
6. **Dropped tags.** Counts of non-canonical category, label and allergen entries removed.

An early warning to act on: if section 3 shows a low pass rate for common allergens, scenario references should be chosen from well-populated categories and the evidence-sufficiency threshold examined on dev (see [10](10-plan.md#7-risks)).

## 8. Fixtures

- `tests/fixtures/pilot.parquet`: the proposal's 4×100 products in the canonical schema, committed to the repository with an ODbL notice. Unit tests and continuous checks run on it, so tests need no download.
- Golden records for the constraint tests: the products listed in [02](02-data-sources.md#28-data-quality-observed-first-hand), stored as they appear in the pinned snapshot.

## 9. Data card

A short `DATA_CARD.md` at the repository root, written with T8.4: source and snapshot date, licence and attribution, selection criteria (the gates above), known limitations (crowd-sourced, US and English only, records can be stale or vandalized, "pass" means "not declared"), and the funnel numbers.
