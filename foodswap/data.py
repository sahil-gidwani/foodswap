"""Download the Open Food Facts dump and taxonomies, then check the dump isn't truncated.

    python -m foodswap.data download
"""

import datetime
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PARQUET = RAW_DIR / "food.parquet"

DATASET = "openfoodfacts/product-database"
TAXONOMIES = ["categories", "ingredients", "allergens", "labels"]
TAXONOMY_URL = "https://static.openfoodfacts.org/data/taxonomies/{}.json"
USER_AGENT = "FoodSwap/0.1 (university course project)"

# Past exports have been truncated, so refuse anything much smaller than expected.
MIN_ROWS = 4_800_000
MIN_US_ROWS = 950_000


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not PARQUET.exists():
        from huggingface_hub import HfApi, hf_hub_download

        revision = HfApi().dataset_info(DATASET).sha
        print(f"Downloading food.parquet (about 8 GB) at revision {revision}")
        hf_hub_download(DATASET, "food.parquet", repo_type="dataset", revision=revision, local_dir=RAW_DIR)
        (RAW_DIR / "REVISION").write_text(revision + "\n")

    taxonomy_dir = RAW_DIR / "taxonomies"
    taxonomy_dir.mkdir(exist_ok=True)
    for name in TAXONOMIES:
        path = taxonomy_dir / f"{name}.json"
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


if __name__ == "__main__":
    if sys.argv[1:] != ["download"]:
        sys.exit(__doc__)
    download()
