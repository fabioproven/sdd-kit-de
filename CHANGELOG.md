# Changelog — SDD Kit

Formato: mais recente primeiro. O "motor" (`.claude/commands`, `.sdd/settings`, `tools/`) é a
camada versionada; reinstalar uma versão nova não toca no seu `.sdd/steering/` nem nas suas specs.

## 0.9.0 — Quem constrói, e como atualizar sem refazer

Dois problemas de origens diferentes, uma versão. O primeiro: até a 0.8.0 todo subagente do kit
**lê ou julga** (`code-explorer`, `data-analyst`, `report-validator`, `approver`) — nenhum
constrói. O "executor" do loop executor↔aprovador era o próprio prompt do orquestrador, sem
identidade de engenheiro, sem contexto próprio, sem fronteira de permissão. O segundo: um projeto
que atualiza o motor por cima de uma instalação antiga fica com a camada 2 defasada (`CLAUDE.md`
com portão por fase, steering faltando, config sem as chaves novas), e o único remédio era rodar o
`setup-sdd` de novo — que re-pergunta tudo o que o projeto já respondeu.

- **`data-engineer`** (`.claude/agents/data-engineer.md`): o primeiro membro de uma squad de
  dados — o papel que **escreve** código de pipeline e SQL dentro do `spec-impl` /
  `spec-impl-config`. Recebe um **Work Order** (subtarefa, IDs de requisito, critérios de saída
  pass/fail, risco, escopo de escrita, caminhos permitidos, ponteiros do design) e devolve um
  **Work Report** (arquivos, comandos e resultados, evidência, critério a critério com prova,
  observações fora de escopo, parada antecipada, ambiente). Para e reporta — nunca contorna — em
  risco maior que o declarado, escrita fora do escopo, métrica sem contrato, credencial, qualquer
  coisa destrutiva. Nunca marca tarefa, nunca aprova, nunca amplia o escopo. Contratos em
  `rules/orchestration-loop.md` → "Delegation".
- **Bloco `delegation` em `autoapprove.json`** (template): decide **quem digita**, nunca quem
  aprova. Nasce **desligado**; ligado, tem flag por nível (`low` inline, `medium` e `high` — este só
  depois do humano aprovar — vão para o executor). O `spec-impl` e o `spec-impl-config` leem o bloco
  no Step 0 e imprimem o modo (`mode: … · executor: …`); agente ausente → avisa e executa inline;
  `spec-impl-investigation` nunca delega (só leitura, via `data-analyst`). O gate não lê o bloco:
  `high` continua `HUMAN` sempre.
- **`kit-sync.py audit`** (só leitura, exit 0/1/2): o que a camada 2 deve ao motor instalado como
  **fato calculado do disco** — tabela de checagens versionada (cada uma sabe em que versão nasceu:
  steering faltando, `CLAUDE.md` com placeholder / portão por fase / "convenção, não trava" /
  `spec-impl-auto` como instrução / seção do template ausente / agente instalado sem linha de
  roteamento, config sem chave nova, `.sdd-new` pendente, sobra de versão anterior, spec sem evals,
  fase fora do enum), saída humana ou JSON, gravidade `blocking`/`recommended`/`optional`. O
  `UPGRADE.md` passa a ser gerado **dessa mesma computação** (`kit-sync.py report` reescreve).
  Roda de dentro do projeto sem o kit por perto. Testes em `tools/tests/`.
- **`/update-sdd [--dry-run]`** (`.claude/commands/update-sdd.md`): lê o audit e fecha **só** as
  linhas dele, uma por vez, em ordem de gravidade — steering ausente pelos comandos existentes em
  modo Sync; chave de config nova com o default preservando valores; `CLAUDE.md` **remendado por
  seção** a partir do template, com diff e confirmação humana em cada edição; fase de spec
  normalizada com mapeamento confirmado; `.sdd-new` e sobras apresentados para o humano decidir;
  evals oferecidas, não exigidas. Nunca sobrescreve `CLAUDE.md`, steering, specs ou valor de
  config; nunca apaga; nunca re-pergunta intake. Sem pendência, não toca em nada (idempotente).
  `setup-sdd` ganha o passo 0.5: camada 2 já existe → manda para o `/update-sdd`. Instaladores e
  `UPGRADE.md` apontam `/update-sdd` no upgrade e `setup-sdd` na primeira instalação; o
  `CLAUDE.md.template` agora fica **sempre** ao lado do `CLAUDE.md` no destino (é dele que o audit
  deriva as seções).
- `CLAUDE.md.template`: linha de roteamento para o `data-engineer` (inerte com delegação desligada),
  uma frase na seção de auto-approval sobre quem executa, linha do `/update-sdd` na referência
  rápida. `setup-sdd` §4 oferece a delegação como opt-in com postura recomendada.
- Instaladores: `$required` / lista do `.sh` com o agente e o comando novos; `kit-history.json`
  com a entrada 0.9.0.

**Reversibilidade:** `delegation` ausente, inválido ou `enabled: false` → o orquestrador executa,
byte a byte a 0.8.0. `/update-sdd` é aditivo por construção e só escreve o que o audit listou.
A spec desta versão está em `.sdd/specs/data-engineer-and-update-sdd/` (dogfooding), com a
evidência das provas em `evidence/`. Os demais papéis da squad (analytics engineer, data quality,
platform) ficam para quando a delegação de escrita estiver provada ponta a ponta num projeto real.

## 0.8.0 — O que cinco meses de uso ensinaram

Esta versão não nasce de uma ideia; nasce de um inventário. Um projeto real rodou o motor 0.4.0
por cinco meses: 35 specs, ~1.000 IDs de requisito, **35/35 passando no `spec-lint`** — a
rastreabilidade sobreviveu ao uso. Mas o mesmo inventário mostrou o que o kit **não** entregou:
o loop executor↔aprovador estava ligado na config e **nunca rodou uma vez** (zero linhas de
`approval-log.jsonl`), porque morava num comando paralelo que ninguém chama; `spec.json.phase`
tinha onze grafias de "implementado"; treze artefatos apareceram nas specs sem que o template os
previsse; e o projeto escreveu à mão, por necessidade, dois subagentes e um hook que o kit deveria
ter dado. A 0.8.0 é a devolução disso ao motor, generalizado.

- **O loop auto deixa de ser um comando à parte** (`spec-impl.md`, `spec-impl-config.md`,
  `spec-impl-investigation.md` — novo Step 0): cada perfil lê `.sdd/autoapprove.json` e, se
  `enabled` é `true`, roda o loop executor↔aprovador sozinho — gate por exit code, `approver`
  separado, ledger. `spec-quick` herda por tabela. `/sdd:spec-impl-auto` continua como alias
  explícito. Lição: comportamento novo entra no comando que a pessoa já chama, gated por config;
  documentação não cria uso.
- **`data-analyst`** (`.claude/agents/data-analyst.md`): subagente que isola as consultas caras à
  plataforma de dados. Só leitura por construção; escada de amostragem (metadados → agregação →
  amostra `LIMIT 50` → escalona com autorização); PII proibida; devolve o número com proveniência,
  nunca dump. Conecta pelo que `integrations.md` diz, nunca por perfil padrão.
- **`report-validator`** (`.claude/agents/report-validator.md`): auditor adversarial de qualquer
  relatório (HTML, Markdown, notebook, PDF exportado) **antes de circular**. Reproduz cada número
  na fonte e caça `LABEL TOO BROAD`, `MIXED AXES`, `UNSUPPORTED`, `POSSIBLY STALE`. Nasceu de um
  relatório que atribuiu uma diferença "às coligadas do exterior" enquanto a tabela ao lado mostrava
  o exterior caindo. Julga; não edita.
- **`tools/write-guard.py` + `.sdd/write-scope.json`**: hook `PreToolUse` determinístico que **nega**
  escrita SQL (`CREATE/INSERT/MERGE/UPDATE/DELETE/DROP/TRUNCATE/ALTER/COPY INTO/saveAsTable/GRANT`)
  fora do escopo permitido e pede confirmação em alvo ambíguo. Instalado **desligado**. Vem com
  `--self-test` e `--check "<comando>"`, porque a instalação original ficou um mês com o schema
  grafado errado — negando o alvo certo e liberando um inexistente. O self-test manda confirmar cada
  alvo na plataforma.
- **`rules/spec-artifacts.md`**: vocabulário canônico de `spec.json.phase` (sete valores; nuance vai
  em `status_note`) e nome fixo para os artefatos opcionais que o uso inventou — `contract-impact.md`
  (consumidor afetado ⇒ tarefa `high`, regra nova em `risk-classification.md`), `evidence/` (prova
  datada com proveniência), `rollback.md` (obrigatório antes de `high` que sobrescreve). `spec-lint`
  avisa fase desconhecida (também em `--format=vscode`); `spec-status` lista os artefatos e denuncia
  spec implementada sem ledger com o loop ligado.
- **Entrega sem repositório** (`rules/tooling-discovery.md`, `prepare-pr.md`): a linha VCS de
  `integrations.md` aceita `platform` — o workspace da plataforma é o versionamento, e o projeto
  não tem git por decisão. `/prepare-pr` então monta um **pacote de entrega**: checagem de frescor
  do remoto, lista exata dos arquivos alterados, um comando de import por arquivo, rollback — sempre
  `high`, sempre com "sim" explícito.
- **`kit-sync.py` — colisão por nome**: arquivo que o kit passa a publicar mas que o destino já
  tinha, e que **nenhuma versão anterior do kit publicou** (novo `.sdd/settings/kit-history.json`),
  é obra do projeto — preservado, kit ao lado como `.sdd-new` — mesmo na primeira instalação com
  manifesto. Sem isso, esta versão apagaria justamente o `data-analyst.md` que a inspirou. O
  detector do `UPGRADE.md` passou a pegar também as frases do template 0.4.0 que sobrevivem em
  `CLAUDE.md` de duas eras ("o portão é convenção, não trava", "rode via `spec-impl-auto`").
- **`CLAUDE.md.template`**: seção "Where you are running" (o agente pode rodar na cópia local *ou*
  dentro do workspace hospedado, onde hooks e `settings.local.json` **não existem** — a trava só
  vale onde hook roda, e o arquivo agora diz isso); roteamento para `data-analyst` e
  `report-validator`; regra de escopo de escrita ligada ao `write-guard`.
- **`.claude/settings.local.json`** semeado pelo instalador (sem sobrescrever) só com a lista
  **`ask`** de comandos destrutivos (`git push/reset/clean/checkout/rm/rebase`, `rm -rf`,
  `Remove-Item`). `setup-sdd` §4 ganhou o passo a passo do write-guard e o roteamento dos agentes.
- Instaladores em par: `install.ps1` valida os arquivos novos em `$required`, os dois copiam
  `write-scope.json` e `settings.local.json` sem sobrescrever; `.ps1` deixou de imprimir a versão
  sem o espaço.

**Reversibilidade:** `write-scope.json` instala com `enabled: false` e sem hook ligado — nada muda
até o `setup-sdd` oferecer. Com `autoapprove.json` desligado (default do template), `spec-impl*` se
comporta exatamente como antes. Fase não canônica é aviso, não erro. `platform` só entra em
`integrations.md` quando o usuário declara que não há repo.

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
