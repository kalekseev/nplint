import difflib
import unittest

import libcst as cst

from _testparser import TestCaseParser
from annotations import AnnotationsTransformer

testcase_return_annotations = """
with input:
    def f():
        return 'x'
    def ff() -> int:
        return 'y'
    def ffloat():
        return 1.2
    def fbool():
        return True
    def fbytes():
        return b'test'
    def fnone():
        return None
    def fnone2():
        print('test')
    def fnone3(x):
        if x:
            return
        print('test')
    def fnone4():
        if a:
            return
        if b:
            c()
    def fnone5():
        if a:
            return
        if b:
            return None
    def fnone6():
        if a:
            return
        return None
with output:
    def f() -> str:
        return 'x'
    def ff() -> int:
        return 'y'
    def ffloat() -> float:
        return 1.2
    def fbool() -> bool:
        return True
    def fbytes() -> bytes:
        return b'test'
    def fnone() -> None:
        return None
    def fnone2() -> None:
        print('test')
    def fnone3(x) -> None:
        if x:
            return
        print('test')
    def fnone4() -> None:
        if a:
            return
        if b:
            c()
    def fnone5() -> None:
        if a:
            return
        if b:
            return None
    def fnone6() -> None:
        if a:
            return
        return None
"""

testcase_no_return_annotations = """
with input:
    def foptional(val):
        if val:
            return 'string'
        return None
    def foptional2(val):
        if val:
            return 'string'
    def foptional3(val):
        if val:
            return 'string'
        else:
            print('test')
    def foptional4(val):
        if val:
            return 'string'
        print('test')
    def fcall():
        if a:
            return
        return fother()
with output:
    def foptional(val):
        if val:
            return 'string'
        return None
    def foptional2(val):
        if val:
            return 'string'
    def foptional3(val):
        if val:
            return 'string'
        else:
            print('test')
    def foptional4(val):
        if val:
            return 'string'
        print('test')
    def fcall():
        if a:
            return
        return fother()
"""

testcase_yield_annotations = """
with input:
    def fyield():
        yield None
with output:
    def fyield():
        yield None
"""

testcases = {n: v for n, v in locals().items() if n.startswith("testcase_")}


class TestAnnotations(unittest.TestCase):
    def test_annotations(self):
        for testcase in TestCaseParser.parse(testcases):
            source_tree = cst.parse_module(testcase.input)
            modified_tree = source_tree.visit(AnnotationsTransformer())

            assert testcase.output == modified_tree.code, (
                f"{testcase.name} diff:\n"
                + "".join(
                    difflib.unified_diff(
                        testcase.output.splitlines(1), modified_tree.code.splitlines(1)
                    )
                )
            )
