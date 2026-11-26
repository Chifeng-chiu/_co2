"""XML serializers for the two project 10 output formats.

``class_to_xml`` emits the parse-tree XML (``Foo.xml``); ``tokens_to_xml``
emits the flat token XML (``FooT.xml``).  The formatting follows the standard
nand2tetris reference output: two-space indentation for the parse tree, one
token per line for the token stream, and a space on each side of a token's
text.
"""

from __future__ import annotations

from . import ast
from .tokenizer import Token, TokenKind

_INDENT = "  "


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class _XmlBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.level = 0

    def open(self, tag: str) -> None:
        self.lines.append(_INDENT * self.level + f"<{tag}>")
        self.level += 1

    def close(self, tag: str) -> None:
        self.level -= 1
        self.lines.append(_INDENT * self.level + f"</{tag}>")

    def token(self, kind: TokenKind | str, text: str) -> None:
        kind_text = kind.value if isinstance(kind, TokenKind) else kind
        self.lines.append(
            _INDENT * self.level + f"<{kind_text}> {xml_escape(text)} </{kind_text}>"
        )

    def result(self) -> str:
        return "\n".join(self.lines) + "\n"


def _type_token_kind(type_name: str) -> TokenKind:
    if type_name in {"int", "char", "boolean", "void"}:
        return TokenKind.KEYWORD
    return TokenKind.IDENTIFIER


def tokens_to_xml(tokens: list[Token]) -> str:
    lines = ["<tokens>"]
    for token in tokens:
        lines.append(f"<{token.kind.value}> {xml_escape(token.text)} </{token.kind.value}>")
    lines.append("</tokens>")
    return "\n".join(lines) + "\n"


def class_to_xml(class_def: ast.ClassDef) -> str:
    builder = _XmlBuilder()
    _class(builder, class_def)
    return builder.result()


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------


def _class(builder: _XmlBuilder, class_def: ast.ClassDef) -> None:
    builder.open("class")
    builder.token(TokenKind.KEYWORD, "class")
    builder.token(TokenKind.IDENTIFIER, class_def.name)
    builder.token(TokenKind.SYMBOL, "{")
    for var_dec in class_def.class_vars:
        _var_dec(builder, var_dec, "classVarDec")
    for subroutine in class_def.subroutines:
        _subroutine(builder, subroutine)
    builder.token(TokenKind.SYMBOL, "}")
    builder.close("class")


def _var_dec(builder: _XmlBuilder, var_dec: ast.VarDec, tag: str) -> None:
    builder.open(tag)
    builder.token(TokenKind.KEYWORD, var_dec.kind)
    builder.token(_type_token_kind(var_dec.type), var_dec.type)
    for index, name in enumerate(var_dec.names):
        if index:
            builder.token(TokenKind.SYMBOL, ",")
        builder.token(TokenKind.IDENTIFIER, name)
    builder.token(TokenKind.SYMBOL, ";")
    builder.close(tag)


def _subroutine(builder: _XmlBuilder, subroutine: ast.SubroutineDef) -> None:
    builder.open("subroutineDec")
    builder.token(TokenKind.KEYWORD, subroutine.kind)
    builder.token(_type_token_kind(subroutine.return_type), subroutine.return_type)
    builder.token(TokenKind.IDENTIFIER, subroutine.name)
    builder.token(TokenKind.SYMBOL, "(")
    _parameter_list(builder, subroutine.params)
    builder.token(TokenKind.SYMBOL, ")")
    _subroutine_body(builder, subroutine)
    builder.close("subroutineDec")


def _parameter_list(builder: _XmlBuilder, params: list[ast.Parameter]) -> None:
    builder.open("parameterList")
    for index, param in enumerate(params):
        if index:
            builder.token(TokenKind.SYMBOL, ",")
        builder.token(_type_token_kind(param.type), param.type)
        builder.token(TokenKind.IDENTIFIER, param.name)
    builder.close("parameterList")


def _subroutine_body(builder: _XmlBuilder, subroutine: ast.SubroutineDef) -> None:
    builder.open("subroutineBody")
    builder.token(TokenKind.SYMBOL, "{")
    for var_dec in subroutine.vars:
        _var_dec(builder, var_dec, "varDec")
    _statements(builder, subroutine.body)
    builder.token(TokenKind.SYMBOL, "}")
    builder.close("subroutineBody")


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


def _statements(builder: _XmlBuilder, statements: list[ast.Stmt]) -> None:
    builder.open("statements")
    for statement in statements:
        if isinstance(statement, ast.LetStmt):
            _let(builder, statement)
        elif isinstance(statement, ast.IfStmt):
            _if(builder, statement)
        elif isinstance(statement, ast.WhileStmt):
            _while(builder, statement)
        elif isinstance(statement, ast.DoStmt):
            _do(builder, statement)
        elif isinstance(statement, ast.ReturnStmt):
            _return(builder, statement)
        else:  # pragma: no cover - exhaustive guard
            raise TypeError(f"unknown statement {statement!r}")
    builder.close("statements")


def _let(builder: _XmlBuilder, statement: ast.LetStmt) -> None:
    builder.open("letStatement")
    builder.token(TokenKind.KEYWORD, "let")
    builder.token(TokenKind.IDENTIFIER, statement.name)
    if statement.index is not None:
        builder.token(TokenKind.SYMBOL, "[")
        _expression(builder, statement.index)
        builder.token(TokenKind.SYMBOL, "]")
    builder.token(TokenKind.SYMBOL, "=")
    _expression(builder, statement.value)
    builder.token(TokenKind.SYMBOL, ";")
    builder.close("letStatement")


def _if(builder: _XmlBuilder, statement: ast.IfStmt) -> None:
    builder.open("ifStatement")
    builder.token(TokenKind.KEYWORD, "if")
    builder.token(TokenKind.SYMBOL, "(")
    _expression(builder, statement.condition)
    builder.token(TokenKind.SYMBOL, ")")
    builder.token(TokenKind.SYMBOL, "{")
    _statements(builder, statement.then_body)
    builder.token(TokenKind.SYMBOL, "}")
    if statement.else_body is not None:
        builder.token(TokenKind.KEYWORD, "else")
        builder.token(TokenKind.SYMBOL, "{")
        _statements(builder, statement.else_body)
        builder.token(TokenKind.SYMBOL, "}")
    builder.close("ifStatement")


def _while(builder: _XmlBuilder, statement: ast.WhileStmt) -> None:
    builder.open("whileStatement")
    builder.token(TokenKind.KEYWORD, "while")
    builder.token(TokenKind.SYMBOL, "(")
    _expression(builder, statement.condition)
    builder.token(TokenKind.SYMBOL, ")")
    builder.token(TokenKind.SYMBOL, "{")
    _statements(builder, statement.body)
    builder.token(TokenKind.SYMBOL, "}")
    builder.close("whileStatement")


def _do(builder: _XmlBuilder, statement: ast.DoStmt) -> None:
    builder.open("doStatement")
    builder.token(TokenKind.KEYWORD, "do")
    _call(builder, statement.call)
    builder.token(TokenKind.SYMBOL, ";")
    builder.close("doStatement")


def _return(builder: _XmlBuilder, statement: ast.ReturnStmt) -> None:
    builder.open("returnStatement")
    builder.token(TokenKind.KEYWORD, "return")
    if statement.value is not None:
        _expression(builder, statement.value)
    builder.token(TokenKind.SYMBOL, ";")
    builder.close("returnStatement")


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


def _expression(builder: _XmlBuilder, expression: ast.Expr) -> None:
    builder.open("expression")
    _term(builder, expression.first)
    for op, term in expression.rest:
        builder.token(TokenKind.SYMBOL, op)
        _term(builder, term)
    builder.close("expression")


def _term(builder: _XmlBuilder, term: ast.Term) -> None:
    builder.open("term")
    if isinstance(term, ast.IntConst):
        builder.token(TokenKind.INTEGER_CONSTANT, str(term.value))
    elif isinstance(term, ast.StringConst):
        builder.token(TokenKind.STRING_CONSTANT, term.value)
    elif isinstance(term, ast.KeywordConst):
        builder.token(TokenKind.KEYWORD, term.value)
    elif isinstance(term, ast.VarRef):
        builder.token(TokenKind.IDENTIFIER, term.name)
    elif isinstance(term, ast.ArrayRef):
        builder.token(TokenKind.IDENTIFIER, term.name)
        builder.token(TokenKind.SYMBOL, "[")
        _expression(builder, term.index)
        builder.token(TokenKind.SYMBOL, "]")
    elif isinstance(term, ast.Call):
        _call(builder, term)
    elif isinstance(term, ast.ParenTerm):
        builder.token(TokenKind.SYMBOL, "(")
        _expression(builder, term.expr)
        builder.token(TokenKind.SYMBOL, ")")
    elif isinstance(term, ast.UnaryTerm):
        builder.token(TokenKind.SYMBOL, term.op)
        _term(builder, term.term)
    else:  # pragma: no cover - exhaustive guard
        raise TypeError(f"unknown term {term!r}")
    builder.close("term")


def _call(builder: _XmlBuilder, call: ast.Call) -> None:
    if call.receiver is not None:
        builder.token(TokenKind.IDENTIFIER, call.receiver)
        builder.token(TokenKind.SYMBOL, ".")
    builder.token(TokenKind.IDENTIFIER, call.name)
    builder.token(TokenKind.SYMBOL, "(")
    _expression_list(builder, call.args)
    builder.token(TokenKind.SYMBOL, ")")


def _expression_list(builder: _XmlBuilder, expressions: list[ast.Expr]) -> None:
    builder.open("expressionList")
    for index, expression in enumerate(expressions):
        if index:
            builder.token(TokenKind.SYMBOL, ",")
        _expression(builder, expression)
    builder.close("expressionList")
