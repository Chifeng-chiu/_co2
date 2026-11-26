from __future__ import annotations

import unittest

from tests.helpers import (
    parse_xml_file,
    project10_cases,
    read_source,
    token_xml_file,
    tokenize_file,
)
from jackc.parser import Parser
from jackc.tokenizer import tokenize


class Project10XmlTests(unittest.TestCase):
    def test_reference_cases_exist(self) -> None:
        self.assertGreaterEqual(len(project10_cases()), 7)

    def test_parse_tree_xml_matches_reference(self) -> None:
        for jack in project10_cases():
            with self.subTest(jack=str(jack)):
                expected = read_source(jack.with_suffix(".xml")).strip()
                actual = parse_xml_file(jack).strip()
                self.assertEqual(expected, actual)

    def test_token_xml_matches_reference(self) -> None:
        for jack in project10_cases():
            with self.subTest(jack=str(jack)):
                expected = read_source(jack.with_name(jack.stem + "T.xml")).strip()
                actual = token_xml_file(jack).strip()
                self.assertEqual(expected, actual)


class ParserStructureTests(unittest.TestCase):
    def test_class_structure(self) -> None:
        source = """
        class Point {
            field int x, y;
            static int count;
            constructor Point new(int ax, int ay) {
                let x = ax; let y = ay; return this;
            }
            method int getX() { return x; }
        }
        """
        class_def = Parser(tokenize(source)).parse()
        self.assertEqual(class_def.name, "Point")
        self.assertEqual([var.kind for var in class_def.class_vars], ["field", "static"])
        self.assertEqual([var.names for var in class_def.class_vars], [["x", "y"], ["count"]])
        self.assertEqual([sub.kind for sub in class_def.subroutines], ["constructor", "method"])
        self.assertEqual([param.name for param in class_def.subroutines[0].params], ["ax", "ay"])

    def test_else_branch(self) -> None:
        source = """
        class Main {
            function void main() {
                if (true) { do Output.printInt(1); }
                else { do Output.printInt(2); }
                return;
            }
        }
        """
        class_def = Parser(tokenize(source)).parse()
        statement = class_def.subroutines[0].body[0]
        self.assertIsNotNone(statement.else_body)

    def test_syntax_error_reports_location(self) -> None:
        source = "class Main { function void main() { let x = ; } }"
        with self.assertRaises(Exception) as context:
            Parser(tokenize(source, filename="Broken.jack"), filename="Broken.jack").parse()
        self.assertIn("Broken.jack", str(context.exception))


if __name__ == "__main__":
    unittest.main()
