# tamiz — paired EN/ES everyday-tasks dataset

Benchmark dataset for evaluating local/open LLMs (≤32 GB VRAM) on everyday, non-coding
tasks, with the **same test items in English and Spanish** to measure the ES↔EN quality gap
for ordinary users in Latin America and Spanish-speaking countries.

## Build

```bash
python3 -m venv .venv
.venv/bin/pip install "datasets==3.6.0" pandas pyarrow
.venv/bin/python scripts/build_dataset.py
```

Output goes to `data/<task>.<lang>.jsonl`. Sampling is seeded (`random.seed(72)`) so
builds are reproducible.

## Tasks

| Task | EN source | ES source | Rows/lang | Parallel? |
|---|---|---|---|---|
| `qa_openbook` | [allenai/openbookqa](https://huggingface.co/datasets/allenai/openbookqa) | [BSC-LT/openbookqa-es](https://huggingface.co/datasets/BSC-LT/openbookqa-es) | 962 | Yes — aligned by original id |
| `commonsense_copa` | [aps/super_glue](https://huggingface.co/datasets/aps/super_glue) (copa) | [BSC-LT/COPA-es](https://huggingface.co/datasets/BSC-LT/COPA-es) | 600 | Yes — aligned by (split, id); EN hidden test labels recovered from the ES release |
| `summarize` | [csebuetnlp/xlsum](https://huggingface.co/datasets/csebuetnlp/xlsum) english | xlsum spanish | 500 | No — same task/format (BBC articles), different articles per language |
| `categorize` | [AmazonScience/massive](https://huggingface.co/datasets/AmazonScience/massive) en-US | massive es-ES | 500 | Yes — professionally localized utterances, same intent label (60 classes) |
| `translate` | [google/wmt24pp](https://huggingface.co/datasets/google/wmt24pp) en→es_MX | same (source/reference) | 960 | Yes — human post-edited references, **Latin American (Mexican) Spanish** |
| `polish` | [grammarly/coedit](https://huggingface.co/datasets/grammarly/coedit) (gec, paraphrase, formality, simplification, clarity, coherence) | **none exists publicly** | 500 (EN only) | — |

## Schema

One JSON object per line:

```json
{
  "task": "categorize",
  "lang": "es",
  "id": "31",
  "pair_id": "31",          // same pair_id across .en/.es files = same test item
  "split": "test",
  "instruction": "Clasifica la petición del usuario…",
  "input": "aspira el pasillo",
  "choices": null,           // dict for multiple-choice tasks, null otherwise
  "answer": "iot_cleaning",
  "source": "AmazonScience/massive"
}
```

Instructions are natively written in each language (not machine-translated), so the prompt
itself also tests Spanish instruction-following.

## Known gaps / next steps

- **`polish` has no Spanish side** — no public Spanish text-editing/GEC benchmark exists.
  Options: human-translate a CoEdIT sample, or author items from Spanish learner corpora
  (e.g. COWS-L2H). The `pair_id` field is already in place for a future ES file.
- `summarize` is task-parallel but not item-parallel (XL-Sum has no cross-lingual article
  alignment). MLSUM is an alternative for ES but has no EN split either.
- COPA-es and OpenBookQA-es are peninsular-Spanish professional translations (BSC);
  only the `translate` task uses a Latin American variety so far.
- Not yet covered from the original benchmark plan: needle-in-a-haystack (ES), brainstorm,
  learning/tutoring, meeting/email triage, spreadsheet analysis — no usable public
  datasets exist in Spanish; these need to be authored.

## Scoring suggestions

- `qa_openbook`, `commonsense_copa`, `categorize`: exact match (letter / 1-2 / label).
- `translate`: chrF++ or COMET against the reference.
- `summarize`, `polish`: LLM-as-judge rubric (ROUGE is considered weak); keep the judge
  model fixed and stronger than the models under test.
