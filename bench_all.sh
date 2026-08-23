#!/usr/bin/env bash
set -euo pipefail

PROVIDER="lmstudio"
# Context window to load every model with. The KV pool is SHARED across in-flight
# requests, and the governing constraint is measured to be:
#   concurrency x (prompt_tokens + ACTUAL output tokens) <= CTX
# 16384 covers every model here at its configured parallelism; gemma is the
# tightest because it answers translate prompts with ~235 tokens of prose.
CTX=16384
DEFAULT_PARALLEL=16
TASK="all"
LANG="all"
LOG_DIR="results/logs"
PYTHON=".venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

declare -A QUANTS=(
  ["meta/muse-glimmer"]="q4_k_m"
  ["qwen/qwen3.8-27b"]="q4_k_m"
  ["google/gemma-4-e4b"]="q4_k_m"
  ["google/gemma-4-e2b"]="q4_k_m"
  ["bonsai-27b"]="q1_0"
  ["nanbeige4.1-3b"]="q4_k_m"
  ["google/gemma-4-12b-qat"]="q4_0"
  ["laguna-xs-2.1"]="q4_k_m"
  ["qwen3.5-0.8b"]="q8_0"
  ["microsoft/phi-4"]="q4_k_m"
  ["qwen/qwen3.6-27b"]="q4_k_m"
  ["qwen/qwen3.6-35b-a3b"]="q4_k_m"
  ["qwen/qwen3.5-9b"]="q4_k_m"
  ["ornith-1.5-9b"]="q4_k_m"
  ["openai/gpt-oss-20b"]="mxfp4"
)

# Measured sweet spot per model: aggregate tok/s on 64 translate rows at CTX above,
# reasoning off. Values are where throughput peaks before latency/errors take over.
#   qwen3.5-0.8b  16 -> 552 tok/s (saturates early; 32 adds only +4%)
#   gemma-4-e2b   32 -> 582 tok/s (48 is -5%, 64 exhausts the KV pool)
#   gemma-4-e4b   32 -> 486 tok/s (48 is -6%, 64 exhausts the KV pool)
#   ornith-1.5-9b 32 -> 256 tok/s
#   qwen3.5-9b    32 -> 255 tok/s
#   gpt-oss-20b   64 -> 250 tok/s (MoE, ~3.6B active; still climbing at 64)
declare -A PARALLEL=(
  ["qwen3.5-0.8b"]=16
  ["google/gemma-4-e2b"]=32
  ["google/gemma-4-e4b"]=32
  ["ornith-1.5-9b"]=32
  ["qwen/qwen3.5-9b"]=32
  ["openai/gpt-oss-20b"]=64
)

MODELS=(
  "qwen3.5-0.8b"
  "google/gemma-4-e4b"
  "google/gemma-4-e2b"
  # "bonsai-27b"
  # "nanbeige4.1-3b"
  # "google/gemma-4-12b-qat"
  # "laguna-xs-2.1"
  "microsoft/phi-4"
  # "qwen/qwen3.6-27b"
  # "qwen/qwen3.6-35b-a3b"
  "ornith-1.5-9b"
  "qwen/qwen3.5-9b"
  "openai/gpt-oss-20b"
)

mkdir -p "$LOG_DIR"

echo "Provider: $PROVIDER | ctx: $CTX | Models: ${#MODELS[@]}"
echo "Checking server..."
if ! curl -sf http://localhost:1234/v1/models >/dev/null 2>&1; then
  echo "Error: LM Studio server not reachable at http://localhost:1234/v1/models" >&2
  exit 1
fi

i=0
for model in "${MODELS[@]}"; do
  quant="${QUANTS[$model]}"
  par="${PARALLEL[$model]:-$DEFAULT_PARALLEL}"
  slug=$(echo "$model" | tr '[:upper:]' '[:lower:]' | sed 's#[/: ]#-#g')
  log="$LOG_DIR/${slug}.log"
  echo ""
  echo "=== [$((++i))/${#MODELS[@]}] $model (quant=$quant ctx=$CTX parallel=$par) ===" | tee -a "$log"
  if command -v lms >/dev/null 2>&1 || [[ -x "$HOME/.lmstudio/bin/lms" ]]; then
    LMS_BIN="$(command -v lms 2>/dev/null || echo "$HOME/.lmstudio/bin/lms")"
    # -c/--parallel only apply to a fresh load; a model that is already resident
    # keeps its existing settings, so unload unconditionally first.
    "$LMS_BIN" unload --all >/dev/null 2>&1 || true
    sleep 3
    echo "Loading: lms load $model -c $CTX --parallel $par -y" | tee -a "$log"
    "$LMS_BIN" load "$model" -c "$CTX" --parallel "$par" -y 2>&1 | tee -a "$log" \
      || echo "lms load failed for $model" | tee -a "$log" >&2
    for _ in {1..30}; do
      if curl -sf http://localhost:1234/api/v0/models 2>/dev/null | MODEL="$model" python3 -c "import json,sys,os; d=json.load(sys.stdin); m=os.environ['MODEL']; sys.exit(0 if any(x.get('id')==m and x.get('state')=='loaded' for x in d.get('data',[])) else 1)"; then break; fi
      sleep 2
    done
    # Confirm the settings actually took, since a silent fallback to parallel=4
    # would cap throughput without any error.
    "$LMS_BIN" ps 2>/dev/null | tee -a "$log"
  fi
  set +e
  "$PYTHON" scripts/run_bench.py \
    --provider "$PROVIDER" \
    --model "$model" \
    --quantization "$quant" \
    --task "$TASK" \
    --lang "$LANG" \
    --concurrency "$par" 2>&1 | tee -a "$log"
  status=${PIPESTATUS[0]}
  set -e
  if [[ $status -ne 0 ]]; then
    echo "WARN: $model failed with exit $status (see $log)" >&2
  else
    echo "OK: $model done."
  fi
done

echo ""
echo "Scoring all results..."
"$PYTHON" scripts/score.py 2>&1 | tee -a "$LOG_DIR/score.log"
echo "Done. Logs: $LOG_DIR | Raw: results/raw/ | Scores: results/scores.json"
