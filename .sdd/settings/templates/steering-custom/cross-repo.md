# Cross-Repo Steering

[Purpose: auto-discover sibling repos, synthesize inter-repo contracts from existing steering files, and write cross-repo.md to all platform repos in a single pass]

---
<!-- AGENT INSTRUCTIONS — read and execute. Do not copy this section to the output file. -->

## Prerequisite Check

Before running discovery, verify steering files exist:

1. For the current repo: check `.sdd/steering/` for at least one of `product.md`, `tech.md`, `structure.md`.
   - If none found → **hard abort**:
     > ⚠️ `{repo-name}` has no steering files yet. Run `/sdd:steering` there first, then re-run `/sdd:steering-custom cross-repo`.
2. For each discovered sibling repo: check the same files.
   - If none found → issue a per-repo warning and skip that repo from synthesis; do not abort.
     > ⚠️ `{repo-name}` has no steering files — skipped from synthesis. Run `/sdd:steering` there first, then re-run `/sdd:steering-custom cross-repo`.

## Discovery Algorithm

Execute the following steps in order:

1. **Extract prefix**: Read the current repo's directory name (last segment of the working directory path). Extract the prefix — everything before the last `-` or `_` separator.
   - `acme-api` → prefix `acme`
   - `my-platform-backend` → prefix `my-platform`
   - `acme_web` → prefix `acme`
2. **Scan parent dir**: List subdirectories of `../` (the parent directory). Keep only those whose names begin with the extracted prefix.
3. **Filter by SDD presence**: From the prefix-matched candidates, keep only directories that contain a `.sdd/` subdirectory.
4. **Build repo set**: Union of current repo + all qualifying siblings.

**Edge cases**:

- **No siblings found** (single repo or no prefix match after both filters):
  Display and offer manual fallback:
  > No sibling repos with matching prefix and `.sdd/` found. This template is intended for multi-repo products. If your repos use different naming, list them manually when prompted.
  Then ask the user to provide repo paths manually and include them in the set.

- **5 or more repos discovered**: Proceed normally, then append the microservices note (see scaffold) to the generated file.

- **Repos in different parent directories** (monorepo tools, symlinks): Out of scope for automatic discovery. Inform the user and ask them to list paths manually.

## User Interaction

After discovery and prerequisite checks, ask exactly **one** confirmation question:

> I found these repos for the `{prefix}` platform:
> - `{repo-name}` (has steering: {comma-separated list of found steering files})
> - `{repo-name}` (has steering: {comma-separated list})
> - `{repo-name}` ⚠️ no steering files — will be skipped
>
> Are these all the repos in this platform? (yes / no — if no, list any missing repo paths)

- If the user says **yes**: proceed to synthesis.
- If the user says **no** with additional paths: add those paths to the repo set, then proceed.
- **No other questions** are permitted during execution.

## Synthesis Instructions

Read steering files from each repo in the set (skip repos with no steering files). Synthesize the following outputs:

**From each repo's `tech.md`**:
- Communication protocols in use (REST, GraphQL, WebSocket, events, gRPC)
- Exposed API base paths, event topics, or shared schemas
- External service dependencies

**From each repo's `structure.md`**:
- Entry points (API gateway paths, main app entry, public site routes)
- Where shared types or contracts are defined

**From each repo's `product.md`**:
- Domain responsibility (what business capability this repo owns)
- User-facing vs. internal service distinction

**Produce these five synthesis outputs**:
1. Repo inventory with domain ownership and type (API / Frontend / Admin / Service / Worker)
2. Communication contracts between repos (directional: repo-a → repo-b)
3. Authentication boundary: who issues tokens, who validates, token format and location, public routes
4. Shared type/schema source of truth (or note if types are duplicated)
5. Deployment dependencies: deploy order, environment parity, shared infrastructure

**Content rules** (mandatory):
- Do not write secrets, credentials, API tokens, or internal IP addresses to any file
- Do not duplicate content already present in individual repos' `tech.md`, `structure.md`, or `product.md`
- Use patterns and representative examples rather than exhaustive endpoint lists
- Target 80–150 lines in the generated file; do not exceed 200 lines

## Canonical Repo Designation

Identify one repo as the canonical source for `cross-repo.md`:

1. Prefer the repo whose name ends in `-api`, `-backend`, `-server`, or `-service`.
2. Tie-break rule: if the current repo (where the command is run from) qualifies by suffix, it wins. Otherwise, take the first alphabetical match among qualifying repos.
3. If no repo matches any canonical suffix, the current repo is canonical.

The canonical repo's `cross-repo.md` is the source of truth. Non-canonical repos receive an identical copy with the following note added at the very top of the file (before the `# Cross-Repo Contracts` heading):
```
> **Note**: This is a copy. Canonical source: `.sdd/steering/cross-repo.md` in `{canonical-repo-name}`. Update the canonical copy first, then sync here.
```

## Multi-Repo Write Pass

After synthesis, write the generated file to all repos:

1. Write `cross-repo.md` to `{current-repo}/.sdd/steering/` first (canonical or copy as appropriate).
2. For each other discovered repo that has `.sdd/steering/`: write the file there.
3. If a write operation fails for a specific repo (permission issue, path not found):
   - Display: `⚠️ Could not write to {repo-path}/.sdd/steering/cross-repo.md — skipped.`
   - Continue writing to remaining repos.
4. If a repo was discovered but has no `.sdd/steering/` directory at write time: skip and warn; do not create the directory.

After all writes, display the completion summary (see scaffold).

---
<!-- END AGENT INSTRUCTIONS -->

## Output scaffold — write the following to `.sdd/steering/cross-repo.md` in each repo

---

# Cross-Repo Contracts

> **Platform**: {prefix} platform — {N} repos
> **Canonical source**: `.sdd/steering/cross-repo.md` in `{canonical-repo-name}`
> **Last generated**: {date}
> **Sync note**: Keep copies in all repos consistent when contracts change.

## Platform Repos

| Repo | Domain Responsibility | Type |
|------|-----------------------|------|
| `{repo-name}` | {one-line description of what it owns} | API / Frontend / Admin / Service / Worker |

## Communication Contracts

### {repo-a} → {repo-b}
- **Protocol**: REST / GraphQL / WebSocket / events / gRPC
- **Base URL / topic**: `{value}`
- **Auth**: {how the calling repo authenticates to the receiving repo}
- **Key operations**: {2–4 bullet points of primary interactions}

*(Repeat block for each directional dependency)*

## Authentication Boundary

- **Token issuer**: `{repo-name}` — {mechanism, e.g. JWT signed with RS256}
- **Token consumers**: `{repo-name}`, `{repo-name}` — validate via {method}
- **Token location**: `{e.g. Authorization: Bearer <token>}`
- **Session storage**: {where sessions are stored, e.g. httpOnly cookie in frontend}
- **Public routes** (no auth required): {list or pattern, e.g. `GET /api/v1/health`}

## Shared Types and Data Models

| Concept | Source of Truth | Consumed By |
|---------|-----------------|-------------|
| `{TypeName}` | `{repo-name}/{path}` | `{repo-name}`, `{repo-name}` |

*(If no shared type library exists: "Types are duplicated — consider extracting to a shared package.")*

## Deployment Dependencies

- **Deploy order**: {repo} before {repo} when {condition}
- **Environment parity**: {list envs that must be in sync, e.g. API_BASE_URL}
- **Shared infrastructure**: {CDN, DB, message broker — what is shared}

## Cross-Repo Development Workflow

- **Feature spanning repos**: open linked issues/specs in both repos; implement API contract first
- **Contract changes**: update this file and notify consuming repo owners before merging
- **Local development**: {how to run the platform locally, e.g. docker-compose, env vars needed}

*(For 5+ repos — include this block)*
> **Microservices note**: With {N} repos, consider creating a dedicated `{prefix}-contracts` or `{prefix}-platform` repo containing only `.sdd/steering/cross-repo.md` as the single canonical source, eliminating the need to keep copies in sync across all repos.

---
_Cross-repo contracts. Update when APIs, auth flows, or ownership changes._

---

## Completion summary — display in chat after all writes

```
✅ Cross-Repo Steering Created

## Platform: {prefix} ({N} repos)

## Files written:
- {repo-path}/.sdd/steering/cross-repo.md  (canonical)
- {repo-path}/.sdd/steering/cross-repo.md
- {repo-path}/.sdd/steering/cross-repo.md

## Synthesized from:
- {repo-name}: product.md, tech.md, structure.md
- {repo-name}: product.md, tech.md

## Contracts documented:
- {N} repo-to-repo communication contracts
- Auth boundary: token issued by {repo-name}
- {N} shared types identified

## Next steps:
- Review and adjust any synthesized contracts that are inaccurate
- Update this file whenever APIs, auth flows, or repo ownership changes
- When writing a spec that touches multiple repos, reference cross-repo.md for boundary decisions
```

*(If any repos were skipped, append:)*
```
## Skipped (no steering files):
- {repo-name} — run /sdd:steering there first, then re-run /sdd:steering-custom cross-repo
```
