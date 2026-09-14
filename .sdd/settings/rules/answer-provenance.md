# Answer Provenance Rules

Applies whenever the agent reports a number, a metric, or a data-derived claim to a human. Loaded
alongside `data-readiness.md` on data projects.

A number with no source is a guess with formatting. The goal is not to sound confident — it is to
let the reader calibrate how much to trust the answer.

## Every substantive answer carries its provenance

```
Result:      R$ 18.7M
Source:      gold_sales_monthly            <- the dataset actually queried
Metric:      net_revenue                   <- the contract used, or "ad-hoc (defined below)"
Freshness:   2026-08-11 06:10              <- last successful load of that source
Validation:  semantic layer · DQ passed · reviewer agent
Confidence:  High
```

Write it in the project's artifact language, and keep it compact — a footer, not a report. For a
throwaway exploratory count, one line is enough: *"1,204 rows — `silver_orders`, loaded 06:10, ad-hoc
count, medium confidence."*

## Confidence levels (state the reason, not just the word)

| Level | When |
|---|---|
| **High** | Rung 1–2 of the source ladder, freshness inside SLA, DQ assertions passed. |
| **Medium** | Hand-written SQL over governed data, or freshness not verified. |
| **Low** | Raw/bronze source, a metric with no contract, or an assumption you had to make. |

**Low confidence obliges you to name the assumption.** "Low confidence" alone is not a disclosure.

## Hard rules

- Never report a number without the rung of the source ladder it came from
  (`data-readiness.md` defines the ladder).
- Never present an ad-hoc metric definition as if it were the canonical one. If you defined it in
  the moment, show the formula and say so.
- If freshness could not be determined, say "freshness unknown" — do not omit the line.
- If two sanctioned sources disagree, report **both** numbers and the disagreement. Picking the
  nicer one is the most expensive mistake in this file.
