---
description: Self-review your diff, then open a pull request on the project's PR host
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [base-branch]
---

# Prepare & Open Pull Request

<background_information>
- **Mission**: Turn a finished change into a reviewable PR — validate against the spec, self-review the diff, then open the PR on whichever host the project actually uses.
- **Success Criteria**: A clean, conventional PR with a Context / Changes / How-to-test description, opened only after a passing self-review and an explicit user go-ahead.
</background_information>

<instructions>
## Step 1: Know the backend (do not guess)
Read `.sdd/steering/integrations.md` → **VCS / PR host** row.
- `mcp-native` → use that MCP server's PR tools.
- `cli` → use the named CLI: `gh pr create` (GitHub), `glab mr create` (GitLab), `az repos pr create` (Azure DevOps).
- `platform` → there is no repo by decision; the workspace on the data platform is the source of
  truth. Skip Steps 2 and 5 and run the **delivery package** path in Step 5b instead.
- `needs-setup` or missing → **stop**; tell the user which integration to configure. Do not improvise.
If `integrations.md` is absent, run `/sdd:discover-tools` first.

## Step 2: Establish the diff
- Base branch = `$1` if given, else the repo default (`main`/`master`, or the tracked upstream).
- If currently on the base branch, **stop** and ask to branch first (never commit straight to main).
- Collect the diff: `git status`, `git diff <base>...HEAD`, and unstaged changes.

## Step 3: Validate against the spec (if one exists)
- If the branch maps to a `.sdd/specs/<feature>/`, run `/sdd:spec-lint <feature>` and confirm the diff covers the approved tasks. Report gaps; do not silently proceed past an incomplete spec.

## Step 4: Self-review the diff
Check, and report findings grouped **Must-fix / Should-fix / Nits**:
- Correctness and obvious bugs; missing error handling.
- Tests updated/added for the change (or a stated reason none apply).
- Secrets, hardcoded IDs, debug leftovers — none present.
- Matches the conventions in steering (`inherited-knowledge.md` included).
If there are Must-fix items, stop and surface them — do not open the PR.

## Step 5: Commit & open — WITH confirmation
- Propose a branch name (`<type>/<ticket-or-slug>-<short>`), a commit title (`[<TICKET>] What changed`), and the PR description (Context / Changes / How to test).
- **Opening a PR is outward-facing: read the plan back and wait for an explicit "yes" before pushing or creating the PR.**
- `git push` is fine as part of the happy path once confirmed; never use `--force` unless the user explicitly asks.

## Step 5b: Delivery package (only when the VCS row is `platform`)
There is no branch and no PR; delivery is an **import into a shared workspace**, which is a write
to a system other people read — `high` by `risk-classification.md`, always.
- **Freshness first**: run the check `integrations.md` names (e.g. `workspace get-status` →
  `modified_at`) for every file you changed. If the remote copy is newer than your base, **stop**:
  importing would overwrite someone's edit. Show both timestamps.
- **Scope = exactly the files this change touched.** Never a directory, never a mirror, never a
  file you did not edit. List each one with its remote path.
- Self-review (Step 4) and spec validation (Step 3) still apply.
- Present the package: the file list, the one-command-per-file import lines with the exact
  profile/flags from `integrations.md`, and the rollback (the pre-import versions or
  `rollback.md` from the spec). **Wait for an explicit "yes" before running any import.** Run them
  one at a time; report each result; stop on the first failure.

## Critical Constraints
- Never open the PR without a passing self-review and user confirmation.
- Never import into a platform workspace without the freshness check and an explicit "yes".
- Never push to the base branch directly.
- Never fabricate a "How to test" — derive it from the actual change.
</instructions>

## Output Description
1. Backend used (from integrations.md). 2. Self-review report (Must/Should/Nits). 3. Proposed branch/commit/PR text. 4. After confirmation: the PR URL.

## Safety & Fallback
- **Detached HEAD / dirty unrelated changes**: stop and clarify scope.
- **No PR host configured**: point to `/sdd:discover-tools` and the `needs-setup` item.
