# Data Readiness Rules

Loaded when the work touches a data platform: by `/data-quality`, by `/sdd:spec-design` for data
features, and by `/sdd:spec-impl-config`. **Skip entirely** when `integrations.md` says the data
platform row is `n/a` — this file does not apply to projects without one.

The hard problem is not generating SQL. It is mapping a business question to the right **entity,
metric, and source**. These rules force that mapping to be explicit instead of inferred.

## Source priority ladder (never invert it)

Resolve every data question in this order, stopping at the first rung that covers it:

1. **Semantic layer / metric contract** — a defined metric with grain, population, and owner.
2. **Governed model** — a canonical gold/mart dataset that the team owns and tests.
3. **Hand-written SQL over silver** — governed data, ungoverned aggregation.
4. **Raw / bronze** — last resort.

Going down the ladder is allowed. Going down **silently** is not: state which rung you used and why
the rung above did not cover it. Rung 3 or 4 on a metric that matters is a finding to surface, not a
shortcut to take quietly.

## Agent-Ready Dataset checklist

Before a dataset counts as a sanctioned source for the agent:

- [ ] **Canonical** — one dataset per concept. If `orders`, `orders_v2`, and `orders_final` all
      exist, none of them is canonical until someone says which is.
- [ ] **Grain documented** — "one row = one ___". Ambiguous grain is the single most common cause
      of a confidently wrong number.
- [ ] **Ownership** — a named owner who can answer a definition question.
- [ ] **Freshness** — expected update cadence, and the query that shows the last successful load.
- [ ] **Quality** — key columns non-null, merge key unique, ranges valid (see `/data-quality`).
- [ ] **Semantics** — the business meaning of every non-obvious column, and the metrics built on it.
- [ ] **Lineage** — the upstream it derives from.
- [ ] **Access** — the read path the agent may use; read-only by default.

The answers live in steering (`database.md`, `semantic-layer.md`) — **not** duplicated into specs.
A spec references them; it does not restate them.

## Ambiguous sources are a finding, not a detail

If discovery turns up several candidate tables for one concept, never pick one silently. Name the
candidates, say which one you used and on what evidence, and raise the ambiguity in the design as a
decision the human owns. Reducing dozens of possible sources to a few governed ones is the work —
skipping it just moves the error downstream.

## Metric definitions belong in a contract, not in a query

`SUM(valor)` is not a metric. A metric is a name, a formula, a grain, a population filter, and an
owner. When a spec needs a metric that has no contract:

1. Do not invent it inline.
2. Propose the definition explicitly (formula + grain + population).
3. Get it confirmed, then write it to `.sdd/steering/semantic-layer.md`.
4. Only then use it.

An invented metric that produces a plausible number is worse than an error — it does not announce itself.

## When to stop and ask

- No canonical source and no owner to ask → stop.
- Metric undefined or two sources disagree → stop; propose, don't guess.
- The dataset fails the readiness checklist on **grain** or **ownership** → stop. The other boxes
  can be filled as you go; these two cannot.
