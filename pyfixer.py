import difflib
import sys

import libcst as cst

from transformers.asserts import AssertsTransformer
from transformers.comprehension import ComprehensionsTransformer

INPLACE = True

if __name__ == "__main__":
    fname = sys.argv[1]
    print(fname)
    with open(fname, "r") as f:
        source_text = f.read()
    source_tree = cst.parse_module(source_text)
    modified_tree = source_tree.visit(ComprehensionsTransformer())
    modified_tree = modified_tree.visit(AssertsTransformer())
    result_text = modified_tree.code
    if source_text != result_text:
        if INPLACE:
            with open(fname, "w") as f:
                f.write(result_text)
        else:
            print(
                "".join(
                    difflib.unified_diff(
                        source_text.splitlines(1), result_text.splitlines(1)
                    )
                )
            )
        sys.exit(1)
