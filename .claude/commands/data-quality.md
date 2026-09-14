---
description: Define and run data-quality checks against a target table/dataset on the project's data platform
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
argument-hint: <table-or-dataset> [--spec <feature>]
---

# Data Quality Checks

<background_information>
- **Mission**: Assert that a data asset is correct — schema, completeness, uniqueness, ranges, freshness — on whatever data platform the project uses, without mutating data.
- **Success Criteria**: A defined, re-runnable DQ check set for the target, executed read-only, with pass/fail per assertion and a clear summary.
</background_information>

<instructions>
Load `.sdd/settings/rules/data-readiness.md` first — it defines the source ladder and the
Agent-Ready Dataset checklist this command reports against.

## Step 1: Applicability & backend
Read `.sdd/steering/integrations.md` → **Data platform** row.
- `n/a` (no data platform) → this command does not apply; tell the user and stop.
- `mcp-native` → run queries via that MCP server (Databricks, BigQuery, Snowflake, etc.).
- `cli` → use the named CLI (`databricks`, `bq`, `snowsql`, `psql`).
- `needs-setup` → stop; name the integration to configure. Do not guess.

## Step 2: Scope the target
- Target = `$1` (a table/dataset). If `--spec <feature>` is given, read that spec's design for the
  intended schema, keys, and partitioning to check against.
- Read steering (`database.md` / `structure.md`) for canonical naming, key columns, partition scheme.
- Read `.sdd/steering/semantic-layer.md` if present: if the target backs a metric contract, its
  grain and population filter are assertions too — check them, not just the physical schema.
- **If several datasets could be "the" target** (`orders`, `orders_v2`, `orders_final`), do not pick
  one. Name the candidates and ask which is canonical — ambiguity is the finding.

## Step 3: Define the check set
Generate assertions appropriate to the target (only those that apply):
- **Schema** — expected columns and types present; no unexpected drift.
- **Completeness** — no NULLs in required/key columns.
- **Uniqueness** — primary/merge key has no duplicates after dedup.
- **Range / domain** — numeric/enum columns within valid bounds (e.g. quantity ≥ 0).
- **Referential** — foreign keys resolve (where applicable).
- **Freshness** — latest partition/timestamp within the expected SLA window.
- **Row-count expectation** — vs a baseline when the change should preserve counts.

## Step 4: Run read-only and report
- Execute each assertion as a **read-only** query (`SELECT`/`COUNT`/`DESCRIBE`). Never write, drop, or overwrite.
- For each: assertion, query, result, PASS/FAIL, and the threshold that decided it.
- Summarize: N passed / M failed; list every failure with the offending value.

## Step 5: Agent-readiness verdict
Beyond pass/fail per assertion, answer the question that decides whether an agent may use this
dataset at all — the checklist in `data-readiness.md`: canonical · grain documented · owner ·
freshness · quality · semantics · lineage · access. Report it as a short checklist with the gaps
named. **Missing grain or missing owner is a blocker**, not a warning: say so.

## Step 6: Persist (optional)
- If the project has a DQ config location, offer to save the check set there (following its format) so it can run in CI. Do not invent a framework the project doesn't use.
- If the spec has an eval suite (`.sdd/specs/<feature>/evals.md`), offer to promote the durable
  assertions into it as artifact evals, so they re-run as regressions (`/sdd:spec-evals`).

## Critical Constraints
- **Read-only** — DQ never mutates data. No non-SELECT statements. Respect any read-only env (e.g. PROD).
- **No secrets** in output.
- **Platform-correct SQL** — dialect matches the backend (Databricks SQL vs BigQuery Standard SQL vs …).
</instructions>

## Output Description
Backend + target, the assertion table (name · result · threshold), a pass/fail summary with failures
detailed, and the agent-readiness checklist with its gaps. Close with the provenance footer from
`.sdd/settings/rules/answer-provenance.md` (source · freshness · validation · confidence).

## Safety & Fallback
- **Target not found**: report it; list candidate names from steering.
- **Query blocked / no access**: record the exact error and which assertion could not run — do not fabricate a pass.
