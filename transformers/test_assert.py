import difflib
import unittest

import libcst as cst

from _testparser import TestCaseParser
from asserts import AssertsTransformer

testcase_assert_missing = """
with input:
    assert x == y
    x == y
    print(x); x == y
    if a == 1: x == y
with output:
    assert x == y
    assert x == y
    print(x); assert x == y
    if a == 1: assert x == y
"""

testcases = {n: v for n, v in locals().items() if n.startswith("testcase_")}


class TestAssert(unittest.TestCase):
    def test_assert(self):
        for testcase in TestCaseParser.parse(testcases):
            source_tree = cst.parse_module(testcase.input)
            modified_tree = source_tree.visit(AssertsTransformer())

            assert testcase.output == modified_tree.code, (
                f"{testcase.name} diff:\n"
                + "".join(
                    difflib.unified_diff(
                        testcase.output.splitlines(1), modified_tree.code.splitlines(1)
                    )
                )
            )
