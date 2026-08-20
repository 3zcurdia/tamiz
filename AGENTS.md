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

- `scripts/build_dataset.py` downloads from HuggingFace at runtime — needs
  network. Some datasets require `trust_remote_code=True`.
- Builds are reproducible: `random.seed(72)`. Data files are committed to git
  (no `.gitignore`); do not hand-edit them — regenerate instead.

## Data schema

One JSON object per line in `data/<task>.<lang>.jsonl`. `pair_id` is the join
key: the same `pair_id` across `.en`/`.es` files is the same test item.
`choices` is a dict for multiple-choice tasks, `null` otherwise.

## polish ES pipeline (scripts not mentioned in README)

The `polish` task has no public Spanish source. Three scripts close that gap, in order:

1. `scripts/build_dataset.py` → `data/polish.en.jsonl` (EN side only)
2. `scripts/translate_polish.py` → `data/polish.es.draft.jsonl` (Google
   Translate; needs `deep_translator`; append-only + resumable)
3. `scripts/review_polish.py` → interactive human review (a/e/r/s/u/q keys);
   writes `data/polish.es.review.jsonl` and compiles accepted rows into
   `data/polish.es.jsonl`

Draft/review files are intermediate; only `polish.{en,es}.jsonl` are final.

## Feature work

Planned/next-step features are described in `.ai/docs/features/` (one file per
feature). Read the relevant file before implementing a task.
