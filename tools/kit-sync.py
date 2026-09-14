#!/usr/bin/env python3
"""
kit-sync — continuidade entre versões do SDD Kit no repo de destino.

Parte do SDD Kit — Fabio Provençale <fabio.provencale@gmail.com> — licença MIT.

Reinstalar o motor sobrescreve a camada 1. Sem memória do que foi instalado
antes, três coisas se perdem em silêncio: a edição local que alguém fez num
comando ou numa rule, o rastro de qual versão gerou o quê, e a noção do que a
camada 2 do destino ainda deve ao motor novo.

Este script fecha isso de forma determinística, com hash — não com confiança:

  1. `preflight` — antes do instalador copiar: tira um backup completo do que
     o motor vai tocar e imprime o caminho dele (única saída em stdout).
  2. `finish`    — depois da cópia: compara o estado pré-instalação com o
     manifesto da instalação anterior. Arquivo que bate com o manifesto era
     intocado, e a versão nova fica. Arquivo que NÃO bate foi editado no
     destino: a edição local é restaurada do backup e a versão do kit fica ao
     lado como `<arquivo>.sdd-new`. Nada é decidido pelo modelo.

Ao final, `finish` grava dois arquivos no destino:
  - `.sdd/.kit-manifest.json` — o que esta versão escreveu, com sha256 de cada
    arquivo. É o que permite a PRÓXIMA atualização saber o que foi editado.
  - `.sdd/UPGRADE.md` — relatório legível: de onde veio, o que foi preservado,
    o que revisar, e o que a camada 2 ainda não tem para esta versão do motor.

Primeira execução num destino sem manifesto (kit <= 0.6.0): nada é restaurado
(não há como distinguir edição local de arquivo original), mas o backup existe
e o manifesto passa a existir daí em diante. É o fallback conservador.

Uso (chamado pelos instaladores; raramente à mão):
  python tools/kit-sync.py preflight --kit <dir-do-kit> --target <destino>
  python tools/kit-sync.py finish    --kit <dir-do-kit> --target <destino> \\
                                     --backup <dir-impresso-pelo-preflight>

Sem dependências externas — Python 3.7+ stdlib apenas.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MANIFEST = os.path.join(".sdd", ".kit-manifest.json")
BACKUPS = os.path.join(".sdd", "backups")
REPORT = os.path.join(".sdd", "UPGRADE.md")
NEW_SUFFIX = ".sdd-new"

# Subárvores da camada 1: o instalador copia estas do kit para o destino com o
# mesmo caminho relativo. Se a lista de cópia dos instaladores mudar, mude aqui.
ENGINE_TREES = [
    os.path.join(".claude", "commands"),
    os.path.join(".claude", "agents"),
    os.path.join(".claude", "skills"),
    os.path.join(".sdd", "settings"),
]
ENGINE_GLOB_DIRS = [("tools", ".py")]

# O que o backup captura. Camada 2 (steering/specs/CLAUDE.md) entra não porque
# o instalador a toque, mas para que o backup sirva de prova de que não tocou.
BACKUP_ITEMS = [
    ".claude",
    ".sdd",
    "tools",
    ".vscode",
    "CLAUDE.md",
    "CLAUDE.md.template",
]

# Artefatos de camada 2 que o motor espera encontrar, e o comando que os gera.
# Genérico de propósito: são conceitos do kit, não de um projeto.
LAYER2_EXPECTED = [
    ("product.md", "/sdd:steering", "o que o projeto faz e para quem"),
    ("tech.md", "/sdd:steering", "stack, versões, comandos de build/test"),
    ("structure.md", "/sdd:steering", "layout do repo e convenções"),
    ("integrations.md", "/sdd:discover-tools", "Jira/git/dados — sem ele, /prepare-pr e /review param"),
    ("inherited-knowledge.md", "/sdd:absorb-knowledge", "convenções herdadas de configs de IA anteriores"),
]


def _copytree(src, dst, skip=frozenset()):
    """Cópia recursiva. Escrita à mão porque `dirs_exist_ok` só existe no 3.8+
    e o kit se compromete com 3.7."""
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name in skip:
            continue
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.isdir(s):
            _copytree(s, d, skip)
        else:
            shutil.copy2(s, d)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_version(kit_dir):
    p = os.path.join(kit_dir, "VERSION")
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "sem versao"


HISTORY = os.path.join(".sdd", "settings", "kit-history.json")


def kit_history_paths(kit_dir):
    """União dos caminhos de motor que TODA versão anterior do kit publicou.

    Serve para a primeira instalação com manifesto: um arquivo que já existia
    no destino e que nenhuma versão do kit jamais publicou não pode ser motor
    editado — é obra do projeto com o mesmo nome. Sem isso, o kit ao começar a
    publicar `agents/data-analyst.md` sobrescreveria o `data-analyst.md` que o
    projeto escreveu à mão. Vazio se o arquivo não existir (comportamento antigo).
    """
    p = os.path.join(kit_dir, HISTORY)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return frozenset()
    paths = set()
    for _version, rels in (data.get("versions") or {}).items():
        paths.update(rels or [])
    return frozenset(paths)


def engine_files(kit_dir):
    """Caminhos relativos de todo arquivo da camada 1 que o kit publica."""
    rels = []
    for tree in ENGINE_TREES:
        base = os.path.join(kit_dir, tree)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                full = os.path.join(root, fn)
                rels.append(os.path.relpath(full, kit_dir).replace(os.sep, "/"))
    for d, ext in ENGINE_GLOB_DIRS:
        base = os.path.join(kit_dir, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if fn.endswith(ext):
                rels.append(f"{d}/{fn}")
    return sorted(set(rels))


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def cmd_preflight(args):
    target = os.path.abspath(args.target)
    version = read_version(args.kit).replace("sdd-kit ", "").replace(" ", "-") or "sem-versao"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(target, BACKUPS, f"pre-{version}-{stamp}")

    os.makedirs(dest, exist_ok=True)
    copied = 0
    for item in BACKUP_ITEMS:
        src = os.path.join(target, item)
        if not os.path.exists(src):
            continue
        dst = os.path.join(dest, item)
        if os.path.isdir(src):
            # backups/ nunca entra no backup — senão cada upgrade dobra de tamanho.
            _copytree(src, dst, skip={"backups", "__pycache__"})
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        copied += 1

    print(f"[kit-sync] backup do estado atual: {os.path.relpath(dest, target)}", file=sys.stderr)
    if copied == 0:
        print("[kit-sync] destino vazio - instalacao nova, nada a preservar", file=sys.stderr)
    # stdout = so o caminho, para o instalador capturar
    print(dest)
    return 0


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------

def cmd_finish(args):
    target = os.path.abspath(args.target)
    kit = os.path.abspath(args.kit)
    backup = os.path.abspath(args.backup) if args.backup else None
    version = read_version(kit)

    prev_manifest = {}
    prev_version = None
    if backup:
        mp = os.path.join(backup, MANIFEST)
        if os.path.isfile(mp):
            try:
                with open(mp, encoding="utf-8") as f:
                    data = json.load(f)
                prev_manifest = data.get("files", {})
                prev_version = data.get("version")
            except (OSError, ValueError):
                pass
    if prev_version is None:
        vp = os.path.join(backup or "", ".sdd", "SDD_KIT_VERSION")
        if backup and os.path.isfile(vp):
            with open(vp, encoding="utf-8") as f:
                prev_version = f.read().strip()

    rels = engine_files(kit)
    preserved, first_time = [], (not prev_manifest)
    ever_shipped = kit_history_paths(kit)

    if backup:
        for rel in rels:
            tgt = os.path.join(target, rel.replace("/", os.sep))
            bak = os.path.join(backup, rel.replace("/", os.sep))
            src = os.path.join(kit, rel.replace("/", os.sep))
            if not os.path.isfile(bak) or not os.path.isfile(src):
                continue                      # nao existia no destino: nada a preservar
            known = prev_manifest.get(rel)
            if known:
                if sha256(bak) == known:
                    continue                  # intocado desde a ultima instalacao
                keep = True                   # editado no destino
            elif not first_time or rel not in ever_shipped:
                # O kit passa a publicar este caminho AGORA, mas o destino ja tinha um
                # arquivo com esse nome — e nenhuma versao anterior do kit o publicou.
                # Logo e obra do projeto (um agente, um hook, uma skill propria):
                # colisao por nome, nao edicao. Preservar, kit ao lado.
                keep = sha256(bak) != sha256(src)
            else:
                continue                      # primeira instalacao com manifesto: sem como saber
            if not keep:
                continue
            # A edicao/obra local volta, a do kit fica ao lado.
            if os.path.isfile(tgt):
                shutil.copy2(tgt, tgt + NEW_SUFFIX)
            shutil.copy2(bak, tgt)
            preserved.append(rel)

    # Arquivos que a versao anterior instalou e esta nao publica mais.
    orphans = [
        rel for rel in sorted(prev_manifest)
        if rel not in rels and os.path.isfile(os.path.join(target, rel.replace("/", os.sep)))
    ]

    # Manifesto novo: o hash do que o KIT publica nesta versão — não o do que
    # ficou em disco. A diferença importa exatamente nos arquivos preservados:
    # se gravássemos o conteúdo local, o próximo upgrade veria "bate com o
    # manifesto", concluiria "intocado" e comeria a customização em silêncio.
    # Guardando o hash do kit, a edição local continua sendo detectada como
    # edição local em toda atualização futura.
    files = {}
    for rel in rels:
        tgt = os.path.join(target, rel.replace("/", os.sep))
        src = os.path.join(kit, rel.replace("/", os.sep))
        if os.path.isfile(tgt) and os.path.isfile(src):
            files[rel] = sha256(src)
    manifest_path = os.path.join(target, MANIFEST)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(
            {
                "version": version,
                "previous_version": prev_version,
                "installed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "backup": os.path.relpath(backup, target).replace(os.sep, "/") if backup else None,
                "preserved": preserved,
                "files": files,
            },
            f, indent=2, ensure_ascii=False, sort_keys=True,
        )
        f.write("\n")

    gaps = layer2_gaps(target)
    write_report(target, kit, version, prev_version, backup, preserved, orphans, gaps, first_time)

    print(f"[kit-sync] manifesto: {len(files)} arquivos de motor registrados", file=sys.stderr)
    if preserved:
        print(f"[kit-sync] {len(preserved)} edicao(oes) local(is) preservada(s) - veja .sdd/UPGRADE.md",
              file=sys.stderr)
    if orphans:
        print(f"[kit-sync] {len(orphans)} arquivo(s) do motor antigo sobraram - listados em .sdd/UPGRADE.md",
              file=sys.stderr)
    if gaps:
        print(f"[kit-sync] camada 2: {len(gaps)} pendencia(s) - veja .sdd/UPGRADE.md", file=sys.stderr)
    return 0


def layer2_gaps(target):
    """O que o motor espera da camada 2 e o destino ainda não tem.

    Só checagens de existência sobre artefatos do próprio kit — nada aqui sabe
    nada sobre o projeto de destino.
    """
    gaps = []
    steering = os.path.join(target, ".sdd", "steering")
    for name, cmd, why in LAYER2_EXPECTED:
        if not os.path.isfile(os.path.join(steering, name)):
            gaps.append((f"`.sdd/steering/{name}`", cmd, why))

    claude_md = os.path.join(target, "CLAUDE.md")
    if os.path.isfile(claude_md):
        try:
            with open(claude_md, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            text = ""
        if "{{" in text:
            gaps.append(("`CLAUDE.md` ainda tem `{{PLACEHOLDERS}}`", "setup-sdd",
                         "o template nunca foi preenchido"))
        low = text.lower()
        if "approval gate at each phase" in low:
            gaps.append(("`CLAUDE.md` descreve portao por FASE", "setup-sdd",
                         "postura anterior a 0.5.0 — a autonomia por risco nao esta ativa"))
        # Texto de duas eras convivendo: o "nao use --auto ... o portao e convencao"
        # do template 0.4.0 sobrevive em CLAUDE.md que ja diz "portoes por risco".
        if ("the gate is convention, not a lock" in low
                or "portão é convenção, não trava" in low
                or "portao e convencao, nao trava" in low):
            gaps.append(("`CLAUDE.md` ainda diz que o portao 'e convencao, nao trava'", "setup-sdd",
                         "frase do template 0.4.0; desde 0.8.0 o write-guard e a trava — "
                         "ligue-o em .sdd/write-scope.json e troque a frase"))
        if "spec-impl-auto" in low and "0.8" not in low:
            gaps.append(("`CLAUDE.md` manda usar `/sdd:spec-impl-auto`", "setup-sdd",
                         "desde 0.8.0 o loop roda dentro de /sdd:spec-impl quando "
                         "autoapprove.json esta ligado — o comando separado e so alias"))
    else:
        gaps.append(("`CLAUDE.md`", "setup-sdd", "o orquestrador do projeto nao existe"))

    specs_dir = os.path.join(target, ".sdd", "specs")
    if os.path.isdir(specs_dir):
        for spec in sorted(os.listdir(specs_dir)):
            d = os.path.join(specs_dir, spec)
            if os.path.isdir(d) and os.path.isfile(os.path.join(d, "requirements.md")) \
               and not os.path.isfile(os.path.join(d, "evals.md")):
                gaps.append((f"`.sdd/specs/{spec}/evals.md`", "/sdd:spec-evals",
                             "spec sem suite de evals"))
    return gaps


def write_report(target, kit, version, prev_version, backup, preserved, orphans, gaps, first_time):
    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append(f"# Upgrade do SDD Kit — {version}\n")
    L.append(f"Gerado por `kit-sync.py` em {when}. Este arquivo é reescrito a cada instalação.\n")
    if prev_version and prev_version != version:
        L.append(f"**De:** {prev_version} → **para:** {version}\n")
    elif prev_version:
        L.append(f"**Reinstalação da mesma versão** ({version}).\n")
    else:
        L.append(f"**Primeira instalação registrada** ({version}).\n")
    if backup:
        L.append(f"**Backup do estado anterior:** `{os.path.relpath(backup, target).replace(os.sep, '/')}`\n")

    L.append("\n## O que foi preservado\n")
    if first_time and not preserved:
        L.append(
            "Esta é a primeira instalação com manifesto. Não havia como distinguir "
            "arquivo de motor editado no destino de arquivo original, então **nada foi "
            "restaurado** — o motor novo está inteiro. O backup acima tem o estado "
            "anterior, e da próxima atualização em diante a preservação é automática.\n"
        )
    elif first_time and preserved:
        L.append(
            "Esta é a primeira instalação com manifesto: arquivo de motor que uma versão "
            "anterior do kit publicou não pôde ser distinguido de edição local, então foi "
            "**atualizado** (o backup acima guarda o anterior). Já estes arquivos **nunca "
            "foram publicados por nenhuma versão do kit** — são obra do projeto que colidiu "
            "por nome com algo que o kit passou a instalar agora. A sua versão ficou; a do "
            "kit está ao lado como `.sdd-new` para você comparar e fundir:\n"
        )
        for rel in preserved:
            L.append(f"- `{rel}` (nova em `{rel}{NEW_SUFFIX}`)")
        L.append("")
    elif preserved:
        L.append(
            "Estes arquivos do motor tinham edição local. A sua versão foi mantida; "
            "a do kit novo está ao lado com o sufixo `.sdd-new` para você comparar "
            "e decidir:\n"
        )
        for rel in preserved:
            L.append(f"- `{rel}` (nova em `{rel}{NEW_SUFFIX}`)")
        L.append("")
    else:
        L.append("Nenhum arquivo do motor tinha edição local — atualização limpa.\n")

    L.append("\n## Camada 2 — intocada por definição\n")
    L.append(
        "`.sdd/steering/`, `.sdd/specs/` e `CLAUDE.md` são **gerados do seu projeto**, "
        "não copiados do kit. Nenhuma instalação os sobrescreve. O backup acima serve "
        "de prova: compare os hashes se quiser confirmar.\n"
    )

    if orphans:
        L.append("\n## Sobras da versão anterior\n")
        L.append(
            "Estes arquivos foram instalados por uma versão anterior e **não existem "
            "mais no motor**. Ficaram no lugar de propósito — apagar é irreversível, "
            "logo é decisão humana. Se você não os customizou, pode remover:\n"
        )
        for rel in orphans:
            L.append(f"- `{rel}`")
        L.append("")

    L.append("\n## O que a camada 2 ainda deve a esta versão\n")
    if gaps:
        L.append(
            "O motor novo espera estes artefatos. Reinstalar **não** os cria: camada 2 "
            "é gerada, não copiada. Rode os comandos abaixo dentro do projeto.\n"
        )
        L.append("| Falta | Gere com | Por quê |")
        L.append("|---|---|---|")
        for what, cmd, why in gaps:
            L.append(f"| {what} | `{cmd}` | {why} |")
        L.append("")
    else:
        L.append("Nada pendente — a camada 2 está completa para esta versão do motor.\n")
    L.append(
        "\nA lista acima cobre só o steering que todo projeto tem. Os arquivos "
        "opcionais (`semantic-layer.md` entre eles, o que fixa a definição de "
        "cada métrica num projeto de dados) são oferecidos por "
        "`/sdd:steering-custom` — não entram aqui porque nem todo projeto os "
        "quer.\n"
    )

    L.append("\n## Próximo passo\n")
    if gaps:
        L.append(
            "Abra o agente na raiz do projeto e rode a skill `setup-sdd`: ela cobre as "
            "pendências acima numa conversa só, aproveitando o que já existe em vez de "
            "recomeçar. Para fechar uma pendência isolada, use o comando da tabela.\n"
        )
    else:
        L.append("Rode `/sdd:spec-lint --all` e siga o fluxo normalmente.\n")

    path = os.path.join(target, REPORT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description="Continuidade entre versões do SDD Kit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("preflight", help="backup antes da cópia; imprime o caminho do backup")
    pf.add_argument("--kit", required=True)
    pf.add_argument("--target", required=True)
    pf.set_defaults(func=cmd_preflight)

    fi = sub.add_parser("finish", help="preserva edições locais, grava manifesto e UPGRADE.md")
    fi.add_argument("--kit", required=True)
    fi.add_argument("--target", required=True)
    fi.add_argument("--backup", help="caminho impresso pelo preflight")
    fi.set_defaults(func=cmd_finish)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
