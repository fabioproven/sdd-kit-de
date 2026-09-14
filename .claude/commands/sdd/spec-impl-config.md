---
description: Execute spec tasks for CONFIG / INFRA work — validation via dry-run, not unit TDD
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Grep, Glob, LS
argument-hint: <feature-name> [task-numbers]
---

# Implementation Executor — Config / Infra Profile

<background_information>
- **Mission**: Execute tasks whose deliverable is **configuration or infrastructure** (pipeline JSON, CI YAML, IaC, manifests, schema files) — where "a failing unit test first" does not fit, but a validation gate still must exist.
- **Why this profile exists**: The default `/sdd:spec-impl` assumes application code + unit TDD. Config work is verified by **schema/lint/dry-run**, not by a red test. This profile keeps a real "prove it before done" gate without pretending config has unit tests.
- **Success Criteria**:
  - Every config change passes a validator (schema check, linter, plan/dry-run) before its task is marked done
  - Changes follow the canonical shapes documented in steering — no invented structures
  - No apply to production; validation only
</background_information>

<instructions>
## Core Task
Execute config/infra tasks for feature **$1**, gating each on a validation step.

## Execution Steps

### Step 0: Approval posture — read the config, don't ask
Read `.sdd/autoapprove.json` (missing or invalid → `enabled: false`). State the mode in one line.
- **`enabled: true`** → run the executor↔approver loop per `.sdd/settings/rules/orchestration-loop.md`
  for every selected task: atomic subtasks, risk per `risk-classification.md`,
  `py tools/approval-gate.py check` before every round (obey the exit code), the VALIDATE cycle
  below as the executor's work inside a round, the `approver` subagent judging each result,
  `record` every verdict. `high` is always human. No `py`/`python3` → say so, fall back to manual.
- **`false` or absent** → manual mode, identical to before 0.8.0.
Same loop as `/sdd:spec-impl-auto`, which remains as an explicit alias.

### Step 1: Load Context
- Read `.sdd/specs/$1/spec.json`, `requirements.md`, `design.md`, `tasks.md`
- Load `.sdd/steering/` for canonical config conventions (naming, cluster/env shapes, placeholders)
- Read `contract-impact.md` and `rollback.md` if present (`.sdd/settings/rules/spec-artifacts.md`):
  a task touching a listed consumer contract is `high`; an overwrite/migration with no `rollback.md`
  does not run
- Verify tasks are approved in spec.json (stop if not)

### Step 2: Select Tasks
- If `$2` provided: those task numbers; otherwise all pending `- [ ]`.

### Step 3: Execute with the VALIDATE cycle
For each task:

1. **MIRROR** — Find the closest analogous existing config and mirror its structure. Never invent a new shape when a canonical one exists (steering names it).
2. **WRITE** — Make the minimal change the task requires. Use placeholders for env-specific values (never hardcode secrets, accounts, or IDs).
3. **VALIDATE** — Run the available check and paste its output:
   - JSON/YAML: parse + schema-validate.
   - IaC: `plan` / dry-run (never `apply`).
   - Pipelines/manifests: the project's lint/validate command.
   If no validator exists, at minimum assert the file parses and diff it against the mirrored reference.
4. **VERIFY AGAINST DESIGN** — Confirm the change matches the design's contract and the steering checklist.
5. **MARK COMPLETE** — Update `- [ ]` to `- [x]` in tasks.md. Keep `spec.json.phase` canonical
   (`implementation-in-progress` on the first checked task, `implementation-complete` when all are;
   nuance in `status_note`). Validation output that proves the step (dry-run result, row counts,
   reconciliation) goes in `evidence/<what>-<YYYY-MM-DD>.md` with provenance.

## Critical Constraints
- **No production apply / deploy** — validation and dry-run only.
- **No hardcoded secrets or env-specific IDs** — placeholders resolved by the deploy pipeline.
- **Canonical shapes only** — mirror steering; propose new shapes in a PR, don't improvise.
- **Design alignment**: the config must satisfy the contracts in design.md.
</instructions>

## Output Description
Concise summary (under 150 words), in the language from spec.json:
1. **Tasks executed**, and the validation result for each (parsed / schema-ok / plan-clean).
2. **Status**: files changed, remaining task count.

## Safety & Fallback
- **Validation fails**: stop; fix the config before marking the task done.
- **No validator available**: state that explicitly, fall back to parse + reference diff, and flag it as a gap for the reviewer.
