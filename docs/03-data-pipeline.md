# 03 · Data pipeline and storage

**Use:** design (frozen after the schema freeze on Tue Nov 10, except through [decisions.md](decisions.md)).
**Read by:** DATA role (owner); RANK and QUX for the schema in section 2.
**Last updated:** 2026-11-10.

This document specifies how the Open Food Facts dump becomes the corpus the search engine runs on. Sources are described in [02-data-sources.md](02-data-sources.md).

## 1. Principles

1. **Sample first.** A 20K-product sample corpus exists on Tue Nov 10, before any cleaning is finished, so the other three roles are never blocked on data.
2. **Flag and exclude, never repair.** A record that fails a check gets a flag and is kept out of the searchable set. We do not guess a corrected value. Repair is unbounded work and quietly changes the data we report on.
3. **Every exclusion is counted.** The pipeline emits a funnel (rows in, rows out, per gate). The funnel is a deliverable, not a log line.
4. **One row index.** After the corpus is frozen, the row position `idx` is the document id in every index and array. The barcode `code` is the external id used in run files and labels.
5. **One command, one snapshot.** `python -m foodswap.data build` goes from the raw Parquet to the corpus, and every artifact records the manifest hash it was built from.

## 2. Canonical schema

`data/corpus/products.parquet`, one row per product. This schema is the contract between roles.

### 2.1 Identity and text

| Column | Type | Derived from | Notes |
|---|---|---|---|
| `idx` | int32 | row position | Document id in all indexes |
| `code` | string | `code` | Barcode as stored by OFF, digits only |
| `name` | string | `product_name` entry with `lang = 'en'` | Required by the searchable gate |
| `generic_name` | string, nullable | `generic_name`, `en` | |
| `brand` | string, nullable | `brands` | First brand, trimmed; original kept in `brands_raw` |
| `ingredients_text` | string, nullable | `ingredients_text`, `en` | Lower-cased copy in `ingredients_text_norm` |
| `lang` | string | `lang` | Kept for the audit; not trusted on its own |

### 2.2 Tags

| Column | Type | Derived from | Notes |
|---|---|---|---|
| `categories` | list<string> | `categories_tags` | Only ids that exist in the category taxonomy; free-text entries dropped and counted |
| `category_leaf` | string, nullable | computed | Deepest canonical category on the product |
| `comparison_category` | string, nullable | computed | See section 5.2 |
| `ingredient_tags` | list<string> | `ingredients_tags` | Canonical ids only |
| `ingredients_n`, `unknown_ingredients_n` | int32 | same-named columns | Inputs to the evidence-sufficiency rule |
| `allergen_tags`, `trace_tags` | list<string> | `allergens_tags`, `traces_tags` | Canonical ids only; non-canonical entries such as `en:Corn` dropped and counted |
| `label_tags` | list<string> | `labels_tags` | Canonical ids only |
| `analysis_tags` | list<string> | `ingredients_analysis_tags` | Vegan / vegetarian / palm-oil status (used by S7) |

### 2.3 Nutrition

All values are per 100 g or per 100 ml, as given by the `100g` member of each `nutriments` struct.

| Column | Type | Nutrient name in `nutriments` | Unit |
|---|---|---|---|
| `energy_kcal` | float32 | `energy-kcal` | kcal |
| `sugars` | float32 | `sugars` | g |
| `added_sugars` | float32 | `added-sugars` | g |
| `proteins` | float32 | `proteins` | g |
| `fat` | float32 | `fat` | g |
| `saturated_fat` | float32 | `saturated-fat` | g |
| `carbohydrates` | float32 | `carbohydrates` | g |
| `fiber` | float32 | `fiber` | g |
| `sodium` | float32 | `sodium` | **g** (OFF stores grams; display converts to mg) |
| `salt` | float32 | `salt` | g |
| `basis` | string | computed | `g` or `ml`. Two products are only ever compared on the same basis. |

Missing values are `NaN`, never zero. A blank on a label is not a zero.

### 2.4 Scores, popularity and provenance

| Column | Type | Derived from | Notes |
|---|---|---|---|
| `nutriscore_grade` | string, nullable | `nutriscore_grade` | `a`–`e`; other values become null. Computed by OFF. Used by baseline X2 and shown in the UI. |
| `nutriscore_score` | int32, nullable | `nutriscore_score` | |
| `nova_group` | int8, nullable | `nova_group` | Shown in the UI only |
| `unique_scans_n` | int32 | `unique_scans_n` | Popularity; a tie-breaker and the family representative rule |
| `completeness` | float32 | `completeness` | |
| `quality_flags` | list<string> | computed | Section 4 |
| `searchable` | bool | computed | Section 4 |
| `family_id` | int32 | computed | Section 5.1 |
| `last_modified_t` | int64 | `last_modified_t` | Shown as "record last edited" |

Companion files in the same directory:

- `families.parquet`: `family_id`, member `idx` list, representative `idx`.
- `nutrients.npy`: a float32 matrix (rows × the ten nutrient columns) for vectorized scoring.
- `evidence.parquet`: built by the constraints module, specified in [07](07-constraints-and-safety.md#4-storage).
- `category_postings.npz`: for each category id, the sorted `idx` array of products at or below it.

## 3. Extraction

Two passes with DuckDB, so the expensive scan over 4.9M rows happens once.

**Pass 1: the US subset.** Keep rows whose `countries_tags` contains `en:united-states` and that are not obsolete. Write `data/interim/us.parquet` (about 1.0M rows).

**Pass 2: the canonical projection.** Select the English entry of each multilingual field, pivot the nutrient list into columns, and keep only canonical tags.

The queries below are illustrative. DuckDB 2.0 rejects the old `x -> …` lambda syntax, so use `lambda x: …`; `name` and `text` are reserved words and need double quotes (checked on the 2026-11-14 snapshot).

```sql
-- Pass 1
COPY (
  SELECT *
  FROM read_parquet('data/raw/food.parquet')
  WHERE list_contains(countries_tags, 'en:united-states')
) TO 'data/interim/us.parquet' (FORMAT parquet, COMPRESSION zstd);

-- Pass 2 (excerpt)
SELECT
  code,
  list_filter(product_name,     lambda x: x.lang = 'en')[1]."text" AS name,
  list_filter(ingredients_text, lambda x: x.lang = 'en')[1]."text" AS ingredients_text,
  list_filter(nutriments, lambda x: x."name" = 'sugars')[1]."100g"   AS sugars,
  list_filter(nutriments, lambda x: x."name" = 'proteins')[1]."100g" AS proteins,
  categories_tags, allergens_tags, traces_tags, ingredients_tags,
  ingredients_n, unknown_ingredients_n, nutriscore_grade, unique_scans_n
FROM read_parquet('data/interim/us.parquet');
```

`python -m foodswap.data build --sample 20000` produces the sample corpus: the 5,000 most-scanned products in each of the four proposal categories (breakfast cereals, yogurts, snacks, beverages). It uses the same code path as the full build.

**Basis.** Checked on the 2026-11-14 snapshot (US rows): neither field is reliable.

- `nutrition_data_per` records how values were *entered* (`100g` 560K, `serving` 327K, missing 115K, `100ml` only 66), not the basis of the stored per-100 values.
- `product_quantity_unit` is missing for 845K of 1.0M rows (`g` 137K, `ml` 20K).

So the fallback rule applies: products under `en:beverages` are `ml`, everything else `g`, unless `product_quantity_unit` says otherwise. The rule is stated in the report.

## 4. Quality flags and the searchable gate

Each check adds a flag. A product is `searchable` only if it has none of the blocking flags.

| Flag | Check | Blocking |
|---|---|---|
| `no_english_name` | No `en` entry in `product_name`, or the name is empty | yes |
| `no_category` | No canonical category after dropping free-text entries | yes |
| `obsolete` | Marked obsolete by OFF | yes |
| `nutrient_out_of_range` | Any per-100 value below 0; any gram value above 100; energy above 900 kcal | yes |
| `macros_exceed_100` | fat + carbohydrates + proteins above 105 g per 100 g | yes |
| `energy_mismatch` | Stated energy differs from 4·carbohydrates + 4·proteins + 9·fat by more than 30% and more than 50 kcal | yes |
| `off_quality_error` | Any entry in `data_quality_errors_tags` | yes |
| `mostly_unknown_ingredients` | OFF warning `en:ingredients-90-percent-unknown` | no (the evidence rule handles it) |
| `no_english_ingredients` | No `en` entry in `ingredients_text` | no (searchable, but every allergen verdict will be unknown) |
| `no_nutrition` | All ten nutrient columns missing | no (searchable, but cannot satisfy a numeric limit or earn nutrient improvement) |
| `noncanonical_tags_dropped` | At least one tag was dropped | no |

Two points about the non-blocking flags. A product without English ingredients stays in the corpus because it can still be a valid answer to a request with no exclusions, and because rejecting it for an exclusion is a result we want to count ("unknown-rejection rate"), not hide. The thresholds in the table are starting values; they are tuned once against the sample and then logged in [decisions.md](decisions.md).

Acceptance for T2.3: the vandalized Cheerios record (`0016000275287`) and the Italian-language product (`20621483`) are both outside the searchable set, and the funnel counts are written to `reports/data_funnel.json`.

## 5. Enrichment

### 5.1 Product families

A family is one product sold under several barcodes, typically different pack sizes. Without families, the top five fills with sizes of the same thing.

**Key (exact match):** normalized brand + normalized name + nutrient signature.

- Normalized brand and name: lower-case, strip punctuation, collapse whitespace, remove size tokens ("18 oz", "510 g", "family size").
- Nutrient signature: the ten nutrient values rounded to one decimal place, with missing values encoded as such.

The representative of a family is the member with the most scans, ties broken by completeness. Search results show one member per family and note how many other sizes exist.

Acceptance for T2.5: the two Cheerios records `0016000275263` and `0016000170032` share a family, and a reference product's own family is never returned as a substitute.

Fuzzy matching (edit distance, MinHash over ingredients) would merge more, and would also merge things that are different products. It is out of scope (F-D12).

### 5.2 Comparison category

The comparison category answers "which products are the same kind of thing as the reference". It is the deepest canonical category on the reference product that contains at least `min_category_size` searchable families (default 30), found by walking up the taxonomy from `category_leaf`.

Example: a granola tagged `en:breakfast-cereals` → `en:mueslis` uses `en:mueslis` if that category has 30 or more families, and otherwise backs off to `en:breakfast-cereals`.

A type term in the request overrides this: "a similar cereal" on a granola reference widens the scope to the category whose name matches "cereal". The override logic lives in query formulation ([05](05-query-understanding.md#6-query-formulation)).

### 5.3 Nutrient percentiles

For each nutrient and each category with enough products, store the empirical distribution of per-100 values over searchable products on the same basis. The score term N compares the percentile of the candidate with the percentile of the reference inside the comparison category ([06](06-retrieval-and-ranking.md#62-nutrient-improvement-n)). Percentiles are robust to the outliers that survive the gates and are easy to explain: "from the 80th percentile for sugar among cereals to the 20th".

## 6. Storage layout

```
data/                  (git-ignored)
  raw/                 food.parquet, taxonomies/*.json, REVISION, MANIFEST.json   (never edited)
  interim/             us.parquet                                                 (rebuildable)
  corpus/              products.parquet, families.parquet, evidence.parquet,
                       nutrients.npy, category_postings.npz
  index/               bm25_name/, bm25_categories/, bm25_ingredients/, dense/vectors.f16.npy
  runs/                one folder per system run
eval/                  scenarios/, b3_cache/, pools/, labels/, qrels/                (tracked)
reports/               data_funnel.json, data_audit.md, figures/                     (generated)
```

A rebuilt corpus records the manifest's SHA-256 it came from, so builds from the same snapshot are interchangeable and anything else is visibly different.

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
