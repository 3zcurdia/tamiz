#!/usr/bin/env python3
"""Machine-translate data/polish.en.jsonl to Spanish drafts via Google Translate.

Writes data/polish.es.draft.jsonl incrementally; safe to interrupt and re-run
(already-translated ids are skipped). Instructions are cached by string since
CoEdIT reuses a small set of them.

The drafts are NOT the final dataset — run scripts/review_polish.py to
human-review each item into data/polish.es.jsonl.
"""
import json
import os
import sys
import time

from deep_translator import GoogleTranslator

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
SRC = os.path.join(DATA, "polish.en.jsonl")
DST = os.path.join(DATA, "polish.es.draft.jsonl")

translator = GoogleTranslator(source="en", target="es")
_cache = {}


def tr(text, retries=4):
    if not text:
        return text
    if text in _cache:
        return _cache[text]
    for attempt in range(retries):
        try:
            out = translator.translate(text)
            _cache[text] = out
            time.sleep(0.3)
            return out
        except Exception as e:
            wait = 2 ** (attempt + 1)
            print(f"    retry in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"translation failed after {retries} retries: {text[:80]}")


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    done = set()
    if os.path.exists(DST):
        done = {json.loads(l)["id"] for l in open(DST, encoding="utf-8")}
        print(f"resuming: {len(done)} already translated")

    with open(DST, "a", encoding="utf-8") as out:
        for i, r in enumerate(rows):
            if r["id"] in done:
                continue
            draft = dict(r)
            draft["lang"] = "es"
            draft["instruction"] = tr(r["instruction"])
            draft["input"] = tr(r["input"])
            draft["answer"] = tr(r["answer"])
            draft["mt"] = "google-translate"
            out.write(json.dumps(draft, ensure_ascii=False) + "\n")
            out.flush()
            print(f"[{i + 1}/{len(rows)}] {r['id']} ({r['source'].split(':')[-1]})")

    print(f"done -> {os.path.relpath(DST)}")


if __name__ == "__main__":
    main()
