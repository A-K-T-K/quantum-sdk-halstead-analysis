"""Execute the functional notebook headlessly and save real, fresh cell outputs."""
import ast
import contextlib
import io
import os
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    path = ROOT / "functional_equivalence.ipynb"
    notebook = nbformat.read(path, as_version=4)
    namespace = {"__name__": "__verification_notebook__"}
    count = 0
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        count += 1
        tree = ast.parse(cell.source, filename=f"notebook:cell{index}")
        expression = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            exec(compile(tree, f"notebook:cell{index}", "exec"), namespace)
            result = eval(compile(ast.Expression(expression.value), f"notebook:cell{index}", "eval"),
                          namespace) if expression else None
        outputs = []
        if captured.getvalue():
            outputs.append(nbformat.v4.new_output("stream", name="stdout", text=captured.getvalue()))
        if result is not None:
            data = {"text/plain": repr(result)}
            if hasattr(result, "to_html"):
                data["text/html"] = result.to_html()
            outputs.append(nbformat.v4.new_output("execute_result", data=data, execution_count=count))
        cell.outputs = outputs
        cell.execution_count = count
        cell.metadata.pop("execution", None)
    nbformat.write(notebook, path)
    print(f"Refreshed {count} functional notebook code cells and their outputs")


if __name__ == "__main__":
    main()
