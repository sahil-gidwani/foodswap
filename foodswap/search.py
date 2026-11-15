"""Find the products that best match a text query.

Two methods, merged by rank:
- keyword search (BM25) over each product's name, categories and ingredients;
- meaning-based search: a small embedding model turns products and queries into vectors,
  so "fizzy drink" can find "soda" without sharing a word.
Products that fail a requested allergen exclusion are removed before ranking.

    python -m foodswap.search build [--sample]
    python -m foodswap.search query "crunchy oat cereal" [--exclude peanuts milk] [--sample]
"""

import argparse
import json
import re
import time

import bm25s
import numpy as np
import pandas as pd
import Stemmer

from foodswap.allergens import ALLERGENS
from foodswap.data import CORPUS_DIR, DATA_DIR, load_taxonomy
from foodswap.schema import Verdict

INDEX_DIR = DATA_DIR / "index"

# Keyword search scores each field separately and adds them up; a match in the name counts most.
# Starting weights, to be tuned once on the practice scenarios and then shared by every system.
FIELD_WEIGHTS = {"name": 1.0, "categories": 0.5, "ingredients": 0.3}
BM25 = {"method": "lucene", "k1": 1.2, "b": 0.75}
STEMMER = Stemmer.Stemmer("english")

MODEL = "BAAI/bge-small-en-v1.5"
# The model expects this instruction in front of queries, but not in front of documents.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
# Product descriptions for the model stay short: the model reads at most 512 tokens.
INGREDIENT_WORDS = 40

# Reciprocal Rank Fusion: each list adds 1 / (RRF_K + rank) for every product in its top FUSION_DEPTH.
# 60 is the value from the original paper (Cormack, Clarke and Buettcher, 2009).
RRF_K = 60
FUSION_DEPTH = 1000

COLUMNS = ["code", "name", "brand", "generic_name", "ingredients_text", "category", "categories",
           "family_id", "scans"] + [f"allergen_{a}" for a in ALLERGENS]
HTML_TAG = re.compile(r"<[^>]+>")


def build(corpus="products"):
    """Build the three keyword indexes and the embedding matrix for a corpus, and save them."""
    products = pd.read_parquet(CORPUS_DIR / f"{corpus}.parquet", columns=COLUMNS)
    folder = INDEX_DIR / corpus
    folder.mkdir(parents=True, exist_ok=True)
    category_name = english_category_names()
    timings = {}

    start = time.time()
    for field, texts in field_texts(products, category_name).items():
        index = bm25s.BM25(**BM25)
        index.index(bm25s.tokenize(texts, stopwords="en", stemmer=STEMMER, show_progress=False),
                    show_progress=False)
        index.save(folder / f"bm25_{field}")
    timings["keyword_seconds"] = round(time.time() - start, 1)

    from sentence_transformers import SentenceTransformer

    start = time.time()
    vectors = SentenceTransformer(MODEL).encode(
        dense_texts(products, category_name), batch_size=64, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=True,
    )
    np.save(folder / "dense.npy", vectors.astype(np.float16))
    timings["dense_seconds"] = round(time.time() - start, 1)

    summary = {"corpus": corpus, "products": len(products), "model": MODEL, **timings}
    (folder / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def english_category_names():
    categories = load_taxonomy("categories")

    def name(tag):
        return categories.get(tag, {}).get("name", {}).get("en") or tag.split(":", 1)[-1].replace("-", " ")

    return name


def clean(text):
    return HTML_TAG.sub(" ", text) if isinstance(text, str) else ""


def field_texts(products, category_name):
    """The text keyword search sees for each product, one field at a time."""
    return {
        "name": [" ".join(clean(t) for t in parts) for parts in
                 zip(products.name, products.generic_name, products.brand)],
        "categories": [" ".join(category_name(t) for t in tags) for tags in products.categories],
        "ingredients": [clean(t) for t in products.ingredients_text],
    }


def dense_texts(products, category_name):
    """A short description of each product for the embedding model."""
    return [
        f"{clean(name)}. {clean(brand)}. {category_name(category)}. "
        f"Ingredients: {' '.join(clean(ingredients).split()[:INGREDIENT_WORDS])}"
        for name, brand, category, ingredients in
        zip(products.name, products.brand, products.category, products.ingredients_text)
    ]


class Search:
    """Loads a corpus and its indexes once, then answers queries."""

    def __init__(self, corpus="products"):
        from sentence_transformers import SentenceTransformer

        folder = INDEX_DIR / corpus
        self.products = pd.read_parquet(CORPUS_DIR / f"{corpus}.parquet", columns=COLUMNS)
        self.keyword = {field: bm25s.BM25.load(folder / f"bm25_{field}", mmap=True) for field in FIELD_WEIGHTS}
        self.vectors = np.load(folder / "dense.npy").astype(np.float32)
        self.model = SentenceTransformer(MODEL)

    def keyword_scores(self, text):
        tokens = bm25s.tokenize([text], stopwords="en", stemmer=STEMMER, return_ids=False, show_progress=False)[0]
        if not tokens:
            return np.zeros(len(self.products), dtype=np.float32)
        return sum(weight * self.keyword[field].get_scores(tokens) for field, weight in FIELD_WEIGHTS.items())

    def dense_scores(self, text):
        query = self.model.encode([QUERY_PREFIX + text], normalize_embeddings=True, convert_to_numpy=True)[0]
        return self.vectors @ query

    def eligible(self, exclude=(), category=None):
        """Products that pass every excluded allergen (UNKNOWN doesn't pass), optionally in one category."""
        mask = np.ones(len(self.products), dtype=bool)
        for allergen in exclude:
            mask &= (self.products[f"allergen_{allergen}"] == Verdict.PASS).to_numpy()
        if category:
            mask &= self.products.categories.map(lambda tags: category in tags).to_numpy()
        return mask

    def search(self, text, exclude=(), category=None, k=10, keyword=True, dense=True):
        """The top k eligible products for the text, best first, with each method's rank."""
        unknown = set(exclude) - set(ALLERGENS)
        if unknown:
            raise ValueError(f"Unknown allergens {sorted(unknown)}; choose from {sorted(ALLERGENS)}")
        mask = self.eligible(exclude, category)

        ranked = {}
        if keyword:
            ranked["keyword"] = top(self.keyword_scores(text), mask, FUSION_DEPTH, positive_only=True)
        if dense:
            ranked["dense"] = top(self.dense_scores(text), mask, FUSION_DEPTH)
        fused = rrf(ranked.values())[:k]

        results = self.products.iloc[[i for i, _ in fused]][["code", "name", "brand", "category"]].copy()
        results["score"] = [score for _, score in fused]
        for method, order in ranked.items():
            position = {i: rank for rank, i in enumerate(order, start=1)}
            results[f"{method}_rank"] = [position.get(i) for i, _ in fused]
        results.attrs["eligible"] = int(mask.sum())
        return results.reset_index(names="idx")


def top(scores, mask, n, positive_only=False):
    """Indices of the n best-scoring eligible products, best first."""
    scores = np.where(mask, scores, -np.inf)
    if positive_only:
        scores = np.where(scores > 0, scores, -np.inf)
    n = min(n, int(np.isfinite(scores).sum()))
    if n == 0:
        return np.array([], dtype=int)
    best = np.argpartition(-scores, n - 1)[:n]
    return best[np.argsort(-scores[best], kind="stable")]


def rrf(ranked_lists, k=RRF_K):
    """Reciprocal Rank Fusion: merge ranked lists without comparing their score scales."""
    fused = {}
    for ranked in ranked_lists:
        for rank, i in enumerate(ranked, start=1):
            fused[int(i)] = fused.get(int(i), 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda item: (-item[1], item[0]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build")
    build_command.add_argument("--sample", action="store_true")
    query = commands.add_parser("query")
    query.add_argument("text")
    query.add_argument("--exclude", nargs="*", default=[], choices=sorted(ALLERGENS))
    query.add_argument("--category")
    query.add_argument("--sample", action="store_true")
    query.add_argument("-k", type=int, default=10)
    args = parser.parse_args()

    corpus = "sample" if args.sample else "products"
    if args.command == "build":
        build(corpus)
        return
    results = Search(corpus).search(args.text, args.exclude, args.category, args.k)
    print(f"{results.attrs['eligible']:,} eligible products")
    print(results.drop(columns="idx").to_string(index=False))


if __name__ == "__main__":
    main()
