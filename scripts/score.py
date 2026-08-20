#!/usr/bin/env python3
"""Score raw benchmark outputs and produce results/scores.json.

Fully offline — reads results/raw/**/*.jsonl, joins to data/*.jsonl, scores.
"""
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"
SCORES_PATH = Path(__file__).resolve().parent.parent / "results" / "scores.json"
SITE_SCORES_PATH = Path(__file__).resolve().parent.parent / "site" / "results" / "scores.json"

SCORABLE_TASKS = ("qa_openbook", "commonsense_copa", "categorize", "translate")


def load_dataset(task: str, lang: str) -> dict[str, dict]:
    path = DATA_DIR / f"{task}.{lang}.jsonl"
    if not path.exists():
        return {}
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def extract_mc_letter(output: str, choices: dict, valid_letters: list[str]) -> str | None:
    """Extract the chosen letter/number from model output for MC tasks."""
    s = output.strip()
    # strip markdown and trailing punctuation
    s = re.sub(r"[*`]", "", s)
    s = re.sub(r"[.,;:!?]+$", "", s)
    s = s.strip()

    # whole string is a single valid letter
    if s in valid_letters:
        return s

    # regex at start: optional paren, letter, optional paren/period/colon/whitespace
    pattern = r"^\(?([" + "".join(valid_letters) + r"])\)?[).:\s]"
    m = re.match(pattern, s, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # fallback: exactly one option's full text appears verbatim (case-insensitive)
    matches = []
    for letter, text in choices.items():
        if text.lower() in s.lower():
            matches.append(letter)
    if len(matches) == 1:
        return matches[0]

    return None


def extract_categorize(output: str, labels: set[str]) -> str | None:
    """Extract the label from model output for categorize tasks."""
    s = output.strip()
    s = re.sub(r"[*`]", "", s)
    s = re.sub(r"[.,;:!?]+$", "", s)
    s_lower = s.lower().strip()

    # exact match
    for label in labels:
        if s_lower == label.lower():
            return label

    # substring match — only if exactly one label matches
    found = [label for label in labels if label.lower() in s_lower]
    if len(found) == 1:
        return found[0]

    return None


def score_exact_match(rows: list[dict], dataset: dict[str, dict]) -> tuple[float, int, int]:
    """Score exact-match tasks. Returns (score_pct, n, format_failures)."""
    matches = 0
    n = 0
    format_failures = 0
    for rec in rows:
        n += 1
        ds_row = dataset.get(rec["id"])
        if rec.get("error"):
            format_failures += 1
            continue
        if not ds_row:
            format_failures += 1
            continue

        task = rec["task"]
        output = rec["output"]
        answer = ds_row["answer"]
        choices = ds_row.get("choices") or {}

        extracted = None
        if task in ("qa_openbook", "commonsense_copa"):
            valid = list(choices.keys())
            extracted = extract_mc_letter(output, choices, valid)
        elif task == "categorize":
            labels = {r["answer"] for r in dataset.values()}
            extracted = extract_categorize(output, labels)

        if extracted is None:
            format_failures += 1
        elif extracted.upper() == answer.upper():
            matches += 1

    score = (matches / n * 100) if n else 0.0
    return round(score, 1), n, format_failures


def score_chrf(rows: list[dict], dataset: dict[str, dict]) -> tuple[float, int, int]:
    """Score translate with chrF++. Returns (score, n, format_failures)."""
    from sacrebleu.metrics import CHRF
    chrf = CHRF(word_order=2)

    hypotheses = []
    references = []
    n = 0
    format_failures = 0

    for rec in rows:
        n += 1
        ds_row = dataset.get(rec["id"])
        if rec.get("error") or not ds_row:
            hypotheses.append("")
            references.append(ds_row["answer"] if ds_row else "")
            format_failures += 1
            continue

        output = rec["output"]
        # strip leading translation labels
        for prefix in ("Traducción:", "Translation:", "Traduccion:"):
            if output.startswith(prefix):
                output = output[len(prefix):].strip()
        hypotheses.append(output)
        references.append(ds_row["answer"])

    if not hypotheses:
        return 0.0, n, format_failures

    score = chrf.corpus_score(hypotheses, [references]).score
    return round(score, 1), n, format_failures


def main():
    if not RAW_DIR.exists():
        print("No results/raw/ directory found. Nothing to score.")
        return

    records = []

    for provider_dir in sorted(RAW_DIR.iterdir()):
        if not provider_dir.is_dir():
            continue
        # provider__model-slug
        parts = provider_dir.name.split("__", 1)
        if len(parts) != 2:
            continue
        provider, model_slug = parts

        for fpath in sorted(provider_dir.glob("*.jsonl")):
            stem = fpath.stem  # e.g. "qa_openbook.en"
            parts = stem.rsplit(".", 1)
            if len(parts) != 2:
                continue
            task, lang = parts
            if task not in SCORABLE_TASKS:
                continue

            # load raw outputs
            raw_rows = []
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        raw_rows.append(json.loads(line))

            if not raw_rows:
                continue

            # determine model id from first row
            model_id = raw_rows[0].get("model", model_slug)

            # load ground truth
            dataset = load_dataset(task, lang)

            # score
            if task == "translate":
                score, n, ff = score_chrf(raw_rows, dataset)
                metric = "chrf++"
            else:
                score, n, ff = score_exact_match(raw_rows, dataset)
                metric = "exact_match"

            ff_rate = round(ff / n * 100, 1) if n else 0.0

            records.append({
                "provider": provider,
                "model": model_id,
                "task": task,
                "lang": lang,
                "metric": metric,
                "score": score,
                "n": n,
                "format_failure_rate": ff_rate,
            })

    scores = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": records,
    }

    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    # Copy to site directory for Next.js import
    SITE_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(records)} records to {SCORES_PATH.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
