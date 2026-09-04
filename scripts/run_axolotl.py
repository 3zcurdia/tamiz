#!/usr/bin/env python3
"""Axolotl test: one prompt, every target LM Studio model, direct API.

Sends the same SVG-generation prompt directly to LM Studio's OpenAI-compatible
API (no agent harness), saves SVGs into site/public/axolotl/<slug>.svg and
regenerates the manifest consumed by the /axolotl page.

Usage:
    python scripts/run_axolotl.py                  # target models (page set + qwen3.8-27b)
    python scripts/run_axolotl.py --model qwen3.8  # substring filter, repeatable
    python scripts/run_axolotl.py --force          # regenerate existing SVGs
    python scripts/run_axolotl.py --list           # just list discovered/target models
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_bench import _is_model_loaded, _lms_bin, loaded_context_length  # noqa: E402

import requests  # noqa: E402

BASE_URL = "http://localhost:1234/v1"
TARGET_MODELS = [
    "google/gemma-4-12b-qat",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.6-35b-a3b",
    "qwen/qwen3.8-27b",
]
LOAD_CTX = 20000
MAX_TOKENS = 4096

ASSETS_DIR = ROOT / "site" / "public" / "axolotl"
MANIFEST_PATH = ROOT / "site" / "results" / "axolotl.json"
LOG_PATH = ROOT / "results" / "axolotl.jsonl"

PROMPT = (
    "Create an SVG for a purple axolotl riding a scooter. "
    "Output ONLY the raw SVG code, no markdown, no explanation, "
    "starting with <svg and ending with </svg>."
)

FILE_RE = re.compile(r"^(?P<slug>.+?)(?:-(?P<harness>pi|opencode|direct))?\.svg$")
SVG_RE = re.compile(r"<svg\b[\s\S]*?</svg>", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def axolotl_slug(model_id: str) -> str:
    s = model_id.lower().replace("/", "--").replace(":", "-")
    return re.sub(r"\s+", "-", s)


def filename_for(model_id: str) -> str:
    return f"{axolotl_slug(model_id)}.svg"


def list_models(base_url: str) -> list[str]:
    try:
        r = requests.get(f"{base_url.replace('/v1', '/api/v0')}/models", timeout=10)
        r.raise_for_status()
        ids = [
            m["id"]
            for m in r.json().get("data", [])
            if m.get("id") and m.get("type") in ("llm", "vlm")
        ]
        if ids:
            return ids
    except Exception:
        pass
    r = requests.get(f"{base_url}/models", timeout=10)
    r.raise_for_status()
    return [
        m["id"]
        for m in r.json().get("data", [])
        if m.get("id") and "embed" not in m["id"].lower()
    ]


def resolve_targets(discovered: list[str]) -> list[str]:
    """Keep only models that exist in LM Studio among TARGET_MODELS."""
    out = []
    for t in TARGET_MODELS:
        hit = next((d for d in discovered if d == t or d.lower() == t.lower()), None)
        if hit:
            out.append(hit)
        elif any(t.lower() in d.lower() or d.lower() in t.lower() for d in discovered):
            best = next(
                d
                for d in discovered
                if t.lower() in d.lower() or d.lower() in t.lower()
            )
            out.append(best)
        else:
            print(
                f"  warn: target '{t}' not found in LM Studio — will try as-is",
                file=sys.stderr,
            )
            out.append(t)
    seen = set()
    uniq = []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def extract_svg(text: str) -> str | None:
    if not text:
        return None
    m = SVG_RE.search(text)
    return m.group(0) if m else None


def svg_check(path: Path) -> tuple[str | None, bool]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unreadable", False
    if "<svg" not in text.lower():
        return "no_svg", False
    try:
        ET.fromstring(text)
        return None, True
    except ET.ParseError:
        return None, False


def call_lmstudio(
    model: str, prompt: str, base_url: str, timeout: int = 300
) -> tuple[str | None, str, int]:
    t0 = time.perf_counter()
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "reasoning_effort": "low",
    }

    def extract(data: dict) -> str:
        msg = data.get("choices", [{}])[0].get("message", {})
        return msg.get("content") or msg.get("text") or ""

    try:
        r = requests.post(f"{base_url}/chat/completions", json=payload, timeout=timeout)
        if r.status_code == 400 and "reasoning" in r.text.lower():
            payload.pop("reasoning_effort", None)
            r = requests.post(
                f"{base_url}/chat/completions", json=payload, timeout=timeout
            )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code >= 400:
            return None, f"http_{r.status_code}: {r.text[:600]}", latency_ms
        data = r.json()
        content = extract(data)
        if not content:
            payload["reasoning_effort"] = "none"
            r = requests.post(
                f"{base_url}/chat/completions", json=payload, timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if r.status_code < 400:
                content = extract(r.json())
        return content, "", latency_ms
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return None, str(e)[:600], latency_ms


def generate(model: str, base_url: str, timeout: int) -> dict:
    slug = axolotl_slug(model)
    target = ASSETS_DIR / f"{slug}.svg"
    rec: dict = {
        "generated_at": now_iso(),
        "model": model,
        "harness": "direct",
        "slug": slug,
        "file": f"{slug}.svg",
    }
    t0 = time.perf_counter()
    content, err, latency_ms = call_lmstudio(model, PROMPT, base_url, timeout)
    if "latency_ms" not in rec or latency_ms:
        rec["latency_ms"] = (
            latency_ms
            if err or content is not None
            else int((time.perf_counter() - t0) * 1000)
        )
    if err and content is None:
        rec["error"] = err[:200]
        rec["output_tail"] = err[-400:]
        return rec
    svg = extract_svg(content or "")
    if svg:
        target.write_text(svg + "\n", encoding="utf-8")
        e, xml_ok = svg_check(target)
        rec.update(error=e, xml_ok=xml_ok, bytes=target.stat().st_size)
        return rec
    if content:
        rec["error"] = "no_svg_in_output"
        rec["output_tail"] = content[-600:]
    else:
        rec["error"] = err[:200] if err else "empty_response"
        rec["output_tail"] = (err or "")[-400:]
    return rec


def unload_model(model: str) -> None:
    lms = _lms_bin()
    if not lms:
        return
    try:
        subprocess.run([lms, "unload", model], capture_output=True, timeout=120)
    except Exception:
        pass


def model_max_ctx(base_url: str, model_id: str) -> int | None:
    try:
        r = requests.get(f"{base_url.replace('/v1', '/api/v0')}/models", timeout=5)
        r.raise_for_status()
        for m in r.json().get("data", []):
            if m.get("id") == model_id:
                v = m.get("max_context_length")
                if isinstance(v, int) and v > 0:
                    return v
    except Exception:
        pass
    return None


def ensure_loaded(model: str, base_url: str) -> None:
    target = min(LOAD_CTX, model_max_ctx(base_url, model) or LOAD_CTX)
    if _is_model_loaded(model, base_url):
        ctx = loaded_context_length(base_url, model)
        if ctx and ctx >= target:
            return
        print(
            f"Model '{model}' loaded with ctx={ctx} (< {target}) — reloading.",
            file=sys.stderr,
        )
        unload_model(model)
    lms = _lms_bin()
    if not lms:
        print("lms CLI not found — cannot auto-load; trying anyway.", file=sys.stderr)
        return
    print(f"Loading: lms load {model} -c {target} -y", file=sys.stderr)
    try:
        subprocess.run([lms, "load", model, "-c", str(target), "-y"], timeout=600)
    except Exception as e:
        print(f"lms load failed: {e}", file=sys.stderr)
    for _ in range(60):
        if _is_model_loaded(model, base_url):
            print(f"Model '{model}' is now loaded.", file=sys.stderr)
            return
        time.sleep(2)
    print(
        f"Model '{model}' still not reported as loaded — trying anyway.",
        file=sys.stderr,
    )


def build_manifest() -> int:
    latest: dict[str, dict] = {}
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rec = json.loads(line)
                if rec.get("file"):
                    latest[rec["file"]] = rec
    items = []
    for path in sorted(ASSETS_DIR.glob("*.svg")):
        m = FILE_RE.match(path.name)
        if not m:
            continue
        rec = latest.get(path.name, {})
        err, xml_ok = svg_check(path)
        items.append(
            {
                "model": rec.get("model") or m.group("slug").replace("--", "/"),
                "harness": rec.get("harness") or m.group("harness") or "direct",
                "slug": m.group("slug"),
                "file": f"/axolotl/{path.name}",
                "bytes": path.stat().st_size,
                "xml_ok": xml_ok,
                "error": err,
                "latency_ms": rec.get("latency_ms"),
                "generated_at": rec.get("generated_at"),
            }
        )
    items.sort(key=lambda i: (i["model"], i["harness"]))
    manifest = {
        "test": "axolotl",
        "prompt": PROMPT,
        "updated_at": now_iso(),
        "items": items,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return len(items)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run axolotl SVG test via direct LM Studio API"
    )
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument(
        "--model",
        action="append",
        default=None,
        help="substring filter on model id; repeatable",
    )
    ap.add_argument("--force", action="store_true", help="regenerate existing SVGs")
    ap.add_argument("--keep-loaded", action="store_true", help="do not unload models")
    ap.add_argument(
        "--timeout", type=int, default=900, help="per-model API timeout seconds"
    )
    ap.add_argument("--list", action="store_true", help="list models and exit")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    try:
        discovered = list_models(base)
    except Exception as e:
        print(
            f"LM Studio at {base} is not reachable — start its server first.\n{e}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not discovered:
        print(f"LM Studio at {base} returned no models.", file=sys.stderr)
        sys.exit(1)

    models = resolve_targets(discovered)
    if args.model:
        for f in args.model:
            models = [m for m in models if f.lower() in m.lower()]
        if not models:
            print("No models match the given filters.", file=sys.stderr)
            sys.exit(1)

    print(f"LM Studio: {base}  ctx={LOAD_CTX}")
    print(f"Target models ({len(models)}):")
    for m in models:
        print(f"  {m} -> {axolotl_slug(m)}")
    print(
        f"Discovered ({len(discovered)}): {', '.join(discovered[:8])}{' ...' if len(discovered) > 8 else ''}"
    )
    if args.list:
        return

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    done = failed = skipped = 0
    for i, model in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}] {model}")
        ensure_loaded(model, base)
        fname = filename_for(model)
        if (ASSETS_DIR / fname).exists() and not args.force:
            print(f"  direct: skip ({fname} exists)")
            skipped += 1
            continue
        print(f"  direct: generating {fname} ...", flush=True)
        rec = generate(model, base, args.timeout)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if rec.get("error"):
            failed += 1
            print(f"  direct: FAILED ({rec['error']})")
        else:
            done += 1
            print(f"  direct: ok ({rec.get('bytes')} bytes, {rec['latency_ms']} ms)")
        if not args.keep_loaded:
            unload_model(model)

    n = build_manifest()
    print(
        f"\nDone. ok={done} failed={failed} skipped={skipped} manifest={MANIFEST_PATH} ({n} items)"
    )
    print("Publish with: cd site && npm run build")


if __name__ == "__main__":
    main()
