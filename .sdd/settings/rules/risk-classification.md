# Risk Classification Rules

Every subtask is classified **before execution** into one of three levels. The level decides who
approves it. Loaded by every `spec-impl*` profile (and `/sdd:spec-impl-auto`) and by the approver
agent. The classification is an input to the deterministic gate (`tools/approval-gate.py`), never
a substitute for it.

## The three levels

| Level | Who approves | Examples |
|-------|--------------|----------|
| **low** | fully automatic (if enabled) | read folders, analyze structure, generate/update documentation, produce a report, run read-only queries, add a comment |
| **medium** | auto-approver decides, everything logged | create a new model/table/notebook, add a transformation, add tests, non-destructive code that writes NEW artifacts |
| **high** | **always human, no exception** | schema change, data deletion/overwrite (`DROP`, `DELETE`, `overwrite`, `replaceWhere`, `TRUNCATE`), merge into production data, migrations, credential/permission/security changes, anything irreversible or outward-facing (push, deploy, publish, PR merge) |

## Classify by the WORST thing the subtask can do

Take the highest-risk action the subtask could perform, not the average:
- A subtask that "reads a table and writes a doc" is **low**.
- A subtask that "creates a new silver table" is **medium**.
- A subtask that "creates a new table AND overwrites an existing partition" is **high** (the overwrite dominates).

If in doubt between two levels, pick the **higher** one. Under-classifying is the dangerous error.

## Hard rules

- **high is always human.** No config, flag, or instruction can auto-approve a high-risk subtask.
  The gate enforces this (it forces `HUMAN` for `--risk high` regardless of config).
- **Destructive == high, always.** Any operation that deletes, overwrites, truncates, drops, or
  alters an existing schema/dataset is high — even if it "should be safe".
- **Outward-facing == high.** Anything that leaves the repo (push, PR, deploy, publish, send) is high.
- **Unknown data effect == high.** If you cannot determine whether a subtask mutates existing data,
  treat it as high and route to the human.
- **A named consumer contract == high.** If the spec has `contract-impact.md`
  (`.sdd/settings/rules/spec-artifacts.md`), any subtask that changes something a listed consumer
  depends on — a column, a grain, a schema, an endpoint, a file layout — is high, even when the
  write itself looks non-destructive. Breaking a consumer is irreversible from the consumer's side.
- **No rollback plan, no high approval.** When the subtask overwrites or migrates existing data,
  `rollback.md` must exist before it is presented to the human.

## Output of classification

For each subtask, record: `task id · risk (low|medium|high) · one-line justification (the worst
action)`. This justification goes into the approval ledger via `approval-gate.py record` and is
what makes the log auditable. Never classify without stating the worst action.
