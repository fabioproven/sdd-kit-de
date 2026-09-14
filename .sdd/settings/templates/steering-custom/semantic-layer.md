# Semantic Layer

[Purpose: define what the business words MEAN in data terms, so the agent maps a question to the
right metric, grain, and source instead of inferring it. This file is the contract; queries are
implementations of it.]

## How to use this file

- One entry per metric that matters. Do not catalog every column — capture the terms people argue about.
- A metric is not a formula alone: it is **name + formula + grain + population + source + owner**.
- If a metric is not here, the agent must propose a definition and get it confirmed before using it
  (`.sdd/settings/rules/data-readiness.md`).

## Canonical entities

| Concept | Canonical dataset | Grain (one row = ) | Owner |
|---|---|---|---|
| [customer] | [gold_customers] | [one active customer] | [team] |
| [order] | [gold_orders] | [one order line] | [team] |

Datasets not listed here are **not** sanctioned sources. Deprecated look-alikes worth naming
explicitly so nobody reaches for them: [orders_v2, orders_final, …].

## Metric contracts

```yaml
metric:
  name: net_revenue
  description: >
    Revenue actually recognized, after returns, discounts and taxes.
grain:
  - order
  - month
formula: >
  gross_revenue - returns - discounts - taxes
population: >
  status = 'INVOICED' AND cancelled = false AND is_test_sale = false
source: gold_sales_monthly
dimensions:
  - business_unit
  - region
  - channel
freshness: daily by 07:00 [timezone]
owner: [team / person]
known_gotchas: >
  [e.g. excludes intercompany; before 2024-01 the tax component was estimated]
```

Repeat one block per metric. Keep the population filter literal — it is the part that silently
changes an answer.

## Shared dimensions

| Dimension | Source of truth | Notes |
|---|---|---|
| [calendar] | [dim_date] | [fiscal year starts in …] |
| [org hierarchy] | [dim_org] | [snapshot vs current — say which] |

## Ambiguities to resolve out loud

Terms the business uses inconsistently. When one appears in a request, **ask which is meant** —
do not pick:

- [e.g. "active customer" — bought in 90 days vs. account not closed]
- [e.g. "headcount" — at period end vs. average]

---
_Patterns and definitions only. No credentials, no environment-specific connection details._
