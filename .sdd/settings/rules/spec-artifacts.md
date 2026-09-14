# Spec Artifacts & Phases

What a spec folder may contain, what each file is for, and the **one vocabulary** every command
uses for `spec.json.phase`. Loaded by `/sdd:spec-init`, `/sdd:spec-status`, the `spec-impl*`
profiles, and read by `tools/spec-lint.py` (phase check).

## Why this exists

Five months of real use produced eleven different spellings of "implemented" in `spec.json`
(`implemented`, `implementado`, `implementation-complete`, `parcialmente-implementado`, …) and
thirteen artifact names the template never anticipated (`impacto-contrato.md`, `evidencia-*.md`,
`rollback/`, `validacao.md`). Both are signs the flow works — people extend it — and both make
`spec-status` blind. This rule gives the extensions a name so tools can see them.

## Canonical phases (`spec.json.phase`)

Exactly one of these, in this order. Commands **write** them; humans should not invent others.

| Phase | Set by | Meaning |
|---|---|---|
| `initialized` | `spec-init` | folder + `spec.json` + empty `requirements.md` exist |
| `requirements-generated` | `spec-requirements` | the WHAT is written, awaiting approval |
| `design-generated` | `spec-design` | the HOW is written, awaiting approval |
| `tasks-generated` | `spec-tasks` | the plan is written, awaiting approval |
| `tasks-approved` | approval of tasks (human or `-y`) | ready for implementation |
| `implementation-in-progress` | first task checked by any `spec-impl*` | at least one `- [x]` in `tasks.md` |
| `implementation-complete` | last task checked by any `spec-impl*` | every task in `tasks.md` is `- [x]` |

Nuance that does not fit a phase (partial rollout, reconciliation pending, blocked on a business
question) goes in **`spec.json.status_note`** (free text), never in `phase`. `spec-lint` warns on an
unknown phase; `spec-status` reads `status_note` and shows it beside the phase.

The `approvals.*` flags in `spec.json` stay as they are — `phase` is the coarse position, the flags
are the gates.

## Core artifacts (the template)

| File | Written by | Role |
|---|---|---|
| `spec.json` | every phase | state machine + approvals + `status_note` |
| `requirements.md` | `spec-requirements` | the WHAT — EARS criteria with IDs `N.M` |
| `design.md` | `spec-design` | the HOW — components, contracts, traceability to `N.M` |
| `tasks.md` | `spec-tasks` | the plan — checkboxes with `_Requirements:_` lines |
| `research.md` | `spec-design` (optional) | decision log from design discovery |

## Optional artifacts (recognized by name)

Use **these names** so tools can find them. They are optional — create only what the work needs.

| File / dir | Created by | Role | Read by |
|---|---|---|---|
| `evals.md` | `spec-evals` | golden questions + regression assertions, human ground truth | `spec-lint` (`--require-evals`), `data-quality` |
| `findings.md` | `spec-impl-investigation` | the single authoritative report of an investigation | `spec-status` |
| `contract-impact.md` | design or impl, when a **consumer** is affected | which downstream consumers (dashboards, APIs, other pipelines) depend on what this spec changes; what breaks, who owns it, what the migration is | **`risk-classification`**: any task touching a listed contract is `high` |
| `evidence/` | any `spec-impl*` | proof that a step ran: query results, row counts, reconciliation tables, baselines, pilot results — one file per run, named `<what>-<YYYY-MM-DD>.md` | `spec-status` (lists them), `report-validator` (as source) |
| `rollback.md` | design or impl, when the change is not trivially reversible | how to undo: commands, restore points, order of operations, who can execute | the human at the `high` gate |
| `approval-log.jsonl` | `approval-gate.py` | ledger of the executor↔approver loop | `approval-gate.py summary`, `spec-status` |

Rules:
- **Every file in `evidence/` carries provenance** (source · freshness · validation · confidence,
  per `answer-provenance.md`) and the date it was measured. Evidence without a date ages silently.
- **`contract-impact.md` is a risk input, not paperwork.** If it names a consumer, the tasks that
  touch that consumer's contract are `high` — the gate forces a human even with auto-approval on.
- **`rollback.md` is required before any `high` task runs** when the change overwrites or migrates
  existing data. No rollback plan, no approval.
- `spec-lint` ignores every optional artifact except `evals.md` — they never affect traceability.

## Anti-patterns

- Inventing a new phase string to express nuance. Use `status_note`.
- Naming evidence ad hoc (`validacao.md`, `verification.md`, `resultado-x.md`). Put it in
  `evidence/` with a date, so the next person — and `spec-status` — can find it.
- A `contract-impact.md` that lists no consumer. If nothing consumes it, don't create the file.
