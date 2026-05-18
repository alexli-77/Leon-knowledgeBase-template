#!/usr/bin/env python3

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "curator"))

from vault_gate import GateConfig, GateError, capture, edit_request, safe_join  # noqa: E402


class VaultGateTests(unittest.TestCase):
    def test_capture_writes_inbox_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = GateConfig(root=Path(tmp))
            result = capture(config, "test", "Hello", "Body")
            self.assertEqual(result.decision, "captured")
            self.assertTrue((Path(tmp) / result.path).exists())
            logs = list((Path(tmp) / "99_Meta" / "automation-log").glob("*.md"))
            self.assertEqual(len(logs), 1)

    def test_edit_request_goes_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = GateConfig(root=Path(tmp))
            result = edit_request(config, "hermes", "Change", "Please edit note X")
            self.assertEqual(result.decision, "pending-review")
            self.assertIn("Pending-Review", result.path)

    def test_denies_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GateError):
                safe_join(Path(tmp).resolve(), "../secret.md")

    def test_denies_hidden_system_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GateError):
                safe_join(Path(tmp).resolve(), ".git/config")


if __name__ == "__main__":
    unittest.main()

