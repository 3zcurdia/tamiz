#!/usr/bin/env python3
"""Human-in-the-loop review of machine-translated polish items.

Reads data/polish.es.draft.jsonl, walks you through each item, and records
decisions in data/polish.es.review.jsonl (append-only, resumable). Accepted
(or edited) items are compiled into the final data/polish.es.jsonl on every
save, so you can stop and resume anytime.

Commands at each item:
  a / Enter  accept the draft as-is
  e          edit fields (Enter on a field keeps the draft value)
  r          reject (excluded from the final dataset)
  s          skip for now (will show up again next run)
  u          undo the previous decision
  q          quit (progress is saved)

GEC items are flagged: Google Translate usually FIXES the grammar error in the
input, which makes the item trivial. For those, check that the Spanish input
still contains a real error; if not, edit one in (or reject).
"""
import json
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
DRAFT = os.path.join(DATA, "polish.es.draft.jsonl")
REVIEW = os.path.join(DATA, "polish.es.review.jsonl")
FINAL = os.path.join(DATA, "polish.es.jsonl")

BOLD, DIM, GREEN, YELLOW, RED, CYAN, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m")


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def save_review(decisions):
    with open(REVIEW, "w", encoding="utf-8") as f:
        for d in decisions.values():
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def compile_final(decisions):
    rows = [d["row"] for d in decisions.values() if d["verdict"] == "accept"]
    with open(FINAL, "w", encoding="utf-8") as f:
        for r in rows:
            r = dict(r)
            r.pop("mt", None)
            r["source"] = r["source"].replace("grammarly/coedit", "grammarly/coedit+google-mt+human-review")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def edit_field(name, value):
    print(f"\n{CYAN}{name}{RESET} (Enter = keep):\n  {value}")
    new = input("  > ").strip()
    return new if new else value


def show(i, total, en, es):
    task = es["source"].split(":")[-1]
    if es["input"].strip().lower() == es["answer"].strip().lower():
        warn = f"  {RED}<- input == answer: MT erased the edit; fix the input or reject{RESET}"
    elif task == "gec":
        warn = f"  {RED}<- GT probably fixed the error; verify the ES input is still broken!{RESET}"
    else:
        warn = ""
    print(f"\n{BOLD}[{i}/{total}] id={es['id']}  task={task}{RESET}{warn}")
    print(f"{DIM}EN instruction: {en['instruction']}{RESET}")
    print(f"{DIM}EN input:       {en['input']}{RESET}")
    print(f"{DIM}EN answer:      {en['answer']}{RESET}")
    print(f"{CYAN}ES instruction:{RESET} {es['instruction']}")
    print(f"{YELLOW}ES input:      {RESET} {es['input']}")
    print(f"{GREEN}ES answer:     {RESET} {es['answer']}")


def main():
    drafts = load_jsonl(DRAFT)
    if not drafts:
        print(f"no drafts at {DRAFT} — run scripts/translate_polish.py first")
        return
    en_by_id = {r["id"]: r for r in load_jsonl(os.path.join(DATA, "polish.en.jsonl"))}
    decisions = {d["id"]: d for d in load_jsonl(REVIEW)}
    pending = [d for d in drafts if d["id"] not in decisions]
    print(f"{len(drafts)} drafts | {len(decisions)} decided | {len(pending)} pending")

    history = []
    i = 0
    while i < len(pending):
        es = pending[i]
        show(len(decisions) + 1, len(drafts), en_by_id[es["id"]], es)
        cmd = input(f"{BOLD}[a]ccept / [e]dit / [r]eject / [s]kip / [u]ndo / [q]uit:{RESET} ").strip().lower()

        if cmd in ("a", ""):
            decisions[es["id"]] = {"id": es["id"], "verdict": "accept", "row": es}
            history.append(es["id"])
            i += 1
        elif cmd == "e":
            row = dict(es)
            for field in ("instruction", "input", "answer"):
                row[field] = edit_field(field, row[field])
            decisions[es["id"]] = {"id": es["id"], "verdict": "accept", "row": row, "edited": True}
            history.append(es["id"])
            i += 1
        elif cmd == "r":
            decisions[es["id"]] = {"id": es["id"], "verdict": "reject", "row": es}
            history.append(es["id"])
            i += 1
        elif cmd == "s":
            pending.append(pending.pop(i))
        elif cmd == "u" and history:
            last = history.pop()
            decisions.pop(last, None)
            pending.insert(i, next(d for d in drafts if d["id"] == last))
            print(f"{YELLOW}undid {last}{RESET}")
        elif cmd == "q":
            break
        else:
            continue

        save_review(decisions)
        n = compile_final(decisions)

    n = compile_final(decisions)
    accepted = sum(1 for d in decisions.values() if d["verdict"] == "accept")
    rejected = len(decisions) - accepted
    print(f"\nsaved: {accepted} accepted ({rejected} rejected) -> {os.path.relpath(FINAL)} ({n} rows)")
    print(f"{len(drafts) - len(decisions)} still pending — re-run to continue.")


if __name__ == "__main__":
    main()
