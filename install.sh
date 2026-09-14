#!/usr/bin/env bash
#
# install.sh — instala o SDD Kit (motor genérico) num projeto de destino.
#
# Uso:
#   ./install.sh /caminho/do/projeto-destino
#   ./install.sh .                      # instala no diretório atual
#
# O que faz:
#   - copia a CAMADA 1 (motor): comandos SDD, rules, templates, o linter e o
#     subagente code-explorer + a skill setup-sdd
#   - cria .sdd/steering e .sdd/specs VAZIOS (a serem gerados por /sdd:steering)
#   - instala CLAUDE.md a partir do template (sem sobrescrever um existente)
#   - instala .vscode/ (tasks, settings, extensions) sem sobrescrever
#   - NÃO gera a camada de projeto — isso é o próximo passo, com o agente
#
# Atualização sobre uma instalação anterior (via tools/kit-sync.py):
#   - faz backup de tudo que o motor pode tocar antes de copiar
#   - arquivo do motor editado no destino é PRESERVADO; a versão do kit fica
#     ao lado como <arquivo>.sdd-new
#   - grava .sdd/UPGRADE.md: o que foi preservado e o que a camada 2 ainda deve
#
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  echo "uso: ./install.sh <caminho-do-projeto-destino>"
  echo "     ./install.sh .        # diretório atual"
  exit 2
fi

TARGET="$(cd "$TARGET" 2>/dev/null && pwd || true)"
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "erro: diretório de destino não existe: ${1}"
  exit 1
fi
if [ "$TARGET" = "$KIT_DIR" ]; then
  echo "erro: o destino é a própria pasta do kit. Aponte para o seu projeto."
  exit 1
fi

echo "==> instalando SDD Kit ($(cat "$KIT_DIR/VERSION" 2>/dev/null || echo '?')) em: $TARGET"

# --- Continuidade: backup + memória do que a versão anterior instalou --------
# Mesmo runtime que o spec-lint já exige. `python` costuma cair no stub da
# Microsoft Store no Windows, que não executa — por isso testamos de verdade.
PYBIN=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1; then
    PYBIN="$c"
    break
  fi
done

BACKUP_DIR=""
if [ -n "$PYBIN" ]; then
  BACKUP_DIR="$("$PYBIN" "$KIT_DIR/tools/kit-sync.py" preflight \
                 --kit "$KIT_DIR" --target "$TARGET")" || BACKUP_DIR=""
else
  echo "    aviso: Python 3 nao encontrado — sem backup e sem preservacao de edicoes locais."
  echo "           O kit precisa de Python 3.7+ de qualquer forma (spec-lint, approval-gate)."
fi

# --- Camada 1: motor ---------------------------------------------------------
mkdir -p "$TARGET/.claude/commands/sdd" \
         "$TARGET/.claude/agents" \
         "$TARGET/.claude/skills/setup-sdd" \
         "$TARGET/.sdd/settings" \
         "$TARGET/.sdd/steering" \
         "$TARGET/.sdd/specs" \
         "$TARGET/tools"

cp -R "$KIT_DIR/.claude/commands/." "$TARGET/.claude/commands/"   # sdd/* + top-level (prepare-pr, review, data-quality)
cp -R "$KIT_DIR/.claude/agents/."   "$TARGET/.claude/agents/"
cp -R "$KIT_DIR/.claude/skills/."   "$TARGET/.claude/skills/"
cp -R "$KIT_DIR/.sdd/settings/."    "$TARGET/.sdd/settings/"
cp "$KIT_DIR/tools/"*.py "$TARGET/tools/"                       # spec-lint.py + approval-gate.py
cp "$KIT_DIR/VERSION" "$TARGET/.sdd/SDD_KIT_VERSION" 2>/dev/null || true

# Config do modo aprovador automatico: instala a versao editavel (nao sobrescreve)
if [ ! -f "$TARGET/.sdd/autoapprove.json" ]; then
  cp "$KIT_DIR/.sdd/settings/templates/autoapprove.json" "$TARGET/.sdd/autoapprove.json"
fi

# keep empty dirs under version control
[ -e "$TARGET/.sdd/steering/.gitkeep" ] || : > "$TARGET/.sdd/steering/.gitkeep"
[ -e "$TARGET/.sdd/specs/.gitkeep" ]    || : > "$TARGET/.sdd/specs/.gitkeep"

# --- Camada 2: CLAUDE.md (não sobrescreve) -----------------------------------
if [ -f "$TARGET/CLAUDE.md" ]; then
  cp "$KIT_DIR/CLAUDE.md.template" "$TARGET/CLAUDE.md.template"
  echo "    CLAUDE.md já existe — template copiado ao lado como CLAUDE.md.template"
else
  cp "$KIT_DIR/CLAUDE.md.template" "$TARGET/CLAUDE.md"
  echo "    CLAUDE.md criado a partir do template (edite os {{PLACEHOLDERS}})"
fi

# --- Integração com o editor: .vscode (nunca sobrescreve) --------------------
mkdir -p "$TARGET/.vscode"
for f in tasks.json settings.json extensions.json; do
  src="$KIT_DIR/.sdd/settings/templates/vscode/$f"
  dst="$TARGET/.vscode/$f"
  [ -f "$src" ] || continue
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    echo "    .vscode/$f criado"
  elif ! cmp -s "$src" "$dst"; then
    cp "$src" "$dst.sdd-new"
    echo "    .vscode/$f já existe — versão do kit ao lado como $f.sdd-new"
  fi
done

# --- Continuidade: preserva edições locais, grava manifesto e UPGRADE.md -----
if [ -n "$PYBIN" ]; then
  if [ -n "$BACKUP_DIR" ]; then
    "$PYBIN" "$KIT_DIR/tools/kit-sync.py" finish \
      --kit "$KIT_DIR" --target "$TARGET" --backup "$BACKUP_DIR" || true
  else
    "$PYBIN" "$KIT_DIR/tools/kit-sync.py" finish \
      --kit "$KIT_DIR" --target "$TARGET" || true
  fi
fi

echo ""
echo "==> motor instalado. Leia primeiro: .sdd/UPGRADE.md"
echo "    (o que foi preservado, o que revisar e o que a camada 2 ainda deve)"
echo ""
echo "    Próximos passos (no agente, dentro de $TARGET):"
echo "    1. rode a skill  setup-sdd        (bootstrap guiado — recomendado)"
echo "       ou manualmente:"
echo "    2. edite CLAUDE.md  (troque os {{PLACEHOLDERS}})"
echo "    3. /sdd:steering                  (gera product/tech/structure do seu código)"
echo "    4. /sdd:spec-quick \"feature real\" --spec-only   (teste ponta a ponta)"
echo "    5. /sdd:spec-lint <feature>       (valida rastreabilidade)"
echo ""
echo "steering foi deixado VAZIO de propósito — ele é gerado do SEU projeto."
