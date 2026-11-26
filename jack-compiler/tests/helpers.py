"""Shared helpers for the test suite."""

from __future__ import annotations

from pathlib import Path

from jackc.compiler import Compiler
from jackc.parser import Parser
from jackc.tokenizer import Token, tokenize
from jackc.xml_writer import class_to_xml, tokens_to_xml

TESTS_DIR = Path(__file__).resolve().parent
COMPILER_ROOT = TESTS_DIR.parent
PROJECTS = COMPILER_ROOT.parent
GOLDEN_VM = TESTS_DIR / "golden" / "vm"


def project_dir(number: str) -> Path:
    """Resolve a project folder, accepting both ``9`` and ``09`` layouts."""

    candidates = [PROJECTS / number]
    if number.isdigit():
        candidates.append(PROJECTS / number.zfill(2))
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def tokenize_file(path: Path) -> list[Token]:
    return tokenize(read_source(path), filename=str(path))


def parse_file(path: Path):
    return Parser(tokenize_file(path), filename=str(path)).parse()


def compile_file(path: Path) -> str:
    return Compiler(parse_file(path)).compile()


def parse_xml_file(path: Path) -> str:
    return class_to_xml(parse_file(path))


def token_xml_file(path: Path) -> str:
    return tokens_to_xml(tokenize_file(path))


def project10_cases() -> list[Path]:
    """Jack files in project 10 that have both reference XML files."""

    cases: list[Path] = []
    project = project_dir("10")
    for jack in sorted(project.rglob("*.jack")):
        if jack.with_suffix(".xml").exists() and jack.with_name(jack.stem + "T.xml").exists():
            cases.append(jack)
    return cases


def golden_vm_cases() -> list[tuple[Path, Path]]:
    """Return (source .jack, expected .vm) pairs from the golden directory."""

    cases: list[tuple[Path, Path]] = []
    for vm in sorted(GOLDEN_VM.rglob("*.vm")):
        relative = vm.relative_to(GOLDEN_VM)
        parts = relative.parts
        source = project_dir(parts[0]).joinpath(*parts[1:]).with_suffix(".jack")
        cases.append((source, vm))
    return cases
