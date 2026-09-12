"""Producer exporter regressions using fictional committed source fixtures."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from crypto_research_export.bundle import export
from research_bundle import digest, validate

SOURCE = "charters/scientific_state.json"
SAMPLE = '{"schema_version":"crypto-scientific-state/1","hypotheses":{"TEST-HYPOTHESIS-001":"UNKNOWN"},"hypothesis_trials":{"TEST-HYPOTHESIS-001":"TEST-TRIAL-001"},"frozen_families":[],"as_of_commit":"test","notes":"fictional test"}'


class ExportTests(unittest.TestCase):
    def setUp(self):
        area = Path(tempfile.gettempdir()) / "bundle-export-tests"
        area.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=area)
        self.base = Path(self.temporary.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        self.source = self.root / SOURCE
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_bytes(SAMPLE.encode())
        self.commit()
        self.expected = {SOURCE: digest(self.source.read_bytes())}

    def commit(self):
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-m",
                "fictional fixture",
            ],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def run_export(self, destination="out", expected=None):
        return export(
            self.root,
            self.expected if expected is None else expected,
            self.base / destination,
            "2026-09-11T00:00:00Z",
        )

    def test_pinned_harness_receipt_preserves_operational_limits(self):
        import json

        from crypto_research_export.bundle import ATTESTATIONS

        name = sorted(ATTESTATIONS)[0]
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        record = dict(
            schema_version="pipeline-power/2",
            passed_at="2026-09-01T00:00:00Z",
            expires_at="2026-09-02T00:00:00Z",
            edge_verdict="TEST_CONTROL",
        )
        path.write_text(json.dumps(record), encoding="utf-8")
        self.commit()
        self.expected[name] = digest(path.read_bytes())
        bundle = self.run_export()
        node = next(e for e in bundle["entities"] if e["entity_type"] == "attestation")
        assert node["status"] == "RECORDED" and node["status_axis"] == "operational"
        assert node["payload"] == record
        assert not any(r["type"] == "HAS_ATTESTATION" for r in bundle["relations"])

    def test_deterministic_read_only_unknown(self):
        first = self.run_export()
        second = self.run_export("other")
        self.assertEqual(first, second)
        validate(first)
        self.assertEqual(self.expected[SOURCE], digest(self.source.read_bytes()))
        self.assertTrue(all(e["event_at"] is None for e in first["entities"]))
        self.assertEqual(
            subprocess.check_output(["git", "-C", str(self.root), "status", "--porcelain"]), b""
        )

    def test_unexpected_source(self):
        with self.assertRaises(ValueError):
            self.run_export(expected={"private.env": "0" * 64})

    def test_existing_trial_selected_without_reexecution(self):
        import json

        from crypto_research_export.bundle import TRIALS

        path = self.root / TRIALS
        path.parent.mkdir(parents=True)
        selected = {
            "name": "TEST-TRIAL-001",
            "registered_at": "2026-01-02T00:00:00Z",
            "params": {"horizon": 7},
            "sharpe": None,
            "notes": "Recorded fixture",
        }
        path.write_text(
            json.dumps([selected, {"name": "UNSELECTED", "status": "UNKNOWN"}]), encoding="utf-8"
        )
        self.commit()
        self.expected[TRIALS] = digest(path.read_bytes())
        result = self.run_export()
        trial = next(e for e in result["entities"] if e["entity_type"] == "trial")
        self.assertEqual(trial["payload"], selected)
        self.assertEqual(trial["recorded_at"], selected["registered_at"])
        self.assertEqual(trial["status"], "UNKNOWN")
        self.assertIsNone(trial["payload"]["sharpe"])
        self.assertNotIn("UNSELECTED", str(result))

    def test_hash_mismatch(self):
        with self.assertRaises(ValueError):
            self.run_export(expected={SOURCE: "0" * 64})

    def test_missing(self):
        self.source.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.run_export()

    def test_changed(self):
        self.source.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.run_export()

    def test_existing_output(self):
        self.run_export()
        with self.assertRaises(FileExistsError):
            self.run_export()

    def test_inside_checkout(self):
        with self.assertRaises(ValueError):
            export(self.root, self.expected, self.root / "out", "2026-09-11T00:00:00Z")

    def test_malformed_committed(self):
        self.source.write_bytes(b"malformed")
        self.commit()
        with self.assertRaises((ValueError, KeyError)):
            self.run_export(expected={SOURCE: digest(self.source.read_bytes())})

    def test_sensitive_content(self):
        self.source.write_bytes(b'{"api_key":"FAKE_SECRET_TEST_ONLY"}')
        self.commit()
        with self.assertRaisesRegex(ValueError, "SENSITIVE_CONTENT"):
            self.run_export(expected={SOURCE: digest(self.source.read_bytes())})


if __name__ == "__main__":
    unittest.main()
