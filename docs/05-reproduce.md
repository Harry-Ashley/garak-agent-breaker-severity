# 05 · Reproduce

Everything below was run on Ubuntu under WSL2 with Python 3.12. Budget: the six garak runs cost a
few dollars of gpt-4o-mini and gpt-oss-120b; the judging (852 × 3 judges × 2 tasks, plus retries
and the v2 severity pass) is the larger cost, dominated by claude-opus-5-5.

## 0. Keys

```
export OPENAI_API_KEY=...             # victim (gpt-4o-mini) and judge gpt-6-astra
export ANTHROPIC_API_KEY=...          # judge claude-opus-5-5
export OPENAICOMPATIBLE_API_KEY=...   # DeepInfra: attacker, in-loop judge and judge gpt-oss-120b
```

Type the quotes by hand if you paste from a document; a curly quote in a key produced a 524 from
Anthropic that took a while to diagnose. `preflight.py` now checks for non-ASCII characters.

## 1. Install

```
git clone https://github.com/NVIDIA/garak ~/code/garak
cd ~/code/garak && git checkout <commit in lab/GARAK_COMMIT>   # v0.17.2.pre1 on main at the time
cd <this repo>/lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ~/code/garak
```

## 2. Put the tool contract where garak reads it

```
python victim_agent.py --dump-agent-yaml > agent.yaml
mkdir -p ~/.local/share/garak/data/agent_breaker
cp agent.yaml ~/.local/share/garak/data/agent_breaker/agent.yaml
```

`agent.yaml` is generated from the victim's `TOOL_CONTRACTS`, so the two cannot drift.

## 3. Check before spending

```
python -m pytest -q test_oracle.py      # 18 tests, one per frozen rule
python preflight.py                     # keys, all four models live, victim logic, agent.yaml identical to installed copy
```

`preflight.py` must print `ALL CLEAR`.

## 4. Run garak (six runs)

```
mkdir -p logs results
nohup bash run_all.sh > logs/run_all.master.log 2>&1 &
```

`run_all.sh` launches condition A and B for seeds 1 to 3 in parallel; `bash run_all.sh A 2` runs one.
Each run writes `logs/<tag>.console.log`, `logs/<tag>.tool_calls.jsonl` and garak's
`~/.local/share/garak/garak_runs/<tag>.report.jsonl`.

**Check every run actually attacked something.** A run can finish in five seconds with exit 0 and
zero attempts if the attacker's tool-analysis JSON fails to parse (`Analyzed 0 tools` in the
console log). Count attempts:

```
for t in condA_seed1 condA_seed2 condA_seed3 condB_seed1 condB_seed2 condB_seed3; do
  printf "%-13s attempts=%s\n" "$t" "$(grep -c '"entry_type": "attempt"' ~/.local/share/garak/garak_runs/$t.report.jsonl)"
done
```

(garak writes two entries per attempt, so expect roughly double the per-run counts in the README.)
Re-run any zero with `bash run_all.sh <A|B> <seed>`.

## 5. Oracle, judges, tables

```
nohup bash postprocess.sh > logs/postprocess.log 2>&1 &     # oracle (both policies) → judges (v1, both tasks) → analyze
python retry_judges.py --judges opus,gptoss --tries 3        # re-run refused / empty / unparseable cells
python analyze.py --oracle results/all.oracle.strict.jsonl  --judged results/all.judged.jsonl --label strict
python analyze.py --oracle results/all.oracle.lenient.jsonl --judged results/all.judged.jsonl --label lenient
```

Rubric v2, severity task only, all three judges:

```
nohup python judges_v2.py > logs/judges_v2.log 2>&1 &
python analyze.py --oracle results/all.oracle.strict.jsonl  --judged results/all.judged.v2.jsonl --label strict_v2
python analyze.py --oracle results/all.oracle.lenient.jsonl --judged results/all.judged.v2.jsonl --label lenient_v2
```

If you change the oracle, `bash regrade.sh` re-grades and re-tables without re-judging (the judges
never see the oracle) and keeps the previous tables in `results/v-final.0/`.

## 6. Charts

```
python ../charts/make_charts.py
```

Reads `results/all.oracle.strict.jsonl`, `results/all.judged.jsonl`, `results/all.judged.v2.jsonl`;
writes `charts/*.png` and `charts/numbers.json`, which lists every number drawn.

## Things that went wrong, so you can skip them

- NIM endpoint for `openai/gpt-oss-120b` returns HTTP 410. Use any OpenAI-compatible host and set
  `suppressed_params: ["stop"]` in the generator config, or garak's default `stop=["#", ";"]` will
  truncate the attacker's JSON.
- Ask DeepInfra for at least 512 output tokens; gpt-oss-120b spends tokens on reasoning first and
  returns an empty string with a small budget.
- A laptop going to sleep kills the runs. `nohup` and a power setting of "never sleep".
- Judge calls on Claude: give a large `max_tokens` (8000) or truncation looks like a refusal.
