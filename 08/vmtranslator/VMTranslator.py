#!/usr/bin/env python3
"""Nand2Tetris VM Translator for Chapters 7 and 8.

Usage:
    python VMTranslator.py <source>

<source> may be one .vm file or a directory containing .vm files.
"""

import os
import sys

from code_writer import CodeWriter
from parser import Parser


def translate_commands(parser, writer):
    """Translate every command in one parsed VM file."""
    while parser.has_more_lines():
        parser.advance()
        command_type = parser.command_type()

        if command_type == Parser.C_ARITHMETIC:
            writer.write_arithmetic(parser.arg1())
        elif command_type == Parser.C_PUSH:
            writer.write_push_pop("push", parser.arg1(), parser.arg2())
        elif command_type == Parser.C_POP:
            writer.write_push_pop("pop", parser.arg1(), parser.arg2())
        elif command_type == Parser.C_LABEL:
            writer.write_label(parser.arg1())
        elif command_type == Parser.C_GOTO:
            writer.write_goto(parser.arg1())
        elif command_type == Parser.C_IF:
            writer.write_if(parser.arg1())
        elif command_type == Parser.C_FUNCTION:
            writer.write_function(parser.arg1(), parser.arg2())
        elif command_type == Parser.C_CALL:
            writer.write_call(parser.arg1(), parser.arg2())
        elif command_type == Parser.C_RETURN:
            writer.write_return()
        else:
            raise ValueError("Unsupported command type: {}".format(command_type))


def get_vm_files(directory):
    """Return all .vm files in a directory, sorted by file name."""
    files = []
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isfile(path) and entry.lower().endswith(".vm"):
            files.append(path)
    return sorted(files)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) != 2:
        print("Usage: python VMTranslator.py <source>", file=sys.stderr)
        return 1

    source = os.path.normpath(argv[1])

    if os.path.isfile(source):
        if not source.lower().endswith(".vm"):
            print("Error: source file must have a .vm extension.", file=sys.stderr)
            return 1

        vm_files = [source]
        output_file = os.path.splitext(source)[0] + ".asm"
        bootstrap = False
    elif os.path.isdir(source):
        vm_files = get_vm_files(source)
        if not vm_files:
            print("Error: no .vm files found in directory.", file=sys.stderr)
            return 1

        directory_name = os.path.basename(source)
        output_file = os.path.join(source, directory_name + ".asm")
        bootstrap = any(
            os.path.basename(vm_file).lower() == "sys.vm" for vm_file in vm_files
        )
    else:
        print("Error: source does not exist: {}".format(source), file=sys.stderr)
        return 1

    writer = CodeWriter(output_file)
    try:
        if bootstrap:
            writer.write_init()

        for vm_file in vm_files:
            base_name = os.path.splitext(os.path.basename(vm_file))[0]
            writer.set_file_name(base_name)
            translate_commands(Parser(vm_file), writer)
    finally:
        writer.close()

    print("Translated to {}".format(output_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
