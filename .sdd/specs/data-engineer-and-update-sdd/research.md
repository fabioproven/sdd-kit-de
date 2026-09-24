# Research & Design Decisions

## Summary
- **Feature**: `data-engineer-and-update-sdd` (SDD Kit 0.9.0)
- **Discovery Scope**: Extension of an existing system (the kit's own engine)
- **Key Findings**:
  - Every specialist agent shipped up to 0.8.0 reads or judges; none writes. The "executor" of the
    executor↔approver loop is the orchestrator's own prompt, not an agent.
  - `kit-sync.py` already computes a layer-2 gap table (`layer2_gaps`) at install time and writes it
    to `UPGRADE.md`, but it is existence-only, not versioned, and has no machine-readable output.
  - The real test bed exists: `workspace_export/` carries engine 0.8.0 over a 0.1.0 project layer,
    exactly the debt `/update-sdd` must close without re-running `setup-sdd`.

## Research Log

### Why the orchestrator "works little as an engineer"
- **Context**: user observation after five months of use.
- **Sources Consulted**: `.claude/agents/*.md`, `spec-impl.md` Step 0/3, `orchestration-loop.md`.
- **Findings**: the loop defines two roles (executor with write access, approver without) but only
  the approver is an agent file. The executor is "the normal implementation behavior" of the main
  thread. Subagents cannot spawn subagents in Claude Code, so the main thread is structurally the
  orchestrator; the fix is to give it an engineer teammate, not to make it "more engineer".
- **Implications**: the new agent must be the executor of the *existing* loop, called from the
  commands people already run (`spec-impl`, `spec-impl-config`), gated by config. No new command.

### What the update path already has
- **Context**: `/update-sdd` must not duplicate `kit-sync.py`.
- **Findings**: `preflight` (backup) and `finish` (manifest, preservation, `UPGRADE.md`) exist.
  `layer2_gaps()` checks five steering files, three CLAUDE.md phrases, and `evals.md` per spec.
  The report's "Próximo passo" always points to `setup-sdd`.
- **Implications**: add an `audit` subcommand that generalizes `layer2_gaps()` into a versioned
  check table with JSON output; make `finish` call it so the report and the command read the same
  truth. Routing text becomes: first install → `setup-sdd`; upgrade → `/update-sdd`.

### Do PreToolUse hooks apply to subagent tool calls?
- **Context**: Req 3.3 — the write-guard must bound the delegated executor.
- **Findings**: Claude Code hooks are session-level and fire for tool calls made by subagents
  launched via the Task tool; this is the documented behavior but has not been proven inside this
  kit. Treated as an **open question to verify in implementation** (task 3.5), with the agent
  prompt applying the scope as convention regardless (Req 3.4).
- **Implications**: if verification fails, the fallback is already in place (convention + the
  orchestrator's review of the work report); the requirement text stays true either way because
  it is conditioned on "where the hook is enabled".

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Delegation inside `spec-impl*`, config-gated | New agent is the executor of the existing loop | No new command; off by default; reuses gate + ledger | Two config keys to keep coherent (`auto_approve`, `delegation`) | **Selected** — same lesson as 0.8.0 ("the parallel command does not exist") |
| New `/sdd:spec-impl-squad` command | Separate command that runs a multi-agent implementation | Clean separation | Exactly the `spec-impl-auto` trap: five months unused | Rejected |
| `/update-sdd` as a skill | Conversational, like `setup-sdd` | Consistent with setup | Skills trigger on intent; the user asked for a named command they can run on demand | Rejected — command at top level, like `/prepare-pr` |
| Audit as a new tool `kit-audit.py` | Standalone script | Small file | Second source of truth next to `kit-sync.finish`; both installers would need a new call | Rejected — subcommand of `kit-sync.py` |
| Audit as prompt instructions in `/update-sdd` | Model inspects and decides | No code | Non-deterministic; violates "guardrail determinístico > instrução no prompt" | Rejected |

## Design Decisions

### Decision: Delegation config lives in `autoapprove.json`
- **Context**: where a project decides who executes.
- **Alternatives Considered**: (1) new `.sdd/squad.json`; (2) a `delegation` block inside `autoapprove.json`.
- **Selected Approach**: (2). `autoapprove.json` already answers "how does execution run here"; a
  second file would split one decision in two.
- **Rationale**: one place, one read in Step 0, one line of status output.
- **Trade-offs**: the file name says "autoapprove" and now also configures delegation; the
  `_comment` explains it. Renaming the file would be a MAJOR change — not worth it.
- **Follow-up**: `/update-sdd` adds the missing `delegation` block to existing files (Req 5.5).

### Decision: `high` after human approval is executed through the delegated path
- **Context**: Req 1.4. Delegation is about *who types*, approval is about *who decides*.
- **Selected Approach**: per-level flags `low`, `medium`, `high` in `delegation`. Defaults when
  enabled: `low: false` (cheaper to do inline), `medium: true`, `high: true` (execute after the
  human said yes). The gate is untouched: it still forces `HUMAN` for high.
- **Trade-offs**: a project can set `high: false` to keep the orchestrator typing high changes.

### Decision: the work order / work report are prose contracts, not JSON
- **Context**: what crosses the boundary between orchestrator and `data-engineer`.
- **Selected Approach**: two fixed markdown blocks with named fields, defined once in
  `orchestration-loop.md` and mirrored in the agent prompt. The approver already consumes
  "result + claimed exit criteria"; the work report is that, with fields.
- **Rationale**: agents exchange text; a fixed shape is enough for the approver to check
  criterion by criterion and for the ledger note to be filled deterministically.

### Decision: CLAUDE.md is patched section by section, never rewritten
- **Context**: Req 5.6/5.7. The project's `CLAUDE.md` is hand-written; it is the one file the kit
  never overwrites.
- **Selected Approach**: the audit reports *which* template section is missing or stale
  (by heading + marker phrase); `/update-sdd` builds a patch for that section only from
  `CLAUDE.md.template`, shows the diff, and writes after confirmation. Section identity comes from
  the template's `## ` headings; project-added sections are never touched.
- **Trade-offs**: a project that renamed template headings will see "missing section" — the
  command must then ask, not insert a duplicate.

## Risks & Mitigations
- Delegation fragments context (the engineer starts blank) — mitigated by the work order carrying
  the design pointers and by `design.md` being the contract between roles, not chat.
- Extra latency/cost per subtask — mitigated by `low: false` default and by delegation being off.
- Audit false positives on heavily customized `CLAUDE.md` — mitigated by marker phrases that are
  specific (the three already in `layer2_gaps`) and by the command asking before inserting.

## References
- `.sdd/settings/rules/orchestration-loop.md` — the loop this release gives a real executor.
- `tools/kit-sync.py` `layer2_gaps()` — the seed of the audit.
- Memory: "comando paralelo não existe" (0.8.0 lesson) — why nothing here is a new command except `/update-sdd`, which is invoked on demand by name.
