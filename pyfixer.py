import difflib
import textwrap
from collections import namedtuple
from typing import Dict, List, Optional, Tuple, Union

import libcst as cst

TestCase = namedtuple("TestCase", ["name", "input", "output"])


def assert_output(testcase, actual):
    assert testcase.output == actual, f"{testcase.name} diff:\n" + "".join(
        difflib.unified_diff(
            testcase.output.splitlines(1), modified_tree.code.splitlines(1)
        )
    )


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


class ComprehensionsTransformer(cst.CSTTransformer):
    GEN_BUILTINS = [
        "all",
        "any",
        "enumerate",
        "frozenset",
        "max",
        "min",
        "sorted",
        "sum",
        "tuple",
    ]

    def __init__(self):
        self.stack: List[Tuple[str, ...]] = []

    def _list_call(self, node: cst.Call) -> Union[cst.Call, cst.List, cst.ListComp]:
        if not node.args:
            return cst.List(elements=[])
        if len(node.args) != 1:
            return node
        value = node.args[0].value
        if isinstance(value, cst.ListComp):
            return value
        if isinstance(value, cst.GeneratorExp):
            return cst.ListComp(elt=value.elt, for_in=value.for_in)
        if isinstance(value, cst.List):
            return value
        if isinstance(value, cst.Tuple):
            return cst.List(elements=value.elements)
        return node

    def _tuple_call(self, node: cst.Call) -> Union[cst.Call, cst.Tuple]:
        if not node.args:
            return cst.Tuple(elements=[])
        if len(node.args) != 1:
            return node
        value = node.args[0].value
        if isinstance(value, (cst.List, cst.Tuple)):
            if value.elements:
                return cst.Tuple(elements=value.elements)
            else:
                return cst.Tuple(elements=[])
        return node

    def _set_call(self, node: cst.Call) -> Union[cst.Call, cst.Set, cst.SetComp]:
        if len(node.args) != 1:
            return node
        value = node.args[0].value
        if isinstance(value, (cst.List, cst.Tuple)):
            if value.elements:
                return cst.Set(elements=value.elements)
            else:
                return node.with_changes(args=[])
        if isinstance(value, (cst.ListComp, cst.SetComp, cst.GeneratorExp)):
            return cst.SetComp(elt=value.elt, for_in=value.for_in)

    def _dict_call(self, node: cst.Call) -> Union[cst.Call, cst.Dict, cst.DictComp]:
        if not node.args:
            return cst.Dict(elements=[])
        if len(node.args) != 1:
            return node
        value = node.args[0].value
        if isinstance(value, cst.DictComp):
            return value
        if isinstance(value, (cst.ListComp, cst.GeneratorExp)):
            elt = value.elt
            if isinstance(elt, (cst.Tuple, cst.List)) and len(elt.elements) == 2:
                return cst.DictComp(
                    key=elt.elements[0].value,
                    value=elt.elements[1].value,
                    for_in=value.for_in,
                )
        if isinstance(value, (cst.Tuple, cst.List)):
            if value.elements:
                elements = []
                for el in value.elements:
                    if (
                        isinstance(el.value, (cst.Tuple, cst.List))
                        and len(el.value.elements) == 2
                    ):
                        elements.append(
                            cst.DictElement(
                                key=el.value.elements[0].value,
                                value=el.value.elements[1].value,
                            )
                        )
                    else:
                        break
                else:
                    return cst.Dict(elements=elements)
            else:
                return cst.Dict(elements=[])
        return node

    def _gen_builtin_call(self, node: cst.Call) -> cst.Call:
        if not node.args:
            return node
        value = node.args[0].value
        if isinstance(value, (cst.ListComp, cst.GeneratorExp)):
            pars: dict = {"lpar": [], "rpar": []} if len(node.args) == 1 else {}
            arg0 = node.args[0].with_changes(
                value=cst.GeneratorExp(elt=value.elt, for_in=value.for_in, **pars)
            )
            return node.with_changes(args=(arg0, *node.args[1:]))
        return node

    def leave_ComparisonTarget(self, node: cst.In, updated_node: cst.In) -> cst.In:
        if isinstance(updated_node.operator, cst.In) and isinstance(
            updated_node.comparator, cst.ListComp
        ):
            cmp = updated_node.comparator
            return updated_node.with_changes(
                comparator=cst.GeneratorExp(elt=cmp.elt, for_in=cmp.for_in)
            )
        return updated_node

    def leave_Call(
        self, node: cst.Call, updated_node: cst.Call
    ) -> Union[
        cst.Call, cst.ListComp, cst.DictComp, cst.SetComp, cst.List, cst.Tuple, cst.Set
    ]:
        if updated_node.func.value == "list":
            return self._list_call(updated_node)
        if updated_node.func.value == "tuple":
            return self._tuple_call(updated_node)
        if updated_node.func.value == "set":
            return self._set_call(updated_node)
        if updated_node.func.value == "dict":
            return self._dict_call(updated_node)
        if updated_node.func.value in self.GEN_BUILTINS:
            return self._gen_builtin_call(updated_node)
        return updated_node


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
with output:
    sum(x ** 2 for x in range(10))
    all(foo.bar for foo in foos)
    all(foo.bar for foo in foos)
"""

testcase_412 = """
with input:
    y in [f(x) for x in foo]
with output:
    y in (f(x) for x in foo)
"""

testcases = {n: v for n, v in locals().items() if n.startswith("testcase_")}
for testcase in TestCaseParser.parse(testcases):
    source_tree = cst.parse_module(testcase.input)
    modified_tree = source_tree.visit(ComprehensionsTransformer())
    assert_output(testcase, modified_tree.code)
