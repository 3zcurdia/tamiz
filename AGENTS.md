# AGENTS.md

Paired EN/ES benchmark dataset for local/open LLMs. `data/*.jsonl` are the
artifact; `scripts/` build and curate them. No tests, lint, or CI.

## Commands

```bash
# Python is pinned via mise.toml (`python = "latest"`); or use a venv (see README).
python3 -m venv .venv
.venv/bin/pip install "datasets==3.6.0" pandas pyarrow
.venv/bin/python scripts/build_dataset.py   # regenerate all data/<task>.<lang>.jsonl
```

- Builds are reproducible: `random.seed(72)`. Data files are committed to git
  (no `.gitignore`); do not hand-edit them — regenerate instead.

## Data schema

One JSON object per line in `data/<task>.<lang>.jsonl`. `pair_id` is the join
key: the same `pair_id` across `.en`/`.es` files is the same test item.
`choices` is a dict for multiple-choice tasks, `null` otherwise.
