---
description: Review a pull request, or your own working diff, against the project's conventions
allowed-tools: Bash, Read, Grep, Glob, WebFetch
argument-hint: [<pr-number|pr-url> | --diff]
---

# Code Review

<background_information>
- **Mission**: Produce an architecture-aware, convention-grounded review — of an open PR (peer review) or the current working diff (pre-PR self check).
- **Success Criteria**: Findings ranked by severity, each tied to a concrete file:line and a real failure or convention breach — no vague nits dressed as blockers.
</background_information>

<instructions>
## Step 1: Pick the mode
- `$1` is a PR number/URL → **PR review mode**.
- `$1` is `--diff`, or absent → **working-diff mode** (review uncommitted + branch changes vs base).

## Step 2: Know the backend (PR mode only)
Read `.sdd/steering/integrations.md` → **VCS / PR host** row.
- `mcp-native` → fetch the PR (title, description, diff, comments) via that MCP server.
- `cli` → `gh pr view/diff`, `glab mr view`, `az repos pr show`.
- `needs-setup` → stop; tell the user what to configure (or paste the diff manually).

## Step 3: Load the lens
- Read `.sdd/steering/` (conventions, structure, `inherited-knowledge.md`) — this is the bar you review against.
- If the change maps to a spec, read its `requirements.md` + `design.md` and check the diff honors them.
- Read `.sdd/settings/rules/design-review.md` if present for the review checklist.

## Step 4: Review
Assess and group findings **Blocking / Should-fix / Nits / Questions / Highlights**:
- **Correctness** — bugs, edge cases, error handling, race conditions.
- **Contract fidelity** — does it match the design's interfaces and the requirements' acceptance criteria?
- **Conventions** — matches steering + inherited standards; no reinvention of existing patterns.
- **Safety** — no secrets, no prod writes where prohibited, no bypassed guardrails.
- **Tests** — coverage for the change; DQ checks at data boundaries where relevant (see `/data-quality`).
Every finding cites `path:line` and states the concrete consequence. Verify before asserting — prefer "confirmed" over "possible".

## Step 5: Deliver
- **Working-diff mode**: print the report to the user (read-only; never posts anything).
- **PR mode**: present the report and **ask before posting** any comment or approval to the PR — posting is outward-facing and requires explicit confirmation.

## Critical Constraints
- Read-only until the user confirms posting.
- No approval/merge action without explicit user go-ahead.
- Rank by real severity; don't inflate nits.
</instructions>

## Output Description
Mode + backend used, then the grouped findings (most severe first), each with file:line and consequence. End with a one-line verdict.

## Safety & Fallback
- **PR not found / no access**: report it; offer working-diff mode or a manual diff paste.
- **No spec to check against**: review on conventions + correctness only, and say so.
