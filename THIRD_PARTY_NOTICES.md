# Avisos de terceiros

O SDD Kit é distribuído sob a licença MIT (ver `LICENSE`). Parte do motor deriva de software de
terceiros, cujos avisos de licença são reproduzidos abaixo conforme exigido.

## cc-sdd — gotalab

O fluxo de comandos `/sdd:*` (`spec-init`, `spec-requirements`, `spec-design`, `spec-tasks`,
`spec-quick`, `spec-status`, `steering`, `steering-custom`, `validate-*`), as rules de discovery de
design, formato EARS, geração de tarefas e princípios de steering, e os templates de spec e de
steering foram originalmente criados pelo projeto **cc-sdd** e adaptados aqui (caminho `.kiro/` →
`.sdd/`, ajustes de texto, extensões).

- Projeto: https://github.com/gotalab/cc-sdd
- Licença: MIT

```
MIT License

Copyright (c) 2025 gotalab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

O que **não** vem do cc-sdd e foi escrito para este kit: `absorb-knowledge`, `discover-tools`,
`spec-evals`, `spec-impl-auto` e os perfis `-config`/`-investigation`, os comandos de entrega
(`prepare-pr`, `review`, `data-quality`), os agentes `approver`, `data-analyst` e `report-validator`,
a skill `setup-sdd`, as rules de risco, orquestração, tooling, conhecimento herdado, data-readiness,
evals, proveniência e artefatos de spec, as tools `spec-lint.py`, `approval-gate.py`, `kit-sync.py` e
`write-guard.py`, os instaladores e os templates de integrações, semantic layer, evals, VS Code,
`autoapprove.json` e `write-scope.json`.
