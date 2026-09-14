#!/usr/bin/env python3
"""
approval-gate — trava DETERMINISTICA do ciclo executor<->aprovador.

Parte do SDD Kit — Fabio Provençale <fabio.provencale@gmail.com> — licença MIT.

Por que existe: um agente LLM nao garante, sozinho, que vai parar em N iteracoes
(pode se enganar na contagem). Esta trava vive FORA do modelo: le um ledger
persistido e decide via exit code. O orquestrador DEVE chamar `check` antes de
cada rodada e OBEDECER o exit code; e `record` depois de cada veredito do aprovador.

Politica (nesta ordem, a primeira que bater vence):
  1. auto-approve desligado (master)      -> HUMAN   (fallback = comportamento manual atual)
  2. risco == high                        -> HUMAN   (sempre, sem excecao)
  3. nivel de risco nao auto-aprovado     -> HUMAN
  4. iteracoes >= max_iterations          -> ESCALATE (nao convergiu)
  5. tokens/custo acima do teto           -> ESCALATE (orcamento)
  6. caso contrario                       -> CONTINUE (loop pode prosseguir)

Exit codes (o orquestrador nao pode "decidir" ignorar):
  0 = CONTINUE      2 = ESCALATE (limite)      3 = HUMAN (politica)      4 = erro de uso

Uso:
  py tools/approval-gate.py check   --feature F --task T --risk {low|medium|high}
  py tools/approval-gate.py record  --feature F --task T --risk R --role {executor|approver} \
                                    --decision {APPROVE|REJECT|ESCALATE|APPLIED} [--tokens N] [--usd X] [--note "..."]
  py tools/approval-gate.py summary --feature F [--task T]

Config: .sdd/autoapprove.json  (fallback: .sdd/settings/templates/autoapprove.json).
Ledger: .sdd/specs/<feature>/approval-log.jsonl (uma linha JSON por evento).
Sem dependencias externas. Python 3.7+. Saida ASCII (consoles Windows cp1252).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_CONFIG = {
    "auto_approve": {"enabled": False, "low": True, "medium": True, "high": False},
    "limits": {"max_iterations": 3, "max_tokens_per_task": 100000, "max_usd_per_task": 1.0},
}


def load_config(root):
    for rel in (".sdd/autoapprove.json", ".sdd/settings/templates/autoapprove.json"):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    cfg = json.load(f)
                return _merge(DEFAULT_CONFIG, cfg), p
            except (json.JSONDecodeError, OSError) as e:
                print(f"[gate] config invalida em {rel}: {e} -> usando defaults seguros")
                return DEFAULT_CONFIG, "(defaults)"
    return DEFAULT_CONFIG, "(defaults)"


def _merge(base, over):
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in base.items()}
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def ledger_path(root, feature):
    return os.path.join(root, ".sdd", "specs", feature, "approval-log.jsonl")


def read_ledger(root, feature, task=None):
    p = ledger_path(root, feature)
    rows = []
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if task is None or str(r.get("task")) == str(task):
                    rows.append(r)
    return rows


def cmd_check(args):
    cfg, cfg_src = load_config(args.root)
    aa = cfg["auto_approve"]
    lim = cfg["limits"]
    risk = args.risk.lower()

    def out(state, reason, code):
        print(f"[gate] task={args.task} risk={risk} -> {state}: {reason}  (config: {cfg_src})")
        sys.exit(code)

    if not aa.get("enabled", False):
        out("HUMAN", "auto-approve desligado (master) -> aprovacao manual", 3)
    if risk == "high":
        out("HUMAN", "risco ALTO exige aprovacao humana, sem excecao", 3)
    if risk not in ("low", "medium"):
        out("HUMAN", f"risco '{risk}' desconhecido -> trata como manual", 3)
    if not aa.get(risk, False):
        out("HUMAN", f"nivel '{risk}' nao esta auto-aprovado na config", 3)

    rows = read_ledger(args.root, args.feature, args.task)
    iterations = sum(1 for r in rows if r.get("role") == "approver")
    tokens = sum(int(r.get("tokens", 0) or 0) for r in rows)
    usd = sum(float(r.get("usd", 0) or 0) for r in rows)

    max_it = int(lim.get("max_iterations", 3))
    if iterations >= max_it:
        out("ESCALATE", f"nao convergiu em {iterations}/{max_it} iteracoes -> humano", 2)
    if tokens > int(lim.get("max_tokens_per_task", 0) or 0) > 0:
        out("ESCALATE", f"teto de tokens excedido ({tokens} > {lim['max_tokens_per_task']})", 2)
    if usd > float(lim.get("max_usd_per_task", 0) or 0) > 0:
        out("ESCALATE", f"teto de custo excedido (${usd:.2f} > ${lim['max_usd_per_task']})", 2)

    print(f"[gate] task={args.task} risk={risk} -> CONTINUE: "
          f"iteracao {iterations + 1}/{max_it}, tokens={tokens}, custo=${usd:.2f}  (config: {cfg_src})")
    sys.exit(0)


def cmd_record(args):
    p = ledger_path(args.root, args.feature)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": args.task,
        "risk": (args.risk or "").lower(),
        "role": args.role,
        "decision": args.decision.upper(),
        "tokens": int(args.tokens or 0),
        "usd": float(args.usd or 0),
        "note": args.note or "",
    }
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    print(f"[gate] registrado: task={args.task} role={args.role} decision={entry['decision']}")
    sys.exit(0)


def cmd_summary(args):
    rows = read_ledger(args.root, args.feature, args.task)
    if not rows:
        print(f"[gate] sem eventos para feature={args.feature}"
              + (f" task={args.task}" if args.task else ""))
        sys.exit(0)
    by_task = {}
    for r in rows:
        t = str(r.get("task"))
        d = by_task.setdefault(t, {"iters": 0, "tokens": 0, "usd": 0.0, "decisions": [], "risk": r.get("risk")})
        if r.get("role") == "approver":
            d["iters"] += 1
            d["decisions"].append(r.get("decision"))
        d["tokens"] += int(r.get("tokens", 0) or 0)
        d["usd"] += float(r.get("usd", 0) or 0)
    print(f"\napproval summary - feature: {args.feature}")
    print(f"{'task':<10}{'risk':<8}{'iters':<7}{'tokens':<9}{'usd':<8}decisions")
    for t, d in sorted(by_task.items()):
        print(f"{t:<10}{str(d['risk']):<8}{d['iters']:<7}{d['tokens']:<9}"
              f"{('$%.2f' % d['usd']):<8}{' -> '.join(d['decisions'])}")
    esc = sum(1 for r in rows if r.get("decision") == "ESCALATE")
    print(f"\ntotal escalonamentos para humano: {esc}")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description="Trava deterministica do ciclo executor<->aprovador")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("--feature", required=True)
    c.add_argument("--task", required=True)
    c.add_argument("--risk", required=True)
    c.add_argument("--root", default=".")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("record")
    r.add_argument("--feature", required=True)
    r.add_argument("--task", required=True)
    r.add_argument("--risk", default="")
    r.add_argument("--role", required=True, choices=["executor", "approver"])
    r.add_argument("--decision", required=True)
    r.add_argument("--tokens", type=int, default=0)
    r.add_argument("--usd", type=float, default=0.0)
    r.add_argument("--note", default="")
    r.add_argument("--root", default=".")
    r.set_defaults(func=cmd_record)

    s = sub.add_parser("summary")
    s.add_argument("--feature", required=True)
    s.add_argument("--task", default=None)
    s.add_argument("--root", default=".")
    s.set_defaults(func=cmd_summary)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # nunca deixa o gate falhar aberto
        print(f"[gate] erro interno: {e} -> tratando como HUMAN (seguro)")
        sys.exit(3)
