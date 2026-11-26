"""A tiny writer for Hack VM commands."""

from __future__ import annotations


class VMWriter:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_push(self, segment: str, index: int) -> None:
        self.lines.append(f"push {segment} {index}")

    def write_pop(self, segment: str, index: int) -> None:
        self.lines.append(f"pop {segment} {index}")

    def write_arithmetic(self, command: str) -> None:
        self.lines.append(command)

    def write_label(self, label: str) -> None:
        self.lines.append(f"label {label}")

    def write_goto(self, label: str) -> None:
        self.lines.append(f"goto {label}")

    def write_if(self, label: str) -> None:
        self.lines.append(f"if-goto {label}")

    def write_function(self, name: str, n_locals: int) -> None:
        self.lines.append(f"function {name} {n_locals}")

    def write_call(self, name: str, n_args: int) -> None:
        self.lines.append(f"call {name} {n_args}")

    def write_return(self) -> None:
        self.lines.append("return")

    def text(self) -> str:
        if not self.lines:
            return ""
        return "\n".join(self.lines) + "\n"
