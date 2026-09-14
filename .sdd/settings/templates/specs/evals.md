# Evaluation Suite

Golden questions and regression assertions for this feature. Ground truth is authored or confirmed
by a **human**, never by the agent under test. Rules: `.sdd/settings/rules/evals.md`.

**Suite scope:** {{WHAT_THIS_SUITE_COVERS_AND_WHAT_IT_DOES_NOT}}
**Ground truth by:** {{PERSON_OR_TRUSTED_REPORT}} · **Last run:** {{DATE}} · **Result:** {{N_PASS}}/{{N_TOTAL}}

## Eval Format Template

### E{{NUMBER}} — {{SHORT_TITLE}}
- **Kind:** answer | artifact
- **Question / assertion:** {{THE_REAL_BUSINESS_QUESTION_OR_THE_CHECK}}
- **Sanctioned source:** {{DATASET_OR_METRIC_CONTRACT}} *(which rung of the source ladder)*
- **Ground truth:** {{EXPECTED_VALUE_OR_SHAPE}} — *origin:* {{HOW_IT_WAS_INDEPENDENTLY_OBTAINED}}
- **Pass criterion:** {{EXACT_MATCH | WITHIN_TOLERANCE_X | SCHEMA_MATCHES | ASKS_FOR_CLARIFICATION}}
- _Requirements: {{REQUIREMENT_IDS}}_ *(IDs only — same convention as tasks.md; spec-lint checks these)*

## Examples of the three shapes every suite should carry

### E1 — Weekly question people actually ask
- **Kind:** answer
- **Question / assertion:** {{e.g. "Net revenue for July vs. budget"}}
- **Sanctioned source:** {{metric contract net_revenue}}
- **Ground truth:** {{18,700,000}} — *origin:* {{closed monthly report, confirmed by Finance}}
- **Pass criterion:** within 0.5%
- _Requirements: {{X.Y}}_

### E2 — Ambiguity: the correct answer is to ask
- **Kind:** answer
- **Question / assertion:** {{e.g. "How many active customers?" — "active" is undefined here}}
- **Sanctioned source:** n/a
- **Ground truth:** agent asks which definition of "active" applies instead of picking one
- **Pass criterion:** asks for clarification; does not emit a number
- _Requirements: {{X.Y}}_

### E3 — Boundary / regression
- **Kind:** artifact
- **Question / assertion:** {{e.g. "re-running the load for the same date is idempotent — row count unchanged"}}
- **Sanctioned source:** {{target table}}
- **Ground truth:** {{count before == count after}}
- **Pass criterion:** exact match
- _Requirements: {{X.Y}}_

> Every bug that reached a user should end up here as a new `E{{n}}`.
> A suite of only happy-path questions passes forever and catches nothing.
