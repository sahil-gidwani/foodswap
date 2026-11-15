# How we clean the data

The second primer for the team. [01](01-data-and-code.md) explained the raw data and the taxonomies. This one explains how the raw dump becomes the clean product table everything else will use: every rule, why it exists, what it removes, and what we changed along the way.

**State as of Nov 14.** One command, about 20 seconds:

```
python -m foodswap.data build
```

| Input | Output |
|---|---|
| `data/raw/food.parquet`: 4.9M products worldwide, messy | `data/corpus/products.parquet`: **349,308** clean US products (60 MB) |
| `data/raw/taxonomies/*.json` | `data/corpus/sample.parquet`: 18,293 of them, for quick development (4 MB) |
| | `data/corpus/build.json`: the counts below, the nutrient list, and the fingerprint of the dump it came from |

## 1. The checks, in order

Each check removes products that fail it. All the counts are recorded, because the report has to show what was lost and why.

| Step | Rule | Products left | Removed |
|---|---|---|---|
| 1. US products | Sold in the US, not marked obsolete | 1,002,000 | |
| 2. English | Main language is English, and there is an English name | 960,992 | 41,008 |
| 3. Has a category | At least one category the taxonomy recognizes | 367,436 | 593,556 |
| 4. No data errors | Open Food Facts flagged no data errors | 349,527 | 17,909 |
| 5. Plausible nutrition | No impossible headline nutrition value | **349,308** | 219 |

### Step 1: US products

We keep products whose country list includes the United States. "Obsolete" means discontinued, but no US product in this snapshot is marked obsolete, so this removes nothing today. It stays for future snapshots.

### Step 2: English

The product's **main language** must be English, and it must have an English name. If there is no separate English entry, the main-language name counts, since the main language is English.

Why English: the request parser reads English, the allergen check reads English ingredient lists, and the people grading results read English. It costs little: 96% of US products pass.

This step also catches bad records:

- The vandalized Cheerios record (`0016000275287`) has its main language set to Latin.
- The Italian bran flakes (`20621483`) that showed up under the US filter have Italian as their main language.

Both are removed here.

### Step 3: Has a category

The product must have at least one category the category taxonomy recognizes. Free-text categories, like Italian phrases typed into the category field, are dropped first, then the check runs.

Why: without a category we cannot decide what "the same kind of product" means, and that is the first thing a substitute must be.

The cost is large. **62% of English-named US products have no usable category.** Many look like bulk imports that never got categorized. This is the biggest limitation of the corpus. Inferring missing categories (Open Food Facts runs a model that predicts them) is possible future work.

### Step 4: No data errors

Open Food Facts runs its own consistency checks and tags records that fail them. The common ones in our data:

- calories that don't match the fat, carbs and protein;
- nutrients adding up to more than 105 g per 100 g;
- energy over 3,800 kJ per 100 g.

We trust these flags and drop the record.

### Step 5: Plausible nutrition

The eight **headline nutrients** are the numbers every label carries: calories, fat, saturated fat, carbohydrates, sugars, fiber, protein and sodium. They must be physically possible:

| Rule | Why it's a physical limit |
|---|---|
| No value below 0 | Food can't contain negative grams of anything |
| No value above **105 g per 100 g** | 100 g of food can't contain more than 100 g of one thing. We allow 105 because labels round: corn syrup can show 103 g of carbohydrate. 105 is also the threshold Open Food Facts uses. |
| At most **900 kcal per 100 g** | Fat is the most energy-dense nutrient at 9 kcal per gram, so nothing can exceed 900 kcal per 100 g |

Real records this removes:

| Product | Recorded value |
|---|---|
| Parmesan | 600 g fat per 100 g |
| Eggs | 7,000 kcal per 100 g |
| Chili seasoning mix | 741 g carbohydrate per 100 g |

These are typos or per-serving numbers in the wrong field.

**Other nutrients are treated more gently.** An impossible value in a minor nutrient, such as water or a vitamin, is erased rather than throwing away the whole product. 184 products had impossible water values; those products stay, with water left blank.

## 2. What gets cleaned inside each product

**Tags are kept only if a taxonomy knows them.** This applies to categories, ingredients, allergens, "may contain" items and labels. A free-text allergen entry like `en:Corn` (capital C, not in the allergen taxonomy) is dropped. The tags that remain are standard IDs the rest of the code can rely on.

**Text fields** (name, generic name, ingredient list) use the English entry, or the main-language entry when there is no separate English one.

**Brand** is the first brand listed, trimmed. 36% of products have no brand.

**Nutrients: all of them, not a hand-picked list.** The dump uses 187 nutrient names. We keep the 54 real nutrients that at least 1% of products report. That covers everything from calories and sugars to cholesterol, trans fat, iron, calcium, vitamins and individual sugars. Three groups are left out:

| Left out | Why |
|---|---|
| Nutri-Score points, NOVA group, fruit and vegetable estimates | Scores and estimates, not nutrients |
| Energy in kJ | The same as calories, in another unit |
| `salt` | Always sodium × 2.5 (below) |
| About 120 names used by under 1% of products | Mostly one-off typos, like `es-l-glutamine` and `en-melatonin` |

The list is discovered from the data on each build and saved in `build.json`, so a new nutrient that becomes common gets picked up automatically.

All values are **per 100 g** (per 100 ml for drinks), and masses are in **grams**. Sodium 0.487 means 487 mg per 100 g.

**Why salt was dropped.** Salt is sodium chloride. By weight, sodium is about 39% of it: sodium's atomic mass of 23 divided by salt's 58.4. So salt ≈ sodium × 2.54, and labelling rules round that to 2.5. Open Food Facts stores both, always in that ratio. In 323,000 products, sodium was never missing when salt was present. US labels use sodium, so we keep only sodium.

**Grams or millilitres.** The data doesn't reliably say whether values are per 100 g or per 100 ml. The rule:

- If the package size says g or ml, use that.
- Otherwise, products in the "beverages" category are per 100 ml.
- Everything else is per 100 g.

Result: 300,815 products per 100 g, 48,493 per 100 ml. Products are only ever compared on the same basis.

**Nutri-Score** keeps only real grades (a to e); anything else becomes blank.

**Missing stays missing.** A blank on a label is not a zero, so we never fill in a value.

## 3. Product families: one product, several pack sizes

The same product often appears under several barcodes, one per pack size. Without grouping, someone searching for a cereal substitute could get five sizes of the same cereal.

**Rule:** two products are one family if they have the same brand, the same name once pack-size words are removed ("18 oz", "family size"), and the same eight headline nutrients. Vitamins are left out of the comparison, because two people entering the same product often record different ones.

**Example:** Cheerios is one family of 7 barcodes, all named "Cheerios" with identical nutrition.

**Unbranded products are never grouped.** The first version of the build grouped 72 different olive oils into one "product": no brand, the same name "Extra Virgin Olive Oil", and identical nutrition, because olive oil is olive oil. Without a brand there is no way to tell same product from same kind of product, so each unbranded product now stands alone.

**Result:** 349,308 products form 337,242 families. 9,867 families have two members. The largest have 10 to 21 barcodes: one brand's seltzer water in many flavors, or Diet Pepsi in many sizes.

## 4. Comparison category: what counts as "the same kind"

Every product gets a **comparison category**: the group its substitutes are drawn from.

The rule: take the product's **most specific category** that holds at least **30 distinct products**. For Cheerios that is "extruded cereals" (286 products), not the broader "breakfast cereals".

"Most specific" means deepest in the category hierarchy. A category can have several parents, so depth is measured along the longest path to the top. If none of a product's categories reaches 30, the one with the most products is used.

**Why 30:** too specific a category leaves too few candidates once the allergen filter removes some, and "lower sugar than most" means nothing in a group of five. Too broad, and cookies get suggested for a cereal. The exact number barely matters in practice:

| Minimum size | Products keeping their most specific category |
|---|---|
| 10 | 98.3% |
| 30 (ours) | 96.3% |
| 100 | 92.1% |

**A limitation:** 30,762 products are tagged only as "snacks", with nothing more specific, so plain "snacks" is their comparison category. A precisely categorized reference product never compares against them, because they are not in its category.

## 5. The sample

`sample.parquet` holds the 5,000 most-scanned products in each of the proposal's four categories:

| Category | Products |
|---|---|
| Breakfast cereals | 3,403 (all of them) |
| Yogurts | 5,000 |
| Snacks | 5,035 |
| Beverages | 5,064 |

That's 18,293 in total, because some products sit in two categories (overlaps are kept once, so the column sums to more than the total).

It's a convenience for development. Building search indexes over 18K products takes seconds instead of a long wait, and the file is small enough to send to a teammate. It keeps the full table's families and comparison categories. **All final results use the full table.**

## 6. The columns

`products.parquet` has 75 columns. The row number is each product's ID in every index we build later.

| Group | Columns |
|---|---|
| Identity | `code` (barcode), `name`, `brand`, `generic_name`, `last_modified_t`, `scans` (popularity) |
| What it is | `category` (most specific), `comparison_category`, `categories` (all of them) |
| Ingredients | `ingredients_text` (as printed; present for 88%), `ingredient_tags`, `ingredients_n`, `unknown_ingredients_n` |
| Allergens and claims | `allergen_tags`, `trace_tags` ("may contain"), `label_tags`, `analysis_tags` (vegan / vegetarian / palm-oil status) |
| Nutrition | 54 nutrient columns, plus `basis` (g or ml) |
| Scores | `nutriscore_grade`, `nova_group` |
| Grouping | `family_id` |

Nutrient coverage:

| Nutrient | Present |
|---|---|
| Calories, protein, fat | 95% |
| Sodium | 93% |
| Sugars | 92% |
| Saturated fat | 87% |
| Fiber | 80% |
| Cholesterol, iron, calcium | 66–68% |
| Trans fat | 64% |
| **Added sugars** | **20%** |

Requests about "added sugar" will often meet "not reported".

## 7. What changed along the way

The build was not right the first time. Each fix came from checking the output against real records:

| # | Problem found | Change |
|---|---|---|
| 1 | DuckDB 2.0 rejected the documented query syntax | Rewrote it in DuckDB 2.0 syntax (`lambda x: …`) |
| 2 | 72 unbranded olive oils merged into one "product" | Unbranded products are never grouped into families |
| 3 | The lines filling sodium from salt (and back) never changed anything | Deleted them, and dropped the redundant salt column |
| 4 | Rounding pushed real products like corn syrup just over 100 g | Limit raised to 105 g, matching Open Food Facts' own threshold |
| 5 | A hand-picked list of 10 nutrients left out common ones like cholesterol, iron and calcium | Keep every real nutrient, discovered from the data: 54 |
| 6 | With all 54 checked, 184 products were dropped for impossible water values | Impossible headline values drop the product; impossible minor values are blanked |

## 8. Try it

```python
import pandas as pd

products = pd.read_parquet("data/corpus/products.parquet")
cheerios = products[products.code == "0016000170032"].iloc[0]

same_kind = products[
    (products.comparison_category == cheerios.comparison_category)
    & (products.family_id != cheerios.family_id)
]
lower_sugar = same_kind[same_kind.sugars < cheerios.sugars]
print(len(same_kind), "extruded cereals;", len(lower_sugar), "have less sugar than Cheerios")
print(lower_sugar.nlargest(5, "scans")[["name", "brand", "sugars", "proteins"]].to_string(index=False))
```

Output:

```
286 extruded cereals; 18 have less sugar than Cheerios
                                      name        brand   sugars  proteins
            Toasted Whole Grain Oat Cereal     Cheerios 2.000000  5.000000
                            Protein Cereal  Magic Spoon 0.000000 34.210526
Crispy Oats Toasted Whole Grain Oat Cereal    Millville 0.000000  5.000000
                             Peanut Butter  Magic Spoon 0.000000 38.888889
                                  Joe's Os Trader Joe's 4.878049 12.195122
```

This is already a crude substitute search, and it shows why the next steps exist:

- **"Peanut Butter" cereal is on the list.** For someone who asked for no peanuts, it must be excluded, with the reason shown. That is the allergen check, the next step.
- **The ranking is just popularity.** It doesn't know whether a product is actually similar to Cheerios, or whether the user also wanted more protein. That is the search and ranking work.
- **Cleaning removes impossible values, not every wrong one.** A whole-grain oat cereal with 5 g protein per 100 g is possible but suspiciously low; Cheerios itself has 12.8 g. Values like this stay.

## 9. Known limitations

| Limitation | Size |
|---|---|
| No usable category | 62% of English-named US products, excluded |
| Too-broad categories | 30,762 products tagged only "snacks" |
| No English ingredient list | 12% of the corpus. These products stay, but can never pass an allergen check. |
| Added sugars rarely reported | Present for 20% |
| Unbranded products never grouped | 36% of products. Duplicates among them stay separate. |
| Grams vs millilitres | A rule, not a fact from the data |

The full design is in the [data pipeline doc](../03-data-pipeline.md).
