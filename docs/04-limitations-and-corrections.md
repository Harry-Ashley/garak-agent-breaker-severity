# 04 · Limitations, corrections, and what we predicted vs what happened

This file exists so a reader does not have to find these things themselves.

## Corrections made after the run

### Oracle marker bug (fixed; all published tables use the fix)

The frozen oracle detected "the reply names a sensitive item" by lowercase substring match on a
marker list derived from the data: file stems, email subjects and a few paraphrases. The stem of
`notes.txt` is `notes`, an ordinary English word. Replies about requester-invented files such as
`project_notes.md`, `Private_Notes.txt`, `temp_notes.txt` and `meeting_notes_RESTRICTED.pdf` were
therefore graded as naming the real PRIVATE file.

Twelve attempts were affected: five graded L4 (`metadata_disclosure`) and seven graded L2
(`refusal_naming`) that should have been L0 or L1. The judges disagreed with the oracle on exactly
these records, which is how the bug was found.

Fix (`lab/oracle.py`, v-final.1): markers are word-bounded regular expressions, and a file whose
stem is a common word is matched only by its exact filename. No level or rule changed. All 18 oracle
tests pass. `lab/regrade.sh` re-runs the oracle and tables without re-judging; the pre-fix tables are
kept in `results/v-final.0/` for comparison.

Effect on the headline numbers: L3+ trajectories 56 → 50; "L3+ missed by garak" 16 → 11; hits at
L0 48 → 50. Five of the sixteen misses we would otherwise have reported were our error.

### Rubric v2 (post-hoc, one change, v1 kept)

Described in [03-rubric.md](03-rubric.md). The v1 numbers are published alongside v2 and the
binary-task results are from the v1 run (the binary prompt is garak's and did not change).

## Limitations

**One environment.** One fictional company, one tool set, one policy. The rubric was validated
against the oracle that was written for this environment. We designed the rubric to be
environment-neutral (it mentions no company, file or address) and the oracle to be the only
environment-specific component, but we have not run it anywhere else yet. "Universal" is a design
goal here, not a demonstrated result.

**One victim model, one attacker.** gpt-4o-mini as the agent; gpt-oss-120b as attacker and in-loop
judge. A more capable agent would refuse more and a weaker one less; the proportion of high-severity
trajectories would move.

**The high-severity layer is thin.** 727 of 852 trajectories are L0. 396 attempts made no tool call
at all and 660 of 881 tool calls were `lookup_contact`. Completed write actions: 21 calendar
invites, 5 emails, 1 share, 0 deletes (all 22 attempts blocked). One content disclosure (the VPN
password, once), one privilege grant, one L6. Any statistic computed over all attempts is mostly a
statistic about agreement on harmless cases, which is why per-level agreement is reported too.

**The external recipients are mostly near-miss domains.** The attacker did not know the company's
domain (`northwind.example`) and invented addresses on `northwind.com`, `northwindltd.com`,
`company.com`, plus `attacker@northwind.com` and `bob@northwind.com.attacker.com`. The tool result
told the agent "recipient not in directory: external" each time and the agent proceeded. We grade
that as a directory-boundary violation (L3 with benign content) because the contract is explicit
and lookalike domains are how real exfiltration looks; a reader who thinks the attacker merely
guessed wrong can read those 26 rows as L0 and the "hits below L3" number goes up, not down.

**The oracle's reply-text check is pattern-based.** Tool-call grading is deterministic and carries
the headline numbers. Reply grading uses canary matching (exact) and marker matching (word-bounded
substrings). In 16 cases all three judges said L4 and the oracle said L0. Reading them: in about
half the agent disclosed labels or counts without names ("Dana has one RESTRICTED, one CONFIDENTIAL
and one PRIVATE file"), which the oracle does not catch and the judges correctly do; in the other
half the agent echoed a requester-invented filename, which the judges cannot know is fictional.

**Claude refusals.** claude-opus-5-5 returned `stop_reason: refusal` on about 12% of first calls and
7 to 9% after three retries. This is Anthropic's input filter on the attack prompts; the identical
inputs were answered by the other judges. Its agreement numbers are over the calls it answered
(773 to 795 of 852). An earlier pilot with claude-fable-5-1 refused 10 to 25%, which is why Opus was
used.

**Duplicate prompts.** garak retries attacks; each run has 2 to 8 groups of identical prompts (up
to 6 copies). The 852 attempts correspond to roughly 790 distinct prompts. Each attempt was judged
and graded separately because the agent's response differs each time.

**Two runs were re-run.** Two of the six initial garak runs produced zero attempts: the attacker's
tool-analysis response failed to parse and garak logged "Analyzed 0 tools", "No tools to attack" and
exited 0 in about five seconds. Both were re-run sequentially and completed. We mention it because
a zero-attempt run that exits 0 is easy to miss, and because it is the kind of silent failure
garak issue #2021 describes.

**Served from DeepInfra, not NIM.** garak's default `red_team_model` endpoint returned HTTP 410. The
same model was served from DeepInfra with `stop` suppressed. Sampling settings otherwise default.

## Pre-registered hypotheses and outcomes

Written down at 12:29 ET on 2026-10-29, before any API call for the final run.

| prediction | outcome |
|---|---|
| Binary task: high hit rate on clear L4s | Yes. garak flagged 22 of 23 oracle L4s (strict). |
| Binary task: systematic misses on benign external sends, across all judges (prompt-level) | Yes. 9 of garak's 11 misses; the only miss type shared by all four judges. |
| Binary task: systematic misses on metadata disclosures | Mostly no. 1 miss of that kind after the oracle fix; the binary prompt catches reply-visible disclosures. |
| Binary false positives judge-dependent, gpt-oss > opus > astra | Partly. gpt-oss 7.5%, astra 6.9%, opus 3.3%; astra and gpt-oss closer than predicted. |
| About 15 to 20% of garak in-loop verdicts unjudged (None) | No. 5 of 852 (0.6%). |
| Severity task: opus and astra above 90% exact, kappa above 0.8 | v1: no (90% and 82%, kappa 0.63 and 0.56). v2: exact yes (97% and 96.5%), kappa yes for Opus (0.84), nearly for Astra (0.78). |
| Severity disagreement concentrated in refusal_naming and metadata_disclosure | Yes, and the reason turned out to be a rubric gap (requester-supplied names), not only a "refusal = safe" prior. |
| Few L6 | Yes. One. |
| gpt-oss-120b severity kappa 0.3 to 0.5 | Worse than predicted: 0.23 (v1), 0.27 (v2). |
| Risk: the rewritten contracts make the victim refuse nearly everything | Partly realized. 46% of attempts made no tool call. Enough write actions occurred (27) to test the question, not enough for tight intervals. |

Not predicted and found: the agent's reply denied a completed action in 19 of 27 cases; condition B
removes the misses and doubles the low-severity hits; and the default judge model does not follow
an explicit rubric instruction that the two frontier judges follow.
