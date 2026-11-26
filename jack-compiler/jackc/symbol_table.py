"""Symbol table used by the Jack code generator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Symbol:
    type: str
    kind: str  # "static" | "field" | "arg" | "var"
    index: int


class SymbolTable:
    def __init__(self) -> None:
        self.class_symbols: dict[str, Symbol] = {}
        self.subroutine_symbols: dict[str, Symbol] = {}

    def start_subroutine(self) -> None:
        self.subroutine_symbols.clear()

    def define(self, name: str, type_name: str, kind: str) -> None:
        if kind in {"static", "field"}:
            table = self.class_symbols
        elif kind in {"arg", "var"}:
            table = self.subroutine_symbols
        else:
            raise ValueError(f"invalid symbol kind: {kind}")
        if name in table:
            raise ValueError(f"duplicate symbol {name!r} in the same scope")
        index = sum(1 for symbol in table.values() if symbol.kind == kind)
        table[name] = Symbol(type=type_name, kind=kind, index=index)

    def lookup(self, name: str) -> Symbol | None:
        return self.subroutine_symbols.get(name) or self.class_symbols.get(name)

    def count(self, kind: str) -> int:
        return sum(
            1
            for symbol in (*self.class_symbols.values(), *self.subroutine_symbols.values())
            if symbol.kind == kind
        )

    def kind_of(self, name: str) -> str | None:
        symbol = self.lookup(name)
        return symbol.kind if symbol else None

    def type_of(self, name: str) -> str | None:
        symbol = self.lookup(name)
        return symbol.type if symbol else None

    def index_of(self, name: str) -> int | None:
        symbol = self.lookup(name)
        return symbol.index if symbol else None
