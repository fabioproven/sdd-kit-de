# Orchestration Loop Rules

The executor<->approver protocol for the auto-approval mode. Loaded by every `spec-impl*` profile
(`spec-impl`, `spec-impl-config`, `spec-impl-investigation`) when `.sdd/autoapprove.json` has
`enabled: true`, and by `/sdd:spec-impl-auto`, its explicit alias. Two distinct roles, a
deterministic gate between every round, and a log of every decision.

## Roles (kept separate on purpose)

- **Executor** — plans and applies a subtask. This is the normal implementation behavior. Has write
  access. Produces a result *plus the explicit exit criteria it claims to satisfy*.
- **Approver** — a separate agent (`.claude/agents/approver.md`) with its own prompt and **no write
  access**. Its only job: check the result against the subtask's verifiable exit criteria and return
  `APPROVE` / `REJECT (feedback)` / `ESCALATE (reason)`. It cannot implement — only judge.

Separation matters: the agent that did the work does not grade its own work.

## Decompose first

Before any execution, break the objective into **small, atomic subtasks** — each with a single,
checkable outcome. Smaller subtasks are easier for the approver to validate objectively and reduce
drift. Each subtask runs the loop independently.

## Explicit, verifiable exit criteria (no subjective approval)

A subtask cannot enter the loop without a checklist of **objective** exit criteria, derived from:
- the acceptance-criteria IDs it maps to (`_Requirements:_`),
- the design contracts it must honor,
- concrete checks: tests pass, `spec-lint` clean, schema/row-count assertion, file exists, diff scoped.

"Looks good" is not an exit criterion. If a criterion cannot be stated as pass/fail, the subtask is
not ready for the auto loop — route it to the human.

## The loop (per subtask)

```
classify risk  ->  approval-gate.py check
   HUMAN     -> hand to human (manual approval), record, done
   ESCALATE  -> hand to human, record, done
   CONTINUE  -> run one round:
        1. executor produces result + claimed exit criteria
        2. approver evaluates against the criteria -> APPROVE | REJECT | ESCALATE
        3. approval-gate.py record  (role=approver, decision, tokens, usd, note)
        4. APPROVE  -> apply/commit subtask, record APPLIED, next subtask
           REJECT   -> feed feedback to executor, loop back to `check`
           ESCALATE -> hand to human, done
```

**Every round begins with `approval-gate.py check` and obeys its exit code.** The gate — not the
model — decides when iterations or budget are exhausted. Never proceed past a non-zero exit.

## Guardrails (enforced by the gate, not by good intentions)

- **Max iterations per subtask** (default 5, `.sdd/autoapprove.json`): the gate counts approver verdicts in the ledger; at
  the cap it returns `ESCALATE`. This is the hard stop against infinite loops.
- **Token/cost ceiling per subtask**: best-effort — the orchestrator records estimated tokens/usd per
  round; the gate escalates when the recorded total crosses the ceiling. Record honestly.
- **high risk / master off / level not enabled** -> the gate returns `HUMAN`; the loop never starts.

## Logging (observability is mandatory)

Every `check` and every `record` writes to `.sdd/specs/<feature>/approval-log.jsonl`:
who decided (executor/approver/human), the decision, risk level, iteration, tokens, cost, and a note.
`approval-gate.py summary --feature <f>` rolls it up. If it is not in the log, it did not happen —
never auto-approve without recording.

## Fallback (backward compatibility)

If `.sdd/autoapprove.json` has `enabled: false` (the default), the gate returns `HUMAN` for
everything and the flow is identical to the manual `/sdd:spec-impl`. The auto mode is strictly additive.
