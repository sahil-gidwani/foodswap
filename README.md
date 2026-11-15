# foodswap

A constraint-aware packaged food substitution engine using hybrid lexical-semantic search, nutrition-aware ranking, and Open Food Facts.

## Setup

```
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m foodswap.data download
```

The last step downloads about 8 GB into `data/` (git-ignored) and checks that the dump is complete.

## Project

- Proposal: [docs/proposal.pdf](docs/proposal.pdf)
- Plan and design: [docs/](docs/README.md)

Contains data from Open Food Facts, available under the Open Database License.
