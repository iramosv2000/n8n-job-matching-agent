"""Tests for the repository tooling in scripts/ (stdlib unittest; run: python3 -m unittest -v).

Fake secrets and identifiers are assembled at runtime so that the test file itself does not
trip the secret scanner or the personal-data guard.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_workflows  # noqa: E402
import guard_personal_data  # noqa: E402
import normalize_workflows  # noqa: E402

BASE = {"name": "WF-99 test", "nodes": [], "connections": {}}


class NormalizeWorkflowsTest(unittest.TestCase):
    def test_drops_volatile_and_data_bearing_fields(self):
        raw = {
            **BASE,
            "id": "abc",
            "active": True,
            "versionId": "v1",
            "createdAt": "t",
            "updatedAt": "t",
            "pinData": {"n": [1]},
            "staticData": {"s": 1},
            "meta": {"instanceId": "i"},
            "tags": [{"id": "t1", "name": "m1", "createdAt": "t"}],
        }
        out = normalize_workflows.normalise(raw)
        self.assertEqual(out, {**BASE, "id": "abc", "tags": [{"id": "t1", "name": "m1"}]})

    def test_file_named_after_workflow_and_stale_files_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, target = Path(tmp, "raw"), Path(tmp, "workflows")
            raw.mkdir()
            target.mkdir()
            (raw / "xyz.json").write_text(json.dumps({**BASE, "name": "WF-01 Ingesta Ofertas"}))
            (target / "old.json").write_text("{}")
            normalize_workflows.main(raw, target)
            self.assertEqual(sorted(p.name for p in target.iterdir()), ["wf-01-ingesta-ofertas.json"])


class CheckWorkflowsTest(unittest.TestCase):
    def check(self, workflow) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "wf.json")
            path.write_text(workflow if isinstance(workflow, str) else json.dumps(workflow))
            return check_workflows.check_workflow(path)

    def test_valid_workflow_passes(self):
        ok = {**BASE, "nodes": [{"name": "A", "credentials": {"x": {"id": "1", "name": "n"}}}]}
        self.assertEqual(self.check(ok), [])

    def test_detects_problems(self):
        google = "AIza" + "B" * 35
        telegram = "123456789:" + "A" * 35
        cases = {
            "invalid JSON": "{nope",
            "Google API key": {**BASE, "nodes": [{"name": "H", "parameters": {"k": google}}]},
            "Telegram bot token": {
                **BASE,
                "nodes": [{"name": "T", "parameters": {"u": f"/bot{telegram}/x"}}],
            },
            "pinData": {**BASE, "pinData": {"n": [1]}},
            "bare reference": {
                **BASE,
                "nodes": [{"name": "C", "credentials": {"x": {"id": "1", "data": "s"}}}],
            },
            "missing or invalid 'nodes'": {"name": "x", "connections": {}},
        }
        for expected, workflow in cases.items():
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in e for e in self.check(workflow)), self.check(workflow))


class DuplicateIdsTest(unittest.TestCase):
    def test_same_id_in_two_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a.json", "b.json"):
                Path(tmp, name).write_text(json.dumps({**BASE, "id": "wf01"}))
            self.assertEqual(check_workflows.main([tmp]), 1)


class GuardPersonalDataTest(unittest.TestCase):
    def check_text(self, text: str, denylist=()) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "doc.md")
            path.write_text(text)
            return guard_personal_data.check_file(path, list(denylist))

    def test_forbidden_paths(self):
        for name in (
            "CONFIGURACION_AGENTE_EMPLEO.md",
            "profiles/real/cv.tex",
            "x/data.sqlite",
            "ofertas.csv",
            ".env",
        ):
            with self.subTest(name=name):
                self.assertTrue(guard_personal_data.check_file(Path(name), []))
        for name in ("profiles/README.md", "profiles/example/cv.tex"):
            with self.subTest(name=name):
                self.assertFalse(guard_personal_data.check_file(Path(name), []))

    def test_identifiers(self):
        phone = "+56 9 " + "1234 5678"
        rut = "12.345." + "678-9"
        email = "persona" + "@" + "gmail.com"
        self.assertIn("contains a Chilean phone number", self.check_text(f"tel {phone}"))
        self.assertIn("contains a Chilean RUT", self.check_text(f"rut {rut}"))
        self.assertTrue(any("e-mail" in p for p in self.check_text(f"mail {email}")))
        self.assertEqual(self.check_text("contact: user@example.com"), [])

    def test_local_denylist(self):
        self.assertTrue(self.check_text("Calle Secreta 123", denylist=["calle secreta"]))


if __name__ == "__main__":
    unittest.main()
