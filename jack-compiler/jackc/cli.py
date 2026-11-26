"""Command-line interface for the Jack compiler.

Examples::

    python -m jackc path/to/Pong              # compile to .vm files
    python -m jackc path/to/ArrayTest --xml   # emit project 10 parse XML
    python -m jackc path/to/ArrayTest --tokens
    python -m jackc path/to/Main.jack --stdout
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compiler import Compiler
from .errors import JackError
from .parser import Parser
from .tokenizer import tokenize
from .xml_writer import class_to_xml, tokens_to_xml


def _jack_files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".jack":
            raise SystemExit(f"error: {path} is not a .jack file")
        return [path]
    if path.is_dir():
        pattern = "**/*.jack" if recursive else "*.jack"
        files = sorted(path.glob(pattern))
        if not files:
            raise SystemExit(f"error: no .jack files found in {path}")
        return files
    raise SystemExit(f"error: {path} does not exist")


def _output_path(source: Path, root: Path, out_dir: Path | None, suffix: str) -> Path:
    if out_dir is None:
        return source.with_name(source.stem + suffix)
    if root.is_dir():
        relative = source.relative_to(root)
        return out_dir / relative.parent / (source.stem + suffix)
    return out_dir / (source.stem + suffix)


def _process(source: Path, mode: str) -> str:
    text = source.read_text(encoding="utf-8-sig")
    tokens = tokenize(text, filename=str(source))
    if mode == "tokens":
        return tokens_to_xml(tokens)
    class_def = Parser(tokens, filename=str(source)).parse()
    if mode == "xml":
        return class_to_xml(class_def)
    return Compiler(class_def).compile()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jackc",
        description="Compile Jack source files to Hack VM code or project 10 XML.",
    )
    parser.add_argument("path", type=Path, help="a .jack file or a directory of .jack files")
    parser.add_argument(
        "--xml",
        action="store_true",
        help="emit the parse-tree XML (project 10) instead of VM code",
    )
    parser.add_argument(
        "--tokens",
        action="store_true",
        help="emit the token XML (project 10) instead of VM code",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output directory (default: next to each source file)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the generated text instead of writing files (single file only)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="when given a directory, do not descend into subdirectories",
    )
    parser.add_argument("--version", action="version", version="jackc 1.0.0")
    args = parser.parse_args(argv)

    if args.xml and args.tokens:
        modes = ["xml", "tokens"]
    elif args.xml:
        modes = ["xml"]
    elif args.tokens:
        modes = ["tokens"]
    else:
        modes = ["vm"]

    try:
        files = _jack_files(args.path, recursive=not args.no_recursive)
        if args.stdout and len(files) != 1:
            raise SystemExit("error: --stdout requires exactly one input file")

        if args.out is not None:
            args.out.mkdir(parents=True, exist_ok=True)

        generated = 0
        for source in files:
            for mode in modes:
                output = _process(source, mode)
                if args.stdout:
                    sys.stdout.write(output)
                    continue
                suffix = {"vm": ".vm", "xml": ".xml", "tokens": "T.xml"}[mode]
                destination = _output_path(source, args.path, args.out, suffix)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(output, encoding="utf-8", newline="\n")
                generated += 1
        if not args.stdout:
            print(f"Compiled {len(files)} file(s), wrote {generated} output file(s).")
        return 0
    except JackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
