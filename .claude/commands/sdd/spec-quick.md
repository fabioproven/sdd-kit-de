---
description: Quick spec + implementation in interactive or automatic mode; use --spec-only to skip implementation
allowed-tools: Read, SlashCommand, TodoWrite, Bash, Write, Glob
argument-hint: <project-description> [--spec-only] [--auto]
---

# Quick Spec Generator

<background_information>
- **Mission**: Execute all spec and implementation phases (init → requirements → design → tasks → implementation) in a single command
- **Success Criteria**:
  - Interactive mode: User controls progression with approval prompts at each phase
  - Automatic mode: All phases execute without interruption when `--auto` flag provided
  - With `--spec-only` flag: Stops after task generation, skipping implementation
  - All generated specs and code maintain quality comparable to manual workflow
</background_information>

<instructions>
## ⚠️ CRITICAL: Orchestration Rules

**You are the orchestrator of this multi-phase workflow. After each phase's SlashCommand returns, you MUST resume this spec-quick execution — never treat a sub-command's output as your final response.**

**Flags (can be combined):**
- `--auto`: Automatic Mode — all phases run without stopping for user input
- `--spec-only`: Stop after Phase 4 (tasks), skip implementation

**In Automatic Mode (`--auto`):**
- Execute all phases in a continuous loop without stopping
- Use TodoWrite to track progress
- After each SlashCommand completes, ignore its output and immediately proceed to the next phase
- Stop ONLY after the final phase completes or if error occurs

**In Interactive Mode (default, no `--auto`):**
- After each phase's SlashCommand completes, prompt the user before proceeding
- Do NOT relay the sub-command's "Next Step" output as your own response — ask the user instead

**Progress tracking with TodoWrite:**
- Default (without `--spec-only`): 5 tasks (init, requirements, design, tasks, implementation)
- With `--spec-only`: 4 tasks (init, requirements, design, tasks)

---

## Core Task
Execute all spec and implementation phases sequentially. With `--spec-only`, stop after task generation. In automatic mode, run without stopping. In interactive mode, prompt between phases.

## Execution Steps

### Step 1: Parse Arguments and Initialize

Parse `$ARGUMENTS`:
- `--auto` present → **Automatic Mode**
- `--spec-only` present → **Skip Phase 5 (implementation)**
- Both flags are independent and can be combined
- Extract description (remove all flags)

Examples:
```
"User profile"               → interactive, 5 phases (full)
"User profile --auto"        → automatic, 5 phases (full)
"User profile --spec-only"   → interactive, 4 phases (spec only)
"User profile --auto --spec-only" → automatic, 4 phases (spec only)
```

**Create TodoWrite task list** based on flags:

Default (without `--spec-only`):
```json
[
  {"content": "Initialize spec", "activeForm": "Initializing spec", "status": "pending"},
  {"content": "Generate requirements", "activeForm": "Generating requirements", "status": "pending"},
  {"content": "Generate design", "activeForm": "Generating design", "status": "pending"},
  {"content": "Generate tasks", "activeForm": "Generating tasks", "status": "pending"},
  {"content": "Execute implementation", "activeForm": "Executing implementation", "status": "pending"}
]
```

With `--spec-only`:
```json
[
  {"content": "Initialize spec", "activeForm": "Initializing spec", "status": "pending"},
  {"content": "Generate requirements", "activeForm": "Generating requirements", "status": "pending"},
  {"content": "Generate design", "activeForm": "Generating design", "status": "pending"},
  {"content": "Generate tasks", "activeForm": "Generating tasks", "status": "pending"}
]
```

Display mode banner and proceed to Step 2.

### Step 2: Execute Phase Loop

---

#### Phase 1: Initialize Spec (Direct Implementation)

**Update TodoWrite**: Mark task 1 as `in_progress`.

**Core Logic**:

1. **Generate Feature Name**:
   - Convert description to kebab-case
   - Example: "User profile with avatar upload" → "user-profile-avatar-upload"
   - Keep name concise (2-4 words ideally)

2. **Check Uniqueness**:
   - Use Glob to check `.sdd/specs/*/`
   - If feature name exists, append `-2`, `-3`, etc.

3. **Create Directory**:
   - Use Bash: `mkdir -p .sdd/specs/{feature-name}`

4. **Initialize Files from Templates**:

   a. Read templates:
   ```
   - .sdd/settings/templates/specs/init.json
   - .sdd/settings/templates/specs/requirements-init.md
   ```

   b. Replace placeholders:
   ```
   {{FEATURE_NAME}} → feature-name
   {{TIMESTAMP}} → current ISO 8601 timestamp (use `date -u +"%Y-%m-%dT%H:%M:%SZ"`)
   {{PROJECT_DESCRIPTION}} → description
   ```

   c. Write files using Write tool:
   ```
   - .sdd/specs/{feature-name}/spec.json
   - .sdd/specs/{feature-name}/requirements.md
   ```

5. **Update TodoWrite**: Mark task 1 as `completed`, task 2 as `in_progress`.

6. **Output Progress**:
   ```
   ✅ Spec initialized at .sdd/specs/{feature-name}/
   ```

**Automatic Mode**: IMMEDIATELY continue to Phase 2.

**Interactive Mode**: Prompt "Continue to requirements generation? (yes/no)"
- If "no": Stop, show current state
- If "yes": Continue to Phase 2

---

#### Phase 2: Generate Requirements

**Task 2 is already `in_progress` from Phase 1.**

**Execute SlashCommand**:
```
/sdd:spec-requirements {feature-name}
```

Once the SlashCommand finishes, **ignore any "Next Step" instructions in its output** — those are for standalone command usage only. You are the orchestrator: immediately resume this spec-quick flow.

**Update TodoWrite**: Mark task 2 as `completed`, task 3 as `in_progress`.

**Output Progress**:
```
✅ Requirements generated → Continuing to design...
```

**Automatic Mode**: IMMEDIATELY continue to Phase 3 — do NOT stop.

**Interactive Mode**: Prompt "Continue to design generation? (yes/no)"
- If "no": Stop, show current state
- If "yes": Continue to Phase 3

---

#### Phase 3: Generate Design

**Task 3 is already `in_progress` from Phase 2.**

**Execute SlashCommand**:
```
/sdd:spec-design {feature-name} -y
```

Note: `-y` flag auto-approves requirements.

Once the SlashCommand finishes, **ignore any "Next Step" instructions in its output** — those are for standalone command usage only. You are the orchestrator: immediately resume this spec-quick flow.

**Update TodoWrite**: Mark task 3 as `completed`, task 4 as `in_progress`.

**Output Progress**:
```
✅ Design generated → Continuing to tasks...
```

**Automatic Mode**: IMMEDIATELY continue to Phase 4 — do NOT stop.

**Interactive Mode**: Prompt "Continue to tasks generation? (yes/no)"
- If "no": Stop, show current state
- If "yes": Continue to Phase 4

---

#### Phase 4: Generate Tasks

**Task 4 is already `in_progress` from Phase 3.**

**Execute SlashCommand**:
```
/sdd:spec-tasks {feature-name} -y
```

Note: `-y` flag auto-approves design.

Once the SlashCommand finishes, resume this spec-quick flow immediately.

**Update TodoWrite**: Mark task 4 as `completed`.

**If `--spec-only` flag IS set** — loop is done:
- Output final spec-only completion summary (see Output Description section) and exit.

**If `--spec-only` flag is NOT set** — continue to Phase 5:
- Mark task 5 as `in_progress`
- Output Progress:
  ```
  ✅ Tasks generated → Continuing to implementation...
  ```
- **Automatic Mode**: IMMEDIATELY continue to Phase 5 — do NOT stop.
- **Interactive Mode**: Prompt "Continue to implementation? ⚠️ This will modify your codebase. (yes/no)"
  - If "no": Stop, output spec-only completion summary, suggest `/sdd:spec-impl {feature-name}`
  - If "yes": Continue to Phase 5

---

#### Phase 5: Execute Implementation (skipped when `--spec-only` is set)

**Task 5 is already `in_progress` from Phase 4.**

**Execute SlashCommand**:
```
/sdd:spec-impl {feature-name}
```

Note: Runs all pending implementation tasks. This modifies your codebase.

Once the SlashCommand finishes, resume this spec-quick flow immediately.

**Update TodoWrite**: Mark task 5 as `completed`.

**All 5 tasks complete. Loop is DONE.**

Output full completion summary (see Output Description section) and exit.

---

## Important Constraints

### Phase 1 Implementation Notes
- Feature name generation should be deterministic and readable
- Always check for conflicts before creating directory
- Validate templates exist before reading
- Use ISO 8601 format for timestamp: `YYYY-MM-DDTHH:MM:SSZ`

### Automatic Mode Behavior
- Do NOT stop between phases
- Do NOT wait for user input
- After each SlashCommand returns, discard its output and immediately run the next phase
- Update TodoWrite after each phase to maintain progress visibility
- Continue loop until all phases complete

### Interactive Mode Behavior
- Prompt user after each phase
- Wait for "yes/y" or "no/n" response
- If "no": Stop gracefully, show completed phases
- If "yes": Continue to next phase
- Phase 5 prompt includes an explicit codebase-modification warning

### Implementation Phase Notes
- `spec-impl` modifies your codebase — review changes before committing
- Best suited for simple, well-defined features; for complex features run tasks individually with `/sdd:spec-impl {feature} {task}`
- Use `--spec-only` for specs with many tasks or complex integrations where you prefer to run implementation manually

### Error Handling
- Any phase failure stops the workflow
- Display error and current state
- Suggest manual recovery command

</instructions>

## Tool Guidance

### Phase 1 Tools
- **Glob**: Check `.sdd/specs/*/` for existing feature names
- **Bash**: Create directory with `mkdir -p`, generate timestamp with `date -u`
- **Read**: Fetch templates from `.sdd/settings/templates/specs/`
- **Write**: Create `spec.json` and `requirements.md` in spec directory

### Phase 2-4 Tools
- **SlashCommand**: Execute `/sdd:spec-requirements`, `/sdd:spec-design`, `/sdd:spec-tasks`

### Phase 5 Tools
- **SlashCommand**: Execute `/sdd:spec-impl`

### TodoWrite Usage
- Initialize with 5 tasks (default) or 4 tasks (with `--spec-only`)
- Update after each phase: current task `completed`, next task `in_progress`
- Provides visual progress tracking in UI

## Output Description

### Mode Banners

**Interactive Mode (full)**:
```
🚀 Quick Spec + Implementation (Interactive Mode)

You will be prompted at each phase, including before implementation.
⚠️ Skips gap analysis and design validation.
⚠️ Implementation phase will modify your codebase.
```

**Interactive Mode (--spec-only)**:
```
🚀 Quick Spec Generation (Interactive Mode)

You will be prompted at each phase. Stops after task generation.
⚠️ Skips gap analysis and design validation.
```

**Automatic Mode (full)**:
```
🚀 Quick Spec + Implementation (Automatic Mode)

All phases execute automatically without prompts, including implementation.
⚠️ Skips all validations and reviews.
⚠️ Implementation phase will modify your codebase automatically.
```

**Automatic Mode (--spec-only)**:
```
🚀 Quick Spec Generation (Automatic Mode)

All spec phases execute automatically. Stops after task generation.
⚠️ Skips all validations and reviews.
```

### Intermediate Output

After each phase, show brief progress:
```
✅ Spec initialized at .sdd/specs/{feature}/
✅ Requirements generated → Continuing to design...
✅ Design generated → Continuing to tasks...
✅ Tasks generated → Continuing to implementation...
```

### Final Completion Summary

Provide output in the language specified in `spec.json`.

**Full completion (default, without `--spec-only`)**:
```
✅ Quick Spec + Implementation Complete!

## Generated Files:
- .sdd/specs/{feature}/spec.json
- .sdd/specs/{feature}/requirements.md ({X} requirements)
- .sdd/specs/{feature}/design.md ({Y} components, {Z} endpoints)
- .sdd/specs/{feature}/tasks.md ({N} tasks)

## Implementation:
- All tasks executed via `/sdd:spec-impl`
- Review code changes before committing

⚠️ Quick generation skipped:
- `/sdd:validate-gap` - Gap analysis (integration check)
- `/sdd:validate-design` - Design review (architecture validation)
- `/sdd:validate-impl` - Implementation validation

## Next Steps:
1. Review all code changes
2. Run your test suite
3. Optional: `/sdd:validate-impl {feature}` - Verify implementation against spec
```

**Spec-only completion (with `--spec-only`)**:
```
✅ Quick Spec Generation Complete!

## Generated Files:
- .sdd/specs/{feature}/spec.json
- .sdd/specs/{feature}/requirements.md ({X} requirements)
- .sdd/specs/{feature}/design.md ({Y} components, {Z} endpoints)
- .sdd/specs/{feature}/tasks.md ({N} tasks)

⚠️ Quick generation skipped:
- `/sdd:validate-gap` - Gap analysis (integration check)
- `/sdd:validate-design` - Design review (architecture validation)

## Next Steps:
1. Review generated specs (especially design.md)
2. Optional validation:
   - `/sdd:validate-gap {feature}` - Check integration with existing codebase
   - `/sdd:validate-design {feature}` - Verify architecture quality
3. Start implementation: `/sdd:spec-impl {feature}`
```

## Safety & Fallback

### Argument Parsing
- Use `$ARGUMENTS` to parse (NOT `$1`, `$2`)
- Handle spaces in descriptions correctly
- `--auto` and `--spec-only` are independent flags; both can be present
- Example: `"Multi word description --auto --spec-only"` → extract all three parts correctly

### Feature Name Generation
- Convert to lowercase kebab-case
- Remove special characters
- If ambiguous, prefer descriptive over short
- If conflict exists, append `-2`, `-3`, etc.

### Error Scenarios

**Template Missing**:
- Check `.sdd/settings/templates/specs/` exists
- Report specific missing file
- Exit with error

**Directory Creation Failed**:
- Check permissions
- Report error with path
- Exit with error

**Phase Execution Failed** (Phase 2-5):
- Stop workflow
- Show current state and completed phases
- Suggest: "Continue manually from `/sdd:spec-{next-phase} {feature}`"

**User Cancellation at Phase 5** (Interactive Mode):
- Stop gracefully after tasks
- Output spec-only completion summary
- Suggest: `/sdd:spec-impl {feature}` to run implementation later

### Usage Guidance

**Use default (full workflow)** when:
- Simple, well-defined feature (CRUD, basic UI component)
- Prototyping / proof-of-concept
- Spec will have ≤5 tasks
- Clean, isolated feature with no complex integrations

**Use `--auto`** when:
- Same as above, but fully hands-off
- Confident the spec can be generated and implemented without review

**Use `--spec-only`** when:
- Complex feature where you want to review the spec before implementing
- Spec may have many tasks (run implementation task-by-task with `/sdd:spec-impl {feature} {task}`)
- Need to validate gap or design before implementing

**Use Standard Workflow** (NOT spec-quick) when:
- Complex integration with existing systems
- Security-critical features
- Production-ready quality required
- Need gap analysis or design validation
