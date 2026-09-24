---
description: Execute spec tasks using TDD methodology
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Grep, Glob, LS, WebFetch, WebSearch
argument-hint: <feature-name> [task-numbers]
---

# Implementation Task Executor

<background_information>
- **Mission**: Execute implementation tasks using Test-Driven Development methodology based on approved specifications
- **Success Criteria**:
  - All tests written before implementation code
  - Code passes all tests with no regressions
  - Tasks marked as completed in tasks.md
  - Implementation aligns with design and requirements
</background_information>

<instructions>
## Core Task
Execute implementation tasks for feature **$1** using Test-Driven Development.

## Execution Steps

### Step 0: Approval posture — read the config, don't ask

Read `.sdd/autoapprove.json` (missing or invalid → treat as `enabled: false` for **both** blocks).
Say which mode you are in, in one line, before touching anything:
`mode: manual|loop · executor: self|<agent>(low:no medium:yes high:yes)`.

**Executor — `delegation` block (0.9.0).** `delegation.enabled: true` names an agent
(`delegation.executor`, default `data-engineer`) that **executes** subtasks at the risk levels whose
flag is `true`; the orchestrator executes the others itself. It decides who *types*, never who
*approves*. Absent, invalid or `enabled: false` → executor is **self**, identical to 0.8.0. If the
named agent has no file in `.claude/agents/`, say `executor <name> not installed — executing inline`
and treat as self. Rules: `.sdd/settings/rules/orchestration-loop.md` → "Delegation".

- **`auto_approve.enabled: true` → run the executor↔approver loop from here.** Follow
  `.sdd/settings/rules/orchestration-loop.md` for every task selected in Step 2: decompose into
  atomic subtasks; classify each per `.sdd/settings/rules/risk-classification.md`; call
  `py tools/approval-gate.py check --feature $1 --task <id> --risk <level>` (`python3` if `py` is
  missing) **before every round and obey its exit code** (0 continue · 2 escalate · 3 human); the
  TDD cycle in Step 3 is what the **executor** does inside a round; the `approver` subagent (Task
  tool) judges the result against explicit exit criteria; `record` every verdict. `high` is always
  the human's, whatever the config says. If neither `py` nor `python3` runs, the gate cannot be
  enforced — say so and fall back to manual mode rather than loop unguarded.
- **`false` or absent → manual mode**, identical to the behavior before 0.8.0: no approver loop,
  no ledger; the human gates apply as `CLAUDE.md` describes.

This is the same loop `/sdd:spec-impl-auto` runs — that command remains as an explicit alias.

### Step 1: Load Context

**Read all necessary context**:
- `.sdd/specs/$1/spec.json`, `requirements.md`, `design.md`, `tasks.md`
- **Entire `.sdd/steering/` directory** for complete project memory
- `.sdd/specs/$1/contract-impact.md` and `rollback.md` if present (see
  `.sdd/settings/rules/spec-artifacts.md`) — a task touching a listed consumer contract is `high`

**Validate approvals**:
- Verify tasks are approved in spec.json (stop if not, see Safety & Fallback)

### Step 2: Select Tasks

**Determine which tasks to execute**:
- If `$2` provided: Execute specified task numbers (e.g., "1.1" or "1,2,3")
- Otherwise: Execute all pending tasks (unchecked `- [ ]` in tasks.md)

### Step 3: Execute with TDD

For each selected task, follow Kent Beck's TDD cycle:

1. **RED - Write Failing Test**:
   - Write test for the next small piece of functionality
   - Test should fail (code doesn't exist yet)
   - Use descriptive test names

2. **GREEN - Write Minimal Code**:
   - Implement simplest solution to make test pass
   - Focus only on making THIS test pass
   - Avoid over-engineering

3. **REFACTOR - Clean Up**:
   - Improve code structure and readability
   - Remove duplication
   - Apply design patterns where appropriate
   - Ensure all tests still pass after refactoring

4. **VERIFY - Validate Quality**:
   - All tests pass (new and existing)
   - No regressions in existing functionality
   - Code coverage maintained or improved

**If the subtask is delegated** (its risk level is enabled in `delegation`): do **not** run the
cycle above yourself. Build the **Work Order** (shape in `orchestration-loop.md`: subtask id,
`_Requirements_` IDs, pass/fail exit criteria, risk + worst action, write scope from
`.sdd/write-scope.json`, permitted paths, the `design.md` sections it must honor, profile
`spec-impl`, feedback from the previous round if any) and call the executor agent with the Task
tool. Its **Work Report** is the round's result. With the loop on, hand the report and the criteria
to the `approver`; with the loop off, verify **each** exit criterion yourself against the report's
evidence (open the paths, run the test command) before step 5. A report with `Stopped early: yes`
is handed to the human with its reason — never retried silently. Step 5 below, `spec.json` and
`evidence/` bookkeeping stay **yours**; the executor never marks anything. A `high` subtask reaches
the executor only after the human approved it (and only if `delegation.high` is true).

5. **MARK COMPLETE**:
   - Update checkbox from `- [ ]` to `- [x]` in tasks.md
   - Keep `spec.json.phase` canonical (`.sdd/settings/rules/spec-artifacts.md`): first checked
     task → `implementation-in-progress`; every task checked → `implementation-complete`. Nuance
     goes in `status_note`, never in a new phase string.
   - Proof that a step ran (query results, counts, reconciliations) goes in
     `.sdd/specs/$1/evidence/<what>-<YYYY-MM-DD>.md`, with provenance — not in ad-hoc files.

## Critical Constraints
- **TDD Mandatory**: Tests MUST be written before implementation code
- **Task Scope**: Implement only what the specific task requires
- **Test Coverage**: All new code must have tests
- **No Regressions**: Existing tests must continue to pass
- **Design Alignment**: Implementation must follow design.md specifications
</instructions>

## Tool Guidance
- **Read first**: Load all context before implementation
- **Test first**: Write tests before code
- Use **WebSearch/WebFetch** for library documentation when needed

## Output Description

Provide brief summary in the language specified in spec.json:

1. **Tasks Executed**: Task numbers and test results
2. **Status**: Completed tasks marked in tasks.md, remaining tasks count

**Format**: Concise (under 150 words)

## Safety & Fallback

### Error Scenarios

**Tasks Not Approved or Missing Spec Files**:
- **Stop Execution**: All spec files must exist and tasks must be approved
- **Suggested Action**: "Complete previous phases: `/sdd:spec-requirements`, `/sdd:spec-design`, `/sdd:spec-tasks`"

**Test Failures**:
- **Stop Implementation**: Fix failing tests before continuing
- **Action**: Debug and fix, then re-run

### Task Execution

**Execute specific task(s)**:
- `/sdd:spec-impl $1 1.1` - Single task
- `/sdd:spec-impl $1 1,2,3` - Multiple tasks

**Execute all pending**:
- `/sdd:spec-impl $1` - All unchecked tasks

think
