"""retry_judges.py -- re-run judge calls that came back refused / empty / unparseable / truncated / error.

Patches results/all.judged.jsonl in place (a timestamped backup is written first) and records,
per judge and task, how many retries were needed.  Records that still fail after --tries attempts
keep their last status so the summary tables report them as such.

Run only after postprocess.sh has finished judging:
  python retry_judges.py --judges opus,gptoss --tries 3
Then re-run the two analyze commands (see postprocess.sh) to refresh the summaries.
"""

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

import judges as JU

RETRY_STATUSES = {"refused", "empty", "unparseable", "truncated", "error", "missing"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judged", default="results/all.judged.jsonl")
    ap.add_argument("--oracle", default="results/all.oracle.strict.jsonl")
    ap.add_argument("--garak_repo", default="~/code/garak")
    ap.add_argument("--agent_yaml", default="agent.yaml")
    ap.add_argument("--judges", default="opus,gptoss")
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    verify_template = yaml.safe_load(open(Path(a.garak_repo).expanduser() / "garak/data/agent_breaker/prompts.yaml"))["VERIFY"]
    ay = yaml.safe_load(open(a.agent_yaml))
    contracts_text = ay["agent_purpose"].strip() + "\n\nTOOLS:\n" + "\n".join(f"- {t['name']}: {t['description']}" for t in ay["tools"])

    oracle = {r["attempt_uuid"]: r for r in (json.loads(l) for l in open(a.oracle) if l.strip())}
    rows = [json.loads(l) for l in open(a.judged) if l.strip()]
    judges = [j.strip() for j in a.judges.split(",") if j.strip()]

    backup = f"{a.judged}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy(a.judged, backup)
    print(f"backup -> {backup}")

    def tally(label):
        for j in judges:
            for task in ("binary", "severity"):
                c = Counter(r["judges"].get(j, {}).get(task, {}).get("status", "missing") for r in rows)
                print(f"{label:7s} {j:7s} {task:9s} {dict(c)}")

    tally("before")

    work = [(i, j, task) for i, r in enumerate(rows) for j in judges for task in ("binary", "severity")
            if r["judges"].get(j, {}).get(task, {}).get("status", "missing") in RETRY_STATUSES]
    print(f"to retry: {len(work)} judge/task cells, up to {a.tries} tries each")

    def do(i, j, task):
        rec = oracle[rows[i]["attempt_uuid"]]
        prev = rows[i]["judges"].setdefault(j, {}).get(task, {})
        history = prev.get("retry_history", []) + [prev.get("status", "missing")]
        result, n = prev, 0
        for n in range(1, a.tries + 1):
            try:
                result = JU.judge_binary(j, rec, verify_template) if task == "binary" else JU.judge_severity(j, rec, contracts_text)
            except Exception as e:  # noqa: BLE001
                result = {"status": "error", "error": str(e)[:300]}
            if result["status"] == "ok":
                break
            history.append(result["status"])
            time.sleep(1.5)
        result["retry_history"] = history
        result["retries"] = n
        return i, j, task, result

    done = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for f in as_completed([ex.submit(do, *w) for w in work]):
            i, j, task, result = f.result()
            rows[i]["judges"][j][task] = result
            done += 1
            if done % 10 == 0 or done == len(work):
                print(f"  retried {done}/{len(work)}", file=sys.stderr)

    tmp = a.judged + ".tmp"
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    os.replace(tmp, a.judged)

    tally("after")
    recovered = Counter()
    for r in rows:
        for j in judges:
            for task in ("binary", "severity"):
                cell = r["judges"].get(j, {}).get(task, {})
                if cell.get("retry_history") and cell.get("status") == "ok":
                    recovered[(j, task, cell["retries"])] += 1
    for (j, task, n), v in sorted(recovered.items()):
        print(f"recovered {j} {task}: {v} on try {n}")
    print("written ->", a.judged)


if __name__ == "__main__":
    main()
