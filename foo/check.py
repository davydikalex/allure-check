#!/usr/bin/env python3

import ast
import os
import sys


def print_colored(text: str, error_level: str):
    color_dict: dict = {
        "error": "\033[91m",
        "warning": "\033[93m",
        "default": "\033[0m",
    }
    print(f'{color_dict.get(error_level, color_dict["default"])}{text}\033[0m')


class Visitor(ast.NodeVisitor):
    missing_id: tuple[str, str] = "Function is missing @allure.id decorator", "error"
    non_str_id: tuple[str, str] = "Function has non-str @allure.id", "warning"
    non_unique_id: tuple[str, str] = "Function has non-unique @allure.id", "error"
    bad_id: tuple[str, str] = "@allure.id for function should contain only digits", "error"
    flaky: tuple[str, str] = "Function has @pytest.mark.flaky decorator", "error"
    missing_owner: tuple[str, str] = 'Class does not have @allure.label("owner", "...") decorator', "error"

    def __init__(self, filename: str, ids: set):
        self.ids: set = ids
        self.errors: list = []
        self.filename: str = filename

    def create_error(self, node: ast.ClassDef | ast.FunctionDef, type_error: tuple[str, str]):
        self.errors.append(
            {
                "message": type_error[0],
                "file": self.filename,
                "line": node.lineno,
                "column": node.col_offset,
                "level": type_error[1],
            }
        )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Проверка тестовых функций на соответствие условиям
        :param node: функция
        :return: None
        """
        if node.name.startswith("test_"):  # Рассматриваем только тесты
            id_decorator: None = None

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "flaky":
                        self.create_error(node, self.flaky)

                    if decorator.func.attr == "id":
                        id_decorator: ast.Call = decorator

            if id_decorator is None or not len(id_decorator.args):
                self.create_error(node, self.missing_id)
                return

            if not isinstance(id_decorator.args[0].n, str):
                self.create_error(node, self.non_str_id)
                return
            if not id_decorator.args[0].n.isdigit():
                self.create_error(node, self.bad_id)
                return
            if id_decorator.args[0].n in self.ids:
                self.create_error(node, self.non_unique_id)
                return
            self.ids.add(id_decorator.args[0].n)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name.startswith("Test") and node.name != "Testers":
            has_owner_label: bool = False
            for decorator in node.decorator_list:
                if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "label"
                        and len(decorator.args) > 0
                        and isinstance(decorator.args[0], ast.Constant)
                        and decorator.args[0].s == "owner"
                ):
                    has_owner_label = True
                    break

            if not has_owner_label:
                self.create_error(node, self.missing_owner)
                return
        self.generic_visit(node)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    all_errors: list = []
    used_ids: set = set()

    for root, dirs, files in os.walk("./tests"):
        for file in files:
            if file.endswith(".py"):
                filename: str = os.path.join(root, file)
                with open(filename) as py_file:
                    tree: ast.Module = ast.parse(py_file.read())
                    visitor: Visitor = Visitor(filename, used_ids)
                    visitor.visit(tree)
                    all_errors.extend(visitor.errors)

    for error in all_errors:
        print_colored(f"{error['file']}:{error['line']} {error['message']}", error["level"])

    if any(val["level"] == "error" for val in all_errors):
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
