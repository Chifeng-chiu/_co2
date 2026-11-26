from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import COMPILER_ROOT


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "jackc", *args],
            cwd=COMPILER_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_compile_to_vm_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jackc-cli-") as temp:
            root = Path(temp)
            source = root / "Main.jack"
            source.write_text(
                "class Main { function void main() { return; } }",
                encoding="utf-8",
            )
            result = self.run_cli(str(source))
            self.assertEqual(result.returncode, 0, result.stderr)
            vm = source.with_suffix(".vm")
            self.assertTrue(vm.exists())
            self.assertEqual(vm.read_text(encoding="utf-8"), "function Main.main 0\npush constant 0\nreturn\n")

    def test_xml_and_token_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jackc-cli-") as temp:
            root = Path(temp)
            source = root / "Main.jack"
            source.write_text("class Main { }", encoding="utf-8")
            result = self.run_cli(str(source), "--xml", "--tokens")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "Main.xml").exists())
            self.assertTrue((root / "MainT.xml").exists())
            self.assertIn("<class>", (root / "Main.xml").read_text(encoding="utf-8"))
            self.assertIn("<tokens>", (root / "MainT.xml").read_text(encoding="utf-8"))

    def test_stdout_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jackc-cli-") as temp:
            source = Path(temp) / "Main.jack"
            source.write_text(
                "class Main { function void main() { return; } }",
                encoding="utf-8",
            )
            result = self.run_cli(str(source), "--stdout")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("function Main.main", result.stdout)
            self.assertFalse(source.with_suffix(".vm").exists())

    def test_error_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jackc-cli-") as temp:
            source = Path(temp) / "Broken.jack"
            source.write_text("class Main { function void main() { let x = ; } }", encoding="utf-8")
            result = self.run_cli(str(source))
            self.assertEqual(result.returncode, 1)
            self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
