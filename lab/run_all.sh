#!/usr/bin/env bash
# run_all.sh -- 2 conditions x 3 seeds, in parallel, detached-safe.  bash run_all.sh [A|B] [seed]
set -uo pipefail
for k in OPENAI_API_KEY OPENAICOMPATIBLE_API_KEY; do [[ -z "${!k:-}" ]] && { echo "ERROR: export $k" >&2; exit 2; }; done
mkdir -p logs results
CONDITIONS=(${1:-A B}); SEEDS=(${2:-1 2 3}); PIDS=(); TAGS=()
for cond in "${CONDITIONS[@]}"; do for seed in "${SEEDS[@]}"; do
  tag="cond${cond}_seed${seed}"; [[ "$cond" == "B" ]] && show=1 || show=0
  echo "launching $tag $(date +%H:%M:%S)"
  RUN_TAG="$tag" VICTIM_SHOW_TOOL_LOG="$show" VICTIM_SEED="$seed" PYTHONPATH=. \
    python -m garak --target_type function.Single --target_name "victim_agent#respond" \
      --spec probes.agent_breaker.AgentBreaker --config run_config.yaml --seed "$seed" --report_prefix "$tag" \
      > "logs/${tag}.console.log" 2>&1 &
  PIDS+=($!); TAGS+=("$tag"); sleep 20
done; done
echo "all launched; waiting..."; fail=0
for i in "${!PIDS[@]}"; do wait "${PIDS[$i]}" && echo "OK    ${TAGS[$i]}" || { echo "FAILED ${TAGS[$i]}"; fail=1; }; done
echo; echo "===== SUMMARY $(date) ====="
for tag in "${TAGS[@]}"; do
  line=$(grep -o "ok on *[0-9]*/ *[0-9]*.*hit@1: *[0-9.]*%" "logs/${tag}.console.log" | tail -n1 || true)
  echo "$tag : ${line:-NO RESULT LINE} | victim calls: $(wc -l < "logs/${tag}.tool_calls.jsonl" 2>/dev/null || echo 0)"
done; exit $fail
