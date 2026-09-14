---
description: Generate or run the evaluation suite (golden questions + regression assertions) for a spec
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Grep, Glob, LS, Task
argument-hint: <feature-name> [--run]
---

# Spec Evaluation Suite

<background_information>
- **Mission**: Make correctness measurable. Turn the feature's requirements into golden questions with human-authored ground truth, so the agent's answers and artifacts can be checked instead of trusted.
- **Success Criteria**: `.sdd/specs/<feature>/evals.md` exists with 10–20 evals covering the real questions, at least one ambiguity case and one boundary case; every eval traces to a requirement ID; with `--run`, each eval reports PASS/FAIL against ground truth, read-only.
</background_information>

<instructions>
Load `.sdd/settings/rules/evals.md` before doing anything else. On data projects also load
`.sdd/settings/rules/data-readiness.md` (source ladder) and `answer-provenance.md`.

## Mode A — generate (default)

### Step 1: Read the spec and the semantics
- `.sdd/specs/$1/requirements.md` — the acceptance-criteria IDs are what the suite must cover.
- `.sdd/specs/$1/design.md` (if present) — the contracts the artifact evals assert against.
- `.sdd/steering/semantic-layer.md` (if present) — metric contracts, canonical datasets, and the
  "ambiguities to resolve out loud" list: each of those ambiguities is a candidate for an E-case
  whose correct answer is *to ask*.

### Step 2: Draft the suite from `.sdd/settings/templates/specs/evals.md`
Cover, at minimum:
- the **two or three questions people actually ask** in this domain (not synthetic ones),
- **one ambiguity case** where passing means asking for clarification,
- **one boundary case** (empty period, new entity, late-arriving data, re-run idempotency),
- **one regression case** per bug the spec exists to fix.

Each eval declares its sanctioned source and the rung of the source ladder it should use.

### Step 3: Mark the ground truth you cannot author
**You may not invent ground truth.** For every eval, either:
- point to an independent, verifiable origin (a closed report, a human-confirmed number, an
  invariant like "row count unchanged"), or
- leave it as `GROUND TRUTH NEEDED — <who can answer>` and list these at the end.

A suite where the agent authored the expected answers measures self-consistency, not correctness. Say so plainly if that is what you have.

### Step 4: Write and validate
- Write `.sdd/specs/$1/evals.md`.
- Run `py tools/spec-lint.py $1` (fallback `python3`) — it now also checks that eval references point
  to real requirement IDs and reports requirements with no eval.
- Report which requirement IDs remain uncovered by an eval and whether that is acceptable.

## Mode B — run (`--run`)

### Step 1: Backend check
Read `.sdd/steering/integrations.md` → **Data platform** row. `needs-setup` or `n/a` → stop and say
what to configure; never simulate a run.

### Step 2: Execute read-only
For each eval, in order:
- Resolve the source per the ladder; execute **read-only** queries only (`SELECT`/`COUNT`/`DESCRIBE`).
- Compare against ground truth using the eval's own pass criterion.
- An eval whose ground truth is still `GROUND TRUTH NEEDED` is reported **SKIPPED**, never PASS.

### Step 3: Adversarial pass (high-stakes evals only)
For evals tied to a metric that drives a decision, delegate a second, independent check via the Task
tool: right source · grain · population · join · denominator · period · plausible magnitude. The
reviewer must not be the agent that produced the answer. Note its verdict per eval.

### Step 4: Report and record
- Table: eval · expected · actual · PASS/FAIL/SKIPPED · source used (ladder rung).
- Update the header line of `evals.md` (`Last run` / `Result`).
- **A failing eval blocks the same gate a failing test blocks.** Do not soften it; do not auto-fix
  the expected value to match the actual — that is falsifying the suite.

## Critical Constraints
- **Read-only, always.** Evals never mutate data.
- **Ground truth is human-authored.** Marking it NEEDED is correct; inventing it is not.
- **No secrets in output.** No raw dumps of result sets — report the compared values only.
</instructions>

## Output Description
Path written, eval count by kind, the requirement IDs covered vs. uncovered, and the
`GROUND TRUTH NEEDED` list with who to ask. In `--run` mode, the result table plus a one-line verdict.

## Safety & Fallback
- **No requirements.md**: stop; run `/sdd:spec-requirements` first.
- **No semantic layer**: proceed, but flag that metric definitions are unverified and every answer
  eval is at best medium confidence.
- **Query blocked / no access**: report the exact error and mark the eval SKIPPED — never fabricate a PASS.
