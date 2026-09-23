"""Versioned material checks must preserve earlier reports."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVISION = "docs/revisions/U14-T4-v01"


class MaterialsRevisionTests(unittest.TestCase):
    def run_check(self, directory):
        return subprocess.run([
            sys.executable, "-X", "utf8", "scripts/check_materials_numbers.py",
            "--materials-dir", REVISION,
            "--table", REVISION + "/number_sources.csv",
            "--out", str(directory / "reports"),
            "--report-table", str(directory / "table.md"),
        ], cwd=ROOT, capture_output=True, encoding="utf-8")

    def test_custom_paths_pass(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            result = self.run_check(directory)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((directory / "reports/number_check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["verdict"], "consistency_passed")
            self.assertEqual(len(report["source_checks"]), 86)
            self.assertEqual(len(report["materials"]), 6)
            self.assertTrue((directory / "table.md").exists())

    def test_existing_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            (directory / "reports").mkdir()
            report = directory / "reports/number_check.json"
            report.write_text("sentinel", encoding="utf-8")
            result = self.run_check(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Versioned report already exists", result.stderr)
            self.assertEqual(report.read_text(encoding="utf-8"), "sentinel")
            self.assertFalse((directory / "table.md").exists())

    def test_existing_table_is_preserved(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            table = directory / "table.md"
            table.write_text("sentinel", encoding="utf-8")
            result = self.run_check(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Versioned table already exists", result.stderr)
            self.assertEqual(table.read_text(encoding="utf-8"), "sentinel")
            self.assertFalse((directory / "reports/number_check.json").exists())
