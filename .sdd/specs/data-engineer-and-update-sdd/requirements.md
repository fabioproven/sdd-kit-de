# Requirements Document

## Project Description (Input)
SDD Kit 0.9.0 — two deliverables that come from the same diagnosis: the agent that runs the kit
today works as an orchestrator, and the only specialist agents it has are readers and judges
(`code-explorer`, `data-analyst`, `report-validator`, `approver`). Nobody *builds* except the
orchestrator itself, with no engineer identity, no dedicated context and no permission boundary.

1. **A delegated `data-engineer` executor.** The first member of a data squad: the role that writes
   pipeline code and SQL inside `spec-impl` / `spec-impl-config`, receives a work order with
   explicit exit criteria, is bounded by the write scope, and returns a work report that the
   approver (or the orchestrator) judges. It is the executor half of the executor↔approver loop
   made into a real agent. It ships **off** — the orchestrator keeps executing until a project
   turns delegation on. Further squad roles (analytics engineer, data quality, platform) are
   explicitly out of scope: this version proves that delegated writing works end to end first.

2. **`/update-sdd` — incremental project-layer update.** When a project already has the kit
   installed (any older version) and the engine is upgraded, the project layer (`CLAUDE.md`,
   steering, configs, specs) falls behind: stale gate-by-phase text, missing steering files,
   config files without the keys newer versions added, specs without evals. Today the only
   remedy is re-running `setup-sdd` from scratch, which re-asks everything the project already
   answered. `/update-sdd` reads a deterministic audit of what is missing or stale, and closes
   **only** those gaps, additively, without re-doing the project — never overwriting what exists.

## Introduction

This specification covers SDD Kit release 0.9.0. It has two independent halves that share one
release: a **delegated executor role** for implementation work, and an **incremental update
path** for projects that upgrade the engine over an older installation.

Both halves must respect the kit's invariants: WHAT/HOW separation, ID traceability, gates by
risk with `high` always human, a project-agnostic engine, and strictly reversible additions
(every new mode ships off, with the previous behavior as fallback).

Subjects used in the acceptance criteria:

- **the implementation command** — the `spec-impl` family of commands that execute approved tasks.
- **the delegated executor** — the new `data-engineer` role that performs a subtask when delegation is on.
- **the upgrade audit** — the deterministic, read-only check of what the project layer owes the installed engine.
- **the update command** — `/update-sdd`.
- **the setup skill** — the existing conversational bootstrap of the project layer.
- **the installer** — the scripts that copy the engine into a target project.
- **the orchestrator instruction file** — the project's top-level agent instructions (the kit's template for it and the project's filled-in copy).
- **the project layer** — the orchestrator instruction file plus the generated steering, configs and specs of a target project.

## Requirements

### Requirement 1: Delegated execution by the data-engineer role
**Objective:** As a data engineer using the kit, I want implementation subtasks executed by a dedicated engineer role with its own context and boundaries, so that the orchestrator stops doing the building itself and the executor↔approver separation becomes real.

#### Acceptance Criteria
1. While delegation is disabled or its configuration is missing or invalid, the implementation command shall execute every subtask exactly as it does in kit 0.8.0, with the orchestrator as executor.
2. When delegation is enabled and a subtask is classified at a risk level for which delegation is enabled, the implementation command shall hand that subtask to the delegated executor as a work order that states the subtask identifier, the requirement identifiers it maps to, the objective exit criteria, the risk level and its justification, the permitted write scope, and the design elements the subtask must honor.
3. When delegation is enabled and a subtask is classified at a risk level for which delegation is disabled, the implementation command shall execute that subtask itself, as in Requirement 1.1.
4. When a `high` subtask is presented to the human and the human approves it, the implementation command shall execute it through the same path as a delegated subtask of that level, and delegation shall never change who approves a subtask.
5. When the delegated executor finishes a work order, it shall return a work report that lists the files it changed, the commands it ran with their results, the evidence it wrote, each exit criterion marked met or not met with the evidence for that mark, and any observation outside the work order's scope.
6. The delegated executor shall never mark a task as complete, change the specification state, approve its own work, or expand the work order's scope.
7. If the delegated executor determines that completing the work order requires an action of higher risk than the work order declares, it shall stop without performing that action and return the reason in its work report.
8. The delegated executor shall confine every write it performs to the declared write scope for data targets and to the paths the work order permits, and if a required write falls outside them it shall stop and report instead of writing.
9. While the auto-approval loop is enabled, when the delegated executor returns a work report, the implementation command shall submit that report to the approver under the existing loop and record the round in the approval ledger with the executor identified as the delegated role.
10. While the auto-approval loop is disabled, when the delegated executor returns a work report, the implementation command shall verify each exit criterion against the report's evidence before marking the task complete.
11. The investigation profile of the implementation command shall not delegate to the delegated executor, and shall keep routing data access through the read-only analysis role.
12. The delegated executor shall read the project's steering, the specification's design, and the write scope before acting, and shall treat a metric with no contract in the steering as undefined rather than improvising it.

### Requirement 2: Delegation is configured, reversible and visible
**Objective:** As a project owner, I want delegation to be an explicit, per-project decision that ships off, so that upgrading the kit never changes how my project executes work until I say so.

#### Acceptance Criteria
1. The SDD Kit shall ship with delegation disabled.
2. The delegation posture shall be read from the same project configuration that governs auto-approval, with one flag per risk level, so that a project has a single place to decide how execution runs.
3. When the implementation command starts, it shall state in one line which executor mode it is in (orchestrator or delegated, and for which levels) before touching anything.
4. If the delegation configuration names an executor role that is not installed in the project, the implementation command shall say so and fall back to executing the subtask itself.
5. When the engine is installed or upgraded over an existing project configuration, the installer shall leave the existing configuration untouched.

### Requirement 3: Project-layer awareness of the new role
**Objective:** As a project owner, I want the project layer to know the delegated executor exists and how it is bounded, so that the role is actually used and its guardrails hold where hooks run.

#### Acceptance Criteria
1. The orchestrator instruction file template shall contain a routing line that sends implementation subtasks to the delegated executor when delegation is enabled, and shall say that the routing is inert while delegation is disabled.
2. When the setup skill reaches the guardrails step, it shall offer delegation as an opt-in with a recommended posture and shall state what enabling it changes.
3. Where the write-scope hook is enabled in a project, the hook shall apply to commands issued by the delegated executor exactly as it applies to commands issued by the orchestrator.
4. The delegated executor shall apply the write scope as a convention in environments where hooks do not run, and shall say so in its work report when it operated in such an environment.

### Requirement 4: Deterministic upgrade audit
**Objective:** As a maintainer upgrading a project, I want a deterministic, read-only audit of what the project layer owes the installed engine, so that what needs updating is a fact computed from disk, not an opinion of the model.

#### Acceptance Criteria
1. When invoked against an installed project, the upgrade audit shall list every project-layer gap with what is missing or stale, the engine version that introduced the expectation, the command or action that closes it, and a severity of blocking, recommended or optional.
2. The upgrade audit shall detect at least: missing core steering files; missing integrations and inherited-knowledge steering; an orchestrator instruction file that still contains template placeholders; gate-by-phase wording from before risk gates; instructions to use the standalone auto-loop command; missing routing to the agents the installed engine ships; sections the current template introduced that the project's file lacks; project configuration files missing keys that later engine versions added; engine files awaiting a merge decision; engine files left behind by an earlier version; specifications without an evaluation suite; and specifications whose phase is not canonical.
3. The upgrade audit shall produce a machine-readable result and a human-readable result from the same computation, and the upgrade report written at installation shall be generated from that same computation.
4. The upgrade audit shall not create, modify or delete any file in the project.
5. The upgrade audit shall detect gaps only through concepts the kit defines, and shall not inspect, store or report content that is specific to the target project.
6. The upgrade audit shall be runnable on its own, outside an installation, and shall exit with a distinct status for no gaps, gaps found, and internal error.
7. When the audit runs on a project that has never had the engine installed, it shall report that the engine is absent and stop, rather than reporting every gap.

### Requirement 5: Incremental project-layer update
**Objective:** As a project owner upgrading from an older kit, I want a single command that closes only the gaps the audit found, additively, so that I do not redo the project's setup or lose anything I wrote.

#### Acceptance Criteria
1. When the update command is invoked, it shall report the installed engine version, the previously installed version when known, and the full gap list before changing anything.
2. If the engine has not been installed or upgraded in the project, the update command shall instruct the user to run the installer first and stop.
3. If the upgrade audit reports no gaps, the update command shall say so and stop without changing any file, and running it again in that state shall change nothing.
4. When the update command closes a missing-steering gap, it shall use the existing steering commands in their additive mode and shall not regenerate steering files that already exist.
5. When the update command closes a configuration gap, it shall add only the missing keys with the kit's shipped defaults and shall preserve every existing value.
6. When the update command closes a gap in the orchestrator instruction file, it shall propose a section-level change derived from the current template, show it as a diff, and write it only after the human confirms it.
7. The update command shall never overwrite the orchestrator instruction file as a whole, existing steering content, existing specifications, or existing configuration values.
8. When the update command finds engine files awaiting a merge decision, it shall present each pair for the human to decide and shall not decide for them.
9. When the update command finds engine files left behind by an earlier version, it shall list them for the human and shall never delete them itself.
10. When the update command finds a specification whose phase is not canonical, it shall show the proposed mapping to a canonical phase and apply it only after confirmation.
11. When the update command finds a specification without an evaluation suite, it shall offer the evaluation command and shall not treat the absence as blocking.
12. Where the update command is invoked in dry-run mode, it shall report the plan and change nothing.
13. When the update command finishes applying changes, it shall re-run the upgrade audit, report what was closed and what remains with the reason, and regenerate the upgrade report.
14. The update command shall not re-ask intake questions whose answers already exist in the project layer.
15. If the project layer is absent, the update command shall route the user to the setup skill and stop.
16. When the setup skill starts in a project whose project layer already exists, it shall route the user to the update command instead of restarting the bootstrap.
17. When an installation finishes, the installer and the upgrade report shall point to the update command on an upgrade and to the setup skill on a first installation.

### Requirement 6: Release integrity of 0.9.0
**Objective:** As the kit maintainer, I want the release to be complete and self-consistent across both installers and the version history, so that a target project can tell what it has installed and name collisions are still preserved.

#### Acceptance Criteria
1. If the delegated executor's definition or the update command is missing from the kit, the installer shall fail before writing anything to the target.
2. The kit's version history shall list every engine path published by 0.9.0, so that a target file colliding by name with a newly published engine file is preserved on upgrade.
3. When the engine is installed, the version marker written to the target shall read 0.9.0.
4. The kit's user-facing documentation shall describe both deliverables and the release notes shall state that delegation ships off with the 0.8.0 behavior as fallback.
5. The engine shall remain free of any reference to a specific project, platform vendor or company in the files added or changed by this release.
