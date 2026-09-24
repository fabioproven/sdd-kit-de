# Handoff — SDD Kit v0.9.0

Guia rápido para quem está recebendo o kit. Leitura de 3 minutos. Detalhes no `README.md`.

## O que é

Um kit que instala um fluxo de **Spec-Driven Development** em qualquer projeto usando Claude Code.
Uma ideia vira uma spec (requisitos → design → tarefas) e só então vira código verificado. Os portões
são **por risco, não por fase**: o fluxo roda contínuo e só para em humano no que é alto risco. O **motor é genérico**; o conhecimento do seu projeto é **gerado pelo próprio
agente** a partir do seu código.

## Requisitos

- Claude Code (CLI, desktop, web ou IDE) no projeto de destino.
- Python 3.7+ (`py` no Windows, `python3` no resto) — para o linter e a trava do modo automático.
- Nada mais. Sem pacotes.

## Instalar (2 minutos)

1. `git clone` do repositório (ou extrair o zip do release) → pasta `sdd-kit-de/`.
2. Rodar o instalador apontando para o SEU projeto:
   - Windows: `.\install.ps1 -Target C:\caminho\do\seu-projeto`
   - Linux/macOS: `./install.sh /caminho/do/seu-projeto`
3. Abrir o Claude Code dentro do projeto e rodar a skill **`setup-sdd`**. Ela conduz tudo por conversa:
   pergunta docs/convenções, git host e tracker; absorve conhecimento de IA prévia; gera o steering do
   seu código; mapeia as integrações.

## Primeiros 10 minutos (teste sem risco)

```
setup-sdd                                  # bootstrap guiado
/sdd:spec-quick "uma feature pequena" --spec-only   # gera req+design+tasks, NÃO toca em código
/sdd:spec-lint <feature>                   # valida rastreabilidade
```

Se os três artefatos saírem coerentes e o linter passar, o kit está instalado.

## No editor (0.7.0)

O instalador deixa um `.vscode/` no projeto (sem sobrescrever o que já existir). Abra a pasta no VS
Code com a extensão `anthropic.claude-code`: os mesmos `/sdd:*` rodam no painel lateral, com diff
renderizado no editor, e **Ctrl+Shift+B** roda o linter jogando cada erro de rastreabilidade no painel
**Problems** — clicável, abre na linha exata. A trava deixa de depender de alguém lembrar de pedir.

## Atualizando de uma versão anterior (0.7.0 → 0.9.0)

Reinstale por cima: o instalador faz backup antes de copiar, **preserva** arquivos do motor que você
tenha editado (a versão nova fica como `<arquivo>.sdd-new`) e escreve **`.sdd/UPGRADE.md`** — leia
esse arquivo primeiro. `steering/`, `specs/` e `CLAUDE.md` nunca são tocados.

Depois, dentro do projeto, rode **`/update-sdd`** (0.9.0): ele lê o audit determinístico
(`py tools/kit-sync.py audit --target .`) e fecha **só** o que a camada 2 deve à versão nova — steering
faltando, chave de config nova, `CLAUDE.md` remendado por seção com diff e o seu OK, fase de spec
fora do enum. Nunca sobrescreve, nunca apaga, nunca re-pergunta o que o projeto já respondeu.
`--dry-run` só mostra o plano. Não rode o `setup-sdd` de novo: ele mesmo te manda para o `/update-sdd`.

## Se o projeto tem plataforma de dados (0.6.0)

Três peças opcionais que separam "spec rastreável" de "resposta correta":

- **`semantic-layer.md`** (via `/sdd:steering-custom`) — contrato por métrica: fórmula, **grain**,
  população, dono. Métrica sem contrato não se inventa.
- **Escada de fontes** — semantic layer → modelo governado → SQL manual → raw. Descer é permitido;
  descer em silêncio, não.
- **`/sdd:spec-evals`** — 10–20 golden questions com ground truth **humano**. `--run` executa
  read-only; eval sem ground truth é SKIPPED, nunca PASS. `spec-lint --require-evals` torna a suite
  obrigatória no CI.

Em projeto sem plataforma de dados, nada disso é acionado.

## Três coisas que valem a pena entender

1. **Separação QUÊ/COMO** — `requirements.md` é comportamento testável (sem nomes de arquivo);
   `design.md` é a solução técnica.
2. **Rastreabilidade** — o mesmo ID (`Req 2.1`) viaja req → design → tarefa → checkbox; o
   `/sdd:spec-lint` garante que nada some.
3. **Portões por risco, não por fase** — `low`/`medium` correm sozinhos e logados com o modo aprovador
   ligado; **`high` é sempre humano**, sem exceção, e nenhuma flag ou config muda isso.

## Modo aprovador automático (config em `.sdd/autoapprove.json`, DESLIGADO por padrão)

Ligado, **todo `/sdd:spec-impl*` (e o `spec-quick`) roda sozinho** um loop executor↔aprovador com
trava de risco — desde a 0.8.0 não existe comando separado para lembrar (`spec-impl-auto` é só alias):
- **low** (ler/analisar/documentar) automático · **medium** (novo modelo/transformação) o aprovador
  decide, logado · **high** (schema, delete/overwrite, deploy, contrato de consumidor) **sempre humano**.
- Loop infinito é impossível: `tools/approval-gate.py` conta as iterações num ledger em disco e escala
  pro humano no teto (default 5). Tudo logado em `.sdd/specs/<feature>/approval-log.jsonl` — se a spec
  tem tarefa marcada e não tem ledger, o loop não rodou nela; o `spec-status` avisa.
- Liga/desliga por nível em `.sdd/autoapprove.json`. Comece conservador: só `low`, e observe o log encher.

## Quem constrói: `data-engineer` (0.9.0, desligado por padrão)

O primeiro agente do kit que **escreve** código: executor delegado do `spec-impl` /
`spec-impl-config`. Recebe um Work Order (subtarefa, critérios pass/fail, risco, escopo de escrita,
caminhos permitidos, ponteiros do design) e devolve um Work Report (arquivos, comandos, evidência,
critério a critério). Para e reporta — nunca contorna — fora do escopo, em risco maior que o
declarado, em métrica sem contrato. Liga em `.sdd/autoapprove.json` → `delegation`: **decide quem
digita, nunca quem aprova**; `high` continua humano. Desligado, é a 0.8.0 byte a byte.

## Os agentes de dados e a trava de escrita (0.8.0, para projeto com plataforma de dados)

- **`data-analyst`** — toda consulta à plataforma passa por ele: só leitura, escada de amostragem
  (metadados → agregação → `LIMIT 50`), sem PII, devolve o número com proveniência e nunca dump.
- **`report-validator`** — antes de qualquer relatório circular: reproduz cada número na fonte e
  caça rótulo mais amplo que a evidência, eixos misturados, afirmação sem lastro, número defasado.
- **`tools/write-guard.py`** — hook que **nega** escrita SQL fora de `.sdd/write-scope.json`. Instala
  desligado. Antes de ligar: `py tools/write-guard.py --self-test` e confirme na plataforma que cada
  schema permitido existe com a grafia exata — schema errado inverte a trava. E lembre: o hook só
  vale onde hook roda; dentro de um notebook hospedado ele não existe.

## O que já foi validado em produção — e o que ainda não

Um projeto real de plataforma de dados rodou o motor por cinco meses: **35 specs, ~1.000 IDs de
requisito, 35/35 passando no `spec-lint`**. `absorb-knowledge`, `discover-tools` e `steering` geraram
uma camada 2 que sobreviveu ao uso. O que **não** rodou lá foi o loop executor↔aprovador — estava
ligado na config e ninguém chamou o comando; a 0.8.0 existe em boa parte por isso (agora ele roda
dentro do `spec-impl`). A estreia que ainda falta é justamente essa: uma spec inteira pelo loop, com
o `approval-log.jsonl` enchendo. O `--spec-only` e o modo read-only das descobertas continuam
existindo para a primeira vez falhar de forma segura. Na 0.9.0, o executor delegado (`data-engineer`)
foi provado em bancada — recusa escrita fora do escopo, reporta risco subclassificado, faz TDD e devolve
o Work Report no formato — mas **ainda não rodou dentro de um projeto com o hook ligado**: a prova de
que o `write-guard` dispara na chamada do subagente é a estreia que falta. Manda feedback.

## Mapa rápido

- `docs/fluxo-visual.html` — **mapa visual do fluxo** (abre no navegador, funciona offline): estações,
  portões, rastreabilidade e o modo aprovador automático. Bom para apresentar/ensinar.
- `README.md` — visão completa e todos os comandos.
- `CHANGELOG.md` — o que veio em cada versão.
- `.claude/commands/` — os comandos (`sdd/*` + `prepare-pr`/`review`/`data-quality` + `update-sdd`).
- `.sdd/settings/` — motor (rules + templates). `.sdd/steering/` nasce vazio (é gerado).
- `tools/spec-lint.py`, `tools/approval-gate.py`, `tools/write-guard.py` — as travas determinísticas
  (rastreabilidade, loop, escopo de escrita); `tools/kit-sync.py` — continuidade entre versões e o
  `audit` que alimenta o `/update-sdd` (testes em `tools/tests/`).
- `.claude/agents/` — `code-explorer`, `approver`, `data-analyst`, `report-validator`, `data-engineer`.
- `.sdd/settings/rules/` — `data-readiness.md` (escada de fontes), `evals.md` (golden questions),
  `answer-provenance.md` (fonte/freshness/confiança em toda resposta com número),
  `spec-artifacts.md` (fases canônicas + `contract-impact.md` / `evidence/` / `rollback.md`).
