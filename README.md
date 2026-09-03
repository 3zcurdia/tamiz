# tamiz — paired EN/ES everyday-tasks dataset
> YAPMB: Yet Another Poor Man's Benchmark

Benchmark dataset for evaluating local/open LLMs (≤32 GB VRAM) on everyday, non-coding
tasks, with the **same test items in English and Spanish** to measure the ES↔EN quality gap
for ordinary users in Latin America and Spanish-speaking countries.

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

## Axolotl test (SVG generation via agent harnesses)

Same-prompt visual benchmark in the spirit of "pelican riding a bicycle": every local
LM Studio model gets the identical prompt through two agent harnesses (`opencode run`
and `pi -p`) and must write its own SVG.

```
.venv/bin/python scripts/run_axolotl.py              # all models, both harnesses
.venv/bin/python scripts/run_axolotl.py --model phi-4 --tool pi
.venv/bin/python scripts/run_axolotl.py --force      # regenerate
```

- Prompt (identical for both harnesses): `Create a SVG file for a purple axolotl riding a
  scooter and write it in a file <filename>.svg`
- Output: `site/public/axolotl/<model-slug>-<harness>.svg` (e.g. `microsoft--phi-4-opencode.svg`,
  `microsoft--phi-4-pi.svg`)
- Manifest: `site/results/axolotl.json` (regenerated from the assets dir each run; the
  `/axolotl` page renders whatever the manifest lists, so new models show up automatically)
- Attempt log: `results/axolotl.jsonl`
- Harness config is written by the script: `opencode.json` (`provider.lmstudio`) and
  `.pi-agent-home/models.json` (repo-local pi config dir via `PI_CODING_AGENT_DIR`)
- Publish: `cd site && npm run build`
