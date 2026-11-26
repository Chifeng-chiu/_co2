from __future__ import annotations

import unittest

from tests.vm_runtime import VMRuntime
from jackc.compiler import Compiler
from jackc.parser import Parser
from jackc.tokenizer import tokenize


def compile_source(source: str) -> str:
    return Compiler(Parser(tokenize(source)).parse()).compile()


class RuntimeSmokeTests(unittest.TestCase):
    def test_while_loop_and_static_variable(self) -> None:
        vm = compile_source(
            """
            class Main {
                static int result;
                function void main() {
                    var int i, sum;
                    let i = 1;
                    let sum = 0;
                    while (i < 11) {
                        let sum = sum + i;
                        let i = i + 1;
                    }
                    let result = sum;
                    return;
                }
            }
            """
        )
        runtime = VMRuntime(vm)
        runtime.run()
        self.assertEqual(runtime.static[0], 55)

    def test_function_call_and_arguments(self) -> None:
        vm = compile_source(
            """
            class Main {
                static int result;
                function int add(int a, int b) {
                    return a + b;
                }
                function void main() {
                    let result = Main.add(20, 22);
                    return;
                }
            }
            """
        )
        runtime = VMRuntime(vm)
        runtime.run()
        self.assertEqual(runtime.static[0], 42)

    def test_if_else(self) -> None:
        vm = compile_source(
            """
            class Main {
                static int result;
                function void main() {
                    var int x;
                    let x = 5;
                    if (x > 3) { let result = 1; }
                    else { let result = 2; }
                    return;
                }
            }
            """
        )
        runtime = VMRuntime(vm)
        runtime.run()
        self.assertEqual(runtime.static[0], 1)

    def test_left_to_right_evaluation(self) -> None:
        # Jack has no operator precedence: 2 + 3 * 4 == (2 + 3) * 4 == 20.
        vm = compile_source(
            """
            class Main {
                static int result;
                function void main() {
                    let result = 2 + 3 * 4;
                    return;
                }
            }
            """
        )
        runtime = VMRuntime(vm)
        runtime.run()
        self.assertEqual(runtime.static[0], 20)

    def test_parentheses(self) -> None:
        vm = compile_source(
            """
            class Main {
                static int result;
                function void main() {
                    let result = 2 + (3 * 4);
                    return;
                }
            }
            """
        )
        runtime = VMRuntime(vm)
        runtime.run()
        self.assertEqual(runtime.static[0], 14)


if __name__ == "__main__":
    unittest.main()
