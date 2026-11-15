"""Download the Open Food Facts dump, check it, and build the cleaned US product table.

    python -m foodswap.data download    # dump and taxonomies, then a completeness check
    python -m foodswap.data build       # data/corpus/products.parquet and sample.parquet
"""

import datetime
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PARQUET = RAW_DIR / "food.parquet"
TAXONOMY_DIR = RAW_DIR / "taxonomies"
CORPUS_DIR = DATA_DIR / "corpus"

DATASET = "openfoodfacts/product-database"
TAXONOMIES = ["categories", "ingredients", "allergens", "labels"]
TAXONOMY_URL = "https://static.openfoodfacts.org/data/taxonomies/{}.json"
USER_AGENT = "FoodSwap/0.1 (university course project)"

# Past exports have been truncated, so refuse anything much smaller than expected.
MIN_ROWS = 4_800_000
MIN_US_ROWS = 950_000

# Every nutrient in the dump becomes a column (dashes become underscores), with these exceptions:
# entries that are scores, estimates or duplicates rather than nutrients, and names used by
# under 1% of products, which are mostly one-off typos like "es-l-glutamine".
# Values are per 100 g, or per 100 ml for drinks; masses are in grams.
NOT_NUTRIENTS = {
    "energy",  # the same as energy-kcal, in kJ
    "energy-kj",
    "salt",  # always sodium x 2.5
    "nova-group",
    "nutrition-score-fr",
    "fruits-vegetables-nuts",
    "fruits-vegetables-legumes",
    "fruits-vegetables-nuts-estimate-from-ingredients",
    "fruits-vegetables-legumes-estimate-from-ingredients",
}
MIN_NUTRIENT_SHARE = 0.01

# The headline numbers on a label. They must be plausible, and they identify one product sold in several pack sizes.
LABEL_NUTRIENTS = ["energy_kcal", "fat", "saturated_fat", "carbohydrates", "sugars", "fiber", "proteins", "sodium"]

# Nutrition values outside these bounds can only be data-entry mistakes.
MAX_GRAMS = 105  # a little over 100 g, because labels round (corn syrup: 103 g carbohydrate)
MAX_KCAL = 900

# Only compare within a category once it holds this many distinct products.
MIN_CATEGORY_FAMILIES = 30

# A small corpus for fast development: the most-scanned products in the proposal's four categories.
SAMPLE_CATEGORIES = ["en:breakfast-cereals", "en:yogurts", "en:snacks", "en:beverages"]
SAMPLE_PER_CATEGORY = 5000

# Pack sizes, removed from names so different sizes of one product match.
SIZE_WORDS = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:fl\.?\s*oz|oz|ounces?|lbs?|kg|g|ml|l|ct|count|pk|pack)\b"
    r"|\b(?:family|value|party|snack|king|share)\s+size\b"
)


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not PARQUET.exists():
        from huggingface_hub import HfApi, hf_hub_download

        revision = HfApi().dataset_info(DATASET).sha
        print(f"Downloading food.parquet (about 8 GB) at revision {revision}")
        hf_hub_download(DATASET, "food.parquet", repo_type="dataset", revision=revision, local_dir=RAW_DIR)
        (RAW_DIR / "REVISION").write_text(revision + "\n")

    TAXONOMY_DIR.mkdir(exist_ok=True)
    for name in TAXONOMIES:
        path = TAXONOMY_DIR / f"{name}.json"
        if not path.exists():
            request = urllib.request.Request(TAXONOMY_URL.format(name), headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                path.write_bytes(response.read())

    write_manifest()


def write_manifest():
    """Record what we downloaded so every result can be traced back to this snapshot."""
    con = duckdb.connect()
    source = f"read_parquet('{PARQUET}')"
    rows = con.execute(f"SELECT count(*) FROM {source}").fetchone()[0]
    us_rows = con.execute(
        f"SELECT count(*) FROM {source} WHERE list_contains(countries_tags, 'en:united-states')"
    ).fetchone()[0]

    revision_file = RAW_DIR / "REVISION"
    manifest = {
        "dataset": DATASET,
        "revision": revision_file.read_text().strip() if revision_file.exists() else None,
        "sha256": sha256(PARQUET),
        "rows": rows,
        "us_rows": us_rows,
        "checked": datetime.date.today().isoformat(),
    }
    (RAW_DIR / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))

    if rows < MIN_ROWS or us_rows < MIN_US_ROWS:
        sys.exit(f"The dump looks truncated ({rows:,} rows, {us_rows:,} US rows). Don't build on it.")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(1 << 24):
            digest.update(block)
    return digest.hexdigest()


def build():
    """Turn the raw dump into one clean row per US product, counting what each check removes."""
    categories = load_taxonomy("categories")
    known = {name: set(load_taxonomy(name)) for name in TAXONOMIES}
    funnel = {}

    df, nutrients, funnel["us_products"], funnel["english_name"] = read_us_products()

    # Keep only tags the taxonomies know; the rest are typos or free text in other languages.
    for column, taxonomy in [
        ("categories", "categories"),
        ("ingredient_tags", "ingredients"),
        ("allergen_tags", "allergens"),
        ("trace_tags", "allergens"),
        ("label_tags", "labels"),
    ]:
        df[column] = df[column].map(lambda tags, k=known[taxonomy]: [t for t in tags if t in k])

    df = df[df.categories.map(len) > 0]
    funnel["has_category"] = len(df)

    df = df[~df.has_quality_error]
    funnel["no_quality_errors"] = len(df)

    limits = pd.Series(MAX_GRAMS, index=nutrients)
    limits["energy_kcal"] = MAX_KCAL
    impossible = (df[nutrients] < 0) | (df[nutrients] > limits)
    # An impossible headline number means the record can't be trusted; an impossible
    # minor value (say, water or a vitamin) is just dropped.
    df = df[~impossible[LABEL_NUTRIENTS].any(axis=1)].copy()
    df[nutrients] = df[nutrients].mask(impossible.loc[df.index])
    funnel["plausible_nutrition"] = len(df)

    df["nutriscore_grade"] = df.nutriscore_grade.where(df.nutriscore_grade.isin(list("abcde")))

    is_drink = df.categories.map(lambda tags: "en:beverages" in tags)
    df["basis"] = np.where(
        df.quantity_unit.isin(["g", "ml"]), df.quantity_unit, np.where(is_drink, "ml", "g")
    )

    df = df.sort_values("code").reset_index(drop=True)
    df["family_id"] = family_ids(df)

    depth = category_depths(categories)
    df["category"] = df.categories.map(lambda tags: max(tags, key=lambda t: (depth.get(t, 0), t)))
    df["comparison_category"] = comparison_categories(df, depth)

    columns = [
        "code", "name", "brand", "generic_name", "ingredients_text",
        "category", "comparison_category", "categories",
        "ingredient_tags", "allergen_tags", "trace_tags", "label_tags", "analysis_tags",
        "ingredients_n", "unknown_ingredients_n", *nutrients, "basis",
        "nutriscore_grade", "nova_group", "scans", "last_modified_t", "family_id",
    ]
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    df[columns].to_parquet(CORPUS_DIR / "products.parquet", index=False)

    in_sample = set()
    for category in SAMPLE_CATEGORIES:
        members = df[df.categories.map(lambda tags, c=category: c in tags)]
        in_sample.update(members.nlargest(SAMPLE_PER_CATEGORY, "scans").index)
    sample = df.loc[sorted(in_sample), columns].reset_index(drop=True)
    sample.to_parquet(CORPUS_DIR / "sample.parquet", index=False)

    summary = {
        "funnel": funnel,
        "products": len(df),
        "families": int(df.family_id.nunique()),
        "nutrients": nutrients,
        "with_english_ingredients": int(df.ingredients_text.notna().sum()),
        "sample_products": len(sample),
        "source_sha256": json.loads((RAW_DIR / "MANIFEST.json").read_text())["sha256"],
        "built": datetime.date.today().isoformat(),
    }
    (CORPUS_DIR / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def read_us_products():
    """US products with an English main language and name, flattened to plain columns, plus the nutrient column names."""
    con = duckdb.connect()
    con.execute("""
        CREATE MACRO english(texts) AS coalesce(
            list_filter(texts, lambda x: x.lang = 'en' AND trim(x."text") <> '')[1]."text",
            list_filter(texts, lambda x: x.lang = 'main' AND trim(x."text") <> '')[1]."text")
    """)
    con.execute("""CREATE MACRO nutrient(values, n) AS list_filter(values, lambda x: x."name" = n)[1]."100g" """)

    con.execute(f"""
        CREATE TEMP TABLE us AS
        SELECT
            code,
            lang = 'en' AND english(product_name) IS NOT NULL AS is_english,
            english(product_name) AS name,
            nullif(trim(split_part(brands, ',', 1)), '') AS brand,
            english(generic_name) AS generic_name,
            english(ingredients_text) AS ingredients_text,
            categories_tags AS categories,
            ingredients_tags AS ingredient_tags,
            allergens_tags AS allergen_tags,
            traces_tags AS trace_tags,
            labels_tags AS label_tags,
            ingredients_analysis_tags AS analysis_tags,
            ingredients_n,
            unknown_ingredients_n,
            nutriments,
            product_quantity_unit AS quantity_unit,
            nutriscore_grade,
            nova_group,
            coalesce(unique_scans_n, 0) AS scans,
            last_modified_t,
            len(data_quality_errors_tags) > 0 AS has_quality_error
        FROM read_parquet('{PARQUET}')
        WHERE list_contains(countries_tags, 'en:united-states') AND NOT coalesce(obsolete, false)
    """)
    total = con.execute("SELECT count(*) FROM us").fetchone()[0]
    english = con.execute("SELECT count(*) FROM us WHERE is_english").fetchone()[0]
    con.execute("CREATE TEMP TABLE kept AS SELECT * EXCLUDE (is_english) FROM us WHERE is_english AND len(categories) > 0")

    kept = con.execute("SELECT count(*) FROM kept").fetchone()[0]
    names = con.execute("""
        SELECT x."name" FROM (SELECT unnest(nutriments) AS x FROM kept)
        WHERE x."100g" IS NOT NULL GROUP BY 1 HAVING count(*) >= ? ORDER BY count(*) DESC
    """, [kept * MIN_NUTRIENT_SHARE]).fetchall()
    names = [n for (n,) in names if n not in NOT_NUTRIENTS]
    nutrients = [n.replace("-", "_") for n in names]
    columns = ", ".join(f"nutrient(nutriments, '{n}') AS {c}" for n, c in zip(names, nutrients))
    df = con.execute(f"SELECT * EXCLUDE (nutriments), {columns} FROM kept").df()

    for column in ["categories", "ingredient_tags", "allergen_tags", "trace_tags", "label_tags", "analysis_tags"]:
        df[column] = df[column].map(lambda tags: list(tags) if isinstance(tags, (list, np.ndarray)) else [])
    df["has_quality_error"] = df.has_quality_error.fillna(False).astype(bool)
    return df, nutrients, total, english


def family_ids(df):
    """Same brand, same name apart from pack size, same nutrition: one product sold in several sizes."""
    brand = df.brand.map(normalize)
    name = df.name.map(normalize)
    values = df[LABEL_NUTRIENTS].to_numpy(dtype=float)
    nutrition = [",".join("" if np.isnan(v) else f"{v:.1f}" for v in row) for row in values]
    key = brand + "|" + name + "|" + pd.Series(nutrition, index=df.index)

    # Without a brand, "Extra Virgin Olive Oil" with olive oil's nutrition could be any of dozens
    # of products, so unbranded products stay on their own.
    unbranded = brand == ""
    key[unbranded] = "code:" + df.code[unbranded]
    return pd.factorize(key)[0]


def normalize(text):
    text = SIZE_WORDS.sub(" ", text.lower() if isinstance(text, str) else "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def category_depths(categories):
    """How far each category sits below the top of the hierarchy (longest path, since nodes can have several parents)."""
    depths = {}

    def depth(node, visiting=()):
        if node not in depths:
            parents = [p for p in categories[node].get("parents", []) if p in categories and p not in visiting]
            depths[node] = 1 + max((depth(p, (*visiting, node)) for p in parents), default=-1)
        return depths[node]

    for node in categories:
        depth(node)
    return depths


def comparison_categories(df, depth):
    """The most specific category of each product that still holds enough products to compare against."""
    exploded = df[["family_id", "categories"]].explode("categories")
    families = exploded.groupby("categories").family_id.nunique().to_dict()

    def choose(tags):
        big_enough = [t for t in tags if families[t] >= MIN_CATEGORY_FAMILIES]
        if big_enough:
            return max(big_enough, key=lambda t: (depth.get(t, 0), t))
        return max(tags, key=lambda t: (families[t], t))

    return df.categories.map(choose)


def load_taxonomy(name):
    return json.loads((TAXONOMY_DIR / f"{name}.json").read_text())


COMMANDS = {"download": download, "build": build}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]]()
