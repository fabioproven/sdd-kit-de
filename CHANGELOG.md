# Changelog — SDD Kit

Formato: mais recente primeiro. O "motor" (`.claude/commands`, `.sdd/settings`, `tools/`) é a
camada versionada; reinstalar uma versão nova não toca no seu `.sdd/steering/` nem nas suas specs.

## 0.7.0 — O kit dentro do editor, e upgrade que não perde contexto

Duas lacunas de operação, não de conceito. A primeira: a trava determinística vivia dentro da
conversa — quem não pedisse `/sdd:spec-lint` não via o erro de rastreabilidade. A segunda: reinstalar
o motor era uma escrita cega, sem memória do que a versão anterior tinha instalado nem do que o
destino tinha editado à mão.

- **Saída de máquina no `spec-lint`** (`tools/spec-lint.py --format=vscode`): uma linha por achado,
  ancorada em `arquivo:linha:coluna: severidade: mensagem`. Cada ID passa a ter posição própria — "Req
  2.3 sem tarefa" aponta o critério de aceite em `requirements.md`, "referência solta" aponta a linha
  do `_Requirements:_` em `tasks.md`. O formato `human` é o default e sua saída não mudou; o veredito
  (exit code) é o mesmo nos dois.
- **`.vscode/` como parte da instalação** (`.sdd/settings/templates/vscode/`): `tasks.json` com o
  problemMatcher que joga os achados do linter no painel **Problems** do editor (Ctrl+Shift+B roda o
  lint de todas as specs; há tarefa para a spec do arquivo aberto e para `--require-evals`),
  `settings.json` que agrupa os arquivos de uma spec sob `requirements.md` no explorador, e
  `extensions.json` recomendando `anthropic.claude-code`. Nunca sobrescreve: se o projeto já tem o
  arquivo, a versão do kit fica ao lado como `.sdd-new`.
- **`tools/kit-sync.py` — continuidade entre versões.** O instalador passa a tirar **backup** de tudo
  que pode tocar antes de copiar (`.sdd/backups/pre-<versão>-<timestamp>/`) e a manter um manifesto
  com o sha256 de cada arquivo de motor instalado (`.sdd/.kit-manifest.json`). Na atualização
  seguinte, arquivo que bate com o manifesto era intocado e recebe a versão nova; arquivo que **não**
  bate foi editado no destino, e aí a edição local é **restaurada** e a versão do kit fica ao lado
  como `<arquivo>.sdd-new`. Decidido por hash, não por confiança no modelo.
- **Relatório de upgrade** (`.sdd/UPGRADE.md`, reescrito a cada instalação): de qual versão veio, onde
  está o backup, o que foi preservado, o que sobrou de motor antigo (listado, nunca apagado — remoção
  é irreversível, logo é decisão humana) e **o que a camada 2 ainda deve à versão instalada** —
  steering ausente, `CLAUDE.md` ainda com `{{PLACEHOLDERS}}` ou ainda descrevendo portão por fase
  (postura anterior à 0.5.0), spec sem `evals.md` — cada item com o comando que o gera.
- Instaladores em par, como sempre: `install.ps1` ganhou `.sdd\settings\templates\vscode\tasks.json` e
  `tools\kit-sync.py` na lista `$required`, e sonda o interpretador de fato (no Windows `python` na
  PATH costuma ser o stub da Microsoft Store, que não executa) com o `ErrorActionPreference` relaxado
  só na sonda, porque redirecionar stderr de executável nativo sob `Stop` abortaria o script.

**Reversibilidade:** sem Python 3 no PATH, os instaladores avisam e se comportam exatamente como na
0.6.0 — sem backup, sem manifesto, sem `UPGRADE.md`. A camada 2 (`steering/`, `specs/`, `CLAUDE.md`)
continua fora do alcance do instalador, e o backup existe justamente para provar isso por hash.

## 0.6.0 — Agent-Ready Data (semântica, evals e proveniência)

Fecha a lacuna entre "o fluxo é rastreável" e "a resposta é **correta**". Até aqui o kit validava
**estrutura** (`spec-lint` para rastreabilidade, `approval-gate` para o loop); faltava o eixo de
**correção**. Traz para o motor o que o treinamento de IA agêntica em engenharia de dados prescreve
nos módulos 1, 2, 3, 6 e 7. Tudo opcional e inerte em projeto sem plataforma de dados.

- **Semantic layer como steering** (`.sdd/settings/templates/steering-custom/semantic-layer.md`):
  contrato por métrica — nome + fórmula + **grain** + população + fonte + dono —, entidades canônicas,
  dimensões compartilhadas e os termos que o negócio usa de forma ambígua. `/sdd:steering-custom` passa
  a oferecê-lo; `setup-sdd` o propõe quando há plataforma de dados.
- **Escada de fontes e checklist Agent-Ready** (`.sdd/settings/rules/data-readiness.md`): semantic
  layer → modelo governado → SQL manual → raw, com a regra de que **descer de degrau em silêncio é
  proibido**. Fonte ambígua (`orders`, `orders_v2`, `orders_final`) é finding, não detalhe. Métrica sem
  contrato não se inventa: propõe-se, confirma-se, escreve-se no steering.
- **Suite de evals** (`/sdd:spec-evals`, rule `evals.md`, template `specs/evals.md`): golden questions
  com **ground truth humano** (nunca do agente sob teste), caso de ambiguidade cuja resposta certa é
  *perguntar*, caso de borda e regressão. Validação adversarial delegada a um revisor separado —
  mesmo padrão do agente `approver`, aplicado a respostas em vez de subtarefas.
- **`spec-lint` ganha a checagem de evals** (aditiva): se `evals.md` existe, refs mortas viram **erro**
  e requisitos sem eval viram aviso; `--require-evals` promove ambos a erro e exige a suite. Spec sem
  `evals.md` e sem a flag se comporta **exatamente** como na 0.5.0.
- **Proveniência obrigatória** (`.sdd/settings/rules/answer-provenance.md`): todo número reportado sai
  com fonte, métrica, freshness, validação e confiança — e o nível de confiança obriga a nomear a
  premissa. Fontes sancionadas que discordam: reporta-se **as duas**.
- **Canvas de caso de uso no `setup-sdd`** (uma pergunta, com rascunho preenchido): usuários, perguntas,
  decisões, fontes, criticidade/SLA, **ações permitidas** e **nível de autonomia** — as duas últimas
  alimentam o escopo de risco `high` e a postura de auto-aprovação. Vai para `product.md`.
- **`/data-quality`** passa a emitir veredito de agent-readiness (grain e dono ausentes = bloqueio, não
  aviso) e a oferecer promoção das assertions para evals de regressão.
- Correções de consistência herdadas da 0.5.0: `max_iterations` documentado como 5 (era 3) em
  `orchestration-loop.md`, README e HANDOFF; heading `## Quality gate` duplicado no `CLAUDE.md.template`.

## 0.5.0 — Autonomia por padrão (portões por risco, não por fase)

Reduz "muitas perguntas / tudo aprovado" mantendo o portão exatamente onde importa. Estritamente
aditivo e reversível — quem quiser o comportamento anterior mantém `autoapprove.json` em `low` only.

- **Portões por risco, não por fase** (`CLAUDE.md.template`): o fluxo roda spec→design→tasks→impl
  contínuo; só para em humano quando o próximo passo é `high` (escrita em dado produtivo, mudança de
  schema, contrato de consumidor, deploy/PR). `low`/`medium` rodam sem pedir aprovação.
- **Postura recomendada = Equilibrada** (`setup-sdd`): o instalador agora recomenda ligar o loop auto
  para `low` **e** `medium` (logado), com `high` sempre humano — antes recomendava só `low`. Template
  `autoapprove.json` continua `enabled:false` (primeiro contato seguro); a skill guia o opt-in.
- **Allowlist read-only semeada** (`setup-sdd`): novo passo instrui semear `.claude/settings.local.json`
  com formas claramente read-only (git status/diff/log, verbos de leitura da CLI de dados, spec-lint).
  Nunca liberar comando de escrita — o prompt do harness é a última trava sem hook `PreToolUse`.
- **Teto de iterações** `max_iterations` 3 → 5 no template (menos escalada por "estourou o loop").

## 0.4.0 — Modo aprovador automático

Padrão orquestrador **executor ↔ aprovador** para cortar aprovações manuais sem perder segurança.

- **Dois papéis separados.** Agente `approver` (`.claude/agents/approver.md`) com prompt próprio e
  **sem acesso de escrita** — só julga contra critérios de saída objetivos (APPROVE / REJECT / ESCALATE).
- **Classificação de risco** (`.sdd/settings/rules/risk-classification.md`): low (automático) ·
  medium (aprovador decide, logado) · high (**sempre humano, sem exceção**).
- **Trava determinística contra loop infinito** (`tools/approval-gate.py`): cap de iterações contado
  num ledger em disco (não pela contagem do modelo) + teto de tokens/custo; decide por exit code
  (0 CONTINUE / 2 ESCALATE / 3 HUMAN). Loop infinito impossível por construção.
- **Comando** `/sdd:spec-impl-auto` e **protocolo** `orchestration-loop.md`.
- **Observabilidade**: `.sdd/specs/<feature>/approval-log.jsonl` + `approval-gate.py summary`.
- **Configurável e reversível**: `.sdd/autoapprove.json`. Default `enabled:false` = comportamento
  manual idêntico ao de hoje (fallback). Modo estritamente aditivo.

## 0.3.0 — Intake no setup

- `setup-sdd` agora **solicita** (uma pergunta por vez, antes do discovery): documentação/convenções
  do projeto; qual host de git (GitHub/GitLab/Azure DevOps/Bitbucket/nenhum); qual tracker
  (Jira/Microsoft Planner/Kanbanize/outro/nenhum).
- `discover-tools` parte da intenção declarada e **verifica**; novos backends (Bitbucket, Planner,
  Kanbanize) + tabela de conexão com passos exatos para cada `needs-setup`.

## 0.2.0 — Conhecimento herdado, descoberta de ferramentas e comandos de entrega

- `/sdd:absorb-knowledge` — destila conhecimento de configs de IA prévias (Cursor, Copilot, Claude,
  Gemini, Aider, Windsurf) e docs da raiz para o steering.
- `/sdd:discover-tools` — mapeia integrações (issue/git/dados) → `integrations.md`, dizendo o que é
  nativo (MCP/CLI) e o que precisa configurar.
- Comandos de entrega bem definidos: `/prepare-pr`, `/review`, `/data-quality` — todos leem
  `integrations.md` antes de agir.

## 0.1.0 — Kit portável inicial

- Motor genérico do fluxo SDD (comandos `spec-*`, rules, templates) sem nada específico de projeto.
- **Linter de rastreabilidade** `tools/spec-lint.py` + `/sdd:spec-lint`.
- Perfis de implementação: `spec-impl` (TDD), `spec-impl-investigation` (relatório),
  `spec-impl-config` (dry-run).
- Instaladores `install.sh` / `install.ps1`, skill `setup-sdd`, `CLAUDE.md.template`, subagente
  `code-explorer`.
