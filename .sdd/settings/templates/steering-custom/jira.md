<!--
SETUP GUIDE — display this in chat before writing the file, then do not include it in the output.

## Jira Integration Setup

### Step 1 — Jira Project

**Existing project** — locate two values you will need:
- **Project key**: visible in the URL as `.../projects/KEY/...` or under Project Settings → Details.
- **Instance URL**: `https://<your-site-name>.atlassian.net`

**New free project** — create one in ~2 minutes:
1. Go to https://www.atlassian.com/software/jira/free and click **Get it free**.
2. Sign up or log in (Google sign-in accepted).
3. Create a **Jira Software** project — choose Scrum or Kanban.
4. Note the **project key** shown during creation (e.g. `SDD`).
5. Your instance URL is `https://<your-site-name>.atlassian.net`.

> The free tier supports up to 10 users and full REST API access.

### Step 2 — Shared Configuration (Team Lead — do this once)

Open `.sdd/steering/jira.md` (just created) and fill in the **Project Settings** block:
- `jira_base_url` → your instance URL, e.g. `https://myteam.atlassian.net`
- `jira_project_key` → your project key, e.g. `SDD`

Commit and push `.sdd/steering/jira.md`:
```
git add .sdd/steering/jira.md
git commit -m "chore: activate Jira integration"
git push
```
All team members who pull will inherit the shared configuration automatically.

### Step 3 — Personal Credentials (Every Team Member)

Each person must generate their own API token and set two env vars locally.
These values are **never** stored in any file.

**Get your API token:**
Go to https://id.atlassian.com/manage-profile/security/api-tokens → Create API token → label it `ai-sdd` → copy the value.

**Linux / macOS** — run these commands in your terminal:
```bash
# Bash users
echo 'export JIRA_EMAIL="you@example.com"' >> ~/.bashrc
echo 'export JIRA_TOKEN="your-api-token"' >> ~/.bashrc
source ~/.bashrc

# Zsh users (replace the three lines above with):
# echo 'export JIRA_EMAIL="you@example.com"' >> ~/.zshrc
# echo 'export JIRA_TOKEN="your-api-token"' >> ~/.zshrc
# source ~/.zshrc
```

**Windows (PowerShell — permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable("JIRA_EMAIL","you@example.com","User")
[System.Environment]::SetEnvironmentVariable("JIRA_TOKEN","your-api-token","User")
```
Restart your terminal after running these commands.

> ⚠️ Never commit credential values to version control.

**Next step:** Run `/sdd:spec-init <feature>` to start your first Jira-synced specification.
-->

# Jira Cloud Integration

## Project Settings
<!-- Fill in and commit — safe to share with your team -->

```yaml
jira_base_url: ""              # REQUIRED — e.g. https://myteam.atlassian.net
jira_project_key: ""           # REQUIRED — e.g. SDD
jira_epic_link_field: "parent" # "parent" for modern projects, "customfield_10014" for legacy classic
jira_component: ""             # OPTIONAL — component name to assign to all created issues
jira_labels: ""                # OPTIONAL — comma-separated labels, e.g. "ai-sdd,spec-driven"
jira_story_points_field: ""    # OPTIONAL — custom field name, e.g. "customfield_10016"
jira_story_points_default: ""  # OPTIONAL — default story points value, e.g. "3"
```

## Customizations
<!-- Optional: write plain English instructions here to change how the AI behaves.
     Examples:
     - "Always assign new Stories to the current active sprint."
     - "Set priority to High for all Epics."
     - "Skip Jira sync during spec-design."
     - "Add the label 'backend' to all issues created for features under src/api/."
-->

---
<!-- ═══════════════════════════════════════════════════════════════════
     AGENT INSTRUCTIONS — Read and follow carefully. Do not modify.
     ═══════════════════════════════════════════════════════════════════ -->

## Agent Instructions

### Execution Rules

**Never write credentials to any file.** Do not create `.ps1` scripts, `.sh` scripts, or any
other temporary file to execute an HTTP call. All API calls must run as inline shell commands
that read `JIRA_EMAIL` and `JIRA_TOKEN` directly from environment variables at runtime.

**Never print credential values to the console.** Do not run `printenv JIRA_EMAIL`,
`printenv JIRA_TOKEN`, `echo $JIRA_EMAIL`, `echo $JIRA_TOKEN`, or any command that outputs
the value of a credential variable. Only check whether a variable is set/non-empty.

**Inline call shape (bash — used on all platforms, including Windows):**

```bash
curl -s -w "\n%{http_code}" -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"fields":{...}}' \
  "$JIRA_BASE_URL/rest/api/3/issue"
```

All supported AI agents invoke shell commands via bash, even on Windows. Never use PowerShell for API calls.

### Phase Completion Gate (mandatory)

Jira sync is part of every phase. Do not output the phase completion message until the Jira
step for that phase has run.

| Phase completed | Jira action | spec.json field written |
|---|---|---|
| `spec-init` | Create Epic | `integrations.jira.epic_key` |
| `spec-requirements` | Create Stories (one per requirement) | `integrations.jira.story_keys` |
| `spec-design` (approved or `-y`) | Update Epic description | — |
| `spec-tasks` | Create Subtasks (one per N.M task) | `integrations.jira.subtask_keys` |

If Jira is misconfigured or credentials are missing, display the recovery message and continue
with the phase output. The phase output is never suppressed.

### Before Every Sync

1. Check that `JIRA_EMAIL` and `JIRA_TOKEN` env vars are set — check only, never print their values.
   Always use bash (all supported AI agents invoke shell commands via bash, even on Windows):
   `[ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_TOKEN" ] && echo "ok" || echo "missing"`
2. If either is unset or empty, display and skip all Jira operations:

   > **Jira sync skipped — credentials not set**
   >
   > **Linux / macOS** (Bash): `echo 'export JIRA_EMAIL="you@example.com"' >> ~/.bashrc && echo 'export JIRA_TOKEN="your-api-token"' >> ~/.bashrc && source ~/.bashrc`
   > **Linux / macOS** (Zsh): `echo 'export JIRA_EMAIL="you@example.com"' >> ~/.zshrc && echo 'export JIRA_TOKEN="your-api-token"' >> ~/.zshrc && source ~/.zshrc`
   >
   > **Windows (PowerShell — permanent, restart terminal after)**:
   > `[System.Environment]::SetEnvironmentVariable("JIRA_EMAIL","you@example.com","User")`
   > `[System.Environment]::SetEnvironmentVariable("JIRA_TOKEN","your-api-token","User")`
   >
   > ⚠️ Never commit credential values to any file.

3. If `jira_base_url` or `jira_project_key` are empty:
   display "Jira sync skipped — fill in Project Settings in `.sdd/steering/jira.md`" and skip.

### Error Handling

- **HTTP 2xx**: Write returned `key` to `spec.json`, continue.
- **HTTP 429**: Display "⚠️ Jira rate limit — wait `<Retry-After>` seconds and re-run." Skip remaining.
- **HTTP 4xx/5xx**: Display `⚠️ Jira <OPERATION> failed — HTTP <STATUS>: <excerpt>`. Continue with next item.
- Show warnings **after** normal phase output.

> **Classic project 400 "Epic Name required"**: Add `customfield_10011: "Epic Name"` to Project Settings and re-run.

### Sync Summary

After all Jira operations for a phase, append:
```
Jira sync: N created | N updated | N skipped | N failed
```

---

### Phase: spec-init → Create Epic

**Trigger**: when `spec-init` completes successfully.

1. Check `spec.json` → `integrations.jira.epic_key`. If set, skip: "Jira: Epic `<key>` already exists."
2. Run Before Every Sync checks.
3. Build Epic description as ADF from the project description in `requirements.md`.
4. Create Epic:
   ```bash
   curl -s -w "\n%{http_code}" -u "$JIRA_EMAIL:$JIRA_TOKEN" \
     -X POST -H "Content-Type: application/json" \
     -d "{\"fields\":{\"project\":{\"key\":\"$PROJECT_KEY\"},\"summary\":\"$FEATURE_TITLE\",\"issuetype\":{\"name\":\"Epic\"},\"description\":$ADF_DESC}}" \
     "$JIRA_BASE_URL/rest/api/3/issue"
   ```
   `$FEATURE_TITLE` = `spec.json.feature_name` in Title Case.
5. Write returned `key` to `spec.json` → `integrations.jira.epic_key`.

---

### Phase: spec-requirements → Create Stories

**Trigger**: when `spec-requirements` completes successfully.

1. Check `spec.json` → `integrations.jira.epic_key`. If missing, warn and skip.
2. For each `### Requirement N:` in `requirements.md`:
   - Skip if `spec.json` → `integrations.jira.story_keys["N"]` already set.
   - `summary` = objective sentence; `description` = ADF from acceptance criteria.
   - Epic link: `"parent":{"key":"<epic_key>"}` (modern) or `"<jira_epic_link_field>":"<epic_key>"` (legacy).
   - Write returned `key` to `spec.json` → `integrations.jira.story_keys["N"]`.

---

### Phase: spec-design → Update Epic Description

**Trigger**: when `spec-design` completes and `approvals.design.approved` is `true` or `-y` was passed.

1. Check `spec.json` → `integrations.jira.epic_key`. If missing, warn and skip.
2. If design not approved and no `-y`: display "Jira sync skipped — design not approved." Stop.
3. Build ADF description: project description + key technical decisions from `design.md` + spec path.
4. PUT to `$JIRA_BASE_URL/rest/api/3/issue/$EPIC_KEY`. Success = HTTP 204.

---

### Phase: spec-tasks → Create Subtasks

**Trigger**: when `spec-tasks` completes successfully.

1. For each `- [ ] N.M` or `- [x] N.M` in `tasks.md`:
   - Skip if `spec.json` → `integrations.jira.subtask_keys["N.M"]` already set.
   - Parent = `story_keys["N"]`; fallback to `epic_key` if Story missing.
   - Create Subtask; write `key` to `spec.json` → `integrations.jira.subtask_keys["N.M"]`.

### Phase: spec-impl — No Action

No Jira operations during implementation.

---

### Idempotency Rules

Before creating any artefact, check `spec.json` → `integrations.jira` for an existing key.
If found, skip and notify. On user-requested re-sync: update existing artefacts (PUT) instead
of creating duplicates.

`spec.json` structure under `integrations.jira`:
```json
{
  "epic_key": "PROJ-42",
  "story_keys": { "1": "PROJ-43", "2": "PROJ-44" },
  "subtask_keys": { "1.1": "PROJ-50", "1.2": "PROJ-51" }
}
```

---

### On-Demand Sync

When the user asks in natural language ("sync this spec to Jira", "re-sync Jira for feature X"):
1. Read `spec.json`, `requirements.md`, `design.md`, `tasks.md` for the feature.
2. Apply phase instructions above in sequence: spec-init → spec-requirements → spec-design → spec-tasks.
3. Display: `Jira sync: N created | N updated | N skipped | N failed`
