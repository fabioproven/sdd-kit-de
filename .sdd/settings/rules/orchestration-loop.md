# Orchestration Loop Rules

The executor<->approver protocol for the auto-approval mode. Loaded by every `spec-impl*` profile
(`spec-impl`, `spec-impl-config`, `spec-impl-investigation`) when `.sdd/autoapprove.json` has
`enabled: true`, and by `/sdd:spec-impl-auto`, its explicit alias. Two distinct roles, a
deterministic gate between every round, and a log of every decision.

## Roles (kept separate on purpose)

- **Executor** — plans and applies a subtask. Has write access. Produces a result *plus the
  explicit exit criteria it claims to satisfy*. The executor is **the orchestrator itself** (the
  normal implementation behavior) **or**, when `delegation.enabled` is true in
  `.sdd/autoapprove.json` and the subtask's risk level is enabled there, the agent named in
  `delegation.executor` (`.claude/agents/data-engineer.md` by default) — see "Delegation" below.
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
        1. executor (self or delegated) produces result + claimed exit criteria
           (delegated: Work Order out, Work Report in)
        2. approver evaluates against the criteria -> APPROVE | REJECT | ESCALATE
        3. approval-gate.py record  (role=approver, decision, tokens, usd,
                                     note="executor=<self|agent> ...")
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

## Delegation (0.9.0) — who types is not who approves

`delegation` in `.sdd/autoapprove.json`:

```json
"delegation": {"enabled": false, "executor": "data-engineer", "low": false, "medium": true, "high": true}
```

- **Independent of `auto_approve`.** Delegation says who *executes*; the loop says who *judges*.
  Loop off + delegation on → the agent executes, the orchestrator verifies each exit criterion
  against the Work Report's evidence before marking. Loop on + delegation on → the agent executes,
  the `approver` judges, every round recorded with `executor=<agent>` in the note.
- **The gate is untouched.** `approval-gate.py check` runs before every round whoever executes;
  `high` returns `HUMAN`. Only after the human's yes — and only if `delegation.high` is true — is
  the Work Order sent. Nothing in `delegation` is read by the gate.
- **Per level.** `low` defaults to inline (cheaper than a hand-off); `medium` and `high`
  (post-approval) go to the executor. A project may flip any flag.
- **Agent missing** (`.claude/agents/<executor>.md` absent) → say so, execute inline.
- **The executor never**: marks `tasks.md`, edits `spec.json`, writes the ledger, approves, widens
  the scope, or calls another agent. It may stop early and say why; the orchestrator hands that to
  the human, never retries silently.

### Work Order (orchestrator → executor)

```markdown
## Work Order — <feature> / task <N.M>
- **Requirements:** 2.1, 2.3
- **Risk:** medium — <worst action, one line>
- **Exit criteria (pass/fail):**
  1. <criterion> — verify by: <command / check>
- **Write scope:** <catalog.schema list from .sdd/write-scope.json, or "n/a — no data platform">
- **Permitted paths:** <globs the subtask may create/edit; evidence/ is always permitted>
- **Design pointers:** design.md → <section / component names>
- **Profile:** spec-impl | spec-impl-config
- **Feedback from previous round:** <none | approver text>
```

### Work Report (executor → orchestrator)

```markdown
## Work Report — <feature> / task <N.M> — round <k>
- **Files changed:** path:lines (created | edited)
- **Commands run:** `<cmd>` → <result>; tests: <passed>/<total>
- **Evidence written:** .sdd/specs/<feature>/evidence/<what>-<date>.md | none
- **Exit criteria:** 1. met — <evidence> / 2. NOT met — <why>
- **Out of scope, observed:** <list | none>
- **Stopped early:** no | yes — <reason>
- **Environment:** hooks available | hooks not available here — write scope applied as convention
```

"met" requires evidence the approver can open. Unverified = NOT met.

## Fallback (backward compatibility)

If `.sdd/autoapprove.json` has `enabled: false` (the default), the gate returns `HUMAN` for
everything and the flow is identical to the manual `/sdd:spec-impl`. The auto mode is strictly additive.
Likewise, `delegation` absent, invalid or `enabled: false` → the executor is the orchestrator,
byte-for-byte the 0.8.0 behavior.
