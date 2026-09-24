# Evidence — upgrade path on the test-bed copy (task 4.2)

**Measured:** 2026-09-24 · **Source:** a scratch copy of the test-bed project's kit-relevant
subtree (`.claude`, `.sdd` without `backups/`, `tools`, `.vscode`, `CLAUDE.md`,
`CLAUDE.md.template`; 747 KB) carrying **engine 0.8.0 over a 0.1.0-era project layer** — the
exact debt `/update-sdd` exists for · **Validation:** sha256 of every layer-2 file before/after;
audit JSON captured twice · **Confidence:** high for everything below; the interactive parts of
`/update-sdd` (diff confirmation) were **not** exercised because no human was in the loop.

## 1. Install 0.9.0 over 0.8.0 (installers, `finish`, report routing)

```
==> instalando SDD Kit (sdd-kit 0.9.0) em: <scratch>/testbed
[kit-sync] backup do estado atual: .sdd\backups\pre-0.9.0-20260924-204331
    CLAUDE.md ja existe - intocado; template atualizado ao lado (CLAUDE.md.template)
[kit-sync] manifesto: 80 arquivos de motor registrados
[kit-sync] camada 2: 11 pendencia(s) - veja .sdd/UPGRADE.md
    ATUALIZACAO de uma versao anterior?  rode  /update-sdd
```

- `.sdd/SDD_KIT_VERSION` → `sdd-kit 0.9.0` (Req 6.3). `tools/` received the four `.py` only;
  `tools/tests/` did not travel.
- **Layer 2 hashes unchanged** — 14 files (`CLAUDE.md`, `.sdd/steering/*`, `.sdd/specs/**`)
  byte-identical before and after (`diff hashes-before.txt hashes-after.txt` empty).

## 2. Audit from inside the target, no `--kit` (Req 4.6, 5.1)

`py tools/kit-sync.py audit --target .` → exit 1, 11 gaps, previous version detected
(`sdd-kit 0.8.0`), `layer2: present`:

| severity | id | new since previous? |
|---|---|---|
| blocking | `claude.phase-gates`, `steering.integrations` | — |
| recommended | `claude.routing.approver`, `.data-analyst`, `.report-validator`, **`.data-engineer`** (new), `claude.section.auto-approval-mode`, **`config.autoapprove.key.delegation`** (new), `engine.sdd-new` (`.claude/settings.local.json.sdd-new`), `steering.inherited-knowledge` | marked |
| optional | `spec.validacao-pk-silver-ql.evals` | — |

The four rows the pre-0.9.0 `UPGRADE.md` listed are all still there; the new rows are exactly the
routing lines for installed agents, the missing template section and the new config key.

## 3. `/update-sdd`, non-interactive part, simulated by the command's own rules (Req 5.3, 5.5, 5.7, 5.13)

- `config.autoapprove.key.delegation` → merged: `config keys added: ['delegation']`,
  `delegation.enabled after merge: False`, `auto_approve preserved: True` (existing values and
  order intact).
- Re-audit → **10 gaps**; `closed: ['config.autoapprove.key.delegation']`.
- `kit-sync.py report --target .` → `UPGRADE.md` rewritten from the fresh audit; its "Próximo
  passo" names `/update-sdd`.
- **Idempotence:** a second merge pass adds `[]` and the config's sha is stable.
- `CLAUDE.md` sha before/after the whole exercise: `9744d48242cc` both times — untouched.

## 4. Section patch for `claude.phase-gates` — proposed, not applied (Req 5.6)

The mechanism produced a unified diff replacing only the line carrying "approval gate at each
phase" with the template's "Gates are by risk, not by phase" paragraph. It was **not** written
because the rule is "write only after the human confirms" and nobody was there to confirm.
Caveat noted for implementation: the naive line-level replacement leaves the tail of the original
sentence ("implemented against that spec…") dangling; the command prompt asks for a
*sentence-level* replacement, which the model must do by reading the paragraph, not by line.

## 5. What remains on this test-bed, and why

`claude.*` (7 rows) — need the human's yes per diff · `steering.integrations`,
`steering.inherited-knowledge` — need `/sdd:discover-tools` / `/sdd:absorb-knowledge` run inside
the real project (they read the real repo, not this subtree) · `engine.sdd-new` — human decision ·
`spec.*.evals` — optional, needs human ground truth. None of these can or should be closed by a
script; that is the design.
