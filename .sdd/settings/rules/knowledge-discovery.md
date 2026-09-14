# Knowledge Discovery Rules

How to harvest **prior agent/AI knowledge** already present in a repo and fold it into
steering — so a freshly-installed SDD kit does not throw away conventions a team already
wrote for other AI tools. Loaded on demand by the `setup-sdd` skill and by
`/sdd:absorb-knowledge`.

## Principle

A repo that has been used with any AI assistant usually already encodes real project
knowledge: coding standards, do/don't rules, domain vocabulary, architecture notes. That
knowledge is as valuable as the code itself. **Read it before generating steering**, then
distill (never dump) it into project memory.

## User-provided docs come first

If the setup interview asked the user for technical docs / conventions / a data dictionary and they
pointed to files or URLs, **read those first** — they are the team's own framing and outrank
anything globbing guesses. Local paths → read now; URLs/wikis you can't fetch → ask the user to
paste the key parts. Only then run the automatic sweep below to fill gaps.

## Sweep these locations

Glob and read what exists; silently skip what doesn't. Do **not** descend into `node_modules`,
`.git`, build/`dist` output, or vendored dependencies.

**Root-level markdown & agent files**
- `*.md` at root — `README`, `CONTRIBUTING`, `ARCHITECTURE`, `DEVELOPMENT`, `STYLEGUIDE`, `DECISIONS`/ADRs
- `AGENTS.md` (the cross-tool agent standard), `GEMINI.md`, `CLAUDE.md`
- `docs/`, `adr/`, `.adr/`, `rfcs/` — read titles/summaries, not every line

**Per-tool AI configuration**
- `.claude/` — nested `CLAUDE.md`, `commands/`, `agents/`, `skills/`, `settings.json`
- `.cursor/` and `.cursorrules`, `.cursor/rules/*.mdc`
- `.github/copilot-instructions.md`
- `.windsurfrules`, `.windsurf/`
- `.continue/`, `.aider*` config
- Generic `.agent/`, `.assistant/`, `.ai/` folders — read their `*.md`

## Distill, don't copy

For each source, extract only **durable, decision-guiding** content:
- Coding conventions and style rules ("we use X pattern", "never do Y")
- Domain vocabulary / glossary terms and their canonical meaning
- Architecture boundaries, ownership, and integration contracts
- Explicit prohibitions and guardrails
- Review expectations, definition-of-done, testing norms

Then:
1. **Deduplicate** against what `/sdd:steering` derives from the code. If the code already
   makes it obvious, don't restate it — steering documents *patterns, not catalogs*.
2. **Flag conflicts.** If two sources contradict each other (or contradict the code), do not
   silently pick one — record both and surface them to the human as an open question.
3. **Attribute lightly.** Note which source a non-obvious rule came from, so a reviewer can
   trace it (e.g. "from `.cursorrules`").
4. **Never carry secrets.** Skip tokens, keys, URLs with credentials — even if a prior config
   embedded them.

## Output

Write a consolidated `.sdd/steering/inherited-knowledge.md` (use the steering-custom template).
Keep it 100–200 lines — it is project memory, not an archive. Content that clearly belongs to a
core steering domain (tech, structure) should be merged there instead of duplicated here.

## What this is NOT

- Not a migration of another tool's command set — you harvest *knowledge*, not their commands.
- Not a dumping ground — if you find yourself pasting whole files, you are doing it wrong.
