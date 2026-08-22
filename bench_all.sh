#!/usr/bin/env bash
set -euo pipefail

PROVIDER="lmstudio"
CONCURRENCY=4
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
  ["openai/gpt-oss-20b"]="mxfp4"
)

MODELS=(
  "qwen3.5-0.8b"
  "google/gemma-4-e4b"
  "google/gemma-4-e2b"
  "bonsai-27b"
  "nanbeige4.1-3b"
  "google/gemma-4-12b-qat"
  "laguna-xs-2.1"
  "microsoft/phi-4"
  "qwen/qwen3.6-27b"
  "qwen/qwen3.6-35b-a3b"
  "qwen/qwen3.5-9b"
  "openai/gpt-oss-20b"
)

mkdir -p "$LOG_DIR"

echo "Provider: $PROVIDER | Concurrency: $CONCURRENCY | Models: ${#MODELS[@]}"
echo "Checking server..."
if ! curl -sf http://localhost:1234/v1/models >/dev/null 2>&1; then
  echo "Error: LM Studio server not reachable at http://localhost:1234/v1/models" >&2
  exit 1
fi

prev_model=""
i=0
for model in "${MODELS[@]}"; do
  quant="${QUANTS[$model]}"
  slug=$(echo "$model" | tr '[:upper:]' '[:lower:]' | sed 's#[/: ]#-#g')
  log="$LOG_DIR/${slug}.log"
  echo ""
  echo "=== [$((++i))/${#MODELS[@]}] $model (quant=$quant) ===" | tee -a "$log"
  if [[ -n "${prev_model:-}" && "$prev_model" != "$model" ]]; then
    if command -v lms >/dev/null 2>&1 || [[ -x "$HOME/.lmstudio/bin/lms" ]]; then
      LMS_BIN_U="$(command -v lms 2>/dev/null || echo "$HOME/.lmstudio/bin/lms")"
      echo "Unloading previous model $prev_model..." | tee -a "$log"
      "$LMS_BIN_U" unload "$prev_model" 2>&1 | tee -a "$log" || "$LMS_BIN_U" unload --all 2>&1 | tee -a "$log" || true
      for _ in {1..15}; do
        if ! curl -sf http://localhost:1234/api/v0/models 2>/dev/null | MODEL="$prev_model" python3 -c "import json,sys,os; d=json.load(sys.stdin); m=os.environ['MODEL']; sys.exit(0 if any(x.get('id')==m and x.get('state')=='loaded' for x in d.get('data',[])) else 1)"; then break; fi
        sleep 1
      done
    fi
  fi
  if command -v lms >/dev/null 2>&1 || [[ -x "$HOME/.lmstudio/bin/lms" ]]; then
    LMS_BIN="$(command -v lms 2>/dev/null || echo "$HOME/.lmstudio/bin/lms")"
    if ! curl -sf http://localhost:1234/api/v0/models 2>/dev/null | MODEL="$model" python3 -c "import json,sys,os; d=json.load(sys.stdin); m=os.environ['MODEL']; sys.exit(0 if any(x.get('id')==m and x.get('state')=='loaded' for x in d.get('data',[])) else 1)"; then
      echo "Model $model not loaded — running: lms load $model -y" | tee -a "$log"
      "$LMS_BIN" load "$model" -y 2>&1 | tee -a "$log" || echo "lms load failed for $model" | tee -a "$log" >&2
      for _ in {1..30}; do
        if curl -sf http://localhost:1234/api/v0/models 2>/dev/null | MODEL="$model" python3 -c "import json,sys,os; d=json.load(sys.stdin); m=os.environ['MODEL']; sys.exit(0 if any(x.get('id')==m and x.get('state')=='loaded' for x in d.get('data',[])) else 1)"; then break; fi
        sleep 2
      done
    fi
  fi
  set +e
  "$PYTHON" scripts/run_bench.py \
    --provider "$PROVIDER" \
    --model "$model" \
    --quantization "$quant" \
    --task "$TASK" \
    --lang "$LANG" \
    --concurrency "$CONCURRENCY" 2>&1 | tee -a "$log"
  status=${PIPESTATUS[0]}
  set -e
  if [[ $status -ne 0 ]]; then
    echo "WARN: $model failed with exit $status (see $log)" >&2
  else
    echo "OK: $model done."
  fi
  prev_model="$model"
done

echo ""
echo "Scoring all results..."
"$PYTHON" scripts/score.py 2>&1 | tee -a "$LOG_DIR/score.log"
echo "Done. Logs: $LOG_DIR | Raw: results/raw/ | Scores: results/scores.json"
