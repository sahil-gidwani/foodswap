# 02 · Data sources

**Use:** reference (stable; consult when acquiring data or writing the report's data section).
**Read by:** DATA role first; everyone for section 7 (licensing).
**Checked:** 2026-11-09. Every fact was read on the linked page that day unless it is marked *(unverified)*, which means it came from a secondary source or a search snippet. "Probe" means a request we ran ourselves on 2026-11-09.

## 1. Summary

| Source | What it is | Size | Licence | Role in FoodSwap | Tier |
|---|---|---|---|---|---|
| Open Food Facts (OFF) Parquet dump | Crowd-sourced packaged-food database | 8.0 GB, 4.9M products (~1.0M US) | ODbL | The corpus | Core |
| OFF taxonomies | Category, ingredient, allergen and label hierarchies | A few MB each | ODbL | Category compatibility, ingredient → allergen inference | Core |
| OFF search service (Search-a-licious) | Elasticsearch-based live search | Live | ODbL | Baseline B3, fetched once and cached | Core |
| OFF product API | Product by barcode | Live, 15 requests/min | ODbL | Links from results; records for B3 items outside our corpus | Core |
| USDA FoodData Central, Branded Foods | Manufacturer-submitted US label data | ~450K products, 432 MB zip | CC0 | Cross-check and gap-filling by barcode | Later |
| GroceryDB | 50K products from three US retailers with price | — | MIT | Price-aware swaps | Later |
| Amazon ESCI | Product-search relevance labels | 130K queries | Apache-2.0 | Model for our grading rubric only | Reference |

## 2. Open Food Facts

OFF is a crowd-sourced database of packaged foods: contributors photograph a package and enter or correct its fields. That gives it breadth and openness, and it also gives it the quality problems described in section 2.8.

### 2.1 Bulk exports

All exports are regenerated nightly ([data page](https://world.openfoodfacts.org/data)).

| Export | Location | Size | Notes |
|---|---|---|---|
| **Parquet** | [huggingface.co/datasets/openfoodfacts/product-database](https://huggingface.co/datasets/openfoodfacts/product-database), file `food.parquet` | 8,035,571,362 bytes; 4,899,413 rows; 111 columns | **What we use.** A "simplified" export built from the JSONL. Refreshed about daily. |
| JSONL | `https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz` | Not stated; roughly 10 GB compressed *(unverified)* | The complete record. Use only if a needed field is missing from Parquet. |
| CSV | `https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz` | ~0.9 GB compressed, ~9 GB raw | Tab-separated. Flattened, fewer fields. |
| Daily deltas | `https://static.openfoodfacts.org/data/delta/index.txt` | 14 days | Cannot signal deletions. Not needed: we pin one snapshot. |
| MongoDB dump | `https://static.openfoodfacts.org/data/openfoodfacts-mongodbdump.gz` | Not stated | Same data as JSONL. |

Two cautions:

- **Check the row count of whatever you download.** Earlier in 2026 an export shrank from about 4M to about 0.7M products before being fixed ([forum thread](https://forum.openfoodfacts.org/t/jsonl-file-massive-file-size-reduction/2071)). Our manifest check requires at least 4.8M rows overall and at least 0.95M for the US.
- **Pin the snapshot.** Record the Hugging Face revision hash, the file checksum and the download date in `data/raw/MANIFEST.json`. Every reported number must trace to that manifest.

### 2.2 The Parquet schema

The Parquet file is not a flat table. Read these notes before writing the extractor.

| Aspect | What the file contains |
|---|---|
| Multilingual text | `product_name`, `generic_name`, `ingredients_text` and `packaging_text` are lists of `{lang, text}` structs. Pick the entry with `lang = 'en'`. |
| Nutrition | `nutriments` is a list of structs `{name, value, 100g, serving, unit, prepared_value, prepared_100g, prepared_serving, prepared_unit}`. One struct per nutrient. |
| Parsed ingredients | `ingredients` is a string holding serialized JSON *(exact content unverified)*. `ingredients_tags` is the usable list of canonical ingredient ids. |
| Images | `images` is a list of structs; URLs must be constructed (pattern in section 2.7). |
| Quantities | `serving_quantity` and `product_quantity` are strings. |

Columns we rely on, all present: `code`, `brands`, `categories_tags`, `food_groups_tags`, `labels_tags`, `allergens_tags`, `traces_tags`, `ingredients_tags`, `ingredients_analysis_tags`, `additives_tags`, `ingredients_n`, `unknown_ingredients_n`, `countries_tags`, `lang`, `nutriscore_grade`, `nutriscore_score`, `nova_group`, `unique_scans_n`, `popularity_key`, `completeness`, `states_tags`, `data_quality_errors_tags`, `data_quality_warnings_tags`, `data_sources_tags`, `obsolete`, `created_t`, `last_modified_t`.

Columns that exist in the API but are **absent from Parquet**: every `*_hierarchy` field, the raw `allergens` and `traces` text, `allergens_from_ingredients`, `main_category`, `nutriscore_version`, `pnns_groups_*`, `nutrition_data_prepared_per`, and the `image_*_url` fields. None of these blocks Core work: we infer allergens from ingredients ourselves through the taxonomy ([07](07-constraints-and-safety.md)).

### 2.3 Size of the US slice

| Scope | Products | Source |
|---|---|---|
| World | 4,904,882 | OFF homepage |
| United States | 1,000,124 | `us.openfoodfacts.org`, API count (probe) |
| US beverages | 51,525 | probe |
| US sauces | 27,076 | probe |
| US cheeses | 13,833 | probe |
| US breads | 10,661 | probe |
| US yogurts | 6,384 | probe |
| US chips and fries | 4,608 | probe |
| US breakfast cereals | 3,836 | probe |
| US breakfast cereals with nutrition and ingredients marked complete | 2,704 | probe |
| US milk substitutes | 3,018 | probe |
| US products tagged vegan by ingredient analysis | 81,333 | probe |

The proposal's four categories are well populated: even the strictest cereal count is 27 times the 100 products the proposal planned. The category counts come from the live API, where heavier queries (snacks, sodas, candies, and the combined completeness filter) returned HTTP 503, so the full funnel must be computed from the dump (task T2.6).

### 2.4 API

Documentation: [openfoodfacts.github.io/openfoodfacts-server/api](https://openfoodfacts.github.io/openfoodfacts-server/api/).

| Topic | Fact |
|---|---|
| Versions | v3 is current (latest 3.6) and recommended for new integrations. v2 is deprecated but still supported. |
| Product read | `GET https://world.openfoodfacts.org/api/v2/product/{barcode}?fields=...` |
| Search | `/api/v2/search` filters on structured fields only. Full-text search exists only in the legacy `/cgi/search.pl`. v3 has no search. |
| Rate limits | 15 requests/min per IP for product reads; 10 requests/min per IP for search. Exceeding global limits returns HTTP 503. Abuse can get an IP banned. |
| Identification | Send a custom `User-Agent` in the form `AppName/Version (ContactEmail)`. |
| Bulk use | "If you need to fetch more than a few hundred products, we ask you to download the data." |
| Staging | `https://world.openfoodfacts.net`, HTTP basic auth `off` / `off`. |

**Probe result.** We sent 32 search requests at 8 per minute, under the documented limit. Eighteen returned HTTP 503 with a "Page temporarily unavailable" page; a repeat of six of them failed three more times, and one returned a null count. The failures clustered on queries with large result sets. The conclusion for the project: nothing in the build or the demo may depend on this endpoint.

### 2.5 The newer search service (used for baseline B3)

OFF runs an Elasticsearch-based service, [Search-a-licious](https://github.com/openfoodfacts/search-a-licious), at `https://search.openfoodfacts.org`. It answered every probe in well under a second.

- Query language ([docs](https://openfoodfacts.github.io/search-a-licious/users/explain-query-language/)): Lucene-like. `field:value`, phrases, `AND` / `OR` / `NOT`, numeric ranges such as `nutriments.sugars_100g:[* TO 20]`, existence checks such as `nutriscore:*`.
- **Tag values that contain a colon must be quoted.** `allergens_tags:"en:peanuts"` works; without the quotes the count is zero.
- Full-text search covers the English name, generic name, category and label fields plus brands.
- Reported counts are capped at 10,000 and flagged as inexact, so it cannot be used for sizing.
- Example that worked in a probe: `q=cereal AND allergens_tags:"en:peanuts"&page_size=2&fields=code,product_name`.

For B3 we translate each scenario into the nearest query this service supports, fetch once, and store the raw response. Operations it cannot express (for example "less sugar than this product" or "unknown evidence is rejected") are tabulated in the report as the baseline's limits. See [09](09-evaluation.md#3-systems).

### 2.6 Taxonomies

OFF publishes its controlled vocabularies as JSON at `https://static.openfoodfacts.org/data/taxonomies/{name}.json`, for `categories`, `ingredients`, `allergens`, `labels`, `additives`, `nutrients` and others. Source text files live in the [server repository](https://github.com/openfoodfacts/openfoodfacts-server/tree/main/taxonomies).

Each node is keyed by its id (for example `en:breakfast-cereals`) and has `name` by language, `parents`, `children`, and properties.

| Taxonomy | Size | Properties we use |
|---|---|---|
| Categories | `categories.json` is about 4.6M characters; roughly ten thousand nodes *(node count unverified)* | `parents` / `children` for the comparison category; `food_groups`; `gpc_category_code`; `expected_ingredients` |
| Ingredients | `ingredients.json` is about 3.5M characters | `allergens` (for example `en:milk`), `vegan`, `vegetarian`, `from_palm_oil` |
| Allergens | 27 top-level nodes | See the mapping note below |
| Labels | — | `en:no-gluten`, `en:vegan`, `en:organic` and similar, as supporting evidence |

**The OFF allergen list is not the US list.** It has `en:gluten` but no wheat node; `en:nuts` means tree nuts; sesame is `en:sesame-seeds`; and it includes items that are not US major allergens (molluscs, celery, mustard, lupin, sulphites, and several region-specific ones such as kiwi and peach). The mapping from the nine US major allergens is specified in [07](07-constraints-and-safety.md#2-vocabulary).

Property inheritance runs through parents, and OFF's own documentation warns that it may not behave as expected on a graph with multiple parents. We compute our own ancestor closure.

### 2.7 Python SDK and adjacent services

- **`openfoodfacts` SDK** ([PyPI](https://pypi.org/project/openfoodfacts/), version 5.4.1 of 2026-10-20, still labelled beta). Useful parts: `get_taxonomy("category")`, node methods `is_child_of`, `get_parents_hierarchy`, `get_localized_name`; barcode helpers `normalize_barcode` and `has_valid_check_digit`; an API client that sets the user agent. It has **no Parquet support** (its dataset helper downloads JSONL or CSV), so the dump is fetched with `huggingface_hub`.
- **Image URLs** follow `https://images.openfoodfacts.org/images/products/{barcode split 3/3/3/rest}/{key}.{rev}.{size}.jpg`, for example `.../001/600/027/5287/front_en.8.400.jpg`. Images are CC BY-SA and need the network, so the demo caches thumbnails for scripted scenarios (S4).
- **Preference matching.** OFF's own "personal search" assigns each product a status against the user's preferences, including `unknown_match` when a mandatory attribute is unknown, `may_not_match` for possible traces and `does_not_match` when an allergen is present ([docs](https://openfoodfacts.github.io/openfoodfacts-server/dev/explain-personal-search)). This is a direct precedent for our unknown-means-ineligible policy and is cited in the report.
- **Robotoff** ([docs](https://openfoodfacts.github.io/robotoff/)) serves machine-learning predictions per product, including a neural category predictor. A probe returned `en:breakfast-cereals` at confidence 0.9999 for a Cheerios barcode. It is the obvious tool for category imputation (F-D14, Later).
- **Open Prices** ([stats](https://prices.openfoodfacts.org/api/v1/stats)) holds 342,750 prices across 128 countries. US coverage is small and could not be isolated, so price-aware swaps are not feasible from it.

### 2.8 Data quality, observed first hand

These are real records seen in probes on 2026-11-09. They are cited by product code so they can become golden tests. Records change over time; the tests run against our pinned snapshot.

| Code | Product | What is wrong | Consequence for the design |
|---|---|---|---|
| `20621483` | Crownfield Special Flakes Bran Flakes | Returned under the US filter, but its language is Italian and its ingredient text is Italian. Its category and label lists contain free-text Italian entries. | The corpus needs an English-text gate, not only a country filter. Only canonical `en:` tags known to the taxonomy are kept. |
| `20621483` | same | The label says "may contain traces of ... nuts, peanuts and milk", yet milk and peanuts appear in `allergens_tags`. | Allergen tags **over-report**. Safe, but it lowers coverage. |
| `0058449770565` | Nature's Path Pumpkin Seed + Flax Granola | Nuts and peanuts are in `allergens_tags` although the ingredient list has neither (a facility statement was parsed as an allergen). | Same. |
| `3017624010701` | Nutella | `allergens_tags` lists only `en:nuts`. Milk and soy, which are ingredients (skimmed milk powder, soy lecithin), appear only in `traces_tags`. | Allergen tags **under-report**. A system that trusted that one field would pass Nutella for a milk exclusion. No single field is trusted. |
| `0016000275263`, `0016000170032` | Cheerios, 8.9 oz and 18 oz | Two barcodes, identical nutrition. | Product families are needed, or the top five fills with sizes of one product. |
| both | same | `ingredients_analysis_tags` says `vegan-status-unknown` (an ingredient is unrecognized). | "Unknown" is common even for famous products. The coverage cost of rejecting unknowns must be measured and reported. |
| `0016000275287` | Cheerios | Vandalized: `lang` is `la`, the English name is "My Bff", and `allergens_tags` contains the non-canonical `en:Corn`. Quality warnings include `en:ingredients-90-percent-unknown`. | Quality gates use `data_quality_*_tags` and sanity checks. Flag and exclude; never repair. |
| several | — | `serving_size` and `quantity` are free text: "1 ½ cup (39 g)", "0.75 cup cereal (55 g)", "20.5 OZ (1 LB 4.5 OZ) 581 g". | Comparisons are per 100 g or 100 ml. Per-serving limits are out of Core. |
| several | — | Per-100 g values are derived from per-serving label values, for example `358.974358974359` kcal. | Round for display; never show false precision. |

Published evidence points the same way. An independent audit of the August 2026 CSV found that 5.5% of 857,655 complete French labels have an energy value inconsistent with their macronutrients ([write-up](https://dev.to/leanapp/auditing-857655-open-food-facts-labels-with-pandas-how-many-nutrition-facts-contradict-themselves-4cen), secondary source). We found **no peer-reviewed audit of OFF allergen fields**, which is why the hand audit (S2) is worth doing.

Useful things that are populated for US products in the sample: `added-sugars` (it is on US labels), Nutri-Score and NOVA group as computed by OFF, and labels such as `en:no-gluten`, `en:vegan`, `en:kosher`, `en:usda-organic`.

### 2.9 Schema drift

OFF's schema is changing ([change log](https://openfoodfacts.github.io/openfoodfacts-server/api/ref-api-and-product-schema-change-log)):

| Schema | Date | Change |
|---|---|---|
| v1000 | 2024-12-12 | Eco-Score renamed "environmental score" (`environmental_score_*`) |
| v1001 | 2025-03-12 | Brands became a taxonomy |
| v1002 | 2025-06-11 | New `images` structure |
| v1003 | 2025 | New nested nutrition structure, "still under active development" |
| v1004 | 2026-05-27 | `tags_sources` added; `*_hierarchy` fields removed |

The Parquet export, the JSONL dump, API v2 and API v3 can each present a different shape of the same product. We read one source (Parquet), pin one snapshot, and record its `schema_version`.

## 3. USDA FoodData Central, Branded Foods (Later)

| Topic | Fact |
|---|---|
| Download | [fdc.nal.usda.gov/download-datasets](https://fdc.nal.usda.gov/download-datasets/). Branded release 2026-10-29: CSV zip 432 MB (3 GB unpacked), JSON zip 187 MB. |
| Size | About 450,000 products in 238 categories. |
| Provenance | Manufacturers submit label data through GS1's data network. Countries: US, Canada, New Zealand. |
| Licence | Public domain, published under CC0 1.0 ([API guide](https://fdc.nal.usda.gov/api-guide/)); USDA asks for credit. |
| API | Needs a free api.data.gov key; 1,000 requests/hour. |
| Allergens | No allergen field. Ingredient text only *(unverified in the data dictionary)*. |
| Pitfalls | Duplicate barcodes are versions (keep the latest publication date). Blank nutrient values are not zeros. Values are reconstructed from per-serving label values. Some records are years stale. |

Why it is Later: the join needs GTIN normalization (UPC-A, EAN-13 and GTIN-14 with leading zeros), version handling and a conflict policy, and much of OFF's US data may already derive from USDA imports *(unverified; one OFF facet lists about 170K products sourced from USDA)*. The licence is compatible: CC0 data can be merged into an ODbL database.

## 4. Regulatory reference data

These numbers are used in [07](07-constraints-and-safety.md) to define vocabulary and to word clarifications. They are not applied automatically as hard constraints in Core.

### 4.1 Allergen lists

| List | Members | Source |
|---|---|---|
| US major food allergens (nine) | milk, eggs, fish, crustacean shellfish, tree nuts, peanuts, wheat, soybeans, sesame | [FDA](https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies). Sesame was added by the FASTER Act, effective 2023-01-01. |
| EU allergens (fourteen) | cereals containing gluten, crustaceans, eggs, fish, peanuts, soybeans, milk, tree nuts, celery, mustard, sesame, sulphites above 10 mg/kg, lupin, molluscs | Regulation (EU) 1169/2011, Annex II |

In the US, "may contain" statements are voluntary. Their absence is not evidence that a product is free of an allergen.

### 4.2 Nutrient claim thresholds

**US (21 CFR 101.54–101.62).** Defined per reference amount customarily consumed (RACC), not per 100 g, with an extra per-50 g test for foods with small servings.

| Claim | Threshold per RACC |
|---|---|
| Sugar free | < 0.5 g sugars |
| Reduced sugar | at least 25% less than the reference food |
| Low sodium / very low / sodium free | ≤ 140 mg / ≤ 35 mg / < 5 mg |
| Low fat / fat free | ≤ 3 g / < 0.5 g |
| Low saturated fat | ≤ 1 g and ≤ 15% of calories |
| Low calorie | ≤ 40 kcal |
| High / good source | ≥ 20% / 10–19% of the Daily Value |

**FDA defines no "low sugar" claim.** Daily Values relevant to "high in": protein 50 g, fiber 28 g, sodium 2,300 mg, added sugars 50 g, saturated fat 20 g.

**EU (Regulation (EC) 1924/2006, Annex).** Defined per 100 g or 100 ml, which matches how OFF stores nutrition.

| Claim | Solids, per 100 g | Liquids, per 100 ml |
|---|---|---|
| Low sugars | ≤ 5 g | ≤ 2.5 g |
| Sugars-free | ≤ 0.5 g | ≤ 0.5 g |
| Low fat | ≤ 3 g | ≤ 1.5 g |
| Low saturated fat | ≤ 1.5 g | ≤ 0.75 g |
| Low sodium | ≤ 0.12 g sodium | same |
| Source of / high fibre | ≥ 3 g / ≥ 6 g | — |
| Source of / high protein | ≥ 12% / ≥ 20% of energy from protein | same |

**UK front-of-pack traffic lights, per 100 g of food** ([guidance](https://assets.publishing.service.gov.uk/media/5a80cd03ed915d74e33fc7c5/FoP_Nutrition_labelling_UK_guidance.pdf)): sugars green ≤ 5.0, red > 22.5; fat green ≤ 3.0, red > 17.5; saturates green ≤ 1.5, red > 5.0; salt green ≤ 0.3, red > 1.5. Salt is sodium × 2.5.

Units trap: OFF stores sodium and cholesterol in **grams**; US rules are written in milligrams.

## 5. Other datasets and APIs considered

| Source | What it offers | Verdict |
|---|---|---|
| [Amazon ESCI](https://github.com/amazon-science/esci-data) (Apache-2.0) | 130K shopping queries with Exact / Substitute / Complement / Irrelevant labels | Used only as the model for our rubric. No grocery category column, no nutrition. |
| [GroceryDB](https://github.com/Barabasi-Lab/GroceryDB) (MIT) | 50K products from Walmart, Target and Whole Foods with ingredients, nutrition, a processing score and price | The best route to price-aware swaps. Later. |
| Instacart 2017 basket data | Orders, aisles, departments | No nutrition. Co-purchase priors only. Licence is competition terms *(unverified)*. Not used. |
| Amazon Reviews 2023, Grocery | 603K items with titles and descriptions | No barcodes, so no join. Not used. |
| Recipe1MSubs (GISMo) | ~70K ingredient substitution pairs from recipes | Recipe ingredients, not packaged products. Cited as related work. |
| FoodOn, FoodKG | Food ontologies and knowledge graphs | OFF taxonomies already cover our needs. Cited only. |
| Commercial product APIs (Spoonacular, Nutritionix, Edamam, UPCitemdb, Kroger and others) | Product and nutrition lookups | **Not used.** Their terms forbid redistribution or bulk caching, so their data cannot enter an ODbL database. |

## 6. Acquisition plan

| Step | Action | Cost on a laptop |
|---|---|---|
| 1 | Download `food.parquet` once with `huggingface_hub`, pinning the revision. Write `MANIFEST.json`. | 8.0 GB; 10–30 minutes on a good connection |
| 2 | Download the four taxonomies (categories, ingredients, allergens, labels) as JSON. | A few MB each |
| 3 | DuckDB pass 1: keep rows sold in the US and not obsolete. | Streams; fits in 16 GB RAM; minutes *(estimate)* |
| 4 | DuckDB pass 2: project to the canonical schema ([03](03-data-pipeline.md)). | Minutes *(estimate)* |
| 5 | Fetch and cache B3 responses for the 32 scenarios, and product records for B3 items outside our corpus. | Under 100 requests, rate-limited |

Only one machine downloads and builds. Teammates fetch the built corpus and indexes by manifest hash (see [04](04-architecture.md#6-artifacts-and-reproducibility)).

## 7. Licensing and attribution

OFF's [terms of use](https://world.openfoodfacts.org/terms-of-use): the database is under the Open Database License (ODbL), individual contents under the Database Contents License, and images under CC BY-SA.

| Situation | What we must do |
|---|---|
| Any use | Attribute OFF with a link. Suggested wording: "Contains data from Open Food Facts, available under the Open Database License." |
| The demo app | Show the attribution and link in the UI. Credit CC BY-SA images. Show the snapshot date. |
| A data subset committed to the repo (fixtures, the released test collection) | Publish it under ODbL with a `DATA_LICENSE` notice. The code keeps its own licence (GPL-3.0). |
| Embeddings or indexes | Kept private: no obligation. Published: treat as derived data under ODbL. |
| Combining with other data | Public-domain or CC0 data (USDA) can be merged. Proprietary API data must never enter a published OFF-derived database. |

This is our reading, not legal advice. OFF's contact for reuse questions is `reuse@openfoodfacts.org`.

API etiquette, which also applies to the handful of live requests we make: identify with a proper user agent, stay under 10 searches and 15 product reads a minute, cache every response, and never loop over the API to collect products.

## 8. To verify on day one

- The exact content of the `ingredients` string column, and whether `nutrition_data_per` is present to tell per-100 g from per-100 ml records.
- The type of `obsolete` (boolean or string) and how many US rows it removes.
- Whether the snapshot's `schema_version` already uses the new nutrition structure alongside `nutriments`.
- The share of US rows with English names, English ingredient text, a canonical category, and the key nutrients. This is the funnel in the audit (T2.6).
