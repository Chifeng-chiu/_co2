"""Recursive-descent parser for Jack (nand2tetris project 10).

The parser accepts the full Jack grammar and produces the typed AST in
:mod:`jackc.ast`.  It also records enough information to regenerate the
standard XML representation used by the nand2tetris course.
"""

from __future__ import annotations

from . import ast
from .errors import JackError
from .tokenizer import Token, TokenKind

_BINARY_OPS = frozenset({"+", "-", "*", "/", "&", "|", "<", ">", "="})
_UNARY_OPS = frozenset({"-", "~"})
_STATEMENT_KEYWORDS = frozenset({"let", "if", "while", "do", "return"})
_PRIMITIVE_TYPES = frozenset({"int", "char", "boolean"})
_SUBROUTINE_KINDS = frozenset({"constructor", "function", "method"})


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<input>") -> None:
        self.tokens = tokens
        self.filename = filename
        self.index = 0

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> Token | None:
        index = self.index + offset
        if index >= len(self.tokens):
            return None
        return self.tokens[index]

    def advance(self) -> Token:
        token = self.peek()
        if token is None:
            raise self.error("unexpected end of file")
        self.index += 1
        return token

    def check(self, kind: TokenKind, text: str | None = None, offset: int = 0) -> bool:
        token = self.peek(offset)
        if token is None or token.kind != kind:
            return False
        return text is None or token.text == text

    def check_symbol(self, text: str, offset: int = 0) -> bool:
        return self.check(TokenKind.SYMBOL, text, offset)

    def check_keyword(self, text: str, offset: int = 0) -> bool:
        return self.check(TokenKind.KEYWORD, text, offset)

    def match_symbol(self, text: str) -> bool:
        if self.check_symbol(text):
            self.advance()
            return True
        return False

    def match_keyword(self, text: str) -> bool:
        if self.check_keyword(text):
            self.advance()
            return True
        return False

    def error(self, message: str, token: Token | None = None) -> JackError:
        if token is None:
            token = self.peek()
        if token is None:
            return JackError(message, filename=self.filename)
        return JackError(message, filename=self.filename, line=token.line, column=token.column)

    def _describe(self, token: Token | None) -> str:
        if token is None:
            return "end of file"
        return f"{token.kind.value} {token.text!r}"

    def expect(self, kind: TokenKind, text: str | None = None) -> Token:
        token = self.peek()
        if token is None:
            expected = text if text is not None else kind.value
            raise self.error(f"expected {expected!r} but reached end of file")
        if token.kind != kind or (text is not None and token.text != text):
            expected = text if text is not None else kind.value
            raise self.error(f"expected {expected!r} but found {self._describe(token)}", token)
        self.index += 1
        return token

    def expect_symbol(self, text: str) -> Token:
        return self.expect(TokenKind.SYMBOL, text)

    def expect_keyword(self, text: str) -> Token:
        return self.expect(TokenKind.KEYWORD, text)

    def expect_identifier(self) -> Token:
        return self.expect(TokenKind.IDENTIFIER)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def parse(self) -> ast.ClassDef:
        class_def = self.parse_class()
        if self.peek() is not None:
            token = self.peek()
            raise self.error(f"unexpected token after class definition: {self._describe(token)}", token)
        return class_def

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def parse_class(self) -> ast.ClassDef:
        self.expect_keyword("class")
        name = self.expect_identifier().text
        self.expect_symbol("{")

        class_vars: list[ast.VarDec] = []
        while self.check_keyword("static") or self.check_keyword("field"):
            class_vars.append(self.parse_class_var_dec())

        subroutines: list[ast.SubroutineDef] = []
        while self.peek() is not None and self.peek().kind == TokenKind.KEYWORD:
            token = self.peek()
            assert token is not None
            if token.text not in _SUBROUTINE_KINDS:
                break
            subroutines.append(self.parse_subroutine())

        self.expect_symbol("}")
        return ast.ClassDef(name=name, class_vars=class_vars, subroutines=subroutines)

    def parse_class_var_dec(self) -> ast.VarDec:
        token = self.peek()
        assert token is not None
        kind = token.text
        self.advance()
        type_name = self.parse_type()
        names = [self.expect_identifier().text]
        while self.match_symbol(","):
            names.append(self.expect_identifier().text)
        self.expect_symbol(";")
        return ast.VarDec(kind=kind, type=type_name, names=names)

    def parse_subroutine(self) -> ast.SubroutineDef:
        kind_token = self.peek()
        assert kind_token is not None
        kind = kind_token.text
        self.advance()

        if self.check_keyword("void"):
            return_type = self.advance().text
        else:
            return_type = self.parse_type()

        name = self.expect_identifier().text
        self.expect_symbol("(")
        params = self.parse_parameter_list()
        self.expect_symbol(")")
        vars_, body = self.parse_subroutine_body()
        return ast.SubroutineDef(
            kind=kind,
            return_type=return_type,
            name=name,
            params=params,
            vars=vars_,
            body=body,
        )

    def parse_parameter_list(self) -> list[ast.Parameter]:
        params: list[ast.Parameter] = []
        if self.check_symbol(")"):
            return params
        while True:
            type_name = self.parse_type()
            name = self.expect_identifier().text
            params.append(ast.Parameter(type=type_name, name=name))
            if not self.match_symbol(","):
                break
        return params

    def parse_subroutine_body(self) -> tuple[list[ast.VarDec], list[ast.Stmt]]:
        self.expect_symbol("{")
        vars_: list[ast.VarDec] = []
        while self.check_keyword("var"):
            self.advance()
            type_name = self.parse_type()
            names = [self.expect_identifier().text]
            while self.match_symbol(","):
                names.append(self.expect_identifier().text)
            self.expect_symbol(";")
            vars_.append(ast.VarDec(kind="var", type=type_name, names=names))
        body = self.parse_statements()
        self.expect_symbol("}")
        return vars_, body

    def parse_type(self) -> str:
        token = self.peek()
        if token is None:
            raise self.error("expected a type but reached end of file")
        if token.kind == TokenKind.IDENTIFIER:
            self.advance()
            return token.text
        if token.kind == TokenKind.KEYWORD and token.text in _PRIMITIVE_TYPES:
            self.advance()
            return token.text
        raise self.error(f"expected a type but found {self._describe(token)}", token)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def parse_statements(self) -> list[ast.Stmt]:
        statements: list[ast.Stmt] = []
        while True:
            token = self.peek()
            if token is None:
                break
            if token.kind != TokenKind.KEYWORD or token.text not in _STATEMENT_KEYWORDS:
                break
            if token.text == "let":
                statements.append(self.parse_let())
            elif token.text == "if":
                statements.append(self.parse_if())
            elif token.text == "while":
                statements.append(self.parse_while())
            elif token.text == "do":
                statements.append(self.parse_do())
            else:  # return
                statements.append(self.parse_return())
        return statements

    def parse_let(self) -> ast.LetStmt:
        self.expect_keyword("let")
        name = self.expect_identifier().text
        index: ast.Expr | None = None
        if self.match_symbol("["):
            index = self.parse_expression()
            self.expect_symbol("]")
        self.expect_symbol("=")
        value = self.parse_expression()
        self.expect_symbol(";")
        return ast.LetStmt(name=name, index=index, value=value)

    def parse_if(self) -> ast.IfStmt:
        self.expect_keyword("if")
        self.expect_symbol("(")
        condition = self.parse_expression()
        self.expect_symbol(")")
        self.expect_symbol("{")
        then_body = self.parse_statements()
        self.expect_symbol("}")
        else_body: list[ast.Stmt] | None = None
        if self.match_keyword("else"):
            self.expect_symbol("{")
            else_body = self.parse_statements()
            self.expect_symbol("}")
        return ast.IfStmt(condition=condition, then_body=then_body, else_body=else_body)

    def parse_while(self) -> ast.WhileStmt:
        self.expect_keyword("while")
        self.expect_symbol("(")
        condition = self.parse_expression()
        self.expect_symbol(")")
        self.expect_symbol("{")
        body = self.parse_statements()
        self.expect_symbol("}")
        return ast.WhileStmt(condition=condition, body=body)

    def parse_do(self) -> ast.DoStmt:
        self.expect_keyword("do")
        call = self.parse_subroutine_call()
        self.expect_symbol(";")
        return ast.DoStmt(call=call)

    def parse_return(self) -> ast.ReturnStmt:
        self.expect_keyword("return")
        value: ast.Expr | None = None
        if not self.check_symbol(";"):
            value = self.parse_expression()
        self.expect_symbol(";")
        return ast.ReturnStmt(value=value)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def parse_expression(self) -> ast.Expr:
        first = self.parse_term()
        rest: list[tuple[str, ast.Term]] = []
        while True:
            token = self.peek()
            if token is None or token.kind != TokenKind.SYMBOL or token.text not in _BINARY_OPS:
                break
            op = self.advance().text
            rest.append((op, self.parse_term()))
        return ast.Expr(first=first, rest=rest)

    def parse_term(self) -> ast.Term:
        token = self.peek()
        if token is None:
            raise self.error("expected an expression term but reached end of file")

        if token.kind == TokenKind.INTEGER_CONSTANT:
            self.advance()
            return ast.IntConst(value=int(token.text))

        if token.kind == TokenKind.STRING_CONSTANT:
            self.advance()
            return ast.StringConst(value=token.text)

        if token.kind == TokenKind.KEYWORD:
            if token.text in {"true", "false", "null", "this"}:
                self.advance()
                return ast.KeywordConst(value=token.text)
            raise self.error(f"unexpected keyword {token.text!r} in expression", token)

        if token.kind == TokenKind.IDENTIFIER:
            self.advance()
            if self.check_symbol("("):
                return self.finish_call(token, receiver=None)
            if self.check_symbol("."):
                self.advance()
                method = self.expect_identifier().text
                self.expect_symbol("(")
                args = self.parse_expression_list()
                self.expect_symbol(")")
                return ast.Call(receiver=token.text, name=method, args=args)
            if self.match_symbol("["):
                index = self.parse_expression()
                self.expect_symbol("]")
                return ast.ArrayRef(name=token.text, index=index)
            return ast.VarRef(name=token.text)

        if token.kind == TokenKind.SYMBOL and token.text == "(":
            self.advance()
            expression = self.parse_expression()
            self.expect_symbol(")")
            return ast.ParenTerm(expr=expression)

        if token.kind == TokenKind.SYMBOL and token.text in _UNARY_OPS:
            self.advance()
            return ast.UnaryTerm(op=token.text, term=self.parse_term())

        raise self.error(f"expected an expression term but found {self._describe(token)}", token)

    def parse_subroutine_call(self) -> ast.Call:
        first = self.expect_identifier()
        if self.match_symbol("."):
            method = self.expect_identifier().text
            self.expect_symbol("(")
            args = self.parse_expression_list()
            self.expect_symbol(")")
            return ast.Call(receiver=first.text, name=method, args=args)
        return self.finish_call(first, receiver=None)

    def finish_call(self, name_token: Token, receiver: str | None) -> ast.Call:
        self.expect_symbol("(")
        args = self.parse_expression_list()
        self.expect_symbol(")")
        return ast.Call(receiver=receiver, name=name_token.text, args=args)

    def parse_expression_list(self) -> list[ast.Expr]:
        expressions: list[ast.Expr] = []
        if self.check_symbol(")"):
            return expressions
        while True:
            expressions.append(self.parse_expression())
            if not self.match_symbol(","):
                break
        return expressions
