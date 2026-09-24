---
description: Bring the project layer up to the installed SDD Kit version — closes only what the upgrade audit found, additively; never redoes the setup, never overwrites CLAUDE.md, steering, specs or existing config values
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: [--dry-run]
---

# Update the project layer after an engine upgrade

<background_information>
- **Mission**: After `install.sh` / `install.ps1` upgraded the engine (layer 1), close **only** the
  gaps the deterministic upgrade audit reports in the project layer (`CLAUDE.md`, steering, configs,
  specs) — one gap at a time, additively, with the human at every edit that changes agent behavior.
- **What this is not**: not the installer (it does not copy the engine), not `setup-sdd` (it never
  re-asks what the project already answered), not a rewrite of anything that exists.
- **Success Criteria**:
  - Nothing is written before the plan is shown; `--dry-run` writes nothing at all.
  - A project with zero gaps is left untouched, and a second run reports the same.
  - Every `CLAUDE.md` edit was shown as a diff and confirmed; existing steering, specs and config
    values are byte-identical afterwards.
  - The audit is re-run at the end and `.sdd/UPGRADE.md` is regenerated from it.
</background_information>

<instructions>
## The rule that does not bend
**The audit decides what is pending; you do not.** `tools/kit-sync.py audit` computes the gap
list from disk — versioned checks, read-only. You act on its rows and on nothing else. If you
notice something "that should also be updated" and the audit does not list it, say so at the
end as a suggestion; do not act on it.

## Step 1 — Preconditions (stop early, say why)
1. `.sdd/SDD_KIT_VERSION` missing → *"The engine is not installed here. Run `install.sh` /
   `install.ps1` from the kit first, then `/update-sdd`."* Stop.
2. Run the audit (use `py` on Windows; `python3` elsewhere; try both):
   ```
   py tools/kit-sync.py audit --target . --format json
   ```
   - Exit **2** → print the tool's message verbatim and stop (engine absent or internal error).
     If neither `py` nor `python3` runs, say the audit cannot run and stop — never guess the gaps.
   - `"layer2": "absent"` → *"This project has no project layer yet (CLAUDE.md still has
     placeholders or steering is empty). This is a first install: run the `setup-sdd` skill."* Stop.
   - `"gaps": []` → *"Project layer is complete for `<kit_version>` — nothing to do."* Stop.
     Write nothing.

## Step 2 — Show the plan before touching anything
Print, in the user's language:
- installed version and previous version (from the JSON; "unknown" if null);
- the gap table grouped by severity (`blocking` → `recommended` → `optional`), each row:
  `id · what · since · closes with`, marking rows whose `since` is newer than the previous version.
- one line on posture: *"I close these one at a time. Steering generation and config keys run
  without asking (new, non-destructive). Every `CLAUDE.md` edit and every spec-phase change shows a
  diff and waits for your OK. `.sdd-new` files and leftovers are yours to decide; I never delete."*

If `$ARGUMENTS` contains `--dry-run`: stop here.

## Step 3 — Close the gaps, one per turn, in severity order
Handle each row by the prefix of its `id`. Never combine two `CLAUDE.md` edits into one diff.

### `steering.*` — missing steering file
Invoke the command in `closes_with`:
- `steering.product` / `steering.tech` / `steering.structure` → `/sdd:steering`. When any core
  file exists it runs in **Sync** mode by construction (additive, preserves hand-written content).
  Never delete or regenerate a file that exists.
- `steering.integrations` → `/sdd:discover-tools` (read-only discovery; it may report
  `needs-setup` rows — that is fine, the file's existence is the gap).
- `steering.inherited-knowledge` → `/sdd:absorb-knowledge`. If it finds nothing, it writes the
  file saying so; that closes the gap honestly.

### `config.*` — editable config missing or missing keys
- `config.<name>.missing` → copy `.sdd/settings/templates/<name>.json` to the path in the row.
  It ships **off**; say so.
- `config.<name>.invalid` → show the parse error and ask the user to fix the syntax; do not
  rewrite a config you cannot read.
- `config.<name>.key.<key>[.<sub>]` → read both JSONs; add **only** the absent key (or sub-key)
  with the template's value; keep every existing key, value and their order; `_`-prefixed note
  keys travel with their block. Write with 2-space indent, UTF-8, LF. Show the added keys.
  Never change an existing value, even if it differs from the template.
- `config.vscode.missing` → copy `.sdd/settings/templates/vscode/tasks.json` (and
  `settings.json`, `extensions.json` if absent) into `.vscode/`. Never overwrite.

### `claude.*` — the orchestrator instruction file (section-patch protocol)
`CLAUDE.md` is hand-written: **patch a section, never the file.** The source for every patch is
the installed `CLAUDE.md.template` (kit root copy; the installer places it next to `CLAUDE.md`).
Section identity = the template's `## ` headings.

1. **Build the patch** for this one row:
   - `claude.section.<slug>` → take that section from the template (heading to the next `## `),
     drop the HTML comments meant for template authors, keep the `{{PLACEHOLDERS}}` only where a
     value is genuinely project-specific and **ask for each one** before inserting. Insert the
     section **before the next template heading the project already has** (walk the template's
     heading order); if none follows, append at the end.
   - `claude.routing.<agent>` → insert only the routing bullet for that agent (from the
     template's Routing section) into the project's existing Routing section. If the project has
     no Routing section, treat it as `claude.section.routing` first (ask — Routing is optional in
     the template, so confirm the project wants subagents routed at all).
   - `claude.phase-gates` → replace **only the sentence(s)** containing "approval gate at each
     phase" with the template's "Gates are by risk, not by phase" paragraph.
   - `claude.convention-not-lock` → replace only the sentence carrying the marker with the
     template's write-guard sentence from Hard rules.
   - `claude.spec-impl-auto` → replace the instruction to run `/sdd:spec-impl-auto` with the
     template's quick-reference wording (it is an alias; the loop runs inside `spec-impl`).
   - `claude.placeholders` → list every `{{...}}` left, ask for values one at a time, replace.
2. **Renamed heading?** If the project has a section that clearly plays the same role under a
   different heading (compare the first two words and the content), **ask** which to do — never
   insert a duplicate section.
3. **Show a unified diff** of exactly this patch (`Read` the file, produce the diff in the reply).
4. **Wait for confirmation.** On yes: apply with a single `Edit` whose `old_string` is the exact
   anchor. On no: record "skipped by user" for the final report and move on.

### `spec.<name>.phase` — non-canonical phase
Propose the mapping from the observed value to one of the canonical phases in
`.sdd/settings/rules/spec-artifacts.md`. Derive it from evidence, not from the word: every task in
`tasks.md` checked → `implementation-complete`; some checked → `implementation-in-progress`;
`tasks.md` exists with `approvals.tasks.approved` → `tasks-approved`; and so on down. Put the
original string into `status_note` ("phase was `<old>` before /update-sdd on <date>") so nothing is
lost. Show the change, confirm, then edit `spec.json` only.

### `spec.<name>.evals` — no eval suite
Say: *"`/sdd:spec-evals <name>` builds a suite; ground truth comes from a human. Not blocking —
run it when someone can vouch for the answers."* Do nothing else.

### `engine.sdd-new` — engine file awaiting a merge decision
Show, per pair, a short summary of how `<file>` (the project's version) differs from
`<file>.sdd-new` (the kit's): sections added/removed, roughly how many lines. Offer three choices —
keep mine (delete the `.sdd-new`), take the kit's (replace mine), merge by hand (leave both). Apply
only the choice the user makes; "keep mine" and "take the kit's" both remove a file, so restate
which one before doing it. Never choose for them.

### `engine.orphan` — leftover from an earlier version
List the paths and say deletion is irreversible and theirs: *"remove with `git rm` / delete if you
did not customize them."* Do nothing.

## Step 4 — Re-audit and report
1. Run the audit again (JSON). Then regenerate the report:
   ```
   py tools/kit-sync.py report --target .
   ```
2. Print: **closed** (id → what was done), **remaining** (id → why: skipped by user, needs a
   human decision, needs a human's ground truth), and the path `.sdd/UPGRADE.md`.
3. If the remaining list is empty: *"Project layer is complete for `<kit_version>`."*

## Hard constraints
- Never overwrite `CLAUDE.md`, any `.sdd/steering/*.md` that exists, any `.sdd/specs/**`, or any
  existing config value. Never delete anything. Never run the installer.
- Never ask an intake question (product description, VCS host, tracker, language…). If a value is
  needed for a placeholder, ask for **that placeholder** and nothing else.
- Never act on something the audit did not list.
- Work in the user's language; artifacts stay in the project's artifact language.
</instructions>

## Output Description
Keep each turn short: the row being closed, the diff (when there is one), the question (when
there is one). The final turn is the closed/remaining report — under 200 words plus the table.

## Safety & Fallback
- **Python unavailable** → the audit cannot run; stop and say how to install Python 3.7+.
- **`CLAUDE.md.template` missing next to `CLAUDE.md`** → the audit says so (`template_found:
  false`); section rows will not appear, marker rows still will. Suggest re-running the installer,
  which copies the template alongside.
- **User declines every `CLAUDE.md` edit** → fine; the report lists them as skipped and the next
  install's `UPGRADE.md` will list them again. That is the design, not a failure.
