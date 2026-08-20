#!/usr/bin/env python3
"""Benchmark runner: send prompts to a local model server, collect raw outputs.

Usage:
    python scripts/run_bench.py \
        --provider lmstudio|apple \
        --model <model-id> \
        --task qa_openbook|commonsense_copa|categorize|translate|all \
        --lang en|es|all \
        [--limit N] [--concurrency 1]
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"

PROVIDERS = {
    "lmstudio": "http://localhost:1234/v1",
    "apple": "http://127.0.0.1:1976/v1",
}

TASKS = ("qa_openbook", "commonsense_copa", "categorize", "translate")
LANGS = ("en", "es")

MAX_TOKENS = {
    "qa_openbook": 16,
    "commonsense_copa": 16,
    "categorize": 16,
    "translate": 400,
}


def model_slug(model_id: str) -> str:
    return re.sub(r"[/:\s]+", "-", model_id.lower())


def preflight(base_url: str) -> str:
    """Hit GET /v1/models; return the model id or exit."""
    try:
        r = requests.get(f"{base_url}/models", timeout=10)
        r.raise_for_status()
        models = r.json().get("data", [])
        if not models:
            print(f"Server at {base_url} returned no models.", file=sys.stderr)
            sys.exit(1)
        return models[0]["id"]
    except Exception as e:
        print(
            f"Server at {base_url} is not reachable — start LM Studio's server "
            f"(Developer tab) / the Apple FM bridge first.\n{e}",
            file=sys.stderr,
        )
        sys.exit(1)


def build_prompt(row: dict, label_list: list[str] | None, lang: str) -> str:
    """Construct the prompt from a dataset row."""
    parts = [row["instruction"]]

    if row.get("choices"):
        if row["task"] == "qa_openbook":
            for letter, text in row["choices"].items():
                parts.append(f"{letter}) {text}")
        elif row["task"] == "commonsense_copa":
            for num, text in row["choices"].items():
                parts.append(f"{num}) {text}")
    elif row["task"] == "categorize" and label_list:
        if lang == "es":
            parts.append("Responde exactamente con una de:")
        else:
            parts.append("Answer with exactly one of:")
        parts.append(", ".join(label_list))

    parts.append(row["input"])
    return "\n\n".join(parts)


def load_dataset_file(task: str, lang: str) -> list[dict]:
    path = DATA_DIR / f"{task}.{lang}.jsonl"
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_done_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    ids = set()
    with open(output_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                ids.add(rec["id"])
    return ids


def call_api(base_url: str, prompt: str, max_tokens: int, is_apple: bool) -> dict:
    """Call the chat completions API. Returns dict with output/error/timing."""
    payload = {
        "model": "",  # filled by caller
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 72,
        "max_tokens": max_tokens,
    }
    # seed may be rejected by some servers; try without if 400
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            timeout=300,
        )
        if r.status_code == 400 and "seed" in r.text.lower():
            payload.pop("seed", None)
            r = requests.post(
                f"{base_url}/chat/completions",
                json=payload,
                timeout=300,
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if r.status_code >= 400:
            msg = r.text[:500]
            if is_apple and ("context" in msg.lower() or "length" in msg.lower()):
                return {"error": "context_overflow", "output": msg, "latency_ms": latency_ms,
                        "prompt_tokens": None, "completion_tokens": None}
            if is_apple and "guardrail" in msg.lower():
                return {"error": "guardrail", "output": msg, "latency_ms": latency_ms,
                        "prompt_tokens": None, "completion_tokens": None}
            return {"error": "api_error", "output": msg, "latency_ms": latency_ms,
                    "prompt_tokens": None, "completion_tokens": None}

        data = r.json()
        choice = data["choices"][0]
        text = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return {
            "error": None,
            "output": text,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {"error": "api_error", "output": str(e), "latency_ms": latency_ms,
                "prompt_tokens": None, "completion_tokens": None}


def run_task(
    provider: str,
    base_url: str,
    model: str,
    task: str,
    lang: str,
    limit: int | None,
    concurrency: int,
    label_list: list[str] | None,
):
    """Run one (task, lang) combination."""
    rows = load_dataset_file(task, lang)
    if not rows:
        print(f"  No data for {task}.{lang}, skipping.")
        return

    if limit:
        rows = rows[:limit]

    out_dir = RAW_DIR / f"{provider}__{model_slug(model)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{task}.{lang}.jsonl"

    done_ids = load_done_ids(out_path)
    todo = [r for r in rows if r["id"] not in done_ids]
    if not todo:
        print(f"  {task}.{lang}: all {len(rows)} rows already done (resume).")
        return

    print(f"  {task}.{lang}: {len(todo)} to run ({len(done_ids)} already done).")

    is_apple = provider == "apple"
    max_tok = MAX_TOKENS.get(task, 16)

    def process_row(row: dict) -> dict:
        prompt = build_prompt(row, label_list, lang)
        result = call_api(base_url, prompt, max_tok, is_apple)
        return {
            "id": row["id"],
            "pair_id": row["pair_id"],
            "task": task,
            "lang": lang,
            "provider": provider,
            "model": model,
            "output": result["output"],
            "error": result["error"],
            "latency_ms": result["latency_ms"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        }

    with open(out_path, "a", encoding="utf-8") as fout:
        if concurrency <= 1 or is_apple:
            for row in todo:
                rec = process_row(row)
                # retry once on generic api_error
                if rec["error"] == "api_error":
                    time.sleep(5)
                    rec = process_row(row)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                status = "ERR:" + rec["error"] if rec["error"] else "ok"
                print(f"    [{status}] {rec['id']}")
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = {pool.submit(process_row, row): row for row in todo}
                for fut in as_completed(futures):
                    rec = fut.result()
                    if rec["error"] == "api_error":
                        time.sleep(5)
                        rec = process_row(futures[fut])
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    status = "ERR:" + rec["error"] if rec["error"] else "ok"
                    print(f"    [{status}] {rec['id']}")


def collect_labels(task: str, lang: str) -> list[str]:
    """Collect sorted unique answer values for categorize tasks."""
    rows = load_dataset_file(task, lang)
    return sorted({r["answer"] for r in rows})


def main():
    parser = argparse.ArgumentParser(description="Run benchmark against a local model")
    parser.add_argument("--provider", required=True, choices=PROVIDERS.keys())
    parser.add_argument("--model", default=None, help="Model id (for apple, defaults to the one from /v1/models)")
    parser.add_argument("--task", required=True, choices=list(TASKS) + ["all"])
    parser.add_argument("--lang", required=True, choices=list(LANGS) + ["all"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()

    base_url = PROVIDERS[args.provider]
    if args.model:
        model = args.model
    else:
        model = preflight(base_url)
        print(f"Auto-detected model: {model}")

    # preflight
    preflight(base_url)

    tasks = TASKS if args.task == "all" else (args.task,)
    langs = LANGS if args.lang == "all" else (args.lang,)

    print(f"Provider: {args.provider} ({base_url})")
    print(f"Model: {model}")
    print(f"Tasks: {tasks}")
    print(f"Languages: {langs}")
    print()

    for task in tasks:
        for lang in langs:
            label_list = collect_labels(task, lang) if task == "categorize" else None
            run_task(args.provider, base_url, model, task, lang, args.limit,
                     args.concurrency, label_list)

    print("\nDone.")


if __name__ == "__main__":
    main()
