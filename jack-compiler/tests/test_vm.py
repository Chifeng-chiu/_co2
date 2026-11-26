from __future__ import annotations

import unittest

from tests.helpers import compile_file, golden_vm_cases, project_dir, read_source
from jackc.compiler import Compiler
from jackc.parser import Parser
from jackc.tokenizer import tokenize


class GoldenVmTests(unittest.TestCase):
    def test_golden_cases_exist(self) -> None:
        self.assertGreaterEqual(len(golden_vm_cases()), 35)

    def test_vm_output_matches_official_compiler(self) -> None:
        for source, expected_path in golden_vm_cases():
            with self.subTest(source=str(source)):
                expected = read_source(expected_path)
                actual = compile_file(source)
                self.assertEqual(expected, actual)


class CompilerFeatureTests(unittest.TestCase):
    def compile_source(self, source: str) -> str:
        return Compiler(Parser(tokenize(source)).parse()).compile()

    def test_constructor_allocates_fields_and_returns_this(self) -> None:
        source = """
        class Point {
            field int x, y;
            constructor Point new(int ax, int ay) {
                let x = ax;
                let y = ay;
                return this;
            }
        }
        """
        vm = self.compile_source(source)
        self.assertIn("function Point.new 0\n", vm)
        self.assertIn("push constant 2\ncall Memory.alloc 1\npop pointer 0\n", vm)
        self.assertTrue(vm.rstrip().endswith("push pointer 0\nreturn"))

    def test_method_sets_this_pointer(self) -> None:
        source = """
        class Point {
            field int x;
            method int getX() { return x; }
        }
        """
        vm = self.compile_source(source)
        self.assertIn("function Point.getX 0\npush argument 0\npop pointer 0\n", vm)
        self.assertIn("push this 0\nreturn", vm)

    def test_array_assignment_uses_pointer_one(self) -> None:
        source = """
        class Main {
            function void main() {
                var Array a;
                let a[3] = 2;
                return;
            }
        }
        """
        vm = self.compile_source(source)
        self.assertIn(
            "push constant 3\n"
            "push local 0\n"
            "add\n"
            "push constant 2\n"
            "pop temp 0\n"
            "pop pointer 1\n"
            "push temp 0\n"
            "pop that 0\n",
            vm,
        )

    def test_method_call_on_object_and_on_this(self) -> None:
        source = """
        class Main {
            field Helper helper;
            method void run() {
                do helper.work(1);
                do localCall();
                return;
            }
            method void localCall() { return; }
        }
        """
        vm = self.compile_source(source)
        self.assertIn("push this 0\npush constant 1\ncall Helper.work 2\n", vm)
        self.assertIn("push pointer 0\ncall Main.localCall 1\n", vm)

    def test_string_escapes_are_decoded(self) -> None:
        source = r'''
        class Main {
            function void main() {
                do Output.printString("A\nB\\C\"D");
                return;
            }
        }
        '''
        vm = self.compile_source(source)
        self.assertIn("push constant 7\ncall String.new 1\n", vm)
        for code in (65, 10, 66, 92, 67, 34, 68):
            self.assertIn(f"push constant {code}\ncall String.appendChar 2\n", vm)

    def test_missing_return_is_tolerated(self) -> None:
        source = """
        class Main {
            function int answer() {
            }
        }
        """
        vm = self.compile_source(source)
        self.assertTrue(vm.endswith("push constant 0\nreturn\n"))

    def test_incomplete_project12_os_stubs_compile(self) -> None:
        # These files intentionally have empty bodies; the official compiler
        # refuses them, but a friendly compiler can still emit code.
        for name in (
            "Array.jack",
            "Keyboard.jack",
            "Math.jack",
            "Memory.jack",
            "Output.jack",
            "Screen.jack",
            "String.jack",
            "Sys.jack",
        ):
            with self.subTest(name=name):
                vm = compile_file(project_dir("12") / name)
                self.assertIn("function ", vm)


if __name__ == "__main__":
    unittest.main()
