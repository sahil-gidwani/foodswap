# The data, the taxonomies and the code so far

A primer for the team. It explains what we downloaded, what the taxonomies are, and what the code does today, using real values from the files.

**State as of Nov 14:**

- The Open Food Facts dump and four taxonomies are downloaded and verified.
- Two small Python modules exist.
- Nothing that searches exists yet.

## 1. What we're building, in one paragraph

FoodSwap takes a product you already buy (say, Cheerios) plus a request like "similar, but less sugar and no peanuts". It finds other products that are:

1. **the same kind of thing;**
2. **free of what you excluded,** as far as the data can show;
3. **better on the nutrients you asked about.**

That needs three ingredients:

- **Product data:** names, ingredients, allergens and nutrition. This is the Open Food Facts dump.
- **Background knowledge about food:** whey is dairy, dairy means milk allergen, "extruded cereals" are breakfast cereals. These are the taxonomies.
- **Code** that turns both into a search engine.

## 2. Setup

```
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m foodswap.data download
```

The last command downloads about 8 GB into `data/` (ignored by git) and checks that the file is complete. It skips anything already downloaded, so it is safe to re-run. Only one person needs the full download; the built corpus will be shared later.

## 3. The data: Open Food Facts

### 3.1 What it is

[Open Food Facts](https://world.openfoodfacts.org) is like Wikipedia for food packaging. Volunteers photograph products and type in what is on the label. Anyone can use the data under the Open Database License, as long as we credit them. That is why every page we make carries "Contains data from Open Food Facts".

The upside is scale and openness. The downside is that it is crowd-sourced: records can be incomplete, wrong or vandalized. Much of our design exists to cope with that.

### 3.2 The file: `data/raw/food.parquet` (8.05 GB)

Open Food Facts publishes a nightly export of every product on [Hugging Face](https://huggingface.co/datasets/openfoodfacts/product-database).

It is in **Parquet** format: a compressed table stored column by column. That layout matters. To count US products, the computer reads only the `countries_tags` column, not all 111. **DuckDB** runs SQL directly on the file, so counting 4.9 million rows takes seconds and never loads 8 GB into memory.

| | |
|---|---|
| Products worldwide | 4,912,822 |
| Products sold in the US | 1,002,000 |
| Columns | 111 |

### 3.3 One real record: Cheerios 18 oz, barcode `0016000170032`

| Field | Value | What it means |
|---|---|---|
| `code` | `0016000170032` | The barcode: the product's permanent ID |
| `product_name` | `[{main: "Cheerios"}, {en: "Cheerios"}, {ro: "Cereal: Cheerios"}]` | Names in several languages; we keep the `en` one |
| `brands` | `General Mills` | |
| `categories_tags` | `en:plant-based-foods-and-beverages, …, en:breakfast-cereals, en:extruded-cereals` | What kind of product it is, general to specific. These IDs come from the category taxonomy (section 4). |
| `ingredients_text` (en) | "Whole Grain Oats, Corn Starch, Sugar, Salt, …" | The ingredient list as printed on the box |
| `ingredients_tags` | `en:oat, en:cereal, en:corn-starch, en:starch, en:sugar, en:disaccharide, en:added-sugar, en:salt, …` | Open Food Facts' parse of that text into ingredient IDs. Parents are included: oat *and* cereal; sugar *and* disaccharide *and* added sugar. |
| `ingredients_n` / `unknown_ingredients_n` | 29 / 4 | 25 of 29 ingredients recognized (86%). This feeds our "can we trust this record?" rule. |
| `allergens_tags` / `traces_tags` | `[]` / `[]` | Declared allergens and "may contain" items. Empty here, but **empty does not mean allergen-free**; it can mean nobody entered them. |
| `labels_tags` | `en:no-gluten, en:kosher, en:no-artificial-flavors, …` | Claims printed on the package |
| `nutriments` | sugars 5.13 g, protein 12.8 g, fat 6.41 g, fiber 10.3 g, sodium 0.487 g, 359 kcal per 100 g | Nutrition, normalized to per 100 g. The box says 2 g sugar per 39 g serving, and 2 ÷ 39 × 100 = 5.13, hence the odd decimals. Sodium is stored in grams (0.487 g = 487 mg). |
| `nutriscore_grade`, `nova_group` | c, 3 | A European nutrition grade (A–E) and a processing level (1–4), both computed by Open Food Facts. Nutri-Score is not used on US packages. |
| `ingredients_analysis_tags` | `palm-oil-free, vegan-status-unknown` | Automatic checks; "unknown" because 4 ingredients were not recognized |
| `unique_scans_n` | 35 | How many people scanned it; a popularity signal |
| `serving_size`, `quantity` | "1.5 cup (39 g)", "18oz (510g)" | Free text, unreliable to compute with. We compare everything per 100 g. |

How to read these fields:

- **`en:` IDs.** Tags like `en:breakfast-cereals` are **canonical IDs** from a taxonomy, not English words a user typed. The `en:` prefix is just the namespace. Entries that are not in the taxonomy (we have seen Italian free text inside a "US" product's categories) get dropped.
- **Nested fields.** Names and ingredient text are lists of `{lang, text}`, and `nutriments` is a list of `{name, 100g, serving, unit, …}`. The corpus build will flatten these into plain columns: `name`, `sugars`, `proteins` and so on.
- **Mixed formats.** Records span several Open Food Facts schema versions (999 to 1004), because the format has changed over the years. That is one reason we pin one snapshot.

### 3.4 `REVISION` and `MANIFEST.json`

**`data/raw/REVISION`** (`781426f0…`) is the exact Hugging Face version we downloaded. The dataset updates daily; without this, someone downloading next week would get different data and different results.

**`data/raw/MANIFEST.json`** records that revision, the file's SHA-256 fingerprint, the row counts and the date. It has two jobs:

1. **Proof two laptops have identical data.** Same fingerprint means a byte-identical file.
2. **A guard against broken downloads.** Open Food Facts has published truncated exports before (about 0.7M products instead of 4M), so the script refuses anything under 4.8M rows or 0.95M US rows.

### 3.5 Data problems we design around

All of these were seen in real records:

| Problem | Example | Our response |
|---|---|---|
| Allergen tags miss things | Nutella's tags list only nuts. Milk and soy are real ingredients but appear only under "may contain". | Also infer allergens from ingredients (section 4.2) |
| Allergen tags over-report | Some cereals list "may contain" items as allergens | Accept it: excluding too much is safe |
| Wrong language under the US filter | The most-scanned "US breakfast cereal" is an Italian-language Crownfield product | Require English text |
| Vandalism | One Cheerios record is named "My Bff", with language set to Latin | Quality checks; flagged records are excluded, never "repaired" |
| Duplicates | Cheerios 8.9 oz and 18 oz: two barcodes, identical nutrition | Group them into one "family" |
| Implausible values | A cereal reporting exactly 0 g sugar | Sanity checks on nutrients |
| Per 100 g or per 100 ml? | The data doesn't reliably say | Drinks are assumed per 100 ml |

## 4. Taxonomies

### 4.1 What a taxonomy is

A taxonomy is a dictionary of canonical concepts arranged in a hierarchy. Each entry, called a **node**, has:

- an **ID**, like `en:breakfast-cereals`;
- **names in many languages** ("Breakfast cereals", "Céréales pour petit-déjeuner", …);
- **parents and children**: "is a kind of" links;
- **properties**, such as "this ingredient carries the milk allergen".

It is not a strict tree: a node can have several parents. Breakfast cereals is a kind of "breakfasts" *and* a kind of "cereals and their products", so the code must follow every path upward, not just one.

Open Food Facts uses taxonomies so that "lait", "Milch" and "milk" all become `en:milk`, whatever language the volunteer typed in. That is what makes tags comparable across millions of records.

### 4.2 The four we downloaded (`data/raw/taxonomies/`)

**Categories** (14,946 nodes, 4.9 MB). The product-type hierarchy:

```
en:extruded-cereals → en:breakfast-cereals → en:breakfasts
                                           → en:cereals-and-their-products → …
```

Breakfast cereals alone has 18 child categories (cereal flakes, cereals with caramel, …).

We use this to define **"the same kind of product"**. Start from the reference product's most specific category (Cheerios → extruded cereals). If too few products are in it, step up to the parent (breakfast cereals). That keeps the system from suggesting cookies as a cereal substitute.

**Ingredients** (6,846 nodes, 3.8 MB). Ingredients carry properties such as `vegan`, `vegetarian` and `allergens`.

The key fact: **only 76 nodes carry an allergen property directly. Everything else inherits it from a parent.** Real chains from the file:

```
en:whey                → en:dairy (allergen: en:milk)
en:skimmed-milk-powder → en:milk-powder → en:dairy (allergen: en:milk)
en:oat                 → en:cereal                  (no gluten property)
```

If we checked only an ingredient's own entry, whey and skimmed milk powder would look milk-free. So the allergen check **walks up every parent chain** and collects any allergen it finds. This is how Nutella gets caught for milk even though its allergen tags omit it.

Other things this file tells us:

- **Oats** carry no gluten property, which matches US labelling practice.
- **Coconut** is filed under fruit, not nuts.
- **Soya oil** carries the soy allergen. US law does not count highly refined oils as allergens, so this is stricter than the law, which is acceptable for a conservative tool.

**Allergens** (27 nodes, 10 KB). The canonical allergen IDs: `en:milk`, `en:peanuts`, `en:nuts`, `en:gluten`, `en:sesame-seeds`, `en:soybeans` and others.

They do **not** line up one-to-one with the US list of nine major allergens:

| US list | In the allergen taxonomy |
|---|---|
| wheat | no wheat node; only `en:gluten` (wheat, barley, rye) |
| tree nuts | `en:nuts` (peanuts are separate: `en:peanuts`) |
| sesame | `en:sesame-seeds` |
| (not regulated in the US) | European extras: celery, mustard, lupin, sulphites, … |

Our allergen vocabulary maps what users type ("dairy", "nut-free", "shellfish") onto these IDs.

**Labels** (3,083 nodes, 1.2 MB). Package claims, also in a hierarchy: `en:no-gluten` has children such as `en:certified-gluten-free` and `en:gfco-gluten-free`.

We treat "free-from" labels as **supporting evidence only**. A gluten-free label never overrides an ingredient that contains gluten, and never counts on its own when the ingredient list is missing.

### 4.3 How the taxonomies plug in

| Taxonomy | Used for |
|---|---|
| Categories | Which products count as "the same kind" as the reference; matching words like "cereal" in a request |
| Ingredients | Inferring allergens the tags miss; excluding specific ingredients ("no gelatin") |
| Allergens | The canonical IDs that user words map onto |
| Labels | Supporting evidence for free-from claims |

## 5. The code so far

```
requirements.txt     7 pinned packages
foodswap/
  data.py            download the dump and taxonomies, check the dump is complete
  schema.py          the types shared by the parser, the constraint checks and the ranker
```

### 5.1 `requirements.txt`

| Package | Why |
|---|---|
| `duckdb` | SQL over the 8 GB Parquet file without loading it into memory |
| `huggingface_hub` | Downloads the dump at a pinned revision |
| `numpy` | Arrays: vector search, score math |
| `bm25s`, `PyStemmer` | Keyword search (BM25); the stemmer makes "cereals" match "cereal" |
| `sentence-transformers` | Turns product text into vectors, for search by meaning |
| `streamlit` | The web app |

Versions are pinned exactly (`==`) so all four laptops behave identically. Only the first two are used so far; the rest are the agreed stack, ready for search and UI work.

### 5.2 `foodswap/data.py`

Run as `python -m foodswap.data download`. In order:

1. **Constants:** where data lives (`data/raw/`), which dataset to fetch, the four taxonomy names, and the minimum row counts for a complete dump.
2. **`download()`**
   1. Skips the 8 GB file if it already exists. Otherwise it asks Hugging Face for the current revision, downloads that exact version and saves the revision to `REVISION`.
   2. Fetches each missing taxonomy file from Open Food Facts, identifying itself with a `User-Agent` as their guidelines ask.
3. **`write_manifest()`**
   1. Counts all rows, and the rows tagged `en:united-states`, with DuckDB.
   2. Fingerprints the file with SHA-256, then writes and prints `MANIFEST.json`.
   3. If the counts are too low, it stops with an error, so nobody builds on a broken dump.
4. **`sha256()`:** hashes the file in 16 MB chunks, so the 8 GB file never has to fit in memory.
5. **The `__main__` block:** anything other than `download` prints the usage text.

### 5.3 `foodswap/schema.py`

The types that let the parser author and the ranker author work in parallel: they agree on what passes between them.

**`Verdict`** is the outcome of checking one product against one constraint:

| Verdict | Meaning | Effect |
|---|---|---|
| `FAIL` (0) | The record shows the excluded thing | Excluded, with the evidence shown |
| `PASS` (1) | The record has a usable ingredient list and shows nothing excluded | Eligible. It means "not declared in this record", never "safe". |
| `UNKNOWN` (2) | Not enough information to decide | **Excluded too**, because "we couldn't check" must never look like "safe" |

The numbers 0, 1 and 2 let us store verdicts as one byte per product per allergen.

**`Constraint`** is a hard rule. It has:

- a `kind`: "allergen", "ingredient", "max" or "min";
- a `target`: "peanuts", "en:gelatin", "sugars";
- an optional `value`, in grams per 100 g.

**`NutrientGoal`** is a soft preference: a nutrient and a direction (−1 less, +1 more).

**`ParsedRequest`** is what the parser will produce. For the headline request:

```python
ParsedRequest(
    raw="a similar cereal with less sugar, more protein, and no peanuts",
    type_terms=("cereal",),
    type_category="en:breakfast-cereals",
    hard=(Constraint("allergen", "peanuts"),),
    goals=(NutrientGoal("sugars", -1), NutrientGoal("proteins", +1)),
    negated_terms=("peanuts",),   # never sent to the search engine
)
```

Why `negated_terms` exists: keyword and neural search engines treat "no peanuts" as a request *for* peanuts. The parser pulls those words out, so they are enforced as a filter instead of searched for. The one place we put them back on purpose is the experiment that measures how much harm that does.

## 6. Explore it yourself

Run these from the repository root with the virtual environment active.

**The five most-scanned US breakfast cereals and their sugar per 100 g:**

```python
import duckdb

print(duckdb.sql("""
    SELECT code,
           list_filter(product_name, lambda x: x.lang = 'en')[1]."text" AS name,
           brands,
           list_filter(nutriments, lambda x: x."name" = 'sugars')[1]."100g" AS sugars_100g
    FROM 'data/raw/food.parquet'
    WHERE list_contains(countries_tags, 'en:united-states')
      AND list_contains(categories_tags, 'en:breakfast-cereals')
    ORDER BY unique_scans_n DESC NULLS LAST
    LIMIT 5
"""))
```

On the 2026-11-14 snapshot, the top result is the Italian-language Crownfield product and the third reports 0 g sugar: two of the problems from section 3.5.

Two syntax notes for DuckDB 2.0:

- It needs `lambda x: …`; the older `x -> …` form is rejected.
- `"name"` and `"text"` are reserved words, so they need double quotes.

**Which allergens an ingredient carries, walking up the ingredient taxonomy:**

```python
import json

ingredients = json.load(open("data/raw/taxonomies/ingredients.json"))

def allergens_of(ingredient_id):
    found, stack, seen = set(), [ingredient_id], set()
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        node = ingredients.get(node_id, {})
        if "allergens" in node:
            found.add(node["allergens"]["en"])
        stack.extend(node.get("parents", []))
    return found

for i in ["en:whey", "en:skimmed-milk-powder", "en:soya-lecithin", "en:oat", "en:almond", "en:peanut"]:
    print(i, allergens_of(i))
```

Output:

```
en:whey {'en:milk'}
en:skimmed-milk-powder {'en:milk'}
en:soya-lecithin {'en:soybeans'}
en:oat set()
en:almond {'en:nuts'}
en:peanut {'en:peanuts'}
```

## 7. What comes next

```
food.parquet + taxonomies
  └─ build (done Nov 14: 349,308 products, 54 nutrients): one clean row per US product, broken records dropped,
                   duplicate sizes grouped, each product's comparison category decided
       ├─ evidence: PASS / FAIL / UNKNOWN for every product × allergen
       ├─ keyword index (BM25) and meaning index (embeddings)
       └─ request parser → ParsedRequest
            └─ search: filter on evidence, rank on relevance + similarity + nutrient improvement
                 └─ app, evaluation, report
```

For the full design, see [the docs index](../README.md). The most relevant pages are:

- [data pipeline](../03-data-pipeline.md);
- [constraints and safety](../07-constraints-and-safety.md);
- [plan and tasks](../10-plan.md).
