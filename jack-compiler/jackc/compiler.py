"""Jack-to-VM code generator (nand2tetris project 11).

The generated code follows the conventions of the official nand2tetris
compiler, including label naming, ``this``/``static`` field access, method
call argument counts, and the use of ``Math.multiply`` / ``Math.divide`` for
the ``*`` and ``/`` operators.
"""

from __future__ import annotations

from . import ast
from .errors import JackError
from .symbol_table import SymbolTable
from .vm_writer import VMWriter

_SEGMENT_BY_KIND = {
    "static": "static",
    "field": "this",
    "arg": "argument",
    "var": "local",
}

_STRING_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
    "0": "\0",
    "a": "\a",
    "v": "\v",
    "\\": "\\",
    '"': '"',
    "'": "'",
}


def _decode_string(value: str) -> str:
    """Decode the backslash escapes accepted by the official compiler.

    Unknown escapes simply lose the backslash (``\\q`` becomes ``q``), which
    matches the reference JackCompiler.
    """

    result: list[str] = []
    index = 0
    while index < len(value):
        ch = value[index]
        if ch == "\\" and index + 1 < len(value):
            result.append(_STRING_ESCAPES.get(value[index + 1], value[index + 1]))
            index += 2
        else:
            result.append(ch)
            index += 1
    return "".join(result)


def _always_returns(statements: list[ast.Stmt]) -> bool:
    """Conservative check used to avoid appending an unreachable return."""

    for statement in statements:
        if isinstance(statement, ast.ReturnStmt):
            return True
        if isinstance(statement, ast.IfStmt) and statement.else_body is not None:
            if _always_returns(statement.then_body) and _always_returns(statement.else_body):
                return True
    return False


class Compiler:
    def __init__(self, class_def: ast.ClassDef) -> None:
        self.class_def = class_def
        self.symbols = SymbolTable()
        self.writer = VMWriter()
        self.if_counter = 0
        self.while_counter = 0
        self.current_subroutine: ast.SubroutineDef | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self) -> str:
        for var_dec in self.class_def.class_vars:
            for name in var_dec.names:
                self.symbols.define(name, var_dec.type, var_dec.kind)
        for subroutine in self.class_def.subroutines:
            self._compile_subroutine(subroutine)
        return self.writer.text()

    # ------------------------------------------------------------------
    # Subroutines
    # ------------------------------------------------------------------

    def _compile_subroutine(self, subroutine: ast.SubroutineDef) -> None:
        self.current_subroutine = subroutine
        # The official compiler uses separate per-subroutine counters for
        # if and while labels.
        self.if_counter = 0
        self.while_counter = 0
        self.symbols.start_subroutine()

        if subroutine.kind == "method":
            # argument 0 is the implicit ``this`` receiver.
            self.symbols.define("this", self.class_def.name, "arg")

        for param in subroutine.params:
            self.symbols.define(param.name, param.type, "arg")
        for var_dec in subroutine.vars:
            for name in var_dec.names:
                self.symbols.define(name, var_dec.type, "var")

        n_locals = self.symbols.count("var")
        self.writer.write_function(
            f"{self.class_def.name}.{subroutine.name}", n_locals
        )

        if subroutine.kind == "method":
            self.writer.write_push("argument", 0)
            self.writer.write_pop("pointer", 0)
        elif subroutine.kind == "constructor":
            field_count = self.symbols.count("field")
            self.writer.write_push("constant", field_count)
            self.writer.write_call("Memory.alloc", 1)
            self.writer.write_pop("pointer", 0)

        for statement in subroutine.body:
            self._compile_statement(statement)

        # Jack requires an explicit return, but accepting a missing one makes
        # the compiler friendlier to incomplete OS stubs (e.g. project 12).
        if not _always_returns(subroutine.body):
            if subroutine.kind == "constructor":
                self.writer.write_push("pointer", 0)
            else:
                self.writer.write_push("constant", 0)
            self.writer.write_return()

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _compile_statement(self, statement: ast.Stmt) -> None:
        if isinstance(statement, ast.LetStmt):
            self._compile_let(statement)
        elif isinstance(statement, ast.IfStmt):
            self._compile_if(statement)
        elif isinstance(statement, ast.WhileStmt):
            self._compile_while(statement)
        elif isinstance(statement, ast.DoStmt):
            self._compile_call(statement.call)
            self.writer.write_pop("temp", 0)
        elif isinstance(statement, ast.ReturnStmt):
            self._compile_return(statement)
        else:  # pragma: no cover - exhaustive guard
            raise TypeError(f"unknown statement {statement!r}")

    def _compile_let(self, statement: ast.LetStmt) -> None:
        symbol = self.symbols.lookup(statement.name)
        if symbol is None:
            raise JackError(
                f"undeclared variable {statement.name!r} in "
                f"{self.class_def.name}.{self._subroutine_name()}"
            )
        segment = _SEGMENT_BY_KIND[symbol.kind]

        if statement.index is None:
            self._compile_expression(statement.value)
            self.writer.write_pop(segment, symbol.index)
            return

        # Official nand2tetris compilers evaluate the index before the array
        # base.  Keeping the same order makes the generated VM easy to compare
        # against the reference compiler.
        self._compile_expression(statement.index)
        self.writer.write_push(segment, symbol.index)
        self.writer.write_arithmetic("add")
        self._compile_expression(statement.value)
        self.writer.write_pop("temp", 0)
        self.writer.write_pop("pointer", 1)
        self.writer.write_push("temp", 0)
        self.writer.write_pop("that", 0)

    def _compile_if(self, statement: ast.IfStmt) -> None:
        label = self._next_if_label()
        true_label = f"IF_TRUE{label}"
        false_label = f"IF_FALSE{label}"

        self._compile_expression(statement.condition)
        self.writer.write_if(true_label)
        self.writer.write_goto(false_label)
        self.writer.write_label(true_label)
        for child in statement.then_body:
            self._compile_statement(child)

        if statement.else_body is not None:
            end_label = f"IF_END{label}"
            self.writer.write_goto(end_label)
            self.writer.write_label(false_label)
            for child in statement.else_body:
                self._compile_statement(child)
            self.writer.write_label(end_label)
        else:
            self.writer.write_label(false_label)

    def _compile_while(self, statement: ast.WhileStmt) -> None:
        label = self._next_while_label()
        exp_label = f"WHILE_EXP{label}"
        end_label = f"WHILE_END{label}"

        self.writer.write_label(exp_label)
        self._compile_expression(statement.condition)
        self.writer.write_arithmetic("not")
        self.writer.write_if(end_label)
        for child in statement.body:
            self._compile_statement(child)
        self.writer.write_goto(exp_label)
        self.writer.write_label(end_label)

    def _compile_return(self, statement: ast.ReturnStmt) -> None:
        if statement.value is not None:
            self._compile_expression(statement.value)
        elif self.current_subroutine is not None and self.current_subroutine.kind == "constructor":
            self.writer.write_push("pointer", 0)
        else:
            self.writer.write_push("constant", 0)
        self.writer.write_return()

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _compile_expression(self, expression: ast.Expr) -> None:
        self._compile_term(expression.first)
        for op, term in expression.rest:
            self._compile_term(term)
            self._compile_binary_op(op)

    def _compile_binary_op(self, op: str) -> None:
        if op == "+":
            self.writer.write_arithmetic("add")
        elif op == "-":
            self.writer.write_arithmetic("sub")
        elif op == "*":
            self.writer.write_call("Math.multiply", 2)
        elif op == "/":
            self.writer.write_call("Math.divide", 2)
        elif op == "&":
            self.writer.write_arithmetic("and")
        elif op == "|":
            self.writer.write_arithmetic("or")
        elif op == "<":
            self.writer.write_arithmetic("lt")
        elif op == ">":
            self.writer.write_arithmetic("gt")
        elif op == "=":
            self.writer.write_arithmetic("eq")
        else:  # pragma: no cover - parser guarantees this
            raise ValueError(f"unknown binary operator {op!r}")

    def _compile_term(self, term: ast.Term) -> None:
        if isinstance(term, ast.IntConst):
            self.writer.write_push("constant", term.value)
        elif isinstance(term, ast.StringConst):
            self._compile_string(term.value)
        elif isinstance(term, ast.KeywordConst):
            if term.value == "true":
                self.writer.write_push("constant", 0)
                self.writer.write_arithmetic("not")
            elif term.value in {"false", "null"}:
                self.writer.write_push("constant", 0)
            elif term.value == "this":
                self.writer.write_push("pointer", 0)
            else:  # pragma: no cover - parser guarantees this
                raise ValueError(f"unknown keyword constant {term.value!r}")
        elif isinstance(term, ast.VarRef):
            self._push_variable(term.name)
        elif isinstance(term, ast.ArrayRef):
            self._compile_expression(term.index)
            self._push_variable(term.name)
            self.writer.write_arithmetic("add")
            self.writer.write_pop("pointer", 1)
            self.writer.write_push("that", 0)
        elif isinstance(term, ast.Call):
            self._compile_call(term)
        elif isinstance(term, ast.ParenTerm):
            self._compile_expression(term.expr)
        elif isinstance(term, ast.UnaryTerm):
            self._compile_term(term.term)
            if term.op == "-":
                self.writer.write_arithmetic("neg")
            else:
                self.writer.write_arithmetic("not")
        else:  # pragma: no cover - exhaustive guard
            raise TypeError(f"unknown term {term!r}")

    def _compile_string(self, value: str) -> None:
        value = _decode_string(value)
        self.writer.write_push("constant", len(value))
        self.writer.write_call("String.new", 1)
        for ch in value:
            code = ord(ch)
            if code > 32767:
                raise JackError(f"character {ch!r} is not representable in a Hack string")
            self.writer.write_push("constant", code)
            self.writer.write_call("String.appendChar", 2)

    # ------------------------------------------------------------------
    # Calls and variables
    # ------------------------------------------------------------------

    def _compile_call(self, call: ast.Call) -> None:
        if call.receiver is None:
            # Bare foo(...) is a method call on the current object.
            self.writer.write_push("pointer", 0)
            for argument in call.args:
                self._compile_expression(argument)
            self.writer.write_call(
                f"{self.class_def.name}.{call.name}", len(call.args) + 1
            )
            return

        symbol = self.symbols.lookup(call.receiver)
        if symbol is not None:
            # obj.method(...) -> push obj, push args, call Class.method n+1.
            self._push_variable(call.receiver)
            for argument in call.args:
                self._compile_expression(argument)
            self.writer.write_call(f"{symbol.type}.{call.name}", len(call.args) + 1)
        else:
            # Class.function(...) (or a constructor call).
            for argument in call.args:
                self._compile_expression(argument)
            self.writer.write_call(f"{call.receiver}.{call.name}", len(call.args))

    def _push_variable(self, name: str) -> None:
        if name == "this":
            self.writer.write_push("pointer", 0)
            return
        symbol = self.symbols.lookup(name)
        if symbol is None:
            raise JackError(
                f"undeclared variable {name!r} in "
                f"{self.class_def.name}.{self._subroutine_name()}"
            )
        self.writer.write_push(_SEGMENT_BY_KIND[symbol.kind], symbol.index)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_if_label(self) -> int:
        label = self.if_counter
        self.if_counter += 1
        return label

    def _next_while_label(self) -> int:
        label = self.while_counter
        self.while_counter += 1
        return label

    def _subroutine_name(self) -> str:
        if self.current_subroutine is None:
            return "?"
        return self.current_subroutine.name
