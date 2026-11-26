"""A tiny Hack VM interpreter used by the runtime smoke tests.

It implements the subset of the VM specification needed by self-contained
Jack programs: the arithmetic/logic commands, memory segments, labels, and
function call/return.  It deliberately does not implement the Hack OS, so the
test programs avoid calls such as ``Output.printInt`` or ``Memory.alloc``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class VMError(RuntimeError):
    pass


@dataclass
class _Function:
    name: str
    n_locals: int
    instructions: list[tuple[str, ...]] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)


@dataclass
class _Frame:
    function: _Function
    args: list[int]
    locals: list[int]
    return_pc: int = 0


class VMRuntime:
    def __init__(self, source: str) -> None:
        self.functions: dict[str, _Function] = {}
        self.static = [0] * 240
        self.temp = [0] * 8
        self.pointer = [0, 0]
        self.ram: dict[int, int] = {}
        self.stack: list[int] = []
        self.frames: list[_Frame] = []
        self.builtins = {
            "Math.multiply": lambda a, b: a * b,
            "Math.divide": self._divide,
            "Math.abs": lambda a: abs(a),
            "Math.max": lambda a, b: max(a, b),
            "Math.min": lambda a, b: min(a, b),
        }
        self._parse(source)

    @staticmethod
    def _divide(a: int, b: int) -> int:
        if b == 0:
            raise VMError("division by zero")
        quotient = abs(a) // abs(b)
        return quotient if (a < 0) == (b < 0) else -quotient

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse(self, source: str) -> None:
        current: _Function | None = None
        for raw_line in source.splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line:
                continue
            parts = tuple(line.split())
            command = parts[0]

            if command == "function":
                if len(parts) != 3:
                    raise VMError(f"bad function command: {line}")
                current = _Function(parts[1], int(parts[2]))
                self.functions[current.name] = current
                continue

            if current is None:
                raise VMError(f"instruction before function: {line}")

            if command == "label":
                current.labels[parts[1]] = len(current.instructions)
            current.instructions.append(parts)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, entry: str = "Main.main", max_steps: int = 1_000_000) -> None:
        if entry not in self.functions:
            raise VMError(f"entry function {entry!r} not found")
        function = self.functions[entry]
        self.frames.append(_Frame(function=function, args=[], locals=[0] * function.n_locals))
        pc = 0
        steps = 0

        while self.frames:
            steps += 1
            if steps > max_steps:
                raise VMError("step limit exceeded (possible infinite loop)")

            frame = self.frames[-1]
            instructions = frame.function.instructions
            if pc >= len(instructions):
                raise VMError(f"fell off the end of {frame.function.name}")

            instruction = instructions[pc]
            pc += 1
            command = instruction[0]

            if command == "push":
                self.stack.append(self._read_segment(instruction[1], int(instruction[2])))
            elif command == "pop":
                self._write_segment(instruction[1], int(instruction[2]), self._pop())
            elif command in {"add", "sub", "and", "or"}:
                y = self._pop()
                x = self._pop()
                if command == "add":
                    self.stack.append(x + y)
                elif command == "sub":
                    self.stack.append(x - y)
                elif command == "and":
                    self.stack.append(x & y)
                else:
                    self.stack.append(x | y)
            elif command == "neg":
                self.stack.append(-self._pop())
            elif command == "not":
                self.stack.append(~self._pop())
            elif command in {"eq", "gt", "lt"}:
                y = self._pop()
                x = self._pop()
                if command == "eq":
                    result = x == y
                elif command == "gt":
                    result = x > y
                else:
                    result = x < y
                self.stack.append(-1 if result else 0)
            elif command == "label":
                pass
            elif command == "goto":
                pc = self._label_pc(frame, instruction[1])
            elif command == "if-goto":
                if self._pop() != 0:
                    pc = self._label_pc(frame, instruction[1])
            elif command == "call":
                name = instruction[1]
                n_args = int(instruction[2])
                args = [self._pop() for _ in range(n_args)][::-1]
                builtin = self.builtins.get(name)
                if builtin is not None:
                    self.stack.append(builtin(*args))
                    continue
                callee = self.functions.get(name)
                if callee is None:
                    raise VMError(f"call to unavailable function {name!r} (OS call?)")
                frame.return_pc = pc
                self.frames.append(
                    _Frame(function=callee, args=args, locals=[0] * callee.n_locals)
                )
                pc = 0
            elif command == "return":
                value = self._pop()
                self.frames.pop()
                if not self.frames:
                    self.stack.append(value)
                    break
                pc = self.frames[-1].return_pc
                self.stack.append(value)
            else:
                raise VMError(f"unsupported VM command: {command}")

    def _label_pc(self, frame: _Frame, label: str) -> int:
        try:
            return frame.function.labels[label]
        except KeyError as error:
            raise VMError(f"unknown label {label!r} in {frame.function.name}") from error

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def _read_segment(self, segment: str, index: int) -> int:
        frame = self.frames[-1]
        if segment == "constant":
            return index
        if segment == "local":
            return frame.locals[index]
        if segment == "argument":
            return frame.args[index]
        if segment == "static":
            return self.static[index]
        if segment == "temp":
            return self.temp[index]
        if segment == "pointer":
            return self.pointer[index]
        if segment == "this":
            return self.ram.get(self.pointer[0] + index, 0)
        if segment == "that":
            return self.ram.get(self.pointer[1] + index, 0)
        raise VMError(f"unknown segment {segment!r}")

    def _write_segment(self, segment: str, index: int, value: int) -> None:
        frame = self.frames[-1]
        if segment == "local":
            frame.locals[index] = value
        elif segment == "argument":
            frame.args[index] = value
        elif segment == "static":
            self.static[index] = value
        elif segment == "temp":
            self.temp[index] = value
        elif segment == "pointer":
            self.pointer[index] = value
        elif segment == "this":
            self.ram[self.pointer[0] + index] = value
        elif segment == "that":
            self.ram[self.pointer[1] + index] = value
        else:
            raise VMError(f"cannot pop into segment {segment!r}")

    def _pop(self) -> int:
        if not self.stack:
            raise VMError("stack underflow")
        return self.stack.pop()
