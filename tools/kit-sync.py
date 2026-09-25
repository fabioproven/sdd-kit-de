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
  3. `audit`     — (0.9.0) só leitura: o que a camada 2 ainda deve ao motor
     instalado, como fato calculado do disco. Tabela de checagens versionada
     (cada uma sabe em que versão do kit nasceu), saída humana ou JSON.
     Exit 0 = nada pendente · 1 = pendências · 2 = motor ausente / erro.
     É o que `/update-sdd` lê — e é a MESMA computação que gera o UPGRADE.md,
     para não haver duas verdades.
  4. `report`    — (0.9.0) reescreve `.sdd/UPGRADE.md` a partir de um audit
     novo, sem tocar no manifesto. Chamado pelo `/update-sdd` ao terminar.

Ao final, `finish` grava dois arquivos no destino:
  - `.sdd/.kit-manifest.json` — o que esta versão escreveu, com sha256 de cada
    arquivo. É o que permite a PRÓXIMA atualização saber o que foi editado.
  - `.sdd/UPGRADE.md` — relatório legível: de onde veio, o que foi preservado,
    o que revisar, e o que a camada 2 ainda não tem para esta versão do motor.

Primeira execução num destino sem manifesto (kit <= 0.6.0): nada é restaurado
(não há como distinguir edição local de arquivo original), mas o backup existe
e o manifesto passa a existir daí em diante. É o fallback conservador.

Uso (chamado pelos instaladores; `audit`/`report` também pelo /update-sdd):
  python tools/kit-sync.py preflight --kit <dir-do-kit> --target <destino>
  python tools/kit-sync.py finish    --kit <dir-do-kit> --target <destino> \\
                                     --backup <dir-impresso-pelo-preflight>
  python tools/kit-sync.py audit     --target <destino> [--kit <dir>] [--format human|json]
  python tools/kit-sync.py report    --target <destino> [--kit <dir>]

Sem dependências externas — Python 3.7+ stdlib apenas.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
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
VERSION_MARKER = os.path.join(".sdd", "SDD_KIT_VERSION")
HISTORY = os.path.join(".sdd", "settings", "kit-history.json")
TEMPLATE_NAME = "CLAUDE.md.template"
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
    TEMPLATE_NAME,
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


def _read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_version(kit_dir):
    p = os.path.join(kit_dir, "VERSION")
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "sem versao"


def _ver_tuple(text):
    """'sdd-kit 0.8.0' -> (0, 8, 0). Sem número -> (0, 0, 0)."""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def kit_history(kit_dir):
    data = _read_json(os.path.join(kit_dir, HISTORY)) or {}
    return data.get("versions") or {}


def kit_history_paths(kit_dir, up_to=None, before=None):
    """União dos caminhos de motor que as versões ANTERIORES do kit publicaram.

    Serve para a primeira instalação com manifesto: um arquivo que já existia
    no destino e que nenhuma versão que o destino PODE ter tido publicou não é
    motor editado — é obra do projeto com o mesmo nome. Sem isso, o kit ao
    começar a publicar `agents/data-analyst.md` sobrescreveria o
    `data-analyst.md` que o projeto escreveu à mão.

    `up_to`  = versão que estava instalada (marcador .sdd/SDD_KIT_VERSION):
               conta só versões <= ela.
    `before` = versão que está sendo instalada: conta só versões < ela.
    (0.9.1) Até a 0.9.0 a união incluía a própria versão nova — logo todo
    arquivo publicado hoje contava como "já publicado" e a colisão nunca era
    reconhecida na primeira instalação com manifesto. Vazio se o histórico não
    existir (comportamento antigo).
    """
    paths = set()
    lim_le = _ver_tuple(up_to) if up_to else None
    lim_lt = _ver_tuple(before) if before else None
    for version, rels in kit_history(kit_dir).items():
        v = _ver_tuple(version)
        if lim_le is not None and v > lim_le:
            continue
        if lim_le is None and lim_lt is not None and v >= lim_lt:
            continue
        paths.update(rels or [])
    return frozenset(paths)


def first_version_shipping(kit_dir, rel):
    """Menor versão do histórico que publicou `rel`; None se nenhuma."""
    best = None
    for version, rels in kit_history(kit_dir).items():
        if rel in (rels or []):
            if best is None or _ver_tuple(version) < _ver_tuple(best):
                best = version
    return best


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
        data = _read_json(os.path.join(backup, MANIFEST))
        if data:
            prev_manifest = data.get("files", {})
            prev_version = data.get("version")
    if prev_version is None and backup:
        vp = os.path.join(backup, VERSION_MARKER)
        if os.path.isfile(vp):
            prev_version = (_read_text(vp) or "").strip() or None

    rels = engine_files(kit)
    preserved, first_time = [], (not prev_manifest)
    # So versoes que o destino pode ter tido: ate a que estava instalada, ou,
    # sem marcador, tudo que e anterior a versao que esta entrando agora.
    # Sem marcador, o kit nunca esteve aqui: qualquer arquivo com nome de motor
    # e obra do projeto e fica (o do kit vai ao lado como .sdd-new) - 0.9.2.
    ever_shipped = kit_history_paths(kit, up_to=prev_version) if prev_version else frozenset()

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

    # O relatório nasce da MESMA computação que o `audit` expõe ao /update-sdd.
    result = audit(target, kit)
    write_report(target, result, preserved, first_time)

    gaps = result["gaps"]
    print(f"[kit-sync] manifesto: {len(files)} arquivos de motor registrados", file=sys.stderr)
    if preserved:
        print(f"[kit-sync] {len(preserved)} edicao(oes) local(is) preservada(s) - veja .sdd/UPGRADE.md",
              file=sys.stderr)
    orphans = [g for g in gaps if g["id"] == "engine.orphan"]
    if orphans:
        print(f"[kit-sync] {len(orphans)} arquivo(s) do motor antigo sobraram - listados em .sdd/UPGRADE.md",
              file=sys.stderr)
    if gaps:
        print(f"[kit-sync] camada 2: {len(gaps)} pendencia(s) - veja .sdd/UPGRADE.md", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# audit — o que a camada 2 deve ao motor instalado (só leitura, determinístico)
# ---------------------------------------------------------------------------
#
# Cada checagem sabe em que versão do kit nasceu (`since`), qual a gravidade e o
# que a fecha. Nada aqui lê conteúdo do projeto: só a existência de artefatos
# do kit, frases-marcador dos templates antigos, cabeçalhos do template atual,
# chaves dos JSONs de config e nomes dos agentes que o próprio kit publicou.

SEVERITY_ORDER = {"blocking": 0, "recommended": 1, "optional": 2}

CANONICAL_PHASES = {
    "initialized", "requirements-generated", "design-generated", "tasks-generated",
    "tasks-approved", "implementation-in-progress", "implementation-complete",
}

# Steering que todo projeto tem. (arquivo, since, gravidade, comando, por quê)
STEERING_EXPECTED = [
    ("product.md", "0.1.0", "blocking", "/sdd:steering", "o que o projeto faz e para quem"),
    ("tech.md", "0.1.0", "blocking", "/sdd:steering", "stack, versoes, comandos de build/test"),
    ("structure.md", "0.1.0", "blocking", "/sdd:steering", "layout do repo e convencoes"),
    ("integrations.md", "0.2.0", "blocking", "/sdd:discover-tools",
     "Jira/git/dados - sem ele, /prepare-pr e /review param"),
    ("inherited-knowledge.md", "0.2.0", "recommended", "/sdd:absorb-knowledge",
     "convencoes herdadas de configs de IA anteriores"),
]

# Frases de templates antigos que denunciam a era do CLAUDE.md.
# (id, since, gravidade, marcadores em minusculas, o que, por que)
CLAUDE_STALE_MARKERS = [
    ("claude.phase-gates", "0.5.0", "blocking", ["approval gate at each phase"],
     "`CLAUDE.md` descreve portao por FASE",
     "postura anterior a 0.5.0 - a autonomia por risco nao esta ativa"),
    ("claude.convention-not-lock", "0.8.0", "recommended",
     ["the gate is convention, not a lock", "portão é convenção, não trava",
      "portao e convencao, nao trava"],
     "`CLAUDE.md` ainda diz que o portao 'e convencao, nao trava'",
     "frase do template 0.4.0; desde 0.8.0 o write-guard e a trava - "
     "ligue-o em .sdd/write-scope.json e troque a frase"),
]

# Em que versao cada secao do CLAUDE.md.template nasceu (chave = primeira
# palavra normalizada do cabecalho). Ausente aqui = 0.1.0.
SECTION_SINCE = {
    "auto-approval": "0.4.0",
    "data": "0.6.0",
    "where": "0.8.0",
}

# Configs editaveis que o instalador copia uma vez e nunca sobrescreve.
# (rel no destino, rel do template dentro de .sdd/settings, since, gravidade)
CONFIG_FILES = [
    (os.path.join(".sdd", "autoapprove.json"),
     os.path.join("templates", "autoapprove.json"), "0.4.0", "recommended"),
    (os.path.join(".sdd", "write-scope.json"),
     os.path.join("templates", "write-scope.json"), "0.8.0", "recommended"),
]
# Em que versao cada chave de config nasceu. Ausente aqui = versao do arquivo.
CONFIG_KEY_SINCE = {
    "autoapprove.json": {"delegation": "0.9.0"},
}


def _gap(gid, since, severity, what, closes_with, why, path=None):
    return {"id": gid, "since": since, "severity": severity, "what": what,
            "closes_with": closes_with, "why": why, "path": path}


def _norm_heading(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\-]+", " ", text)
    return " ".join(text.split())


def template_sections(template_text):
    """[(heading, chave, opcional)] das secoes `## ` do template.

    Opcional = o template diz, no comentario logo abaixo do cabecalho, que a
    secao pode ser apagada ('only if', 'delete'). E o proprio template que se
    descreve - nada aqui precisa mudar quando ele ganhar secao nova.
    """
    lines = (template_text or "").splitlines()
    out = []
    for i, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        heading = line[3:].strip()
        window = " ".join(lines[i + 1:i + 4]).lower()
        optional = (("<!--" in window) and ("only if" in window or "delete" in window)
                    or "delete" in heading.lower())
        words = _norm_heading(heading).split()
        key = " ".join(words[:2])
        out.append((heading, key, optional))
    return out


def _project_headings(text):
    return [_norm_heading(l[3:]) for l in (text or "").splitlines() if l.startswith("## ")]


def _heading_present(key, headings):
    first = key.split()[0] if key else ""
    for h in headings:
        if h == first or h.startswith(key):
            return True
    return False


def _installed_engine_agents(target, kit):
    """Agentes instalados que o KIT publicou (nome do frontmatter, since).
    Agente escrito pelo projeto com o mesmo layout nao entra: nao e conceito do kit."""
    out = []
    base = os.path.join(target, ".claude", "agents")
    if not os.path.isdir(base):
        return out
    for fn in sorted(os.listdir(base)):
        if not fn.endswith(".md"):
            continue
        since = first_version_shipping(kit, f".claude/agents/{fn}")
        if since is None:
            continue
        text = _read_text(os.path.join(base, fn)) or ""
        m = re.search(r"^name:\s*(\S+)", text, re.M)
        out.append((m.group(1) if m else fn[:-3], since))
    return out


def _json_top_keys(data):
    return [k for k in (data or {}) if not str(k).startswith("_")]


def _walk_sdd_new(target):
    found, seen = [], set()
    roots = [os.path.join(target, t) for t in ENGINE_TREES]
    roots += [os.path.join(target, "tools"), os.path.join(target, ".vscode"),
              os.path.join(target, ".claude")]
    for root_dir in roots:
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ("backups", "__pycache__")]
            for fn in files:
                if fn.endswith(NEW_SUFFIX):
                    rel = os.path.relpath(os.path.join(root, fn), target).replace(os.sep, "/")
                    if rel not in seen:
                        seen.add(rel)
                        found.append(rel)
    return sorted(found)


def _orphans(target, manifest):
    """Arquivos que a instalacao ANTERIOR publicou, a atual nao publica, e
    continuam no disco. Precisa do manifesto anterior (guardado no backup)."""
    if not manifest or not manifest.get("backup"):
        return []
    prev = _read_json(os.path.join(target, manifest["backup"].replace("/", os.sep), MANIFEST))
    if not prev:
        return []
    current = set(manifest.get("files") or {})
    out = []
    for rel in sorted(prev.get("files") or {}):
        if rel not in current and os.path.isfile(os.path.join(target, rel.replace("/", os.sep))):
            out.append(rel)
    return out


def audit(target, kit=None):
    """Computa as pendencias da camada 2. Puro: recebe caminhos, devolve dados,
    nao escreve nada. `kit` = raiz do kit (template e historico lidos de la);
    sem `kit`, le as copias instaladas no proprio destino."""
    target = os.path.abspath(target)
    kit = os.path.abspath(kit) if kit else target

    engine_present = (os.path.isfile(os.path.join(target, VERSION_MARKER))
                      or os.path.isdir(os.path.join(target, ".sdd", "settings", "rules")))
    if not engine_present:
        return {"engine": "absent", "kit_version": None, "previous_version": None,
                "layer2": "absent", "gaps": [],
                "message": "motor ausente: .sdd/SDD_KIT_VERSION e .sdd/settings/rules nao existem - "
                           "rode o instalador (install.sh / install.ps1) primeiro"}

    kit_version = (_read_text(os.path.join(target, VERSION_MARKER)) or "").strip() or None
    manifest = _read_json(os.path.join(target, MANIFEST)) or {}
    previous_version = manifest.get("previous_version")
    gaps = []

    # --- steering ----------------------------------------------------------
    steering = os.path.join(target, ".sdd", "steering")
    steering_md = [f for f in os.listdir(steering) if f.endswith(".md")] \
        if os.path.isdir(steering) else []
    for name, since, sev, cmd, why in STEERING_EXPECTED:
        if not os.path.isfile(os.path.join(steering, name)):
            gaps.append(_gap(f"steering.{name[:-3]}", since, sev, f"`.sdd/steering/{name}`",
                             cmd, why, f".sdd/steering/{name}"))

    # --- CLAUDE.md ---------------------------------------------------------
    claude = _read_text(os.path.join(target, "CLAUDE.md"))
    template = _read_text(os.path.join(kit, TEMPLATE_NAME))
    if claude is None:
        gaps.append(_gap("claude.missing", "0.1.0", "blocking", "`CLAUDE.md`", "setup-sdd",
                         "o orquestrador do projeto nao existe", "CLAUDE.md"))
        layer2 = "absent"
    else:
        low = claude.lower()
        if "{{" in claude:
            gaps.append(_gap("claude.placeholders", "0.1.0", "blocking",
                             "`CLAUDE.md` ainda tem `{{PLACEHOLDERS}}`", "/update-sdd",
                             "o template nunca foi preenchido", "CLAUDE.md"))
        for gid, since, sev, markers, what, why in CLAUDE_STALE_MARKERS:
            if any(m in low for m in markers):
                gaps.append(_gap(gid, since, sev, what, "/update-sdd", why, "CLAUDE.md"))
        # Citar o comando como *alias* (template >= 0.8.0) nao e pendencia; mandar usa-lo e.
        if "spec-impl-auto" in low and not any(k in low for k in ("alias", "0.8", "0.9")):
            gaps.append(_gap("claude.spec-impl-auto", "0.8.0", "recommended",
                             "`CLAUDE.md` manda usar `/sdd:spec-impl-auto`", "/update-sdd",
                             "desde 0.8.0 o loop roda dentro de /sdd:spec-impl quando "
                             "autoapprove.json esta ligado - o comando separado e so alias",
                             "CLAUDE.md"))
        if template is not None:
            headings = _project_headings(claude)
            for heading, key, optional in template_sections(template):
                if optional or _heading_present(key, headings):
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
                since = SECTION_SINCE.get(key.split()[0], "0.1.0")
                gaps.append(_gap(f"claude.section.{slug}", since, "recommended",
                                 f"`CLAUDE.md` sem a secao `## {heading}`", "/update-sdd",
                                 "secao do template atual ausente - o /update-sdd insere so ela, "
                                 "com diff para confirmar", "CLAUDE.md"))
        for agent, since in _installed_engine_agents(target, kit):
            if agent.lower() not in low:
                gaps.append(_gap(f"claude.routing.{agent}", since, "recommended",
                                 f"`CLAUDE.md` nao roteia para o agente `{agent}`", "/update-sdd",
                                 "o motor instalou o agente mas o orquestrador nao sabe que ele existe",
                                 "CLAUDE.md"))
        layer2 = "present" if (steering_md and "{{" not in claude) else "absent"

    # --- configs -------------------------------------------------------------
    for rel, tpl_rel, since, sev in CONFIG_FILES:
        fname = os.path.basename(rel)
        stem = fname[:-5]
        tpl = _read_json(os.path.join(kit, ".sdd", "settings", tpl_rel))
        dst = os.path.join(target, rel)
        rel_posix = rel.replace(os.sep, "/")
        if not os.path.isfile(dst):
            gaps.append(_gap(f"config.{stem}.missing", since, sev, f"`{rel_posix}`",
                             "/update-sdd", "config editavel ausente - o kit copia o template (desligado)",
                             rel_posix))
            continue
        cur = _read_json(dst)
        if cur is None:
            gaps.append(_gap(f"config.{stem}.invalid", since, "blocking",
                             f"`{rel_posix}` nao e JSON valido", "/update-sdd",
                             "config ilegivel e tratada como desligada; corrija a sintaxe", rel_posix))
            continue
        if not isinstance(tpl, dict) or not isinstance(cur, dict):
            continue
        key_since = CONFIG_KEY_SINCE.get(fname, {})
        for key in _json_top_keys(tpl):
            if key not in cur:
                gaps.append(_gap(f"config.{stem}.key.{key}", key_since.get(key, since),
                                 "recommended", f"`{rel_posix}` sem a chave `{key}`", "/update-sdd",
                                 "chave que uma versao mais nova do kit adicionou - entra com o "
                                 "default (desligado), valores existentes ficam", rel_posix))
            elif isinstance(tpl[key], dict) and isinstance(cur[key], dict):
                for sub in _json_top_keys(tpl[key]):
                    if sub not in cur[key]:
                        gaps.append(_gap(f"config.{stem}.key.{key}.{sub}",
                                         key_since.get(key, since), "recommended",
                                         f"`{rel_posix}` sem `{key}.{sub}`", "/update-sdd",
                                         "subchave nova - entra com o default", rel_posix))

    if not os.path.isfile(os.path.join(target, ".vscode", "tasks.json")):
        gaps.append(_gap("config.vscode.missing", "0.7.0", "optional", "`.vscode/tasks.json`",
                         "/update-sdd", "sem ele o spec-lint nao aparece no painel Problems (Ctrl+Shift+B)",
                         ".vscode/tasks.json"))

    # --- motor: pendencias de merge e sobras --------------------------------
    for rel in _walk_sdd_new(target):
        gaps.append(_gap("engine.sdd-new", "0.7.0", "recommended", f"`{rel}` aguarda decisao",
                         "/update-sdd", "edicao local preservada; a versao do kit esta ao lado - "
                         "compare e decida (manter, trocar, fundir)", rel))
    for rel in _orphans(target, manifest):
        gaps.append(_gap("engine.orphan", "0.7.0", "optional", f"`{rel}` sobrou da versao anterior",
                         "/update-sdd", "o motor atual nao publica mais este arquivo; apagar e "
                         "irreversivel, logo e decisao humana", rel))

    # --- specs ---------------------------------------------------------------
    specs_dir = os.path.join(target, ".sdd", "specs")
    if os.path.isdir(specs_dir):
        for spec in sorted(os.listdir(specs_dir)):
            d = os.path.join(specs_dir, spec)
            if not os.path.isdir(d) or not os.path.isfile(os.path.join(d, "requirements.md")):
                continue
            if not os.path.isfile(os.path.join(d, "evals.md")):
                gaps.append(_gap(f"spec.{spec}.evals", "0.6.0", "optional",
                                 f"`.sdd/specs/{spec}/evals.md`", f"/sdd:spec-evals {spec}",
                                 "spec sem suite de evals", f".sdd/specs/{spec}/evals.md"))
            sj = _read_json(os.path.join(d, "spec.json"))
            phase = (sj or {}).get("phase")
            if sj is not None and phase not in CANONICAL_PHASES:
                gaps.append(_gap(f"spec.{spec}.phase", "0.8.0", "recommended",
                                 f"`.sdd/specs/{spec}/spec.json` com fase `{phase}`", "/update-sdd",
                                 "fase fora do vocabulario canonico (rules/spec-artifacts.md); "
                                 "o /update-sdd propoe o mapeamento e aplica com confirmacao",
                                 f".sdd/specs/{spec}/spec.json"))

    gaps.sort(key=lambda g: (SEVERITY_ORDER.get(g["severity"], 9), g["id"], g["path"] or ""))
    return {"engine": "present", "kit_version": kit_version, "previous_version": previous_version,
            "layer2": layer2, "template_found": template is not None, "gaps": gaps}


def format_audit_human(result):
    L = []
    if result.get("engine") == "absent":
        return "[kit-sync] " + result["message"]
    kv, pv = result.get("kit_version") or "?", result.get("previous_version")
    L.append(f"[kit-sync] audit - motor instalado: {kv}" + (f" (anterior: {pv})" if pv else ""))
    L.append(f"[kit-sync] camada 2: {'presente' if result['layer2'] == 'present' else 'AUSENTE'}")
    if not result.get("template_found", True):
        L.append("[kit-sync] aviso: CLAUDE.md.template nao encontrado - secoes nao verificadas")
    gaps = result["gaps"]
    if not gaps:
        L.append("[kit-sync] nada pendente - a camada 2 esta completa para esta versao do motor")
        return "\n".join(L)
    L.append(f"[kit-sync] {len(gaps)} pendencia(s):")
    prev_t = _ver_tuple(pv) if pv else None
    for sev in ("blocking", "recommended", "optional"):
        rows = [g for g in gaps if g["severity"] == sev]
        if not rows:
            continue
        L.append(f"  [{sev}]")
        for g in rows:
            new = "  (novo desde a sua versao)" if prev_t and _ver_tuple(g["since"]) > prev_t else ""
            L.append(f"    - {g['id']}: {g['what']} -> {g['closes_with']}{new}")
            L.append(f"        {g['why']}")
    return "\n".join(L)


def cmd_audit(args):
    try:
        result = audit(args.target, args.kit)
    except Exception as e:  # noqa: BLE001 - erro interno vira exit 2, nunca um "tudo certo"
        print(f"[kit-sync] erro interno no audit: {e}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_audit_human(result))
    if result.get("engine") == "absent":
        return 2
    return 1 if result["gaps"] else 0


# ---------------------------------------------------------------------------
# report — UPGRADE.md a partir do audit
# ---------------------------------------------------------------------------

def write_report(target, result, preserved, first_time):
    version = result.get("kit_version") or "sem versao"
    prev_version = result.get("previous_version")
    manifest = _read_json(os.path.join(target, MANIFEST)) or {}
    backup = manifest.get("backup")
    gaps = result["gaps"]
    orphans = [g for g in gaps if g["id"] == "engine.orphan"]
    table_gaps = [g for g in gaps if g["id"] != "engine.orphan"]

    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append(f"# Upgrade do SDD Kit — {version}\n")
    L.append(f"Gerado por `kit-sync.py` em {when}. Este arquivo é reescrito a cada instalação "
             "e ao final de cada `/update-sdd`.\n")
    if prev_version and prev_version != version:
        L.append(f"**De:** {prev_version} → **para:** {version}\n")
    elif prev_version:
        L.append(f"**Reinstalação da mesma versão** ({version}).\n")
    else:
        L.append(f"**Primeira instalação registrada** ({version}).\n")
    if backup:
        L.append(f"**Backup do estado anterior:** `{backup}`\n")

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
        for g in orphans:
            L.append(f"- `{g['path']}`")
        L.append("")

    L.append("\n## O que a camada 2 ainda deve a esta versão\n")
    if table_gaps:
        L.append(
            "O motor novo espera estes artefatos. Reinstalar **não** os cria: camada 2 "
            "é gerada, não copiada. `blocking` trava comandos de entrega ou o fluxo; "
            "`recommended` é comportamento novo que o projeto ainda não herdou; `optional` "
            "é conveniência.\n"
        )
        L.append("| Gravidade | Falta | Desde | Gere com | Por quê |")
        L.append("|---|---|---|---|---|")
        for g in table_gaps:
            L.append(f"| {g['severity']} | {g['what']} | {g['since']} | `{g['closes_with']}` | {g['why']} |")
        L.append("")
    else:
        L.append("Nada pendente — a camada 2 está completa para esta versão do motor.\n")
    L.append(
        "\nA lista acima cobre só o que todo projeto tem. Os arquivos "
        "opcionais (`semantic-layer.md` entre eles, o que fixa a definição de "
        "cada métrica num projeto de dados) são oferecidos por "
        "`/sdd:steering-custom` — não entram aqui porque nem todo projeto os "
        "quer.\n"
    )

    L.append("\n## Próximo passo\n")
    if result.get("layer2") == "absent":
        L.append(
            "Abra o agente na raiz do projeto e rode a skill `setup-sdd`: é a primeira "
            "instalação, e a camada 2 (CLAUDE.md + steering) ainda vai ser gerada do seu código.\n"
        )
    elif table_gaps or orphans:
        L.append(
            "Abra o agente na raiz do projeto e rode **`/update-sdd`**: ele fecha só as linhas "
            "acima, aditivamente, sem refazer o setup — nunca sobrescreve CLAUDE.md, steering, "
            "specs ou valores de config existentes. `/update-sdd --dry-run` só mostra o plano. "
            "Para fechar uma pendência isolada, use o comando da tabela.\n"
        )
    else:
        L.append("Rode `/sdd:spec-lint --all` e siga o fluxo normalmente.\n")

    path = os.path.join(target, REPORT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))


def cmd_report(args):
    target = os.path.abspath(args.target)
    result = audit(target, args.kit)
    if result.get("engine") == "absent":
        print("[kit-sync] " + result["message"], file=sys.stderr)
        return 2
    manifest = _read_json(os.path.join(target, MANIFEST)) or {}
    write_report(target, result, manifest.get("preserved") or [],
                 first_time=not manifest.get("previous_version"))
    print(f"[kit-sync] {REPORT.replace(os.sep, '/')} reescrito - {len(result['gaps'])} pendencia(s)",
          file=sys.stderr)
    return 0


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

    au = sub.add_parser("audit", help="só leitura: o que a camada 2 deve ao motor (exit 0/1/2)")
    au.add_argument("--target", required=True)
    au.add_argument("--kit", help="raiz do kit; sem ele, usa as cópias instaladas no destino")
    au.add_argument("--format", choices=["human", "json"], default="human")
    au.set_defaults(func=cmd_audit)

    rp = sub.add_parser("report", help="reescreve .sdd/UPGRADE.md a partir de um audit novo")
    rp.add_argument("--target", required=True)
    rp.add_argument("--kit")
    rp.set_defaults(func=cmd_report)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
