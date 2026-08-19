#!/usr/bin/env python3
"""Build a paired EN/ES everyday-tasks benchmark dataset.

Tasks and sources:
  - qa_openbook      : allenai/openbookqa (EN)  <-> BSC-LT/openbookqa-es (ES), aligned by id
  - commonsense_copa : aps/super_glue:copa (EN) <-> BSC-LT/COPA-es (ES), aligned by id
                       (EN test labels are hidden -1; filled from the ES set, labels are
                        language-independent)
  - summarize        : csebuetnlp/xlsum english / spanish configs (same task, not parallel docs)
  - categorize       : AmazonScience/massive en-US / es-ES (parallel utterances, intent labels)
  - translate        : google/wmt24pp en-es_MX (Latin American Spanish, human references)
  - polish           : grammarly/coedit (EN only; gec/paraphrase/formality/simplification)
                       -> ES counterpart does not exist publicly; emitted EN rows carry
                          pair_id so an ES side can be authored/translated later.

Output: data/<task>.<lang>.jsonl with one unified schema:
  {task, lang, id, pair_id, instruction, input, choices, answer, source}
"""
import json
import os
import random

from datasets import load_dataset

random.seed(72)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE = {"summarize": 500, "categorize": 500, "polish": 500}


def write(task, lang, rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{task}.{lang}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  wrote {len(rows):>5} rows -> {os.path.relpath(path)}")


def row(task, lang, id_, pair_id, instruction, input_, answer, choices=None, source="", split=""):
    return {
        "task": task, "lang": lang, "id": str(id_), "pair_id": str(pair_id),
        "split": split, "instruction": instruction, "input": input_,
        "choices": choices, "answer": answer, "source": source,
    }


INSTR = {
    "qa_openbook": {
        "en": "Answer the multiple-choice question. Reply with the letter of the correct option.",
        "es": "Responde la pregunta de opción múltiple. Responde con la letra de la opción correcta.",
    },
    "commonsense_copa": {
        "en": "Given the premise, choose the more plausible {q}. Reply with 1 or 2.",
        "es": "Dada la premisa, elige la {q} más plausible. Responde con 1 o 2.",
    },
    "summarize": {
        "en": "Summarize the following article in one or two sentences.",
        "es": "Resume el siguiente artículo en una o dos oraciones.",
    },
    "categorize": {
        "en": "Classify the user's request into one of the intent categories. Reply with the category name.",
        "es": "Clasifica la petición del usuario en una de las categorías de intención. Responde con el nombre de la categoría.",
    },
    "translate": {
        "en": "Translate the following text from English to Spanish (Latin America).",
        "es": "Traduce el siguiente texto del inglés al español (Latinoamérica).",
    },
}


def build_openbookqa():
    print("== qa_openbook ==")
    es = {}
    for split in ("validation", "test"):
        ds = load_dataset("BSC-LT/openbookqa-es", split=split)
        for ex in ds:
            es[ex["id"]] = (split, ex)
    en_rows, es_rows = [], []
    for split in ("validation", "test"):
        ds = load_dataset("allenai/openbookqa", "main", split=split)
        for ex in ds:
            if ex["id"] not in es:
                continue
            es_split, es_ex = es[ex["id"]]
            en_rows.append(row(
                "qa_openbook", "en", ex["id"], ex["id"], INSTR["qa_openbook"]["en"],
                ex["question_stem"], ex["answerKey"],
                dict(zip(ex["choices"]["label"], ex["choices"]["text"])),
                "allenai/openbookqa", split))
            es_rows.append(row(
                "qa_openbook", "es", ex["id"], ex["id"], INSTR["qa_openbook"]["es"],
                es_ex["question_stem"], es_ex["answerKey"],
                dict(zip(es_ex["choices"]["label"], es_ex["choices"]["text"])),
                "BSC-LT/openbookqa-es", split))
    write("qa_openbook", "en", en_rows)
    write("qa_openbook", "es", es_rows)


def build_copa():
    print("== commonsense_copa ==")
    es = {}
    for split in ("validation", "test"):
        ds = load_dataset("BSC-LT/COPA-es", split=split)
        for ex in ds:
            # ids restart at 0 in each split, so key by (split, id)
            es[(split, str(ex["id"]))] = ex
    q_word = {"cause": {"en": "cause", "es": "causa"}, "effect": {"en": "effect", "es": "consecuencia"}}
    en_rows, es_rows = [], []
    for split in ("validation", "test"):
        ds = load_dataset("aps/super_glue", "copa", split=split, trust_remote_code=True)
        for ex in ds:
            if (split, str(ex["idx"])) not in es:
                continue
            es_ex = es[(split, str(ex["idx"]))]
            key = f"{split}-{ex['idx']}"
            label = ex["label"] if ex["label"] in (0, 1) else es_ex["label"]
            answer = str(label + 1)
            en_rows.append(row(
                "commonsense_copa", "en", key, key,
                INSTR["commonsense_copa"]["en"].format(q=q_word[ex["question"]]["en"]),
                ex["premise"], answer,
                {"1": ex["choice1"], "2": ex["choice2"]},
                "aps/super_glue:copa", split))
            es_rows.append(row(
                "commonsense_copa", "es", key, key,
                INSTR["commonsense_copa"]["es"].format(q=q_word[es_ex["question"]]["es"]),
                es_ex["premise"], answer,
                {"1": es_ex["choice1"], "2": es_ex["choice2"]},
                "BSC-LT/COPA-es", split))
    write("commonsense_copa", "en", en_rows)
    write("commonsense_copa", "es", es_rows)


def build_summarize():
    print("== summarize ==")
    n = SAMPLE["summarize"]
    for lang, config in (("en", "english"), ("es", "spanish")):
        ds = load_dataset("csebuetnlp/xlsum", config, split="test", trust_remote_code=True)
        idx = random.sample(range(len(ds)), min(n, len(ds)))
        rows = []
        for i in sorted(idx):
            ex = ds[i]
            rows.append(row(
                "summarize", lang, ex["id"], f"{lang}-{ex['id']}",
                INSTR["summarize"][lang], ex["text"], ex["summary"],
                None, f"csebuetnlp/xlsum:{config}", "test"))
        write("summarize", lang, rows)


def build_categorize():
    print("== categorize ==")
    n = SAMPLE["categorize"]
    data = {}
    for lang, config in (("en", "en-US"), ("es", "es-ES")):
        ds = load_dataset("AmazonScience/massive", config, split="test", trust_remote_code=True)
        intents = ds.features["intent"].names
        data[lang] = {str(ex["id"]): (ex["utt"], intents[ex["intent"]]) for ex in ds}
    common = sorted(set(data["en"]) & set(data["es"]), key=int)
    picked = sorted(random.sample(common, min(n, len(common))), key=int)
    for lang in ("en", "es"):
        rows = []
        for id_ in picked:
            utt, intent = data[lang][id_]
            rows.append(row(
                "categorize", lang, id_, id_, INSTR["categorize"][lang],
                utt, intent, None, "AmazonScience/massive", "test"))
        write("categorize", lang, rows)


def build_translate():
    print("== translate ==")
    ds = load_dataset("google/wmt24pp", "en-es_MX", split="train")
    en_rows, es_rows = [], []
    for ex in ds:
        if ex.get("is_bad_source"):
            continue
        id_ = ex["segment_id"] if "segment_id" in ex else ex["document_id"]
        en_rows.append(row(
            "translate", "en", id_, id_, INSTR["translate"]["en"],
            ex["source"], ex["target"], None, "google/wmt24pp:en-es_MX", "test"))
        es_rows.append(row(
            "translate", "es", id_, id_, INSTR["translate"]["es"],
            ex["source"], ex["target"], None, "google/wmt24pp:en-es_MX", "test"))
    write("translate", "en", en_rows)
    write("translate", "es", es_rows)


def build_polish():
    print("== polish (EN only; no public ES counterpart) ==")
    n = SAMPLE["polish"]
    ds = load_dataset("grammarly/coedit", split="validation")
    keep = ("gec", "paraphrase", "formality", "simplification", "clarity", "coherence")
    pool = [ex for ex in ds if ex["task"] in keep]
    picked = random.sample(pool, min(n, len(pool)))
    rows = []
    for ex in picked:
        instruction, _, text = ex["src"].partition(": ")
        rows.append(row(
            "polish", "en", ex["_id"], ex["_id"], instruction or ex["src"],
            text, ex["tgt"], None, f"grammarly/coedit:{ex['task']}", "validation"))
    write("polish", "en", rows)


if __name__ == "__main__":
    build_openbookqa()
    build_copa()
    build_summarize()
    build_categorize()
    build_translate()
    build_polish()
    print("done.")
