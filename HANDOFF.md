# Handoff — SDD Kit v0.7.0

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

## Atualizando de uma versão anterior (0.7.0)

Reinstale por cima: o instalador faz backup antes de copiar, **preserva** arquivos do motor que você
tenha editado (a versão nova fica como `<arquivo>.sdd-new`) e escreve **`.sdd/UPGRADE.md`** — leia
esse arquivo primeiro. Ele diz o que foi preservado e o que a sua camada 2 ainda deve à versão nova,
com o comando que gera cada pendência. `steering/`, `specs/` e `CLAUDE.md` nunca são tocados.

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

## Modo aprovador automático (opcional, DESLIGADO por padrão)

`/sdd:spec-impl-auto` reduz aprovações com um loop executor↔aprovador, com trava de risco:
- **low** (ler/analisar/documentar) automático · **medium** (novo modelo/transformação) o aprovador
  decide, logado · **high** (schema, delete/overwrite, deploy) **sempre humano**.
- Loop infinito é impossível: `tools/approval-gate.py` conta as iterações num ledger em disco e escala
  pro humano no teto (default 5). Tudo logado em `.sdd/specs/<feature>/approval-log.jsonl`.
- Liga/desliga por nível em `.sdd/autoapprove.json`. Comece conservador: só `low`, e observe o log encher.

## O que NÃO foi validado (seja o primeiro a testar)

Os fluxos conversacionais (setup, discovery, o loop do `spec-impl-auto`) são prompts bem definidos e o
mecanismo determinístico (linter, gate, ledger) foi testado — mas rodar isso ponta a ponta no SEU
projeto é a estreia. Por isso o `--spec-only` e o modo read-only das descobertas existem: falham de
forma segura na primeira vez. Manda feedback.

## Mapa rápido

- `docs/fluxo-visual.html` — **mapa visual do fluxo** (abre no navegador, funciona offline): estações,
  portões, rastreabilidade e o modo aprovador automático. Bom para apresentar/ensinar.
- `README.md` — visão completa e todos os comandos.
- `CHANGELOG.md` — o que veio em cada versão.
- `.claude/commands/` — os comandos (`sdd/*` + `prepare-pr`/`review`/`data-quality`).
- `.sdd/settings/` — motor (rules + templates). `.sdd/steering/` nasce vazio (é gerado).
- `tools/spec-lint.py` e `tools/approval-gate.py` — as travas determinísticas.
- `.sdd/settings/rules/` — `data-readiness.md` (escada de fontes), `evals.md` (golden questions),
  `answer-provenance.md` (fonte/freshness/confiança em toda resposta com número).
