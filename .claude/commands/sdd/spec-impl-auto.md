---
description: Implement spec tasks with the automatic executor<->approver loop, risk-gated and logged
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Grep, Glob, LS, Task, WebFetch, WebSearch
argument-hint: <feature-name> [task-numbers]
---

# Auto-Approval Implementation Orchestrator

<background_information>
- **Mission**: Reduce human approvals by letting a separate **approver** agent auto-approve low/medium-risk subtasks against objective exit criteria — while keeping every safety guardrail, never touching high-risk without a human, and making infinite loops impossible.
- **Success Criteria**: Subtasks are small and atomic; each passes the deterministic gate before every round; high-risk always escalates; every decision is logged; behavior is identical to manual `/sdd:spec-impl` when the mode is off.
</background_information>

<instructions>
## Step 0: Load config and check the master switch
- Read `.sdd/autoapprove.json` (fallback: the template default). Read the rules:
  `.sdd/settings/rules/orchestration-loop.md` and `.sdd/settings/rules/risk-classification.md`.
- **If `auto_approve.enabled` is false → announce fallback and defer to manual `/sdd:spec-impl`.**
  Do not run the loop. This preserves the existing behavior exactly.

## Step 1: Load spec context
- Read `.sdd/specs/$1/spec.json`, `requirements.md`, `design.md`, `tasks.md`, and all `.sdd/steering/`.
- Verify tasks are approved (stop if not).

## Step 2: Decompose into atomic subtasks
- For the selected tasks (`$2`, else all pending), break each into **small, atomic subtasks** with a
  single checkable outcome. Smaller = easier to approve objectively and safer.

## Step 3: For each subtask — classify, then run the gated loop
1. **Classify risk** (low | medium | high) per `risk-classification.md`, by the *worst* action it can
   do; state the one-line justification.
2. **Gate check** (deterministic — obey the exit code):
   `py tools/approval-gate.py check --feature $1 --task <id> --risk <level>`
   (use `python3` if `py` is unavailable)
   - exit 3 (HUMAN) → present the subtask to the user for manual approval; record; continue.
   - exit 2 (ESCALATE) → hand to the user with the reason; record; continue.
   - exit 0 (CONTINUE) → run one round:
3. **One round (only on CONTINUE):**
   a. **Executor**: produce the plan/result for the subtask **plus the explicit, verifiable exit
      criteria** it claims to satisfy (from `_Requirements:_`, design contracts, tests, `spec-lint`).
   b. **Approver**: invoke the `approver` subagent (Task tool) with the subtask, its exit criteria,
      the result, and the risk level. It returns `APPROVE | REJECT | ESCALATE`.
   c. **Record**: `py tools/approval-gate.py record --feature $1 --task <id> --risk <level>
      --role approver --decision <APPROVE|REJECT|ESCALATE> --tokens <est> --usd <est> --note "<why>"`
   d. **Act on the verdict:**
      - APPROVE → apply/commit the subtask; `record ... --role executor --decision APPLIED`; next subtask.
      - REJECT → give the approver's feedback to the executor and **loop back to step 3.2 (gate check)**.
      - ESCALATE → hand to the user; record; stop this subtask.

## Step 4: Summary
- Run `py tools/approval-gate.py summary --feature $1` and relay it: subtasks done, auto-approved vs
  escalated, iterations, and estimated cost.

## Critical Constraints
- **The gate decides limits, not you.** Every round starts with `check`; never proceed past a non-zero exit.
- **high risk is always human** — no exception, regardless of config.
- **Executor and approver are separate** — never let the executor approve its own work; always call the `approver` subagent.
- **No exit criterion that isn't pass/fail** — if it's subjective, escalate.
- **Log every decision** — if it isn't recorded, it didn't happen.
- **TDD still applies** to code subtasks (use the right impl profile's discipline).
</instructions>

## Output Description
Per subtask: risk + gate decision + verdict + action. End with the ledger summary and the count of
human escalations. Language from spec.json.

## Safety & Fallback
- **Config missing/invalid** → the gate returns safe defaults / HUMAN; proceed manually.
- **`py`/`python3` missing** → cannot enforce the gate deterministically; **stop and fall back to
  manual `/sdd:spec-impl`** rather than run the loop unguarded.
- **Approver keeps rejecting** → the iteration cap escalates to the human automatically; that is by design.
