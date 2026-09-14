#!/usr/bin/env python3
"""
spec-lint — validador de rastreabilidade de specs SDD.

Parte do SDD Kit — Fabio Provençale <fabio.provencale@gmail.com> — licença MIT.

Fecha a fragilidade nº 3 do fluxo: a matriz de rastreabilidade
(requisito -> tarefa) é verificada só por convenção. Este script a checa
de forma determinística, sem depender da disciplina do modelo.

Checagens:
  1. COBERTURA   — todo ID de requisito (N.M) é referenciado por >= 1 tarefa?
  2. VALIDADE    — todo `_Requirements: X.Y_` aponta para um ID que existe?
  3. ÓRFÃS       — existe tarefa sem nenhuma linha `_Requirements:_`?
  4. EVALS       — se evals.md existe: toda ref aponta para ID real (erro) e
                   quais requisitos não têm eval (aviso; erro com --require-evals).
                   Spec sem evals.md só falha se --require-evals for passado.

Uso:
  python tools/spec-lint.py <feature-name>     # valida .sdd/specs/<feature-name>/
  python tools/spec-lint.py --all              # valida todas as specs
  python tools/spec-lint.py --path <dir>       # valida um diretório de spec
  python tools/spec-lint.py <feat> --require-evals   # exige suite de evals
  python tools/spec-lint.py --all --format=vscode    # arquivo:linha:col por achado

Saída: relatório legível + exit code 0 (ok) / 1 (falhas encontradas).
Com --format=vscode a saída vira uma linha por achado, ancorada em
arquivo:linha:coluna, para o problemMatcher do editor abrir no ponto exato.
O veredito (exit code) é o mesmo nos dois formatos.
Sem dependências externas — Python 3.7+ stdlib apenas.
"""
import argparse
import os
import json
import re
import sys

# Fases canônicas de spec.json.phase — a mesma lista de rules/spec-artifacts.md.
CANONICAL_PHASES = (
    "initialized",
    "requirements-generated",
    "design-generated",
    "tasks-generated",
    "tasks-approved",
    "implementation-in-progress",
    "implementation-complete",
)

# Console Windows (cp1252) não encoda glyphs unicode — força UTF-8 quando dá.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQ_HEADING = re.compile(r"^#{1,6}\s*Requirement\s+(\d+)\b", re.IGNORECASE)
CRITERION = re.compile(r"^\s*(\d+)\.\s+\S")
TASK_REF = re.compile(r"_Requirements:\s*([^_]+)_", re.IGNORECASE)
TASK_LINE = re.compile(r"^\s*-\s*\[[ xX]\]\s*(\d+(?:\.\d+)?)\b")
ID_TOKEN = re.compile(r"\d+(?:\.\d+)?")
EVAL_HEADING = re.compile(r"^#{1,6}\s*E(\d+)\b")
GROUND_TRUTH_MISSING = re.compile(r"GROUND\s+TRUTH\s+NEEDED", re.IGNORECASE)

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
)
if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
    GREEN = RED = YELLOW = DIM = BOLD = RESET = ""


def parse_valid_ids(requirements_md):
    """Constrói o conjunto de IDs válidos (N.M) a partir de requirements.md.

    Para cada 'Requirement N', conta os critérios de aceite numerados que o
    seguem (até o próximo Requirement) e gera N.1..N.k. IDs órfãos escritos
    diretamente (ex.: '2.3') também são capturados.
    """
    valid = set()
    majors = set()
    current = None
    count = 0
    for raw in requirements_md.splitlines():
        m = REQ_HEADING.match(raw)
        if m:
            if current is not None:
                for i in range(1, count + 1):
                    valid.add(f"{current}.{i}")
            current = int(m.group(1))
            majors.add(current)
            count = 0
            continue
        if current is not None:
            c = CRITERION.match(raw)
            if c:
                count = max(count, int(c.group(1)))
    if current is not None:
        for i in range(1, count + 1):
            valid.add(f"{current}.{i}")
    return valid, majors


def parse_task_refs(tasks_md):
    """Retorna (refs_por_tarefa, todas_refs, tarefas_sem_ref).

    tarefas_sem_ref: só sub-tarefas (N.M) contam como órfãs; tarefas maiores
    (N.) costumam ser contêineres e são ignoradas.
    """
    lines = tasks_md.splitlines()
    all_refs = set()
    tasks = []            # (task_id, is_subtask, has_ref)
    i = 0
    while i < len(lines):
        tm = TASK_LINE.match(lines[i])
        if tm:
            task_id = tm.group(1)
            is_sub = "." in task_id
            has_ref = False
            # Coleta refs na própria linha e nos bullets de detalhe seguintes,
            # até a próxima linha de tarefa.
            j = i
            block = [lines[i]]
            j += 1
            while j < len(lines) and not TASK_LINE.match(lines[j]):
                block.append(lines[j])
                j += 1
            for tr in TASK_REF.finditer("\n".join(block)):
                ids = ID_TOKEN.findall(tr.group(1))
                if ids:
                    has_ref = True
                    all_refs.update(ids)
            tasks.append((task_id, is_sub, has_ref))
            i = j
        else:
            i += 1
    return tasks, all_refs


def parse_evals(evals_md):
    """Retorna (eval_ids, refs, pendentes_de_ground_truth).

    Um eval é um heading 'E<N>'; as refs seguem a mesma convenção de tasks.md
    (`_Requirements: X.Y_`), de propósito — uma convenção só para o repo inteiro.
    """
    eval_ids = []
    refs = set()
    pending = []
    lines = evals_md.splitlines()
    current = None
    for raw in lines:
        m = EVAL_HEADING.match(raw)
        if m:
            current = m.group(1)
            eval_ids.append(current)
            continue
        if current is None:
            continue
        for tr in TASK_REF.finditer(raw):
            refs.update(ID_TOKEN.findall(tr.group(1)))
        if GROUND_TRUTH_MISSING.search(raw) and current not in pending:
            pending.append(current)
    return eval_ids, refs, pending


def parse_locations(req_md, task_md, evals_md=None):
    """Mapeia cada ID para a linha (1-based) em que ele aparece.

    Só a saída --format=vscode usa isto — o relatório humano agrupa IDs numa
    linha só. Nada aqui participa do veredito: se um ID não for localizado, o
    achado é ancorado na linha 1 do arquivo e continua valendo.
    """
    id_lines, major_lines = {}, {}
    current = None
    for n, raw in enumerate(req_md.splitlines(), 1):
        m = REQ_HEADING.match(raw)
        if m:
            current = int(m.group(1))
            major_lines.setdefault(current, n)
            continue
        if current is not None:
            c = CRITERION.match(raw)
            if c:
                id_lines.setdefault("%d.%d" % (current, int(c.group(1))), n)

    ref_lines, task_lines = {}, {}
    for n, raw in enumerate(task_md.splitlines(), 1):
        tm = TASK_LINE.match(raw)
        if tm:
            task_lines.setdefault(tm.group(1), n)
        for tr in TASK_REF.finditer(raw):
            for i in ID_TOKEN.findall(tr.group(1)):
                ref_lines.setdefault(i, n)

    eval_ref_lines, eval_lines = {}, {}
    if evals_md is not None:
        cur = None
        for n, raw in enumerate(evals_md.splitlines(), 1):
            m = EVAL_HEADING.match(raw)
            if m:
                cur = m.group(1)
                eval_lines.setdefault(cur, n)
                continue
            if cur is None:
                continue
            for tr in TASK_REF.finditer(raw):
                for i in ID_TOKEN.findall(tr.group(1)):
                    eval_ref_lines.setdefault(i, n)

    return {
        "id": id_lines,
        "major": major_lines,
        "ref": ref_lines,
        "task": task_lines,
        "eval_ref": eval_ref_lines,
        "eval": eval_lines,
    }


def lint_spec(spec_dir, require_evals=False, diags=None, report=True):
    name = os.path.basename(spec_dir.rstrip("/\\"))
    req_path = os.path.join(spec_dir, "requirements.md")
    task_path = os.path.join(spec_dir, "tasks.md")
    evals_path = os.path.join(spec_dir, "evals.md")

    errors, warnings = [], []

    def _d(sev, path, line, msg):
        """Registra um achado ancorado (só alimenta --format=vscode)."""
        if diags is not None:
            diags.append({"sev": sev, "path": path, "line": max(1, line or 1), "msg": msg})

    if not os.path.isfile(req_path):
        errors.append(f"requirements.md não encontrado em {spec_dir}")
        _d("error", req_path, 1, "requirements.md não encontrado (gere com /sdd:spec-requirements)")
        if report:
            _report(name, errors, warnings, None)
        return False
    if not os.path.isfile(task_path):
        errors.append(f"tasks.md não encontrado em {spec_dir} (gere com /sdd:spec-tasks)")
        _d("error", task_path, 1, "tasks.md não encontrado (gere com /sdd:spec-tasks)")
        if report:
            _report(name, errors, warnings, None)
        return False

    with open(req_path, encoding="utf-8") as f:
        req_md = f.read()
    with open(task_path, encoding="utf-8") as f:
        task_md = f.read()

    evals_md = None
    if os.path.isfile(evals_path):
        with open(evals_path, encoding="utf-8") as f:
            evals_md = f.read()

    valid_ids, majors = parse_valid_ids(req_md)
    tasks, all_refs = parse_task_refs(task_md)
    locs = parse_locations(req_md, task_md, evals_md) if diags is not None else None

    def _req_line(rid):
        """Linha do critério N.M; cai no heading do requisito, senão na 1."""
        if not locs:
            return 1
        major = rid.split(".")[0]
        return (locs["id"].get(rid)
                or (locs["major"].get(int(major)) if major.isdigit() else None)
                or 1)

    if not valid_ids:
        warnings.append(
            "nenhum ID de requisito detectado — headings devem seguir "
            "'Requirement N' com critérios de aceite numerados"
        )
        _d("warning", req_path, 1,
           "nenhum ID de requisito detectado — use headings 'Requirement N' "
           "com critérios de aceite numerados")

    # 1. COBERTURA — todo ID válido é referenciado?
    uncovered = sorted(valid_ids - all_refs, key=_idkey)
    if uncovered:
        errors.append("IDs de requisito SEM tarefa (cobertura): " + ", ".join(uncovered))
        for rid in uncovered:
            _d("error", req_path, _req_line(rid),
               f"Req {rid} não é referenciado por nenhuma tarefa (cobertura)")
    covered_majors = {r.split(".")[0] for r in all_refs}
    uncovered_majors = sorted(str(m) for m in majors if str(m) not in covered_majors)
    if uncovered_majors:
        errors.append("Requisitos inteiros sem NENHUMA tarefa: " + ", ".join(uncovered_majors))
        for m in uncovered_majors:
            _d("error", req_path, (locs["major"].get(int(m), 1) if locs else 1),
               f"Requisito {m} não tem nenhuma tarefa em tasks.md")

    # 2. VALIDADE — toda ref aponta para um ID existente?
    dangling = sorted(all_refs - valid_ids, key=_idkey)
    if dangling:
        # Aceita referência a um major válido (N) mesmo sem N.M explícito.
        real_dangling = [d for d in dangling if d.split(".")[0] not in {str(m) for m in majors}]
        if real_dangling:
            errors.append("Referências a IDs INEXISTENTES em tasks.md: " + ", ".join(real_dangling))
            for d in real_dangling:
                _d("error", task_path, (locs["ref"].get(d, 1) if locs else 1),
                   f"referência solta: Req {d} não existe em requirements.md")
        soft = [d for d in dangling if d not in real_dangling]
        if soft:
            warnings.append("Refs a nível de requisito (sem N.M específico): " + ", ".join(soft))
            for d in soft:
                _d("warning", task_path, (locs["ref"].get(d, 1) if locs else 1),
                   f"referência a nível de requisito ({d}) — prefira o ID N.M")

    # 3. ÓRFÃS — sub-tarefa sem _Requirements:_
    # Fase canônica (rules/spec-artifacts.md): onze grafias de "implementado" num
    # projeto real deixaram o spec-status cego. Aviso, não erro — fase não afeta
    # rastreabilidade; afeta quem tenta agregar.
    spec_json = os.path.join(spec_dir, "spec.json")
    if os.path.isfile(spec_json):
        try:
            with open(spec_json, encoding="utf-8-sig") as f:
                phase = json.load(f).get("phase")
        except (OSError, ValueError):
            phase = None
        if phase is not None and phase not in CANONICAL_PHASES:
            warnings.append(
                f"spec.json.phase '{phase}' não é canônica — use uma de: "
                + ", ".join(CANONICAL_PHASES) + " (nuance vai em status_note)"
            )
            _d("warning", spec_json, 1,
               f"phase '{phase}' não é canônica (ver rules/spec-artifacts.md)")

    orphans = [t for (t, is_sub, has_ref) in tasks if is_sub and not has_ref]
    if orphans:
        warnings.append("Sub-tarefas sem linha _Requirements:_: " + ", ".join(orphans))
        for t in orphans:
            _d("warning", task_path, (locs["task"].get(t, 1) if locs else 1),
               f"tarefa {t} sem linha _Requirements:_ — a rastreabilidade quebra aqui")

    # 4. EVALS — opcional por padrão; obrigatório com --require-evals.
    eval_count = None
    if evals_md is not None:
        eval_ids, eval_refs, pending_gt = parse_evals(evals_md)
        eval_count = len(eval_ids)

        eval_dangling = sorted(
            (r for r in eval_refs - valid_ids
             if r.split(".")[0] not in {str(m) for m in majors}),
            key=_idkey,
        )
        if eval_dangling:
            errors.append("Refs a IDs INEXISTENTES em evals.md: " + ", ".join(eval_dangling))
            for d in eval_dangling:
                _d("error", evals_path, (locs["eval_ref"].get(d, 1) if locs else 1),
                   f"eval referencia Req {d}, que não existe em requirements.md")

        no_eval = sorted(valid_ids - eval_refs, key=_idkey)
        if no_eval:
            msg = "IDs de requisito sem eval: " + ", ".join(no_eval)
            (errors if require_evals else warnings).append(msg)
            for rid in no_eval:
                _d("error" if require_evals else "warning", req_path, _req_line(rid),
                   f"Req {rid} não tem eval em evals.md (gere com /sdd:spec-evals)")

        if pending_gt:
            warnings.append(
                "Evals sem ground truth (E" + ", E".join(pending_gt) +
                ") — contam como SKIPPED, nunca PASS"
            )
            for e in pending_gt:
                _d("warning", evals_path, (locs["eval"].get(e, 1) if locs else 1),
                   f"eval E{e} sem ground truth humano — conta como SKIPPED, nunca PASS")
        if not eval_ids:
            warnings.append("evals.md existe mas nenhum eval 'E<N>' foi detectado")
            _d("warning", evals_path, 1, "nenhum eval 'E<N>' detectado neste arquivo")
    elif require_evals:
        errors.append("evals.md não encontrado (--require-evals) — gere com /sdd:spec-evals")
        _d("error", evals_path, 1, "evals.md não encontrado (gere com /sdd:spec-evals)")

    stats = {
        "ids": len(valid_ids),
        "reqs": len(majors),
        "tasks": len(tasks),
        "refs": len(all_refs),
        "evals": eval_count,
    }
    if report:
        _report(name, errors, warnings, stats)
    return not errors


def _idkey(s):
    parts = s.split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


def _report(name, errors, warnings, stats):
    print(f"\n{BOLD}spec:{RESET} {name}")
    if stats:
        line = (
            f"{stats['reqs']} requisitos · {stats['ids']} IDs · "
            f"{stats['tasks']} tarefas · {stats['refs']} refs"
        )
        if stats.get("evals") is not None:
            line += f" · {stats['evals']} evals"
        print(f"  {DIM}{line}{RESET}")
    for e in errors:
        print(f"  {RED}[ERRO] {e}{RESET}")
    for w in warnings:
        print(f"  {YELLOW}[aviso] {w}{RESET}")
    if not errors and not warnings:
        print(f"  {GREEN}[OK] rastreabilidade integra{RESET}")
    elif not errors:
        print(f"  {GREEN}[OK] sem erros{RESET} {DIM}(so avisos){RESET}")


def find_specs(root):
    base = os.path.join(root, ".sdd", "specs")
    if not os.path.isdir(base):
        return []
    return [
        os.path.join(base, d)
        for d in sorted(os.listdir(base))
        if os.path.isdir(os.path.join(base, d))
    ]


def _emit_vscode(diags, root):
    """Uma linha por achado: caminho:linha:coluna: severidade: mensagem.

    Caminho relativo à raiz do repo e com barras normais — é o que o
    problemMatcher do editor espera para conseguir abrir o arquivo.
    """
    base = os.path.abspath(root or ".")
    errs = sum(1 for d in diags if d["sev"] == "error")
    for d in diags:
        try:
            rel = os.path.relpath(os.path.abspath(d["path"]), base)
        except ValueError:           # drives diferentes no Windows
            rel = d["path"]
        rel = rel.replace(os.sep, "/")
        print(f"{rel}:{d['line']}:1: {d['sev']}: {d['msg']}")
    # Linha de resumo: de proposito não casa com o problemMatcher.
    print(f"[spec-lint] {errs} erro(s), {len(diags) - errs} aviso(s)")


def main():
    ap = argparse.ArgumentParser(description="Validador de rastreabilidade de specs SDD")
    ap.add_argument("feature", nargs="?", help="nome da feature em .sdd/specs/<feature>/")
    ap.add_argument("--all", action="store_true", help="valida todas as specs")
    ap.add_argument("--path", help="caminho direto para um diretório de spec")
    ap.add_argument("--root", default=".", help="raiz do repo (default: .)")
    ap.add_argument(
        "--require-evals",
        action="store_true",
        help="exige evals.md e trata requisito sem eval como erro",
    )
    ap.add_argument(
        "--format",
        choices=("human", "vscode"),
        default="human",
        help="human (default) ou vscode (arquivo:linha:col por achado)",
    )
    args = ap.parse_args()

    machine = args.format == "vscode"
    if machine:
        # Saída consumida por problemMatcher: nada de ANSI, nada de banner.
        global GREEN, RED, YELLOW, DIM, BOLD, RESET
        GREEN = RED = YELLOW = DIM = BOLD = RESET = ""

    if args.path:
        dirs = [args.path]
    elif args.all:
        dirs = find_specs(args.root)
        if not dirs:
            print("Nenhuma spec encontrada em .sdd/specs/")
            return 0
    elif args.feature:
        dirs = [os.path.join(args.root, ".sdd", "specs", args.feature)]
    else:
        ap.print_help()
        return 2

    ok = True
    diags = [] if machine else None
    for d in dirs:
        ok = lint_spec(
            d,
            require_evals=args.require_evals,
            diags=diags,
            report=not machine,
        ) and ok

    if machine:
        _emit_vscode(diags, args.root)
        return 0 if ok else 1

    print()
    if ok:
        print(f"{GREEN}{BOLD}PASS{RESET} — rastreabilidade validada.")
        return 0
    print(f"{RED}{BOLD}FAIL{RESET} — corrija os erros acima (ajuste requirements.md, tasks.md ou evals.md).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
