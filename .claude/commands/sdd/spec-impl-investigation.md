---
description: Execute spec tasks for INVESTIGATION work — produces a findings report, not code
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Grep, Glob, LS, WebFetch, WebSearch
argument-hint: <feature-name> [task-numbers]
---

# Implementation Executor — Investigation Profile

<background_information>
- **Mission**: Execute the tasks of an *investigative* spec (root-cause, audit, discovery) whose deliverable is a documented **findings report**, not production code.
- **Why this profile exists**: The default `/sdd:spec-impl` mandates TDD ("tests before code"). Investigation work has no code to test — forcing TDD makes the checkboxes meaningless. This profile swaps the RED→GREEN→REFACTOR cycle for an **evidence cycle**.
- **Success Criteria**:
  - Every task produces a documented, sourced finding in a single authoritative artifact
  - Negative results (no problem found) are recorded as valid findings, never silently dropped
  - No production writes occur during the investigation
</background_information>

<instructions>
## Core Task
Execute investigation tasks for feature **$1**, writing results into a single `findings.md` in the spec directory.

## Execution Steps

### Step 0: Approval posture — read the config, don't ask
Read `.sdd/autoapprove.json` (missing or invalid → `enabled: false`). State the mode in one line.
- **`enabled: true`** → run the executor↔approver loop per `.sdd/settings/rules/orchestration-loop.md`
  for every selected task: atomic subtasks, risk per `risk-classification.md` (investigation tasks
  are read-only, so usually `low`), `py tools/approval-gate.py check` before every round (obey the
  exit code), the EVIDENCE cycle below as the executor's work inside a round, the `approver`
  subagent judging each finding against its threshold, `record` every verdict. No `py`/`python3` →
  say so, fall back to manual.
- **`false` or absent** → manual mode, identical to before 0.8.0.
Same loop as `/sdd:spec-impl-auto`, which remains as an explicit alias.

### Step 1: Load Context
- Read `.sdd/specs/$1/spec.json`, `requirements.md`, `design.md`, `tasks.md`
- Load the entire `.sdd/steering/` directory for project memory
- Delegate data queries to the `data-analyst` subagent when the project has a data platform
  (`integrations.md`): it follows the sampling ladder and returns distilled numbers, not dumps
- Verify tasks are approved in spec.json (stop if not)

### Step 2: Select Tasks
- If `$2` provided: execute those task numbers; otherwise all pending `- [ ]` tasks.

### Step 3: Execute with the EVIDENCE cycle
For each task, instead of TDD:

1. **QUESTION** — State the exact question the task answers and the acceptance threshold from requirements.md (e.g. "gap > 60min = data loss").
2. **GATHER** — Run the read-only queries / read the files / collect the evidence. Delegate heavy repo search to the explorer subagent so the main context stays lean. Never mutate state.
3. **INTERPRET** — Compare evidence against the threshold. State the conclusion in one sentence: confirmed / refuted / inconclusive.
4. **RECORD** — Append the result to `findings.md`: the question, the raw evidence (query result / file excerpt), the interpretation, and the source. Cite where the evidence came from.
5. **MARK COMPLETE** — Update `- [ ]` to `- [x]` in tasks.md. Keep `spec.json.phase` canonical
   (`implementation-in-progress` on the first checked task, `implementation-complete` when all are;
   nuance in `status_note` — see `.sdd/settings/rules/spec-artifacts.md`).

### Step 4: Findings integrity check
Before finishing:
- Every task maps to a section in `findings.md`.
- Every classification carries an evidence note and a source.
- Negative / healthy results are explicitly listed, not omitted.

## Critical Constraints
- **Read-only**: no writes to any external system, table, or workflow.
- **One authoritative artifact**: all tasks write to the same `findings.md`.
- **Evidence over assertion**: no conclusion without a cited source.
- **Design alignment**: follow the classification logic defined in design.md.
</instructions>

## Output Description
Concise summary (under 150 words), in the language from spec.json:
1. **Tasks executed** and the finding each produced (confirmed / refuted / inconclusive).
2. **Artifact**: path to `findings.md`, remaining task count.

## Safety & Fallback
- **Tasks not approved / missing spec files**: stop; point to the missing phase.
- **A query/read fails**: record the exact error as the finding and propose a fallback source — do not fabricate a result.
