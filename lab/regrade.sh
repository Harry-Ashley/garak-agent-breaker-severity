#!/usr/bin/env bash
# regrade.sh -- re-run the oracle (both policies) and the analysis WITHOUT re-judging.
# Use after an oracle fix.  Judges never see the oracle, so all.judged.jsonl stays valid.
set -euo pipefail
R=~/.local/share/garak/garak_runs
mkdir -p results/v-final.0
cp results/summary.*.md results/summary.*.json results/all.oracle.*.jsonl results/v-final.0/ 2>/dev/null || true
for pol in strict lenient; do
  for t in condA_seed1 condA_seed2 condA_seed3 condB_seed1 condB_seed2 condB_seed3; do
    python oracle.py --report "$R/$t.report.jsonl" --toolcalls "logs/$t.tool_calls.jsonl" --out "results/$t.oracle.$pol.jsonl" --policy $pol
  done
  cat results/cond*.oracle.$pol.jsonl > results/all.oracle.$pol.jsonl
done
python analyze.py --oracle results/all.oracle.strict.jsonl  --judged results/all.judged.jsonl --label strict  > /dev/null
python analyze.py --oracle results/all.oracle.lenient.jsonl --judged results/all.judged.jsonl --label lenient > /dev/null
echo "previous tables kept in results/v-final.0/; new tables in results/summary.strict.md and results/summary.lenient.md"
