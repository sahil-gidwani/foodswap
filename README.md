# foodswap

A constraint-aware packaged food substitution engine using hybrid lexical-semantic search, nutrition-aware ranking, and Open Food Facts.

## Setup

```
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m foodswap.data download
python -m foodswap.data build
python -m foodswap.search build
python -m pytest
```

`download` fetches about 8 GB into `data/` (git-ignored) and checks that the dump is complete. `build` turns it into `data/corpus/products.parquet` (the cleaned US products) and `sample.parquet` (18K products for quick development) in about a minute, including the allergen verdicts. `foodswap.search build` builds the search indexes (about 18 minutes; add `--sample` for a one-minute build over the sample). Try it: `python -m foodswap.search query "crunchy oat cereal" --exclude peanuts`.

## Project

- Proposal: [docs/proposal.pdf](docs/proposal.pdf)
- Plan and design: [docs/](docs/README.md)

Contains data from Open Food Facts, available under the Open Database License.
