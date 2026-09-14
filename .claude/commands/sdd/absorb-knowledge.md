---
description: Harvest durable knowledge from prior AI-agent configs and root docs into steering
allowed-tools: Bash, Read, Write, Glob, Grep
argument-hint: (no args)
---

# Absorb Prior Agent Knowledge

<background_information>
- **Mission**: Reuse project knowledge already written for other AI tools (Cursor, Copilot, Claude, Gemini, Aider, Windsurf) and root docs, instead of starting steering from a blank slate.
- **Success Criteria**: A distilled `inherited-knowledge.md` in steering — conventions, vocabulary, guardrails, and flagged conflicts — with secrets excluded and duplication against code-derived steering avoided.
</background_information>

<instructions>
## Core Task
Sweep prior AI/agent knowledge and write `.sdd/steering/inherited-knowledge.md`.

## Execution Steps
1. **Load the rules**: read `.sdd/settings/rules/knowledge-discovery.md` and follow it.
2. **Load the template**: `.sdd/settings/templates/steering-custom/inherited-knowledge.md`.
3. **Sweep** (glob + read; skip `node_modules`, `.git`, build output):
   - Root markdown: `*.md`, `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `docs/`, `adr/`, `rfcs/`
   - Per-tool config: `.claude/`, `.cursor/` + `.cursorrules`, `.github/copilot-instructions.md`, `.windsurfrules`, `.continue/`, `.aider*`, `.agent/`, `.assistant/`, `.ai/`
   - For heavy repo search across many files, delegate to the `code-explorer` subagent so this context stays lean.
4. **Distill** into: conventions & standards, domain vocabulary, guardrails/prohibitions.
   - Deduplicate against what the code already makes obvious (patterns, not catalogs).
   - Attribute non-obvious rules to their source.
5. **Flag conflicts** between sources (or against the code) in the "Conflicts to resolve" table — never silently pick a winner.
6. **Write** the file. Merge anything that clearly belongs in core steering (tech/structure) there instead of duplicating.

## Critical Constraints
- **Distill, never dump.** No whole-file pastes.
- **No secrets** — skip tokens, keys, credentialed URLs.
- **100–200 lines** — it is memory, not an archive.
</instructions>

## Output Description
Confirm the file path; summarize sources found, key conventions absorbed, and any conflicts the human must resolve.

## Safety & Fallback
- **Nothing found**: say so plainly — a clean repo with no prior AI config is a valid outcome; steering will come from `/sdd:steering` alone.
- **Existing inherited-knowledge.md**: refine in place, preserve human edits.
