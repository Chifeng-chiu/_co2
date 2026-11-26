"""A complete Jack compiler for the nand2tetris Hack platform.

The package contains a tokenizer, a recursive-descent parser that can emit the
standard project 10 XML, a symbol table, and a code generator that emits Hack
VM code (project 11).
"""

from .compiler import Compiler
from .parser import Parser
from .tokenizer import Token, TokenKind, tokenize
from .xml_writer import class_to_xml, tokens_to_xml

__all__ = [
    "Compiler",
    "Parser",
    "Token",
    "TokenKind",
    "tokenize",
    "class_to_xml",
    "tokens_to_xml",
]
