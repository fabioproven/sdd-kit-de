#!/usr/bin/env python3
"""
Testes do `kit-sync.py audit` com destinos-fixture em diretorio temporario.

Rode de dentro do kit:  py tools/tests/test_kit_sync.py   (ou python3)
Nao e copiado pelos instaladores (so tools/*.py vai para o destino).
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", ".."))
SYNC = os.path.join(KIT, "tools", "kit-sync.py")

_spec = importlib.util.spec_from_file_location("kit_sync", SYNC)
ks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ks)


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _engine(target, version="sdd-kit 0.9.0", previous=None):
    """Camada 1 minima: marcador de versao, rules, agentes do kit, manifesto."""
    _w(os.path.join(target, ".sdd", "SDD_KIT_VERSION"), version + "\n")
    _w(os.path.join(target, ".sdd", "settings", "rules", "ears-format.md"), "# rule\n")
    for a in ("code-explorer", "approver", "data-analyst", "report-validator", "data-engineer"):
        _w(os.path.join(target, ".claude", "agents", a + ".md"),
           f"---\nname: {a}\ndescription: x\ntools: Read\n---\nbody\n")
    # agente do PROJETO com o mesmo layout: nao pode virar pendencia
    _w(os.path.join(target, ".claude", "agents", "caveman.md"),
       "---\nname: caveman\ndescription: third party\n---\n")
    _w(os.path.join(target, ".sdd", ".kit-manifest.json"),
       json.dumps({"version": version, "previous_version": previous, "files": {}, "backup": None}))
    _w(os.path.join(target, ".vscode", "tasks.json"), "{}\n")
    shutil.copy(os.path.join(KIT, ".sdd", "settings", "templates", "write-scope.json"),
                os.path.join(target, ".sdd", "write-scope.json"))


def _full_claude_md():
    """CLAUDE.md completo: o proprio template com placeholders trocados."""
    with open(os.path.join(KIT, "CLAUDE.md.template"), encoding="utf-8") as f:
        t = f.read()
    return re.sub(r"\{\{[A-Z_0-9]+\}\}", "x", t)


def fixture_engine_only(target):
    _engine(target)
    _w(os.path.join(target, "CLAUDE.md"), "# {{PROJECT_NAME}}\n\n{{ONE_LINE}}\n")
    shutil.copy(os.path.join(KIT, ".sdd", "settings", "templates", "autoapprove.json"),
                os.path.join(target, ".sdd", "autoapprove.json"))


def fixture_old_layer2(target):
    _engine(target, previous="sdd-kit 0.4.0")
    for n in ("product.md", "tech.md", "structure.md"):
        _w(os.path.join(target, ".sdd", "steering", n), "# " + n + "\n")
    _w(os.path.join(target, "CLAUDE.md"),
       "# Proj\n\nOne line.\n\n## How work flows here\n\nThere is a human approval gate at each phase.\n"
       "Use `/sdd:spec-impl-auto` for the loop.\n\n## Language\n\nEnglish.\n\n## Routing\n\n"
       "- code-explorer for search.\n\n## Implementation profile\n\nspec-impl.\n\n"
       "## Hard rules\n\n- none\n\n## Quality gate\n\nlint.\n\n## Quick reference\n\n| a | b |\n")
    _w(os.path.join(target, ".sdd", "autoapprove.json"), json.dumps({
        "auto_approve": {"enabled": True, "low": True, "medium": False, "high": False},
        "limits": {"max_iterations": 3}}))
    _w(os.path.join(target, ".sdd", "specs", "old-feature", "requirements.md"), "# R\n")
    _w(os.path.join(target, ".sdd", "specs", "old-feature", "spec.json"),
       json.dumps({"feature_name": "old-feature", "phase": "implementado"}))
    _w(os.path.join(target, ".claude", "commands", "review.md.sdd-new"), "kit version\n")


def fixture_complete(target):
    _engine(target, previous="sdd-kit 0.8.0")
    for n in ("product.md", "tech.md", "structure.md", "integrations.md", "inherited-knowledge.md"):
        _w(os.path.join(target, ".sdd", "steering", n), "# " + n + "\n")
    _w(os.path.join(target, "CLAUDE.md"), _full_claude_md())
    shutil.copy(os.path.join(KIT, ".sdd", "settings", "templates", "autoapprove.json"),
                os.path.join(target, ".sdd", "autoapprove.json"))
    _w(os.path.join(target, ".sdd", "specs", "feat", "requirements.md"), "# R\n")
    _w(os.path.join(target, ".sdd", "specs", "feat", "evals.md"), "# E\n")
    _w(os.path.join(target, ".sdd", "specs", "feat", "spec.json"),
       json.dumps({"feature_name": "feat", "phase": "implementation-complete"}))


def _snapshot(target):
    out = {}
    for root, _d, files in os.walk(target):
        for fn in files:
            p = os.path.join(root, fn)
            out[p] = (os.path.getmtime(p), ks.sha256(p))
    return out


def _run(*argv):
    return subprocess.run([sys.executable, SYNC] + list(argv), capture_output=True, text=True,
                          encoding="utf-8")


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kit-sync-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _target(self, name, builder):
        t = os.path.join(self.tmp, name)
        os.makedirs(t)
        builder(t)
        return t

    def test_engine_absent_exits_2(self):
        t = os.path.join(self.tmp, "empty")
        os.makedirs(t)
        r = _run("audit", "--target", t, "--kit", KIT)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("motor ausente", r.stdout)

    def test_engine_only_is_layer2_absent(self):
        t = self._target("fresh", fixture_engine_only)
        res = ks.audit(t, KIT)
        self.assertEqual(res["layer2"], "absent")
        ids = {g["id"] for g in res["gaps"]}
        self.assertIn("claude.placeholders", ids)
        self.assertIn("steering.product", ids)

    def test_old_layer2_exact_gaps(self):
        t = self._target("old", fixture_old_layer2)
        res = ks.audit(t, KIT)
        self.assertEqual(res["layer2"], "present")
        ids = sorted(g["id"] for g in res["gaps"])
        expected = sorted([
            "steering.integrations", "steering.inherited-knowledge",
            "claude.phase-gates", "claude.spec-impl-auto",
            "claude.section.auto-approval-mode",
            "claude.routing.approver", "claude.routing.data-analyst",
            "claude.routing.report-validator", "claude.routing.data-engineer",
            "config.autoapprove.key.delegation",
            "config.autoapprove.key.limits.max_tokens_per_task",
            "config.autoapprove.key.limits.max_usd_per_task",
            "engine.sdd-new",
            "spec.old-feature.evals", "spec.old-feature.phase",
        ])
        self.assertEqual(ids, expected)
        self.assertNotIn("claude.routing.caveman", ids)
        by = {g["id"]: g for g in res["gaps"]}
        self.assertEqual(by["claude.phase-gates"]["severity"], "blocking")
        self.assertEqual(by["config.autoapprove.key.delegation"]["since"], "0.9.0")
        self.assertEqual(by["claude.routing.data-analyst"]["since"], "0.8.0")
        sevs = [g["severity"] for g in res["gaps"]]
        self.assertEqual(sevs, sorted(sevs, key=lambda s: ks.SEVERITY_ORDER[s]))

    def test_complete_layer2_is_clean(self):
        t = self._target("done", fixture_complete)
        r = _run("audit", "--target", t, "--kit", KIT, "--format", "json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)["gaps"], [])

    def test_audit_is_read_only_and_deterministic(self):
        t = self._target("old2", fixture_old_layer2)
        before = _snapshot(t)
        r1 = _run("audit", "--target", t, "--kit", KIT, "--format", "json")
        r2 = _run("audit", "--target", t, "--kit", KIT, "--format", "json")
        self.assertEqual(r1.returncode, 1)
        self.assertEqual(r1.stdout, r2.stdout)
        self.assertEqual(before, _snapshot(t))

    def test_audit_without_kit_uses_installed_copies(self):
        t = self._target("self", fixture_complete)
        shutil.copy(os.path.join(KIT, "CLAUDE.md.template"), os.path.join(t, "CLAUDE.md.template"))
        shutil.copy(os.path.join(KIT, ".sdd", "settings", "kit-history.json"),
                    os.path.join(t, ".sdd", "settings", "kit-history.json"))
        os.makedirs(os.path.join(t, ".sdd", "settings", "templates"), exist_ok=True)
        for n in ("autoapprove.json", "write-scope.json"):
            shutil.copy(os.path.join(KIT, ".sdd", "settings", "templates", n),
                        os.path.join(t, ".sdd", "settings", "templates", n))
        res = ks.audit(t)
        self.assertTrue(res["template_found"])
        self.assertEqual(res["gaps"], [])

    def test_report_next_step_routing(self):
        t = self._target("rep1", fixture_engine_only)
        _run("report", "--target", t, "--kit", KIT)
        txt = open(os.path.join(t, ".sdd", "UPGRADE.md"), encoding="utf-8").read()
        self.assertIn("setup-sdd", txt.split("## Próximo passo")[1])
        t2 = self._target("rep2", fixture_old_layer2)
        _run("report", "--target", t2, "--kit", KIT)
        txt2 = open(os.path.join(t2, ".sdd", "UPGRADE.md"), encoding="utf-8").read()
        self.assertIn("/update-sdd", txt2.split("## Próximo passo")[1])
        self.assertIn("| Gravidade |", txt2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
