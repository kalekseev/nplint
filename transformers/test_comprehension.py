import difflib
import unittest

import libcst as cst

from _testparser import TestCaseParser
from comprehension import ComprehensionsTransformer

testcase_list = """
with input:
    list()
    []
    list([])
    list([x for x in d])
    list(x for x in d)
    list(1, 2, 3)
with output:
    []
    []
    []
    [x for x in d]
    [x for x in d]
    list(1, 2, 3)
"""

testcase_set = """
with input:
    set([1, 2, 3])
    set()
    set((1, 2))
    set(())
    set([x for x in d])
    set([])
    set({x for x in d})
with output:
    {1, 2, 3}
    set()
    {1, 2}
    set()
    {x for x in d}
    set()
    {x for x in d}
"""

testcase_dict = """
with input:
    {}
    dict()
    dict({k: v for k, v in d})
    dict([(k, v) for k, v in d])
    dict(k for k in d)
    dict(((1, 2), (3, 4)))
    dict([(1, 2, 3)])
    dict([d])
with output:
    {}
    {}
    {k: v for k, v in d}
    {k: v for k, v in d}
    dict(k for k in d)
    {1: 2, 3: 4}
    dict([(1, 2, 3)])
    dict([d])
"""

testcase_tuple = """
with input:
    ()
    tuple()
with output:
    ()
    ()
"""

testcase_misc = """
with input:
    any(x for x in d)
    any((x for x in d))
    any([x for x in d])
    sorted([x for x in d])
    sorted([x for x in d], reverse=True)
with output:
    any(x for x in d)
    any(x for x in d)
    any(x for x in d)
    sorted(x for x in d)
    sorted((x for x in d), reverse=True)
"""

# testcases from flake8-comprehensions
testcase_400_402 = """
with input:
    list(f(x) for x in foo)
    set(f(x) for x in foo)
    dict((x, f(x)) for x in foo)
with output:
    [f(x) for x in foo]
    {f(x) for x in foo}
    {x: f(x) for x in foo}
"""

testcase_403_404 = """
with input:
    set([f(x) for x in foo])
    dict([(x, f(x)) for x in foo])
with output:
    {f(x) for x in foo}
    {x: f(x) for x in foo}
"""

testcase_405_406_409_410 = """
with input:
    tuple([1, 2])
    tuple((1, 2))
    tuple([])
    list([1, 2])
    list((1, 2))
    list([])
    set([1, 2])
    set((1, 2))
    set([])
    dict([])
    dict([(1, 2)])
with output:
    (1, 2)
    (1, 2)
    ()
    [1, 2]
    [1, 2]
    []
    {1, 2}
    {1, 2}
    set()
    {}
    {1: 2}
"""

testcase_407 = """
with input:
    sum([x ** 2 for x in range(10)])
    all([foo.bar for foo in foos])
    all((foo.bar for foo in foos))
    sorted(
        (
            {
                foo: 1
            } for foo in foos
        ),
        key=lambda x: len(x)
    )
with output:
    sum(x ** 2 for x in range(10))
    all(foo.bar for foo in foos)
    all(foo.bar for foo in foos)
    sorted(
        (
            {
                foo: 1
            } for foo in foos
        ),
        key=lambda x: len(x)
    )
"""

testcase_412 = """
with input:
    y in [f(x) for x in foo]
with output:
    y in (f(x) for x in foo)
"""

testcase_call = """
with input:
    getattr(obj, attr)(params)
with output:
    getattr(obj, attr)(params)
"""

testcases = {n: v for n, v in locals().items() if n.startswith("testcase_")}


class TestComprehension(unittest.TestCase):
    def test_comprehensions(self):
        for testcase in TestCaseParser.parse(testcases):
            source_tree = cst.parse_module(testcase.input)
            modified_tree = source_tree.visit(ComprehensionsTransformer())

            assert testcase.output == modified_tree.code, (
                f"{testcase.name} diff:\n"
                + "".join(
                    difflib.unified_diff(
                        testcase.output.splitlines(1), modified_tree.code.splitlines(1)
                    )
                )
            )
