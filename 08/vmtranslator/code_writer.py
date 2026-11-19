"""Code writer that translates VM commands into Hack assembly."""

import os


class CodeWriter:
    """Translate parsed VM commands and write them to an .asm file."""

    _SEGMENT_POINTERS = {
        "local": "LCL",
        "argument": "ARG",
        "this": "THIS",
        "that": "THAT",
    }

    def __init__(self, output_file_name):
        self._output = open(output_file_name, "w", encoding="utf-8", newline="\n")
        self._file_name = "Unknown"
        self._current_function = ""
        self._comparison_counter = 0
        self._return_label_counters = {}

    def close(self):
        """Close the generated assembly file."""
        if not self._output.closed:
            self._output.close()

    def set_file_name(self, file_name):
        """Set the current VM file name, used for static variables.

        The argument may include a directory or a .vm extension; only the
        basename without the extension is used in static symbols.
        """
        base_name = os.path.basename(file_name)
        self._file_name = os.path.splitext(base_name)[0]
        # A new source file starts outside any VM function.
        self._current_function = ""

    def write_init(self):
        """Write the bootstrap code that calls Sys.init."""
        self._write("// bootstrap")
        self._write(
            "@256",
            "D=A",
            "@SP",
            "M=D",
        )
        self.write_call("Sys.init", 0)

    def write_arithmetic(self, command):
        """Translate an arithmetic or logical command."""
        self._write("// " + command)

        if command in ("add", "sub", "and", "or"):
            self._write(
                "@SP",
                "AM=M-1",
                "D=M",
                "A=A-1",
            )
            if command == "add":
                self._write("M=D+M")
            elif command == "sub":
                self._write("M=M-D")
            elif command == "and":
                self._write("M=D&M")
            else:  # or
                self._write("M=D|M")
            return

        if command in ("neg", "not"):
            self._write(
                "@SP",
                "A=M-1",
            )
            self._write("M=-M" if command == "neg" else "M=!M")
            return

        if command in ("eq", "gt", "lt"):
            self._comparison_counter += 1
            true_label = "COMP_TRUE_{}".format(self._comparison_counter)
            end_label = "COMP_END_{}".format(self._comparison_counter)

            self._write(
                "@SP",
                "AM=M-1",
                "D=M",
                "A=A-1",
                "D=M-D",
                "@" + true_label,
            )
            if command == "eq":
                self._write("D;JEQ")
            elif command == "gt":
                self._write("D;JGT")
            else:  # lt
                self._write("D;JLT")

            self._write(
                "@SP",
                "A=M-1",
                "M=0",
                "@" + end_label,
                "0;JMP",
                "(" + true_label + ")",
                "@SP",
                "A=M-1",
                "M=-1",
                "(" + end_label + ")",
            )
            return

        raise ValueError("Unknown arithmetic command: {!r}".format(command))

    def write_push_pop(self, command, segment, index):
        """Translate a push or pop command."""
        self._write("// {} {} {}".format(command, segment, index))

        if command == "push":
            self._write_push(segment, index)
        elif command == "pop":
            self._write_pop(segment, index)
        else:
            raise ValueError("Unknown stack command: {!r}".format(command))

    def _write_push(self, segment, index):
        if segment == "constant":
            self._write(
                "@" + str(index),
                "D=A",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )
            return

        if segment in self._SEGMENT_POINTERS:
            base = self._SEGMENT_POINTERS[segment]
            self._write(
                "@" + str(index),
                "D=A",
                "@" + base,
                "A=D+M",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )
            return

        if segment == "temp":
            self._check_temp_index(index)
            self._write(
                "@" + str(5 + index),
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )
            return

        if segment == "pointer":
            pointer = self._pointer_register(index)
            self._write(
                "@" + pointer,
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )
            return

        if segment == "static":
            self._write(
                "@" + self._static_symbol(index),
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )
            return

        raise ValueError("Unknown memory segment: {!r}".format(segment))

    def _write_pop(self, segment, index):
        if segment == "constant":
            raise ValueError("pop constant is not a valid VM command.")

        if segment in self._SEGMENT_POINTERS:
            base = self._SEGMENT_POINTERS[segment]
            self._write(
                "@" + str(index),
                "D=A",
                "@" + base,
                "D=D+M",
                "@R13",
                "M=D",
                "@SP",
                "AM=M-1",
                "D=M",
                "@R13",
                "A=M",
                "M=D",
            )
            return

        if segment == "temp":
            self._check_temp_index(index)
            self._write(
                "@SP",
                "AM=M-1",
                "D=M",
                "@" + str(5 + index),
                "M=D",
            )
            return

        if segment == "pointer":
            pointer = self._pointer_register(index)
            self._write(
                "@SP",
                "AM=M-1",
                "D=M",
                "@" + pointer,
                "M=D",
            )
            return

        if segment == "static":
            self._write(
                "@SP",
                "AM=M-1",
                "D=M",
                "@" + self._static_symbol(index),
                "M=D",
            )
            return

        raise ValueError("Unknown memory segment: {!r}".format(segment))

    def write_label(self, label):
        """Translate a label command."""
        self._write("// label " + label)
        self._write("(" + self._scoped_label(label) + ")")

    def write_goto(self, label):
        """Translate a goto command."""
        self._write("// goto " + label)
        self._write(
            "@" + self._scoped_label(label),
            "0;JMP",
        )

    def write_if(self, label):
        """Translate an if-goto command."""
        self._write("// if-goto " + label)
        self._write(
            "@SP",
            "AM=M-1",
            "D=M",
            "@" + self._scoped_label(label),
            "D;JNE",
        )

    def write_function(self, function_name, n_vars):
        """Translate a function declaration and initialize its locals."""
        self._write("// function {} {}".format(function_name, n_vars))
        self._current_function = function_name
        self._return_label_counters.setdefault(function_name, 0)

        self._write("(" + function_name + ")")
        for _ in range(n_vars):
            self._write(
                "@SP",
                "A=M",
                "M=0",
                "@SP",
                "M=M+1",
            )

    def write_call(self, function_name, n_args):
        """Translate a function call."""
        self._write("// call {} {}".format(function_name, n_args))
        return_label = self._new_return_label()

        # Push the return address.
        self._write(
            "@" + return_label,
            "D=A",
            "@SP",
            "A=M",
            "M=D",
            "@SP",
            "M=M+1",
        )

        # Save the caller's LCL, ARG, THIS and THAT.
        for register in ("LCL", "ARG", "THIS", "THAT"):
            self._write(
                "@" + register,
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            )

        # ARG = SP - 5 - nArgs; LCL = SP.
        self._write(
            "@SP",
            "D=M",
            "@5",
            "D=D-A",
            "@" + str(n_args),
            "D=D-A",
            "@ARG",
            "M=D",
            "@SP",
            "D=M",
            "@LCL",
            "M=D",
        )

        # Transfer control to the callee.
        self._write(
            "@" + function_name,
            "0;JMP",
            "(" + return_label + ")",
        )

    def write_return(self):
        """Translate a return command."""
        self._write("// return")

        # R13 = endFrame = LCL.
        self._write(
            "@LCL",
            "D=M",
            "@R13",
            "M=D",
        )

        # R14 = return address = *(endFrame - 5).
        # It must be saved before overwriting the caller's ARG[0].
        self._write(
            "@5",
            "A=D-A",
            "D=M",
            "@R14",
            "M=D",
        )

        # *ARG = pop().
        self._write(
            "@SP",
            "AM=M-1",
            "D=M",
            "@ARG",
            "A=M",
            "M=D",
        )

        # SP = ARG + 1.
        self._write(
            "@ARG",
            "D=M",
            "@SP",
            "M=D+1",
        )

        # Restore THAT, THIS, ARG and LCL from the saved frame.
        for offset, register in ((1, "THAT"), (2, "THIS"), (3, "ARG"), (4, "LCL")):
            self._write(
                "@R13",
                "D=M",
                "@" + str(offset),
                "A=D-A",
                "D=M",
                "@" + register,
                "M=D",
            )

        # Jump to the saved return address.
        self._write(
            "@R14",
            "A=M",
            "0;JMP",
        )

    def _scoped_label(self, label):
        if self._current_function:
            return "{}${}".format(self._current_function, label)
        return label

    def _new_return_label(self):
        base = self._current_function or "GLOBAL"
        index = self._return_label_counters.get(base, 0)
        self._return_label_counters[base] = index + 1
        return "{}${}.{}".format(base, "ret", index)

    def _static_symbol(self, index):
        return "{}.{}".format(self._file_name, index)

    @staticmethod
    def _check_temp_index(index):
        if not 0 <= index <= 7:
            raise ValueError("temp index must be between 0 and 7.")

    @staticmethod
    def _pointer_register(index):
        if index == 0:
            return "THIS"
        if index == 1:
            return "THAT"
        raise ValueError("pointer index must be 0 or 1.")

    def _write(self, *lines):
        for line in lines:
            self._output.write(line + "\n")
