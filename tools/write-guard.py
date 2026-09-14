#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write-guard — hook PreToolUse que barra escrita SQL fora do escopo permitido.

Parte do SDD Kit — Fabio Provençale <fabio.provencale@gmail.com> — licença MIT.

Por que existe: a regra "este projeto só escreve em <catalogo>.<schema>" vive no
CLAUDE.md como convenção. Convenção não trava. Este script vive FORA do modelo:
lê o comando que o agente está prestes a executar, procura verbo de escrita SQL
e confere o alvo contra `.sdd/write-scope.json`. Decide por saída JSON do hook:

  deny  — alvo qualificado e fora do escopo (o comando NÃO roda)
  ask   — alvo ambíguo (não qualificado, ou catálogo implícito): o humano confirma
  nada  — leitura, ou escrita dentro do escopo: o fluxo segue em silêncio

Desligado por padrão (`enabled: false` no template) — instalar o kit não muda o
comportamento de nenhum projeto. O `setup-sdd` oferece ligar quando há plataforma
de dados. Sem config, ou com erro interno, o hook sai em silêncio (fail-open):
uma trava quebrada não pode travar o trabalho — mas também não pode fingir que
protege, por isso existe o `--self-test`.

A lição que motivou o `--self-test`: numa instalação real o schema permitido
estava grafado errado por um mês. O efeito era o INVERSO do pretendido — negava
escrita no alvo certo e liberaria escrita num schema inexistente. Rode o
self-test depois de editar a config, e confirme na plataforma que cada alvo
existe (`databricks schemas list <catalogo>`, `bq ls`, `\\dn` no psql…).

Uso:
  como hook (stdin = JSON do PreToolUse; ver snippet no README/setup-sdd):
    python tools/write-guard.py
  dry-run de um comando, sem hook:
    python tools/write-guard.py --check "INSERT INTO prod.core.t SELECT 1"
  auto-teste da config e dos padrões:
    python tools/write-guard.py --self-test

Só stdlib, Python 3.7+.
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CONFIG_REL = os.path.join(".sdd", "write-scope.json")

# Identificador de até 3 partes, com ou sem crase/aspas.
QUAL = r'(?P<alvo>(?:[`"\w$]+\.){0,2}[`"\w$]+)'

PADROES = [
    ("CREATE", r'\bCREATE\s+(?:OR\s+REPLACE\s+)?(?P<temp>GLOBAL\s+TEMPORARY\s+|TEMPORARY\s+|TEMP\s+)?'
               r'(?:EXTERNAL\s+|STREAMING\s+|LIVE\s+)*'
               r'(?:TABLE|MATERIALIZED\s+VIEW|VIEW|SCHEMA|DATABASE|VOLUME|FUNCTION)\s+'
               r'(?:IF\s+NOT\s+EXISTS\s+)?' + QUAL),
    ("INSERT", r'\bINSERT\s+(?:INTO|OVERWRITE)\s+(?:TABLE\s+)?' + QUAL),
    ("MERGE", r'\bMERGE\s+INTO\s+' + QUAL),
    ("UPDATE", r'\bUPDATE\s+' + QUAL + r'\s+SET\b'),
    ("DELETE", r'\bDELETE\s+FROM\s+' + QUAL),
    ("DROP", r'\bDROP\s+(?:TABLE|MATERIALIZED\s+VIEW|VIEW|SCHEMA|DATABASE|VOLUME|FUNCTION)\s+'
             r'(?:IF\s+EXISTS\s+)?' + QUAL),
    ("TRUNCATE", r'\bTRUNCATE\s+(?:TABLE\s+)?' + QUAL),
    ("ALTER", r'\bALTER\s+(?:TABLE|VIEW|SCHEMA|DATABASE|VOLUME)\s+' + QUAL),
    ("COPY INTO", r'\bCOPY\s+INTO\s+' + QUAL),
    ("saveAsTable", r'saveAsTable\s*\(\s*[\'"](?P<alvo>[^\'"]+)[\'"]'),
    ("GRANT/REVOKE", r'\b(?:GRANT|REVOKE)\b.{0,200}?\bON\s+(?:TABLE|SCHEMA|CATALOG|VOLUME|VIEW)\s+' + QUAL),
]

# Verbos em que alvo de uma parte só ainda merece confirmação humana.
PERIGOSOS = {"INSERT", "MERGE", "DELETE", "DROP", "TRUNCATE", "COPY INTO", "saveAsTable"}

# Palavras que o regex pode pegar como "alvo" em prosa/comentário.
RUIDO = {"the", "a", "an", "all", "set", "from", "table", "this", "my", "your", "into", "if"}


def load_config(project_dir):
    path = os.path.join(project_dir, CONFIG_REL)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def partes(ident):
    return [p.strip('`"[]') for p in ident.split(".") if p.strip('`"[]')]


def _norm_targets(cfg):
    """Alvos permitidos como tuplas (catalogo|None, schema). `catalogo.*` libera o
    catálogo inteiro; `schema` sem catálogo casa com qualquer catálogo."""
    out = []
    for t in cfg.get("allowed_targets") or []:
        p = [x.lower() for x in partes(str(t))]
        if len(p) == 2:
            out.append((p[0], p[1]))
        elif len(p) == 1:
            out.append((None, p[0]))
    return out


def _allowed(cat, schema, targets, default_catalog):
    cat = (cat or default_catalog or "").lower() or None
    schema = schema.lower()
    for tc, ts in targets:
        if ts == "*" and tc == cat:
            return True
        if ts == schema and (tc is None or tc == cat):
            return True
    return False


def analisa(cmd, cfg):
    """Devolve (violacoes, ambiguos) para um comando, dada a config."""
    targets = _norm_targets(cfg)
    default_catalog = cfg.get("default_catalog") or None
    violacoes, ambiguos = [], []
    for verbo, padrao in PADROES:
        for m in re.finditer(padrao, cmd, re.I | re.S):
            g = m.groupdict()
            if g.get("temp"):
                continue  # view temporária de sessão, não persiste
            p = partes(g["alvo"])
            if not p or p[-1].lower() in RUIDO:
                continue
            alvo = ".".join(p)
            if len(p) >= 3:
                if not _allowed(p[0], p[1], targets, None):
                    violacoes.append("%s -> %s" % (verbo, alvo))
            elif len(p) == 2:
                # `schema.tabela` — o catálogo vem da sessão, não do comando.
                schema = p[0].lower()
                if any(tc is None and ts == schema for tc, ts in targets):
                    continue                          # schema liberado em qualquer catálogo
                if default_catalog:
                    if not _allowed(default_catalog, schema, targets, None):
                        violacoes.append("%s -> %s (schema fora do escopo)" % (verbo, alvo))
                elif any(ts == schema for _tc, ts in targets):
                    ambiguos.append("%s -> %s (catalogo implicito)" % (verbo, alvo))
                else:
                    violacoes.append("%s -> %s (schema fora do escopo)" % (verbo, alvo))
            elif verbo in PERIGOSOS:
                ambiguos.append("%s -> %s (alvo nao qualificado)" % (verbo, alvo))
    return violacoes, ambiguos


def decide(decisao, motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decisao,
        "permissionDecisionReason": motivo,
    }}))


def _scope_str(cfg):
    return ", ".join(str(t) for t in (cfg.get("allowed_targets") or [])) or "(vazio)"


def run_hook(project_dir):
    cfg = load_config(project_dir)
    if not cfg or not cfg.get("enabled"):
        return  # desligado: silencio absoluto
    dados = json.load(sys.stdin)
    if dados.get("tool_name") not in ("Bash", "PowerShell"):
        return
    cmd = dados.get("tool_input", {}).get("command") or ""
    if not isinstance(cmd, str):
        return
    violacoes, ambiguos = analisa(cmd, cfg)
    if violacoes:
        decide("deny", "Escrita fora do escopo permitido (%s): %s. Corrija o alvo ou peca "
                       "autorizacao explicita ao usuario. Config: .sdd/write-scope.json"
               % (_scope_str(cfg), "; ".join(sorted(set(violacoes)))))
    elif ambiguos and (cfg.get("on_ambiguous", "ask") == "ask"):
        decide("ask", "Alvo de escrita ambiguo: %s. Confirme que cai em %s."
               % ("; ".join(sorted(set(ambiguos))), _scope_str(cfg)))


# ---------------------------------------------------------------------------
# --check e --self-test (nunca fail-open: aqui erro tem que aparecer)
# ---------------------------------------------------------------------------

def run_check(project_dir, cmd):
    cfg = load_config(project_dir)
    if not cfg:
        print("[write-guard] sem config em %s" % CONFIG_REL)
        return 2
    v, a = analisa(cmd, cfg)
    estado = "ligado" if cfg.get("enabled") else "DESLIGADO (o hook nao agiria)"
    print("[write-guard] escopo: %s — %s" % (_scope_str(cfg), estado))
    if v:
        print("  deny : " + "; ".join(sorted(set(v))))
        return 1
    if a:
        print("  ask  : " + "; ".join(sorted(set(a))))
        return 0
    print("  ok   : nenhuma escrita fora do escopo")
    return 0


def run_self_test(project_dir):
    cfg = load_config(project_dir)
    if not cfg:
        print("[write-guard] sem config em %s — copie de .sdd/settings/templates/write-scope.json"
              % CONFIG_REL)
        return 2
    targets = _norm_targets(cfg)
    if not targets:
        print("[write-guard] FALHA: allowed_targets vazio — com enabled:true isso nega TODA escrita")
        return 1

    # 1) padrões: casos fixos, independentes da config
    fixed = {"enabled": True, "allowed_targets": ["dev.sandbox"], "default_catalog": None}
    casos = [
        ("SELECT * FROM prod.core.t LIMIT 10", "ok"),
        ("CREATE TABLE dev.sandbox.t AS SELECT 1", "ok"),
        ("CREATE TEMP VIEW v AS SELECT 1", "ok"),
        ("INSERT INTO prod.core.t SELECT 1", "deny"),
        ("MERGE INTO dev.other.t USING s ON 1=1", "deny"),
        ("DROP TABLE IF EXISTS prod.core.t", "deny"),
        ("df.write.saveAsTable('prod.core.t')", "deny"),
        ("INSERT INTO t SELECT 1", "ask"),
        ("INSERT INTO sandbox.t SELECT 1", "ask"),
        ("GRANT SELECT ON TABLE prod.core.t TO `x`", "deny"),
        ("TRUNCATE TABLE dev.sandbox.t", "ok"),
    ]
    falhas = 0
    for cmd, esperado in casos:
        v, a = analisa(cmd, fixed)
        obtido = "deny" if v else ("ask" if a else "ok")
        flag = "ok " if obtido == esperado else "ERR"
        if obtido != esperado:
            falhas += 1
        print("  [%s] %-5s %-5s  %s" % (flag, esperado, obtido, cmd))
    print("[write-guard] padroes: %d caso(s) com erro" % falhas)

    # 2) a config real: o que ela permite e o que o humano precisa confirmar fora daqui
    print("[write-guard] config em uso: escopo=%s enabled=%s default_catalog=%s on_ambiguous=%s"
          % (_scope_str(cfg), cfg.get("enabled"), cfg.get("default_catalog"),
             cfg.get("on_ambiguous", "ask")))
    for tc, ts in targets:
        alvo = ("%s.%s" % (tc, ts)) if tc else ts
        v, _ = analisa("CREATE TABLE %s.__probe__ AS SELECT 1" % alvo, cfg)
        print("  %s CREATE em %s" % ("libera" if not v else "NEGA  ", alvo))
    print("[write-guard] CONFIRME NA PLATAFORMA que cada alvo acima existe com essa grafia exata\n"
          "              (ex.: `databricks schemas list <catalogo>`, `bq ls`, `\\dn` no psql).\n"
          "              Um schema grafado errado inverte a trava: nega o certo, libera o inexistente.")
    return 1 if falhas else 0


def main(argv):
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if "--self-test" in argv:
        return run_self_test(project_dir)
    if "--check" in argv:
        i = argv.index("--check")
        cmd = argv[i + 1] if i + 1 < len(argv) else ""
        return run_check(project_dir, cmd)
    try:
        run_hook(project_dir)
    except Exception:
        pass  # falha do hook nunca trava o fluxo
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
