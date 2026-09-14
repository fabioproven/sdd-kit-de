---
description: Discover available external tools (issue tracker, VCS/PR, data platform) and whether each is native (MCP/CLI) or needs setup
allowed-tools: Bash, Read, Write, Glob, Grep
argument-hint: (no args)
---

# Tooling & Integration Discovery

<background_information>
- **Mission**: Determine which external tools this project can actually drive, and how — so delivery commands (`/prepare-pr`, `/review`, `/data-quality`) act on the right backend instead of guessing.
- **Success Criteria**: A written `integrations.md` classifying each capability area as `mcp-native`, `cli`, `needs-setup`, or `n/a`, with a clear "to enable" list for gaps.
</background_information>

<instructions>
## Core Task
Probe the environment and write `.sdd/steering/integrations.md`.

## Execution Steps
1. **Load the rules**: read `.sdd/settings/rules/tooling-discovery.md` and follow it exactly.
2. **Load the template**: `.sdd/settings/templates/steering-custom/integrations.md`.
3. **Start from declared intent** if the setup interview recorded which git host and tracker the user
   uses (GitHub/GitLab/Azure DevOps/Bitbucket; Jira/Planner/Kanbanize/…). Verify those, don't re-ask.
4. **Probe (read-only) each capability area** — issue tracking, VCS/PR host, data platform, CI/CD:
   - Check your own available tools for a connected **MCP server** for that backend (Atlassian/Jira,
     Microsoft Graph/Planner, Kanbanize, GitHub, Databricks, BigQuery, …).
   - Check for an authenticated **CLI** (`command -v gh|glab|az|databricks|bq|gcloud|jira|snowsql`).
     Note: Bitbucket, Planner and Kanbanize have no CLI — they are API/MCP only.
   - Read the **git remote** (`git remote -v`) to identify the PR host even without a CLI.
   - Read CI config paths (`.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`).
5. **Classify** each area: `mcp-native` > `cli` > `needs-setup` > `n/a`. Prefer MCP when both exist; record both.
   Surface any declared-vs-detected mismatch instead of silently choosing.
6. **Write** `.sdd/steering/integrations.md` from the template. For every `needs-setup`, use the
   connect table in the rules to name the exact CLI/MCP to add.

## Critical Constraints
- **Read-only probing.** Never run a command that creates, deletes, authenticates, or mutates.
- **No secrets.** Record that a credential exists, never its value.
- **Honesty.** `needs-setup` is a valid result — do not overstate a capability.
</instructions>

## Output Description
Confirm the file path and print the capability map as a short table. List open setup items, if any.

## Safety & Fallback
- **Ambiguous host** (multiple remotes): record all, mark the `origin` as primary.
- **Existing integrations.md**: refresh it, preserving human-added notes.
