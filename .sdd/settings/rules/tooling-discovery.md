# Tooling & Integration Discovery Rules

How to find out **which external tools a project can actually drive** — issue tracker, version
control / PR host, data platform — and whether each is reachable **natively** (an MCP server or
CLI is already available) or **needs to be configured** (MCP server to add). Loaded by the
`setup-sdd` skill and by `/sdd:discover-tools`. The result is written to
`.sdd/steering/integrations.md` so every downstream command (`/prepare-pr`, `/review`,
`/data-quality`) knows what it may use.

## Why this exists

Commands that create PRs, post reviews, or run data-quality checks are useless if the agent
guesses at the wrong tool. Discover the real capabilities once, record them, and let every
command read the record instead of re-probing.

## Capability areas to probe

| Area | What we need it for | Common backends |
|------|--------------------|-----------------|
| **Issue tracking** | link specs to tickets, create/update issues | Jira, Microsoft Planner, Kanbanize, Linear, GitHub Issues, Azure Boards |
| **VCS / PR host** | branch, commit, open & review PRs | GitHub, GitLab, Azure DevOps, Bitbucket |
| **Data platform** | run queries, DQ checks, job/run inspection | Databricks, BigQuery/GCP, Snowflake, Postgres |
| **CI/CD** | know where checks run | GitHub Actions, Azure Pipelines, GitLab CI |

Only probe areas the project plausibly uses. A static site has no data platform — record it as
`n/a`, don't invent one.

## Declared intent first, then verify

When the setup interview (`setup-sdd`, step 1.4) already asked the user which VCS host and which
tracker they use, **start from that declared answer** and verify it — don't re-ask, and don't
override it silently:
- Confirm the declared backend is reachable (MCP or CLI). If it is → record method accordingly.
- If the declared backend is named but nothing can reach it → `needs-setup`, and give connect steps.
- If detection contradicts the declaration (user said GitHub, remote is GitLab) → record both and
  surface the mismatch as an open item; the human decides.
When there was no interview, fall back to pure detection below.

## How to detect (in priority order)

For each area, classify the **access method** by checking, in this order:

1. **NATIVE (MCP)** — is there already an MCP tool available to the agent for this backend?
   Inspect the current tool list / connected MCP servers (e.g. an Atlassian/Jira server, a
   GitHub server, a Databricks or BigQuery/Supabase server). If present → method = `mcp-native`.
2. **CLI** — is an authenticated CLI installed? Probe with `command -v` (POSIX) /
   `Get-Command` (PowerShell) **without** running mutating commands:
   - VCS/PR: `gh` (GitHub), `glab` (GitLab), `az repos` (Azure DevOps), Bitbucket (no official CLI —
     rely on `git remote -v` host match + app password), `git remote -v` to read the host
   - Issue: `jira` (Jira), `gh issue` (GitHub Issues), `linear` (Linear); Microsoft Planner and
     Kanbanize have **no CLI** — they are API-only (see connect table below)
   - Data: `databricks`, `bq`, `gcloud`, `snowsql`, `psql`
   If present and authenticated → method = `cli`.
3. **NEEDS-MCP / NEEDS-SETUP** — nothing usable found. Record the recommended MCP server (or
   CLI + auth) to configure, with a one-line pointer. Method = `needs-setup`.

### Connect table (what to configure for `needs-setup`)

| Backend | Preferred access | To enable |
|---------|------------------|-----------|
| GitHub | GitHub MCP or `gh` | install `gh` + `gh auth login`, or add the GitHub MCP server |
| GitLab | `glab` | install `glab` + `glab auth login` |
| Azure DevOps | `az repos` (Azure CLI + devops ext) | `az login` + `az extension add --name azure-devops` |
| Bitbucket | git + app password / REST | create an app password; use the git remote (no CLI) |
| Jira | Atlassian MCP | connect the Atlassian MCP server (Cloud), or a `jira` CLI + API token |
| Microsoft Planner | Microsoft Graph MCP | connect a Microsoft Graph MCP (Planner is Graph API only — no CLI) |
| Kanbanize | Kanbanize REST API / MCP | provide the Kanbanize API token + subdomain (REST/MCP wrapper) |
| Databricks | `databricks` CLI | `databricks configure` with a profile, or a Databricks MCP |
| BigQuery/GCP | `bq` / `gcloud` | `gcloud auth login` + set project |

Detect the **VCS host from the git remote** (`git remote -v`) even when no CLI exists — it tells
you which PR backend the project targets.

## Rules

- **Read-only probing only.** `command -v`, `git remote -v`, listing tools. Never run a command
  that creates, deletes, or authenticates during discovery.
- **Never print or store secrets.** Record *that* a token exists, never its value.
- **Prefer MCP-native over CLI** when both exist (structured, safer), but record both so a
  command can fall back.
- **Be honest about gaps.** A `needs-setup` result is a valid, useful finding — it tells the
  team exactly what to configure before `/prepare-pr` or `/data-quality` will work.

## Output — `.sdd/steering/integrations.md`

Use the steering-custom `integrations.md` template. One row per capability area with:
`area · backend · access method (mcp-native | cli | needs-setup | n/a) · command/tool name ·
note`. End with a short **"To enable"** list for every `needs-setup` row (which MCP server or
CLI to add). This file is the contract the delivery commands rely on.
