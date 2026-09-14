---
description: Validate spec traceability (requirement coverage and reference integrity)
allowed-tools: Bash, Read, Glob
argument-hint: <feature-name> | --all
---

# Spec Traceability Linter

<background_information>
- **Mission**: Deterministically verify the traceability matrix that the SDD flow otherwise checks only by convention — closing the gap where a requirement can silently lose its task.
- **Success Criteria**:
  - Every requirement ID (N.M) is covered by at least one task
  - Every `_Requirements:_` reference in tasks.md points to an ID that exists
  - Orphan sub-tasks (no requirement reference) are surfaced
  - When `evals.md` exists: its references resolve, requirements with no eval are named, and evals still missing ground truth are flagged
</background_information>

<instructions>
## Core Task
Run the traceability validator against feature **$1** (or all specs with `--all`) and report the result.

## Execution Steps

1. **Locate the validator**: `tools/spec-lint.py` at the repo root.
2. **Run it** via Bash, using whichever Python launcher exists (`py` on Windows, else `python3`):
   - Single spec: `py tools/spec-lint.py $1` (fallback `python3 tools/spec-lint.py $1`)
   - All specs: `py tools/spec-lint.py --all`
   - Add `--require-evals` when the project mandates an eval suite (a spec without `evals.md`, or a
     requirement without an eval, then fails instead of warning). Without the flag, a spec that has
     no `evals.md` behaves exactly as before.
3. **Relay the report** to the user verbatim (it is already concise and human-readable).
4. **On failure (exit 1)**: do NOT auto-fix. Explain which of the two artifacts is wrong:
   - *Uncovered IDs / whole requirements* → `tasks.md` is missing tasks, or `requirements.md` has criteria nobody planned for. Re-run `/sdd:spec-tasks` or trim the requirement.
   - *Dangling references* → a task cites an ID that does not exist. Fix the `_Requirements:_` line or add the missing requirement.
   - *Eval findings* → a requirement has no golden question, or an eval cites a dead ID. Re-run
     `/sdd:spec-evals`. Never silence it by deleting the eval.

## When to run
- After `/sdd:spec-tasks`, before approving the tasks gate.
- In CI, as a required check on any spec change (exit code 1 fails the build).

## Important Constraints
- Read-only. The linter never edits specs.
- No external dependencies — pure Python 3.7+ stdlib.
</instructions>

## Output Description
Relay the validator's report and end with the next action:
- **PASS** → "Traceability validated — safe to approve the tasks gate."
- **FAIL** → list the specific IDs at fault and the artifact to fix.

## Safety & Fallback
- **Python not found**: report it and point the user to install Python 3, or run the check manually.
- **No spec found**: list available specs under `.sdd/specs/`.
