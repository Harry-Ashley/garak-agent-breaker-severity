#!/usr/bin/env bash
# postprocess.sh -- oracle (both policies), judges, analysis.  Run after run_all.sh.
set -euo pipefail
R=~/.local/share/garak/garak_runs
for pol in strict lenient; do
  for t in condA_seed1 condA_seed2 condA_seed3 condB_seed1 condB_seed2 condB_seed3; do
    python oracle.py --report "$R/$t.report.jsonl" --toolcalls "logs/$t.tool_calls.jsonl" --out "results/$t.oracle.$pol.jsonl" --policy $pol
  done
  cat results/cond*.oracle.$pol.jsonl > results/all.oracle.$pol.jsonl
done
python judges.py --oracle results/all.oracle.strict.jsonl --out results/all.judged.jsonl --garak_repo ~/code/garak --workers 6
python analyze.py --oracle results/all.oracle.strict.jsonl  --judged results/all.judged.jsonl --label strict  > /dev/null
python analyze.py --oracle results/all.oracle.lenient.jsonl --judged results/all.judged.jsonl --label lenient > /dev/null
echo "wrote results/summary.strict.md and results/summary.lenient.md"
