# Implementation Plan — `data-engineer-and-update-sdd` (SDD Kit 0.9.0)

Order matters between majors: the audit (1) is what `/update-sdd` (2) acts on; delegation (3) is
independent of both and may run in parallel with 1–2; release (4) is last. Inside a major, tasks
marked `(P)` touch disjoint files.

- [x] 1. Deterministic upgrade audit in the sync tool
- [x] 1.1 Replace the existence-only gap list with a versioned check table
  - Each check carries an id, the engine version that introduced it, a severity (blocking / recommended / optional), what is missing or stale, the command or action that closes it, and why
  - Cover: core steering, integrations and inherited knowledge, orchestrator file missing / placeholders / phase-gate wording / "convention, not a lock" / standalone auto-loop instruction, template sections absent (skip the optional "Where you are running"), routing lines absent for every agent installed in the project, config files missing or missing top-level keys versus the shipped templates, editor task file absent, pending `.sdd-new` files, orphans from the previous manifest, specs without an eval suite, specs with non-canonical phase
  - Section identity comes from the template's second-level headings (case- and punctuation-insensitive, first two words tolerant); agent names come from installed agent frontmatter — nothing project-specific is read or stored
  - Pure function of the target's disk: takes paths, returns rows, writes nothing
  - _Requirements: 4.1, 4.2, 4.4, 4.5_

- [x] 1.2 Expose the audit as a standalone read-only subcommand with JSON and human output
  - `audit --target <dir> [--kit <dir>] [--format human|json]`; without `--kit`, read the template and version history from the target's own installed copies
  - Exit 0 no gaps, 1 gaps found, 2 engine absent or internal error; engine absent is reported in one line, not as a list of every gap
  - JSON carries kit version, previous version (from the manifest), whether layer 2 is present, and the gap rows; human output groups by severity and marks rows newer than the previous version
  - Console output stays ASCII-safe for cp1252 terminals
  - _Requirements: 4.3, 4.6, 4.7, 5.1_

- [x] 1.3 Generate the upgrade report from the audit and route the next step by situation
  - `finish` calls the audit and hands its rows to the report writer; the old gap function is removed, not kept beside it
  - The report table gains the severity column; "next step" says `/update-sdd` when a previous version is known and layer 2 exists, and the setup skill on a first install or when layer 2 is absent
  - Add a thin `report --target <dir>` subcommand that rewrites the report from a fresh audit without touching the manifest, for the update command to call after it finishes
  - _Requirements: 4.3, 5.13, 5.17_

- [x] 1.4 Test the audit with fixture targets
  - Build three temp targets: engine only (layer 2 absent); an old-style layer 2 with phase-gate wording, three steering files, a config without the delegation block, one spec with a non-canonical phase and no evals; a complete 0.9.0 layer 2
  - Assert the exact gap ids per fixture, exit codes 2 / 1 / 0, identical output on two consecutive runs, and no file modified (mtime and hash) by the audit
  - Assert the report's next-step text for first install versus upgrade
  - _Requirements: 4.1, 4.4, 4.6, 4.7, 5.17_

- [x] 2. The incremental update command
- [x] 2.1 Write the update command flow around the audit
  - Preconditions in order: version marker present (else "run the installer first" and stop); audit exit 2 → stop with its message; layer 2 absent → route to the setup skill and stop; zero gaps → say clean and stop without writing
  - Print installed version, previous version and the full gap table grouped by severity before any change; `--dry-run` stops here
  - Close gaps one per turn in severity order: missing steering via the existing steering commands (Sync mode; never regenerate an existing file); missing config files copied from templates; missing config keys added with shipped defaults while preserving every existing value and key order; non-canonical spec phase mapped from the checkbox state and applied only after confirmation; `.sdd-new` pairs presented for the human to decide; orphans listed and never deleted; missing evals offered, not required
  - Never ask an intake question; every input comes from disk or from the gap row
  - After applying, re-run the audit, report closed versus remaining with reasons, and regenerate the upgrade report through the sync tool
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14, 5.15_

- [x] 2.2 Define the section-patch protocol for the orchestrator instruction file
  - For a missing section: extract it from the current template and insert it before the next template heading the project already has, else append
  - For a stale marker phrase: replace only the sentence carrying the marker with the template's current sentence
  - For placeholders: list them and ask for values, one at a time
  - For a missing routing line: insert only that bullet into the existing routing section
  - If the project renamed a template heading, ask instead of inserting a duplicate
  - Always show a unified diff and write only after confirmation; never rewrite the file as a whole
  - _Requirements: 5.6, 5.7_

- [x] 2.3 (P) Route between setup, update, installer and report
  - Setup skill: new early step that detects an existing layer 2 (filled orchestrator file plus core steering) and routes to the update command, continuing only if the user wants to start over
  - Both installers' next-steps text: upgrade → update command; first install → setup skill
  - Template quick-reference row for the update command
  - _Requirements: 5.16, 5.17_

- [x] 3. The delegated data-engineer executor
- [x] 3.1 (P) Write the data-engineer agent
  - Write-capable tools; reads all steering, the design sections named in the Work Order, the write scope and the data-platform integration row before acting; a metric with no contract is undefined, never improvised
  - Performs the round in the profile's discipline (test-first for code, dry-run validation for config) and returns the fixed Work Report shape: files changed, commands with results, evidence written, each exit criterion met or not with evidence, out-of-scope observations, early-stop reason, environment note
  - Hard stops that end the round with a report and no action: riskier than declared, write outside scope or permitted paths, undefined metric, credential needed, anything destructive
  - Never marks tasks, changes spec state, approves, expands scope, or calls other agents
  - Says in the report when it ran where hooks do not exist and applied the write scope as convention
  - _Requirements: 1.5, 1.6, 1.7, 1.8, 1.12, 3.4_

- [x] 3.2 (P) Add the delegation block to the auto-approval template
  - Ships disabled with the executor name and per-level flags (low off, medium on, high on) and a note that it decides who types, never who approves
  - Installer already copies the file only when absent; confirm no installer change is needed for this file
  - _Requirements: 2.1, 2.2, 2.5_

- [x] 3.3 Wire delegation into the implementation commands and the loop rule
  - Loop rule: executor is self or the configured agent; define the Work Order and Work Report contracts once; the gate is checked before every round regardless of who executes; a `high` subtask is sent as a Work Order only after the human said yes and only if the high flag is on; ledger note carries the executor identity; fallback paragraph states that an absent, invalid or disabled block means self, identical to 0.8.0
  - Code and config profiles: Step 0 reads the block, prints the one-line mode statement (mode and executor with per-level flags), falls back to inline execution with a notice when the configured agent file is not installed; the execution step builds the Work Order from the classification and design, calls the executor, and treats the Work Report as the round result — approver judges when the loop is on, the orchestrator verifies each criterion against the report's evidence when it is off; marking, phase and evidence stay with the orchestrator
  - Investigation profile: one sentence stating it never delegates and keeps data access read-only
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.9, 1.10, 1.11, 2.3, 2.4_

- [x] 3.4 (P) Make the project layer aware of the role
  - Template routing bullet for the delegated executor, stated as inert while delegation is off; one sentence in the auto-approval section that delegation decides who executes, never who approves
  - Setup skill guardrails step: offer delegation as opt-in with the recommended posture and say what enabling changes and how to see it ran
  - _Requirements: 3.1, 3.2_

- [ ] 3.5 Prove the guardrails and the round end to end
  - Scratch project with the write-scope hook enabled and a fake allowed target: a Work Order whose only step is a write outside scope must be denied inside the subagent; save the hook's decision as dated evidence under the spec
  - One-task scratch spec with delegation on and the loop off: Work Order and Work Report appear, the orchestrator marks the task, no ledger is written; repeat with the loop on and confirm ledger rows name the delegated executor
  - Delegation off: run the same spec and confirm the transcript shows no subagent call and the mode line says self
  - _Requirements: 1.1, 1.9, 1.10, 3.3_

- [x] 4. Release 0.9.0
- [x] 4.1 (P) Keep both installers and the version history in step
  - Required-file lists in both installers include the new agent and the new command, failing before any write when either is absent
  - Version history gains the 0.9.0 entry with every engine path this version publishes
  - _Requirements: 6.1, 6.2_

- [x] 4.2 Prove the upgrade path on the test-bed copy
  - Copy the test-bed project to a scratch dir, install 0.9.0 over it, run the update command in dry-run and compare the gap table with the report; then run for real and confirm every orchestrator-file edit was diff-confirmed, existing steering and spec hashes are unchanged, the delegation block was added off, and a second run reports clean
  - _Requirements: 5.3, 5.5, 5.6, 5.7, 5.13_

- [x] 4.3 Close the release per the workbench checklist
  - Version marker to 0.9.0; changelog section on top stating both deliverables and that delegation ships off with 0.8.0 as fallback; readme footer, "Novidades da 0.9.0", command and structure tables; handoff title and changed defaults; visual flow footer plus one section for the delegated executor and one for the update path
  - Sanity grep for the previous version outside historical sections; confirm no project, vendor or company name entered any engine file
  - Package the zip on the workbench root, commit with the local identity, tag, push
  - _Requirements: 6.3, 6.4, 6.5_
