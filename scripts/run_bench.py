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
import shutil
import subprocess
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

# These are ceilings, not reservations: a model that answers in 6 tokens stops at 6,
# so a generous cap costs nothing. But it must leave room for models that emit a
# reasoning preamble before the answer -- gpt-oss-20b ignores reasoning_effort=none
# and scores 3.1 vs 93.8 on qa_openbook at a 32- vs 512-token cap, because the cap
# truncates it mid-reasoning and content comes back empty.
MAX_TOKENS = {
    "qa_openbook": 512,
    "commonsense_copa": 512,
    "categorize": 512,
    "translate": 1024,
}
DEFAULT_MAX_TOKENS = 512

# "none" is sent as reasoning_effort=none, which suppresses thinking on servers that
# honor it (LM Studio + Qwen3.x). Use "default" to omit the field entirely.
DEFAULT_REASONING_EFFORT = "none"


def model_slug(model_id: str) -> str:
    return re.sub(r"[/:\s]+", "-", model_id.lower())


def infer_quantization(model_id: str, raw: dict | None) -> str:
    if raw:
        for k in ("quantization", "quant", "precision", "format", "backend"):
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip().lower()
    s = model_id.lower()
    m = re.search(
        r"q\d+_k(_[sml])?|iq\d+_\w+|q\d+|fp16|bf16|f16|int4|int8|4bit|8bit|awq|gptq|gguf|mlx|exl2",
        s,
    )
    if m:
        return m.group(0).lower()
    return "unknown"


def fetch_raw_model(base_url: str, model_id: str | None) -> dict | None:
    try:
        r = requests.get(f"{base_url}/models", timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        if model_id:
            for m in data:
                if m.get("id") == model_id:
                    return m
        return data[0]
    except Exception:
        return None


def loaded_context_length(base_url: str, model_id: str) -> int | None:
    """Context window the model is actually loaded with, if the server reports it."""
    try:
        api_url = base_url.replace("/v1", "/api/v0")
        r = requests.get(f"{api_url}/models", timeout=5)
        r.raise_for_status()
        for m in r.json().get("data", []):
            if m.get("id") == model_id:
                for k in ("loaded_context_length", "max_context_length"):
                    v = m.get(k)
                    if isinstance(v, int) and v > 0:
                        return v
    except Exception:
        pass
    return None


def clamp_max_tokens(max_tok: int, ctx: int | None, prompt_reserve: int = 2048) -> int:
    """Keep prompt + completion inside the context window."""
    if not ctx:
        return max_tok
    return max(16, min(max_tok, ctx - prompt_reserve))


def _lms_bin() -> str | None:
    for cand in [shutil.which("lms"), os.path.expanduser("~/.lmstudio/bin/lms")]:
        if cand and os.path.exists(cand):
            return cand
    return None


def _is_model_loaded(model: str, base_url: str) -> bool:
    try:
        api_url = base_url.replace("/v1", "/api/v0")
        r = requests.get(f"{api_url}/models", timeout=5)
        r.raise_for_status()
        for m in r.json().get("data", []):
            if m.get("id") == model and m.get("state") == "loaded":
                return True
    except Exception:
        pass
    lms = _lms_bin()
    if lms:
        try:
            pr = subprocess.run(
                [lms, "ps", "--json"], capture_output=True, text=True, timeout=10
            )
            if pr.returncode == 0 and pr.stdout.strip():
                data = json.loads(pr.stdout)
                for m in data if isinstance(data, list) else []:
                    for k in ("key", "modelKey", "identifier", "id", "path"):
                        if m.get(k) == model:
                            return True
                    if model in " ".join(str(v) for v in m.values()):
                        return True
        except Exception:
            pass
    return False


def ensure_model_loaded(model: str, base_url: str, timeout: int = 600) -> bool:
    if _is_model_loaded(model, base_url):
        return True
    lms = _lms_bin()
    if not lms:
        print(
            f"Model '{model}' not loaded and lms CLI not found — cannot auto-load.",
            file=sys.stderr,
        )
        return False
    print(f"Model '{model}' not loaded — running: lms load {model} -y", file=sys.stderr)
    try:
        proc = subprocess.run([lms, "load", model, "-y"], timeout=timeout)
        if proc.returncode != 0:
            print(f"lms load exited with {proc.returncode}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"lms load timed out after {timeout}s", file=sys.stderr)
        return False
    except Exception as e:
        print(f"lms load failed: {e}", file=sys.stderr)
        return False
    for _ in range(30):
        if _is_model_loaded(model, base_url):
            print(f"Model '{model}' is now loaded.", file=sys.stderr)
            return True
        time.sleep(2)
    try:
        r = requests.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
            timeout=20,
        )
        if r.status_code < 400 or "No models loaded" not in r.text:
            return True
    except Exception:
        pass
    print(
        f"Model '{model}' still not reported as loaded after lms load — will try requests anyway.",
        file=sys.stderr,
    )
    return False


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


def call_api(
    base_url: str,
    prompt: str,
    max_tokens: int,
    is_apple: bool,
    model: str = "",
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> dict:
    """Call the chat completions API. Returns dict with output/error/timing."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 72,
        "max_tokens": max_tokens,
    }
    if reasoning_effort and reasoning_effort != "default":
        payload["reasoning_effort"] = reasoning_effort
    # seed / reasoning_effort may be rejected by some servers; try without if 400
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
        if r.status_code == 400 and "reasoning" in r.text.lower():
            payload.pop("reasoning_effort", None)
            r = requests.post(
                f"{base_url}/chat/completions",
                json=payload,
                timeout=300,
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if r.status_code >= 400:
            msg = r.text[:500]
            if is_apple and ("context" in msg.lower() or "length" in msg.lower()):
                return {
                    "error": "context_overflow",
                    "output": msg,
                    "latency_ms": latency_ms,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "tokens_per_second": None,
                }
            if is_apple and "guardrail" in msg.lower():
                return {
                    "error": "guardrail",
                    "output": msg,
                    "latency_ms": latency_ms,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "tokens_per_second": None,
                }
            return {
                "error": "api_error",
                "output": msg,
                "latency_ms": latency_ms,
                "prompt_tokens": None,
                "completion_tokens": None,
                "tokens_per_second": None,
            }

        data = r.json()
        choice = data["choices"][0]
        text = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        tps = (
            round(completion_tokens * 1000 / latency_ms, 2)
            if isinstance(completion_tokens, int) and latency_ms > 0
            else None
        )
        return {
            "error": None,
            "output": text,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tokens_per_second": tps,
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "error": "api_error",
            "output": str(e),
            "latency_ms": latency_ms,
            "prompt_tokens": None,
            "completion_tokens": None,
            "tokens_per_second": None,
        }


def run_task(
    provider: str,
    base_url: str,
    model: str,
    quantization: str,
    task: str,
    lang: str,
    limit: int | None,
    concurrency: int,
    label_list: list[str] | None,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    max_tokens_override: int | None = None,
):
    """Run one (task, lang) combination."""
    rows = load_dataset_file(task, lang)
    if not rows:
        print(f"  No data for {task}.{lang}, skipping.")
        return

    if limit:
        rows = rows[:limit]

    slug = model_slug(model)
    out_dir = RAW_DIR / (f"apple__{slug}" if provider == "apple" else slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{task}.{lang}.jsonl"

    done_ids = load_done_ids(out_path)
    todo = [r for r in rows if r["id"] not in done_ids]
    if not todo:
        print(f"  {task}.{lang}: all {len(rows)} rows already done (resume).")
        return

    print(f"  {task}.{lang}: {len(todo)} to run ({len(done_ids)} already done).")

    is_apple = provider == "apple"
    max_tok = max_tokens_override or MAX_TOKENS.get(task, DEFAULT_MAX_TOKENS)
    ctx = None if is_apple else loaded_context_length(base_url, model)
    clamped = clamp_max_tokens(max_tok, ctx)
    if clamped != max_tok:
        print(f"    max_tokens {max_tok} -> {clamped} (context {ctx})")
        max_tok = clamped

    def is_transient(rec: dict) -> bool:
        """Context overflow / guardrail won't fix themselves -- only retry real faults."""
        if rec["error"] != "api_error":
            return False
        return "Context size has been exceeded" not in (rec["output"] or "")

    def process_row(row: dict) -> dict:
        prompt = build_prompt(row, label_list, lang)
        result = call_api(base_url, prompt, max_tok, is_apple, model, reasoning_effort)
        if result["error"] == "api_error" and "No models loaded" in result["output"]:
            ensure_model_loaded(model, base_url)
            time.sleep(3)
            result = call_api(
                base_url, prompt, max_tok, is_apple, model, reasoning_effort
            )
        return {
            "id": row["id"],
            "pair_id": row["pair_id"],
            "task": task,
            "lang": lang,
            "provider": provider,
            "model": model,
            "quantization": quantization,
            "output": result["output"],
            "error": result["error"],
            "latency_ms": result["latency_ms"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "tokens_per_second": result["tokens_per_second"],
        }

    with open(out_path, "a", encoding="utf-8") as fout:
        if concurrency <= 1 or is_apple:
            for row in todo:
                rec = process_row(row)
                # retry once on a transient api_error
                if is_transient(rec):
                    if "No models loaded" in rec["output"]:
                        ensure_model_loaded(model, base_url)
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
                    if is_transient(rec):
                        if "No models loaded" in rec["output"]:
                            ensure_model_loaded(model, base_url)
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
    parser.add_argument("--provider", default="lmstudio", choices=PROVIDERS.keys())
    parser.add_argument(
        "--model",
        default=None,
        help="Model id (for apple, defaults to the one from /v1/models)",
    )
    parser.add_argument(
        "--quantization",
        default=None,
        help="Quantization label, e.g. q4_k_m, bf16 (auto-detected if omitted)",
    )
    parser.add_argument("--task", default="all", choices=list(TASKS) + ["all"])
    parser.add_argument("--lang", default="all", choices=list(LANGS) + ["all"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=["none", "low", "medium", "high", "default"],
        help="reasoning_effort sent to the server ('default' omits the field)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Override the per-task completion cap",
    )
    args = parser.parse_args()

    base_url = PROVIDERS[args.provider]
    if args.model:
        model = args.model
    else:
        model = preflight(base_url)
        print(f"Auto-detected model: {model}")

    if args.provider == "lmstudio":
        ensure_model_loaded(model, base_url)
    else:
        preflight(base_url)

    if args.quantization:
        quantization = args.quantization.strip().lower()
    else:
        raw_model = fetch_raw_model(base_url, model)
        quantization = infer_quantization(model, raw_model)

    tasks = TASKS if args.task == "all" else (args.task,)
    langs = LANGS if args.lang == "all" else (args.lang,)

    print(f"Provider: {args.provider} ({base_url})")
    print(f"Model: {model}")
    print(f"Quantization: {quantization}")
    print(f"Tasks: {tasks}")
    print(f"Languages: {langs}")
    print()

    for task in tasks:
        for lang in langs:
            label_list = collect_labels(task, lang) if task == "categorize" else None
            run_task(
                args.provider,
                base_url,
                model,
                quantization,
                task,
                lang,
                args.limit,
                args.concurrency,
                label_list,
                args.reasoning_effort,
                args.max_tokens,
            )

    print("\nDone.")


if __name__ == "__main__":
    main()
