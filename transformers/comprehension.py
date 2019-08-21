from typing import List, Tuple, Union

import libcst as cst


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
        return node

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
        if isinstance(node.operator, cst.In) and isinstance(
            node.comparator, cst.ListComp
        ):
            cmp = node.comparator
            return updated_node.with_changes(
                comparator=cst.GeneratorExp(elt=cmp.elt, for_in=cmp.for_in)
            )
        return updated_node

    def leave_Call(
        self, node: cst.Call, updated_node: cst.Call
    ) -> Union[
        cst.Call,
        cst.ListComp,
        cst.DictComp,
        cst.Dict,
        cst.SetComp,
        cst.List,
        cst.Tuple,
        cst.Set,
    ]:
        if isinstance(node.func, cst.Call):
            return updated_node
        if node.func.value == "list":
            return self._list_call(updated_node)
        if node.func.value == "tuple":
            return self._tuple_call(updated_node)
        if node.func.value == "set":
            return self._set_call(updated_node)
        if node.func.value == "dict":
            return self._dict_call(updated_node)
        if node.func.value in self.GEN_BUILTINS:
            return self._gen_builtin_call(updated_node)
        return node
