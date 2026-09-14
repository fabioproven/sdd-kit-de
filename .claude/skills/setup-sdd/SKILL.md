---
name: setup-sdd
description: Bootstrap the Spec-Driven Development kit in THIS project. Use when the user says "set up SDD", "install the spec flow", "configure SDD here", or has just copied the kit in and needs the project layer generated. Turns installation into a short conversation — verifies the engine is present, interviews for the orchestrator instructions, generates steering from the codebase, and suggests guardrails matched to the detected stack.
---

Bootstrap the SDD kit in the current repository. The **engine** (`.claude/commands/sdd/`,
`.sdd/settings/`) is generic and already copied. Your job is to generate the **project layer**
(`CLAUDE.md` + `.sdd/steering/`) and propose the optional **governance layer**. Do it as a
conversation, one decision at a time — never dump a wall of questions.

## 0. Verify the engine is present
Check that these exist; if any is missing, tell the user to re-run `install.sh` and stop:
- `.claude/commands/sdd/spec-init.md` (+ the other sdd commands)
- `.sdd/settings/rules/` and `.sdd/settings/templates/`
- `tools/spec-lint.py`

## 1. Detect the stack (don't ask what you can read)
Glob/read the obvious signals — `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`,
`pom.xml`, CI configs, top-level folders. Form a hypothesis about language, framework, and
project type. You will confirm, not interrogate.

## 1.4 Project intake — ask BEFORE discovering (three asks, one at a time)
Before reading the code, gather what only the user can tell you. One question per turn, each with
options and a sensible default. Capture intent now; do **not** connect or authenticate anything
here — verification and connection instructions happen in step 3.5.

1. **Technical docs & conventions** — _"Do you have technical documentation, coding conventions,
   a data dictionary, an architecture doc, or a style guide I should read first? Point me to paths
   or URLs, or paste the key ones."_ These prime everything that follows. Read what they point to
   (local files → read now; URLs/wikis → ask them to paste if you can't fetch). Fold into the
   knowledge harvest (1.5) and steering (3).
2. **Git / VCS host** — _"Which version-control host does this project use?"_
   Options: **GitHub · GitLab · Azure DevOps · Bitbucket · none/other.** Record the answer; step 3.5
   verifies whether it is reachable (CLI/MCP) or must be connected.
3. **Issue / task tracker** — _"Which issue or task tracker do you want linked?"_
   Options: **Jira · Microsoft Planner · Kanbanize · other · none.** Same: recorded now, verified in 3.5.

Write the three answers into a short "declared intent" note that `/sdd:discover-tools` will consume.

## 1.5 Absorb prior agent knowledge (don't start from a blank slate)
Before generating steering, harvest knowledge the team already wrote for other AI tools and in
root docs — **plus the specific docs the user pointed to in step 1.4** (read those first; they are
the user's own framing and outrank what globbing guesses). Run `/sdd:absorb-knowledge`
(it follows `.sdd/settings/rules/knowledge-discovery.md`):
it sweeps `*.md` at root, `AGENTS.md`/`GEMINI.md`/`CLAUDE.md`, and per-tool config
(`.claude/`, `.cursor/` + `.cursorrules`, `.github/copilot-instructions.md`, `.windsurfrules`,
`.continue/`, `.aider*`, `.agent/`, `.assistant/`, `.ai/`), then distills durable conventions,
vocabulary, and guardrails into `.sdd/steering/inherited-knowledge.md`. Surface any conflicts it
flags to the user. If nothing is found, say so and move on.

## 1.6 Use-case canvas — what is this agent FOR (one ask, not eight)
Before writing anything, pin down the scope that calibrates every gate later. **Propose a filled-in
draft** from what you detected in 1.1–1.5 and ask the user to correct it — do not interrogate field
by field:

- **Users** — who talks to this agent.
- **Questions/tasks** — the three things it will actually be asked to do weekly.
- **Decisions supported** — what someone does differently because of its output.
- **Sources** — the systems it may read.
- **Criticality & SLA** — what breaks if it is wrong or late.
- **Allowed actions** — read? create new artifacts? write to production? open PRs?
- **Autonomy level** — where the human must stay in the loop.

The last two are not paperwork: they are the input to the **high-risk scope** you confirm in step 4
and to the auto-approval posture. An agent whose allowed actions were never stated will have them
decided implicitly, one improvisation at a time.

Fold the canvas into `.sdd/steering/product.md` (an "Agent scope" section) when step 3 runs — not a
separate file, and never duplicated into `CLAUDE.md`.

## 2. Interview for CLAUDE.md (one question at a time)
`CLAUDE.md` is the only piece that must be written by hand. Gather just enough to fill the
template, each as its own turn, each with a recommended default:
- **What is this product, in one line?** (name + who uses it)
- **Artifact language** — code/comments/specs in English or the user's language? (default: English)
- **Roster** — will they use subagents/personas, or keep it lean? (default: just `code-explorer`)
- **Hard rules** — anything that must never happen? (e.g. no edits on the main branch, prod is read-only, no committing secrets)

Then write `CLAUDE.md` at the repo root from `CLAUDE.md.template`, replacing the placeholders.
If a `CLAUDE.md` already exists, propose additions instead of overwriting.

## 3. Generate the steering (the project's memory)
Run the engine's own bootstrapper rather than writing steering yourself:
- Invoke `/sdd:steering` — it reads the codebase and generates `product.md`, `tech.md`, `structure.md`.
- **Fold in the inherited knowledge** from step 1.5: `/sdd:steering` should reconcile what the code
  shows with what prior configs stated, merging into core steering and leaving only project-specific
  extras in `inherited-knowledge.md`. Deduplicate; keep patterns, not catalogs (100–200 lines, no secrets).
- For each real domain the project has, offer `/sdd:steering-custom` (glossary, testing, database, security, api-standards…). Only create what the project actually has.
- **If the project has a data platform, offer `semantic-layer.md` specifically.** It is the file that
  stops the agent inventing a metric: name + formula + grain + population + owner per metric, plus
  which datasets are canonical and which look-alikes are deprecated. Seed it with the metrics the
  canvas (1.6) says people ask about, and mark anything you could not confirm as undefined rather
  than guessing a formula.

## 3.5 Discover tools & integrations (so delivery commands work)
Run `/sdd:discover-tools` (it follows `.sdd/settings/rules/tooling-discovery.md`). It **starts from
the intent declared in step 1.4** (the git host and the tracker the user named) and verifies, read-only,
whether each is actually reachable — plus it probes the data platform and CI. It classifies each as
`mcp-native`, `cli`, `needs-setup`, or `n/a`, writing `.sdd/steering/integrations.md`.
- **Reconcile declared vs detected.** If the user said "GitHub" but the git remote is GitLab, surface
  the mismatch — don't silently pick one.
- Walk the **"To enable"** list with the user: for every `needs-setup`, give the exact connect steps
  (which CLI to install + authenticate, or which MCP server to add — e.g. Atlassian for Jira,
  Microsoft Graph for Planner, the Kanbanize REST/MCP, `gh`/`glab`/`az`/Bitbucket for the PR host).
  This is the moment to wire integrations, before they need `/prepare-pr` or `/data-quality`.
- This file is the contract the delivery commands read — do not skip it.

## 4. Suggest guardrails matched to the stack (optional)
Based on step 1, propose — don't impose — a short list:
- A `PreToolUse` hook if there's an obvious "never write here" (production config, protected branch, secret files).
- Which `spec-impl` profile fits their work: `spec-impl` (code+TDD), `spec-impl-investigation` (reports), `spec-impl-config` (infra).
- Wiring `spec-lint` into CI as a required check (add `--require-evals` only once the team is
  actually writing eval suites — turning it on before that just fails every build).
- **Evals** (`/sdd:spec-evals`): propose making an eval suite mandatory for work that changes a metric
  definition, a canonical dataset, or the agent's domain instructions — those are the three things
  that silently break answers. Explain the rule that ground truth comes from a human, never from the
  agent under test.
- Which **delivery commands** are ready now vs blocked: `/prepare-pr` and `/review` need the VCS/PR
  row in `integrations.md` to be `mcp-native` or `cli`; `/data-quality` needs the data-platform row.
  Point out any that are `needs-setup`.
- **Auto-approval policy** (`.sdd/autoapprove.json`): ask whether to enable the executor↔approver loop
  and for which risk levels. The template ships **off** (identical to manual approval) for safe first
  contact. Recommend the **balanced** posture: `enabled: true` with auto for `low` **and** `medium`
  (logged), `high` always human (non-negotiable; the gate enforces it). This is the posture that gives
  real autonomy while keeping the gate exactly where it matters. Offer the conservative alternative
  (auto `low` only) for teams that want to build trust first. Set `enabled` and the per-level flags
  accordingly, and confirm `max_iterations` (default 5) and the token/cost ceiling.
- **Gates by risk, not by phase** (`CLAUDE.md`): the generated `CLAUDE.md` says the flow runs
  continuously and only stops for a human on **high-risk** steps. Confirm the project's high-risk scope
  with the user (what counts as writing production data / a consumer contract here) so the gate lands
  in the right place — don't reintroduce a stop at every phase.
- **Read-only permission allowlist** (`.claude/settings.local.json`): seed it with the project's
  clearly read-only command shapes so routine work doesn't prompt — e.g. `Bash(git status*)`,
  `Bash(git diff*)`, `Bash(git log*)`, the data-platform CLI's read/list/describe verbs, and the
  read-only `tools/spec-lint.py` / `tools/approval-gate.py` invocations. **Never allowlist
  write-capable commands** (push, import/deploy, destructive SQL) — those must keep prompting, since
  the harness prompt is the last guard when no `PreToolUse` hook exists. Match the shapes to the stack
  detected in step 1.
Leave these as recommendations the user opts into.

## 5. Prove the install with one real spec
Run a tiny end-to-end check and stop for review:
- `/sdd:spec-quick "a small real feature" --spec-only` → produces requirements + design + tasks without touching code.
- `/sdd:spec-lint <feature>` → confirm traceability is intact.
If both look coherent, the kit is installed. Summarize what was created and the three invariants
to protect going forward: **WHAT/HOW separation · ID traceability · human gates**.

## Anti-patterns
- Asking everything at once. Walk it one turn at a time.
- Writing steering by hand instead of running `/sdd:steering`.
- Overwriting an existing `CLAUDE.md`.
- Copying guardrails from another project instead of matching them to this stack's real risks.
