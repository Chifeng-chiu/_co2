"""Typed abstract syntax tree for Jack.

The nodes intentionally keep only semantic information (names, literals and
structure).  The XML writer can reconstruct every source token from this
representation, and the code generator can walk it directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------


@dataclass
class VarDec:
    """A ``static``, ``field`` or ``var`` declaration."""

    kind: str  # "static" | "field" | "var"
    type: str
    names: list[str]


@dataclass
class Parameter:
    type: str
    name: str


@dataclass
class SubroutineDef:
    kind: str  # "constructor" | "function" | "method"
    return_type: str
    name: str
    params: list[Parameter]
    vars: list[VarDec]
    body: list["Stmt"] = field(default_factory=list)


@dataclass
class ClassDef:
    name: str
    class_vars: list[VarDec] = field(default_factory=list)
    subroutines: list[SubroutineDef] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


@dataclass
class LetStmt:
    name: str
    index: "Expr | None"
    value: "Expr"


@dataclass
class IfStmt:
    condition: "Expr"
    then_body: list["Stmt"]
    else_body: list["Stmt"] | None = None


@dataclass
class WhileStmt:
    condition: "Expr"
    body: list["Stmt"]


@dataclass
class DoStmt:
    call: "Call"


@dataclass
class ReturnStmt:
    value: "Expr | None" = None


Stmt = LetStmt | IfStmt | WhileStmt | DoStmt | ReturnStmt


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


@dataclass
class Expr:
    first: "Term"
    rest: list[tuple[str, "Term"]] = field(default_factory=list)


@dataclass
class IntConst:
    value: int


@dataclass
class StringConst:
    value: str


@dataclass
class KeywordConst:
    value: str  # "true" | "false" | "null" | "this"


@dataclass
class VarRef:
    name: str


@dataclass
class ArrayRef:
    name: str
    index: Expr


@dataclass
class Call:
    """A subroutine call.

    ``receiver is None`` means the bare ``foo(...)`` form, i.e. a method call
    on the current object.  Otherwise ``receiver`` is either a class name or a
    variable name; the code generator resolves which one using the symbol
    table.
    """

    receiver: str | None
    name: str
    args: list[Expr] = field(default_factory=list)


@dataclass
class ParenTerm:
    expr: Expr


@dataclass
class UnaryTerm:
    op: str  # "-" | "~"
    term: "Term"


Term = IntConst | StringConst | KeywordConst | VarRef | ArrayRef | Call | ParenTerm | UnaryTerm
