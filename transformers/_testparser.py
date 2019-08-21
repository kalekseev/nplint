import textwrap
from collections import namedtuple
from typing import Dict, List, Optional

import libcst as cst

TestCase = namedtuple("TestCase", ["name", "input", "output"])


class TestCaseParser(cst.CSTVisitor):
    name: str
    input: Optional[str]
    output: Optional[str]
    module: Optional[cst.Module]

    def __init__(self, name):
        self.name = name
        self.input = None
        self.module = None
        self.output = None

    def visit_Module(self, node: cst.Module) -> Optional[bool]:
        self.module = node
        return None

    def visit_With(self, node: cst.With) -> Optional[bool]:
        module = self.module
        if not module:
            return False
        if len(node.items) == 1 and node.items[0].item.value == "input":
            self.input = textwrap.dedent(module.code_for_node(node.body).strip("\n"))
        elif len(node.items) == 1 and node.items[0].item.value == "output":
            self.output = textwrap.dedent(module.code_for_node(node.body).strip("\n"))
        else:
            raise ValueError(f"Invalid with statement in testcase {self.name}.")
        return False

    @property
    def result(self):
        if not self.input or not self.output:
            raise ValueError(f"Invalid testcase {self.name}.")
        return TestCase(self.name, self.input, self.output)

    @staticmethod
    def parse(testcases: Dict[str, str]) -> List[TestCase]:
        result = []
        for name, code in testcases.items():
            visitor = TestCaseParser(name)
            cst.parse_module(code).visit(visitor)
            result.append(visitor.result)
        return result
