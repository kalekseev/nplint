import libcst as cst


class AssertsTransformer(cst.CSTTransformer):
    def leave_SimpleStatementLine(
        self, node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        body = []
        for line in node.body:
            if isinstance(line, cst.Expr) and isinstance(line.value, cst.Comparison):
                body.append(cst.Assert(test=line.value))
            else:
                body.append(line)
        return updated_node.with_changes(body=body)

    def leave_SimpleStatementSuite(
        self, node: cst.SimpleStatementSuite, updated_node: cst.SimpleStatementSuite
    ) -> cst.SimpleStatementSuite:
        body = []
        for line in node.body:
            if isinstance(line, cst.Expr) and isinstance(line.value, cst.Comparison):
                body.append(cst.Assert(test=line.value))
            else:
                body.append(line)
        return updated_node.with_changes(body=body)
