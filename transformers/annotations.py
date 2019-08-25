from typing import List, Optional

import libcst as cst


class AnnotationsTransformer(cst.CSTTransformer):
    def __init__(self):
        self.stack: List[Optional[List[cst.Return]]] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if node.returns:
            self.stack.append(None)
            return False
        self.stack.append([])

    def leave_FunctionDef(
        self, node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        returns = self.stack.pop()
        if returns is None:
            return updated_node
        if not returns:
            return updated_node.with_changes(
                returns=cst.Annotation(annotation=cst.Name(value="None"))
            )
        last_line = node.body.body[-1]
        if not isinstance(last_line, cst.SimpleStatementLine):
            return updated_node
        elif not isinstance(last_line.body[-1], cst.Return):
            return updated_node
        if len(returns) == 1:
            rvalue = returns[0].value
            if isinstance(rvalue, cst.BaseString):
                if isinstance(rvalue, cst.SimpleString) and rvalue.value.startswith(
                    "b"
                ):
                    return updated_node.with_changes(
                        returns=cst.Annotation(annotation=cst.Name(value="bytes"))
                    )
                return updated_node.with_changes(
                    returns=cst.Annotation(annotation=cst.Name(value="str"))
                )
            if isinstance(rvalue, cst.Name):
                if rvalue.value in ("False", "True"):
                    return updated_node.with_changes(
                        returns=cst.Annotation(annotation=cst.Name(value="bool"))
                    )
                if rvalue.value == "None":
                    return updated_node.with_changes(
                        returns=cst.Annotation(annotation=cst.Name(value="None"))
                    )
            if isinstance(rvalue, cst.Integer):
                return updated_node.with_changes(
                    returns=cst.Annotation(annotation=cst.Name(value="int"))
                )
            if isinstance(rvalue, cst.Float):
                return updated_node.with_changes(
                    returns=cst.Annotation(annotation=cst.Name(value="float"))
                )
        return updated_node

    def visit_Return(self, node: cst.Return) -> Optional[bool]:
        if not self.stack:
            return False
        returns = self.stack[-1]
        if returns is not None:
            returns.append(node)
        return False
