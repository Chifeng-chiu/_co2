"""Regenerate the VM golden files with the official nand2tetris compiler.

This script is only needed when the course test programs change.  The tests
themselves read the committed files under ``tests/golden/vm`` and do not need
Java.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
COMPILER_ROOT = TESTS_DIR.parent
PROJECTS = COMPILER_ROOT.parent
TOOLS = PROJECTS.parent / "tools"
GOLDEN = TESTS_DIR / "golden" / "vm"

PROJECT_NUMBERS = ("9", "11", "12")


def project_dir(number: str) -> Path:
    candidates = [PROJECTS / number]
    if number.isdigit():
        candidates.append(PROJECTS / number.zfill(2))
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def official_compiler() -> Path:
    bat = TOOLS / "JackCompiler.bat"
    if bat.exists():
        return bat
    sh = TOOLS / "JackCompiler.sh"
    if sh.exists():
        return sh
    raise SystemExit(f"error: could not find JackCompiler in {TOOLS}")


def case_directories() -> list[Path]:
    cases: list[Path] = []
    for number in PROJECT_NUMBERS:
        project = project_dir(number)
        if not project.is_dir():
            continue
        for directory in sorted(path for path in project.rglob("*") if path.is_dir()):
            if any(directory.glob("*.jack")):
                cases.append(directory)
    return cases


def main() -> int:
    compiler = official_compiler()
    cases = case_directories()
    if not cases:
        raise SystemExit("error: no test directories found")

    failures: list[tuple[Path, str]] = []
    with tempfile.TemporaryDirectory(prefix="jackc-golden-") as temp:
        temp_root = Path(temp)
        for source_dir in cases:
            relative = source_dir.relative_to(PROJECTS)
            work = temp_root / relative
            work.mkdir(parents=True, exist_ok=True)
            for jack in source_dir.glob("*.jack"):
                shutil.copy2(jack, work / jack.name)

            result = subprocess.run(
                [str(compiler), str(work)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            vm_files = sorted(work.glob("*.vm"))
            if result.returncode != 0 or not vm_files:
                failures.append((relative, (result.stdout + result.stderr).strip()))
                continue

            destination = GOLDEN / relative
            destination.mkdir(parents=True, exist_ok=True)
            for vm in vm_files:
                shutil.copy2(vm, destination / vm.name)
            print(f"ok  {relative} ({len(vm_files)} VM file(s))")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for relative, message in failures:
            print(f"  {relative}: {message}", file=sys.stderr)
        return 1
    print(f"\nGolden files written to {GOLDEN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
