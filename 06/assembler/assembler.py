#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nand2Tetris (Project 6) - Hack Assembler / Disassembler
=======================================================

Usage
-----
    python assembler.py Prog.asm
    python assembler.py Prog.asm -o build/Prog.hack
    python assembler.py Prog.asm --symbols
    python assembler.py --disassemble Prog.hack
    python assembler.py -d Prog.hack -o Prog.asm

The assembler implements the official Hack assembly language:

  * comments  : "// ..." (whole line or end of line)
  * labels    : "(LOOP)" - virtual, they do not occupy a ROM address
  * A-instruction : "@value"  -> 0 + 15-bit address
  * C-instruction : "dest=comp;jump" -> 111 a cccccc ddd jjj
  * predefined symbols, user labels and variables allocated from RAM[16]

Errors are reported with their original source line number.  If any error is
found, no output file is written and the process exits with status 1.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Symbol / instruction tables (Nand2Tetris Project 6 specification)
# ---------------------------------------------------------------------------

PREDEFINED: dict[str, int] = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    **{f"R{i}": i for i in range(16)},
    "SCREEN": 16384,
    "KBD": 24576,
}

# mnemonic -> 7 bits: a + cccccc
COMP_TABLE: dict[str, str] = {
    "0": "0101010",
    "1": "0111111",
    "-1": "0111010",
    "D": "0001100",
    "A": "0110000",
    "!D": "0001101",
    "!A": "0110001",
    "-D": "0001111",
    "-A": "0110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "D|A": "0010101",
    "M": "1110000",
    "!M": "1110001",
    "-M": "1110011",
    "M+1": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "D|M": "1010101",
}

# Commutative / alternate spellings accepted as a convenience.
COMP_ALIASES: dict[str, str] = {
    "A+D": "D+A",
    "M+D": "D+M",
    "A&D": "D&A",
    "M&D": "D&M",
    "A|D": "D|A",
    "M|D": "D|M",
    "1+D": "D+1",
    "1+A": "A+1",
    "1+M": "M+1",
}

DEST_TABLE: dict[str, str] = {
    "null": "000",
    "M": "001",
    "D": "010",
    "MD": "011",
    "A": "100",
    "AM": "101",
    "AD": "110",
    "AMD": "111",
}

JUMP_TABLE: dict[str, str] = {
    "null": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

COMP_REVERSE = {bits: name for name, bits in COMP_TABLE.items()}
DEST_REVERSE = {bits: name for name, bits in DEST_TABLE.items()}
JUMP_REVERSE = {bits: name for name, bits in JUMP_TABLE.items()}

SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")
DECIMAL_RE = re.compile(r"^[0-9]+$")
BINARY_RE = re.compile(r"^[01]{16}$")


# ---------------------------------------------------------------------------
# Result / error types
# ---------------------------------------------------------------------------


class AsmError(Exception):
    """A single source-level error with an original line number."""

    def __init__(self, line_no: int, message: str, source: str = "") -> None:
        super().__init__(message)
        self.line_no = line_no
        self.message = message
        self.source = source

    def format(self) -> str:
        text = f"line {self.line_no}: {self.message}"
        if self.source:
            text += f"\n    {self.line_no:>4} | {self.source}"
        return text


@dataclass
class AsmResult:
    words: list[str] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)
    variables: dict[str, int] = field(default_factory=dict)
    errors: list[AsmError] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def strip_comment(line: str) -> str:
    """Remove a // comment (whole-line or trailing) from one source line."""
    index = line.find("//")
    return line[:index] if index >= 0 else line


def comp_bits(comp: str) -> str:
    """Return the 7-bit (a + cccccc) code for a comp mnemonic."""
    key = re.sub(r"\s+", "", comp)
    for candidate in (key, key.upper()):
        if candidate in COMP_TABLE:
            return COMP_TABLE[candidate]
        alias = COMP_ALIASES.get(candidate)
        if alias is not None and alias in COMP_TABLE:
            return COMP_TABLE[alias]
    raise ValueError(f'unknown comp mnemonic "{comp}"')


def dest_bits(dest: str | None) -> str:
    """Return the 3-bit ddd code for a dest field (order A, D, M)."""
    if dest is None:
        return "000"
    key = dest.strip()
    if not key or key.lower() == "null":
        return "000"
    a = d = m = 0
    for char in key.upper():
        if char == "A":
            a = 1
        elif char == "D":
            d = 1
        elif char == "M":
            m = 1
        else:
            raise ValueError(f'invalid dest "{dest}"')
    return f"{a}{d}{m}"


def jump_bits(jump: str | None) -> str:
    """Return the 3-bit jjj code for a jump field."""
    if jump is None:
        return "000"
    key = jump.strip().upper()
    if not key or key == "NULL":
        return "000"
    if key not in JUMP_TABLE:
        raise ValueError(f'unknown jump mnemonic "{jump}"')
    return JUMP_TABLE[key]


def parse_c_instruction(code: str) -> tuple[str | None, str, str | None]:
    """Split a C-instruction into (dest, comp, jump); dest/jump are optional."""
    rest = code
    dest: str | None = None
    jump: str | None = None

    if "=" in rest:
        dest, rest = rest.split("=", 1)
        dest = dest.strip()
        if not dest:
            raise ValueError("missing dest before '='")

    if ";" in rest:
        rest, jump = rest.split(";", 1)
        jump = jump.strip()
        if not jump:
            raise ValueError("missing jump after ';'")

    comp = rest.strip()
    if not comp:
        raise ValueError("missing comp field")
    if "=" in comp or ";" in comp:
        raise ValueError(f'invalid C-instruction syntax "{code}"')
    return dest, comp, jump


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


def assemble(text: str) -> AsmResult:
    """Assemble Hack assembly source into 16-bit words."""
    symbols: dict[str, int] = dict(PREDEFINED)
    labels: dict[str, int] = {}
    variables: dict[str, int] = {}
    errors: list[AsmError] = []
    instructions: list[tuple[int, str, int]] = []  # (line_no, code, rom_address)
    rom = 0

    # ---- First pass: collect labels, keep line numbers -------------------
    for line_no, raw in enumerate(text.splitlines(), start=1):
        code = strip_comment(raw).strip()
        if not code:
            continue

        if code.startswith("("):
            if not code.endswith(")"):
                errors.append(AsmError(line_no, 'label must end with ")"', raw.strip()))
                continue
            name = code[1:-1].strip()
            if not name:
                errors.append(AsmError(line_no, "empty label name", raw.strip()))
                continue
            if not SYMBOL_RE.fullmatch(name):
                errors.append(AsmError(line_no, f'invalid label name "{name}"', raw.strip()))
                continue
            if name in PREDEFINED:
                errors.append(
                    AsmError(line_no, f'cannot redefine predefined symbol "{name}"', raw.strip())
                )
                continue
            if name in labels:
                errors.append(
                    AsmError(
                        line_no,
                        f'duplicate label "{name}" (first defined at ROM {labels[name]})',
                        raw.strip(),
                    )
                )
                continue
            labels[name] = rom
            symbols[name] = rom
            continue

        # Every other non-empty line is one machine instruction.
        instructions.append((line_no, code, rom))
        rom += 1

    # ---- Second pass: variables and machine code ------------------------
    ram = 16
    words: list[str] = []

    for line_no, code, _rom_address in instructions:
        try:
            if code.startswith("@"):
                value = code[1:].strip()
                if not value:
                    raise ValueError("missing value after '@'")

                if DECIMAL_RE.fullmatch(value):
                    address = int(value)
                    if address > 0x7FFF:
                        raise ValueError(
                            f"address {address} is outside the 15-bit range (0..32767)"
                        )
                else:
                    if not SYMBOL_RE.fullmatch(value):
                        raise ValueError(f'invalid symbol "{value}"')
                    if value in symbols:
                        address = symbols[value]
                    else:
                        if ram > 0x7FFF:
                            raise ValueError("out of RAM space for variables (> 32767)")
                        address = ram
                        ram += 1
                        symbols[value] = address
                        variables[value] = address

                words.append("0" + format(address, "015b"))
            else:
                dest, comp, jump = parse_c_instruction(code)
                words.append(
                    "111"
                    + comp_bits(comp)
                    + dest_bits(dest)
                    + jump_bits(jump)
                )
        except ValueError as exc:
            errors.append(AsmError(line_no, str(exc), code))
            # Keep the output length aligned with the instruction count.
            words.append("0000000000000000")

    errors.sort(key=lambda item: item.line_no)
    return AsmResult(words=words, labels=labels, variables=variables, errors=errors)


# ---------------------------------------------------------------------------
# Disassembler
# ---------------------------------------------------------------------------


def disassemble(text: str) -> tuple[list[str], list[AsmError]]:
    """Convert 16-bit Hack machine words back into Hack assembly."""
    output: list[str] = []
    errors: list[AsmError] = []

    for line_no, raw in enumerate(text.splitlines(), start=1):
        code = strip_comment(raw).strip()
        if not code:
            continue
        bits = re.sub(r"\s+", "", code)
        if not BINARY_RE.fullmatch(bits):
            errors.append(
                AsmError(line_no, "expected exactly 16 binary digits (0/1)", raw.strip())
            )
            continue

        if bits[0] == "0":
            output.append(f"@{int(bits, 2)}")
            continue

        if bits[:3] != "111":
            errors.append(
                AsmError(
                    line_no,
                    "invalid instruction: must start with 0 (A) or 111 (C)",
                    raw.strip(),
                )
            )
            continue

        comp_code = bits[3:10]
        dest_code = bits[10:13]
        jump_code = bits[13:16]

        comp = COMP_REVERSE.get(comp_code)
        if comp is None:
            errors.append(AsmError(line_no, f"unknown comp bits {comp_code}", raw.strip()))
            continue

        dest = DEST_REVERSE[dest_code]
        jump = JUMP_REVERSE[jump_code]
        mnemonic = ""
        if dest != "null":
            mnemonic += dest + "="
        mnemonic += comp
        if jump != "null":
            mnemonic += ";" + jump
        output.append(mnemonic)

    return output, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_symbols(result: AsmResult) -> None:
    print("\nSymbols")
    print("-------")
    print("Labels (ROM):")
    if result.labels:
        for name, address in sorted(result.labels.items(), key=lambda kv: (kv[1], kv[0])):
            print(f"  {name:<24} {address}")
    else:
        print("  (none)")
    print("Variables (RAM):")
    if result.variables:
        for name, address in sorted(result.variables.items(), key=lambda kv: (kv[1], kv[0])):
            print(f"  {name:<24} {address}")
    else:
        print("  (none)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assembler.py",
        description="Nand2Tetris Project 6 Hack assembler / disassembler.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python assembler.py Prog.asm\n"
            "  python assembler.py Prog.asm -o Prog.hack --symbols\n"
            "  python assembler.py -d Prog.hack\n"
        ),
    )
    parser.add_argument("input", help="input file (.asm, or .hack with --disassemble)")
    parser.add_argument("-o", "--output", help="output file (default: same name, new suffix)")
    parser.add_argument(
        "-d",
        "--disassemble",
        action="store_true",
        help="disassemble a .hack file into .asm instead of assembling",
    )
    parser.add_argument(
        "--symbols",
        action="store_true",
        help="print the label / variable symbol table after assembling",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress the success message")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[ERROR] input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        text = input_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"[ERROR] cannot read {input_path}: {exc}", file=sys.stderr)
        return 2

    if not args.disassemble and input_path.suffix.lower() == ".hack":
        print(
            "[ERROR] this looks like a .hack file; use --disassemble (-d) for HACK -> ASM",
            file=sys.stderr,
        )
        return 2

    if args.disassemble:
        lines, errors = disassemble(text)
        default_suffix = ".asm"
        unit = "instructions"
    else:
        result = assemble(text)
        lines, errors = result.words, result.errors
        default_suffix = ".hack"
        unit = "instructions"

    if errors:
        for error in errors:
            print(error.format(), file=sys.stderr)
        print(
            f"\n{len(errors)} error(s). No output file was written.",
            file=sys.stderr,
        )
        return 1

    output_path = Path(args.output) if args.output else input_path.with_suffix(default_suffix)
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))
            if lines:
                handle.write("\n")
    except OSError as exc:
        print(f"[ERROR] cannot write {output_path}: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        action = "Disassembled" if args.disassemble else "Assembled"
        print(f"[OK] {action} {len(lines)} {unit} -> {output_path}")
        if not args.disassemble:
            print(
                f"     labels: {len(result.labels)}, "
                f"variables: {len(result.variables)}, "
                f"errors: 0"
            )

    if args.symbols and not args.disassemble:
        _print_symbols(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
