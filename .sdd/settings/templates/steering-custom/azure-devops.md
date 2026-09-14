<!--
SETUP GUIDE — display this in chat before writing the file, then do not include it in the output.

## Azure DevOps Integration Setup

### Step 1 — Azure DevOps Project

**Existing project** — locate two values you will need:
- **Organization name**: visible in the URL as `https://dev.azure.com/<organization>/`.
- **Project name**: the project name shown in the top nav bar.

**New free project** — create one in ~2 minutes:
1. Go to https://dev.azure.com and sign in with a Microsoft or GitHub account.
2. Click **New organization** (or use an existing one).
3. Click **+ New project**, enter a name, choose visibility (Private recommended).
4. Enable **Azure Boards** — it is on by default.
5. Note the **organization name** and **project name** from the URL:
   `https://dev.azure.com/<organization>/<project>/`

> The free tier includes 5 Basic users with full Boards access and unlimited REST API calls.

### Step 2 — Shared Configuration (Team Lead — do this once)

Open `.sdd/steering/azure-devops.md` (just created) and fill in the **Project Settings** block:
- `ado_organization` → your ADO organization name, e.g. `myteam`
- `ado_project` → your project name, e.g. `MyProject`
- `ado_process` → work item process template: `Agile` (User Story/Task), `Scrum` (Product Backlog Item/Task), or `CMMI` (Requirement/Task).
  Not sure? Check under **Project Settings → Overview → Process**.

Commit and push `.sdd/steering/azure-devops.md`:
```
git add .sdd/steering/azure-devops.md
git commit -m "chore: activate Azure DevOps integration"
git push
```
All team members who pull will inherit the shared configuration automatically.

### Step 3 — Personal Credentials (Every Team Member)

Each person must generate their own Personal Access Token (PAT) and set the env var locally.
This value is **never** stored in any file.

**Get your PAT:**
1. Go to https://dev.azure.com → click your profile avatar (top right) → **Personal access tokens**.
2. Click **+ New Token** → name it `ai-sdd`.
3. Set **Expiration** as appropriate (90 days recommended).
4. Under **Scopes**, select **Work Items → Read & write**.
5. Click **Create** and copy the token immediately.

**Linux / macOS** — run these commands in your terminal:
```bash
# Bash users
echo 'export ADO_PAT="your-personal-access-token"' >> ~/.bashrc
source ~/.bashrc

# Zsh users (replace the two lines above with):
# echo 'export ADO_PAT="your-personal-access-token"' >> ~/.zshrc
# source ~/.zshrc
```

**Windows (PowerShell — permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable("ADO_PAT","your-personal-access-token","User")
```
Restart your terminal after running this command.

> ⚠️ Never commit credential values to version control.

**Next step:** Run `/sdd:spec-init <feature>` to start your first ADO-synced specification.
-->

# Azure DevOps Integration

## Project Settings
<!-- Fill in and commit — safe to share with your team -->

```yaml
ado_organization: ""   # REQUIRED — e.g. myteam (from https://dev.azure.com/myteam/)
ado_project: ""        # REQUIRED — e.g. MyProject
ado_process: "Agile"   # REQUIRED — "Agile" | "Scrum" | "CMMI"
ado_area_path: ""      # OPTIONAL — override area path, e.g. "MyProject\Backend"
ado_iteration_path: "" # OPTIONAL — override iteration, e.g. "MyProject\Sprint 1"
ado_tags: ""           # OPTIONAL — semicolon-separated tags, e.g. "ai-sdd;spec-driven"
```

## Customizations
<!-- Optional: write plain English instructions here to change how the AI behaves.
     Examples:
     - "Always assign new Epics to the current iteration."
     - "Set story points to 3 by default for all User Stories."
     - "Skip ADO sync during spec-design."
     - "Add the tag 'backend' to all work items created for features under src/api/."
-->

---
<!-- ═══════════════════════════════════════════════════════════════════
     AGENT INSTRUCTIONS — Read and follow carefully. Do not modify.
     ═══════════════════════════════════════════════════════════════════ -->

## Agent Instructions

### Work Item Type Mapping

ADO work item types vary by process template. Always read `ado_process` before creating work items:

| SDD Phase | Agile | Scrum | CMMI |
|---|---|---|---|
| `spec-init` | Epic | Epic | Epic |
| `spec-requirements` | User Story | Product Backlog Item | Requirement |
| `spec-tasks` | Task | Task | Task |

The ADO REST API requires a literal `$` prefix on the work item type in the URL path.
This `$` is **not** a bash variable — it is part of the ADO URL syntax.
Always assign the type using **single quotes** so bash never expands it:

```bash
ITEM_TYPE='$Epic'                       # Agile / Scrum / CMMI
ITEM_TYPE='$User%20Story'               # Agile
ITEM_TYPE='$Product%20Backlog%20Item'   # Scrum
ITEM_TYPE='$Requirement'                # CMMI
ITEM_TYPE='$Task'                       # All processes
```

Then reference `${ITEM_TYPE}` in the URL (shown in the call shape below).

### Execution Rules

**Never write credentials to any file.** Do not create `.ps1` scripts, `.sh` scripts, or any
other temporary file to execute an HTTP call. All API calls must run as inline shell commands
that read `ADO_PAT` directly from environment variables at runtime.

**Never print credential values to the console.** Do not run `printenv ADO_PAT`,
`echo $ADO_PAT`, or any command that outputs the value of a credential variable.
Only check whether a variable is set/non-empty.

**Authentication:** ADO uses HTTP Basic auth with an empty username and the PAT as the password.
Encode as Base64: `:<PAT>` (note the colon prefix with empty username).

**Content-Type:** All create/update calls use `application/json-patch+json`.

**Inline call shape (bash — used on all platforms, including Windows):**

```bash
ITEM_TYPE='$Epic'   # single quotes — keeps the literal $ that ADO requires; never use double quotes here
B64=$(echo -n ":$ADO_PAT" | base64 | tr -d '\n')
curl -s -w "\n%{http_code}" \
  -X POST -H "Content-Type: application/json-patch+json" \
  -H "Authorization: Basic $B64" \
  -d '[{"op":"add","path":"/fields/System.Title","value":"..."}]' \
  "https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis/wit/workitems/${ITEM_TYPE}?api-version=7.1"
```

All supported AI agents invoke shell commands via bash, even on Windows. Never use PowerShell for API calls.

### Phase Completion Gate (mandatory)

ADO sync is part of every phase. Do not output the phase completion message until the ADO
step for that phase has run.

| Phase completed | ADO action | spec.json field written |
|---|---|---|
| `spec-init` | Create Epic | `integrations.ado.epic_id` |
| `spec-requirements` | Create User Stories / PBIs / Requirements (one per requirement) | `integrations.ado.story_ids` |
| `spec-design` (approved or `-y`) | Update Epic description | — |
| `spec-tasks` | Create Tasks (one per N.M task) | `integrations.ado.task_ids` |

If ADO is misconfigured or credentials are missing, display the recovery message and continue
with the phase output. The phase output is never suppressed.

### Before Every Sync

1. Check that the `ADO_PAT` env var is set — check only, never print its value.
   Always use bash (all supported AI agents invoke shell commands via bash, even on Windows):
   `[ -n "$ADO_PAT" ] && echo "ok" || echo "missing"`
2. If unset or empty, display and skip all ADO operations:

   > **ADO sync skipped — credentials not set**
   >
   > **Linux / macOS** (Bash): `echo 'export ADO_PAT="your-personal-access-token"' >> ~/.bashrc && source ~/.bashrc`
   > **Linux / macOS** (Zsh): `echo 'export ADO_PAT="your-personal-access-token"' >> ~/.zshrc && source ~/.zshrc`
   >
   > **Windows (PowerShell — permanent, restart terminal after)**:
   > `[System.Environment]::SetEnvironmentVariable("ADO_PAT","your-personal-access-token","User")`
   >
   > ⚠️ Never commit credential values to any file.

3. If `ado_organization` or `ado_project` are empty:
   display "ADO sync skipped — fill in Project Settings in `.sdd/steering/azure-devops.md`" and skip.

### Error Handling

- **HTTP 200**: Write returned `id` to `spec.json`, continue.
- **HTTP 429**: Display "⚠️ ADO rate limit — wait and re-run." Skip remaining.
- **HTTP 4xx/5xx**: Display `⚠️ ADO <OPERATION> failed — HTTP <STATUS>: <excerpt>`. Continue with next item.
- Show warnings **after** normal phase output.

> **"VS402375: Work item type 'X' does not exist"**: Check `ado_process` — ensure it matches your project's process template (Agile/Scrum/CMMI).

### Sync Summary

After all ADO operations for a phase, append:
```
ADO sync: N created | N updated | N skipped | N failed
```

---

### Phase: spec-init → Create Epic

**Trigger**: when `spec-init` completes successfully.

1. Check `spec.json` → `integrations.ado.epic_id`. If set, skip: "ADO: Epic `#<id>` already exists."
2. Run Before Every Sync checks.
3. Build the request body as a JSON Patch document:
   ```json
   [
     {"op":"add","path":"/fields/System.Title","value":"<FEATURE_TITLE>"},
     {"op":"add","path":"/fields/System.Description","value":"<DESCRIPTION_HTML>"},
     {"op":"add","path":"/fields/System.Tags","value":"<ado_tags>"}
   ]
   ```
   `<FEATURE_TITLE>` = `spec.json.feature_name` in Title Case.
   `<DESCRIPTION_HTML>` = project description from `requirements.md` as plain HTML.
   Omit the Tags field if `ado_tags` is empty.
   Include `/fields/System.AreaPath` and `/fields/System.IterationPath` ops if `ado_area_path` / `ado_iteration_path` are set.
4. Set `ITEM_TYPE='$Epic'` (single quotes) and POST to `"https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis/wit/workitems/${ITEM_TYPE}?api-version=7.1"`
5. Write returned `id` (integer) to `spec.json` → `integrations.ado.epic_id`.

---

### Phase: spec-requirements → Create User Stories / PBIs / Requirements

**Trigger**: when `spec-requirements` completes successfully.

1. Check `spec.json` → `integrations.ado.epic_id`. If missing, warn and skip.
2. Determine work item type from `ado_process`: `User Story` (Agile), `Product Backlog Item` (Scrum), `Requirement` (CMMI).
3. For each `### Requirement N:` in `requirements.md`:
   - Skip if `spec.json` → `integrations.ado.story_ids["N"]` already set.
   - `System.Title` = objective sentence of the requirement.
   - `System.Description` = acceptance criteria as plain HTML.
   - Link to Epic via a `System.LinkTypes.Hierarchy-Reverse` relation:
     ```json
     {"op":"add","path":"/relations/-","value":{
       "rel":"System.LinkTypes.Hierarchy-Reverse",
       "url":"https://dev.azure.com/<org>/_apis/wit/workItems/<epic_id>"
     }}
     ```
   - Set `ITEM_TYPE='$User%20Story'` (or the appropriate type in single quotes) and POST to `"https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis/wit/workitems/${ITEM_TYPE}?api-version=7.1"`
   - Write returned `id` to `spec.json` → `integrations.ado.story_ids["N"]`.

---

### Phase: spec-design → Update Epic Description

**Trigger**: when `spec-design` completes and `approvals.design.approved` is `true` or `-y` was passed.

1. Check `spec.json` → `integrations.ado.epic_id`. If missing, warn and skip.
2. If design not approved and no `-y`: display "ADO sync skipped — design not approved." Stop.
3. Build PATCH body: project description + key technical decisions from `design.md` + spec path, as plain HTML.
4. PATCH to `https://dev.azure.com/<org>/<project>/_apis/wit/workitems/<epic_id>?api-version=7.1`
   using `[{"op":"replace","path":"/fields/System.Description","value":"<HTML>"}]`.
   Success = HTTP 200.

---

### Phase: spec-tasks → Create Tasks

**Trigger**: when `spec-tasks` completes successfully.

1. For each `- [ ] N.M` or `- [x] N.M` in `tasks.md`:
   - Skip if `spec.json` → `integrations.ado.task_ids["N.M"]` already set.
   - `System.Title` = task description text.
   - Parent = `story_ids["N"]`; fallback to `epic_id` if Story missing.
   - Link parent via `System.LinkTypes.Hierarchy-Reverse` relation (same shape as Stories above).
   - Set `ITEM_TYPE='$Task'` (single quotes) and POST to `"https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis/wit/workitems/${ITEM_TYPE}?api-version=7.1"`
   - Write returned `id` to `spec.json` → `integrations.ado.task_ids["N.M"]`.

### Phase: spec-impl — No Action

No ADO operations during implementation.

---

### Idempotency Rules

Before creating any artefact, check `spec.json` → `integrations.ado` for an existing id.
If found, skip and notify. On user-requested re-sync: update existing artefacts (PATCH) instead
of creating duplicates.

`spec.json` structure under `integrations.ado`:
```json
{
  "epic_id": 42,
  "story_ids": { "1": 43, "2": 44 },
  "task_ids": { "1.1": 50, "1.2": 51 }
}
```

---

### On-Demand Sync

When the user asks in natural language ("sync this spec to ADO", "re-sync Azure DevOps for feature X"):
1. Read `spec.json`, `requirements.md`, `design.md`, `tasks.md` for the feature.
2. Apply phase instructions above in sequence: spec-init → spec-requirements → spec-design → spec-tasks.
3. Display: `ADO sync: N created | N updated | N skipped | N failed`
