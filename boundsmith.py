"""BoundSmith core — extract boundary conditions from Python AST."""
import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Boundary:
    file: str
    line: int
    variable: str
    operator: str
    value: object
    triplet: tuple
    expression: str


_OP = {ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<=",
       ast.Eq: "==", ast.NotEq: "!="}
_FLIP = {ast.Gt: ast.Lt, ast.Lt: ast.Gt, ast.GtE: ast.LtE,
         ast.LtE: ast.GtE, ast.Eq: ast.Eq, ast.NotEq: ast.NotEq}


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
        return ast.unparse(node)
    return None


def _literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        if isinstance(node.operand, ast.Constant):
            v = node.operand.value
            if isinstance(v, (int, float)):
                return -v
    return None


class _Extractor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.results: list[Boundary] = []

    def visit_Compare(self, node: ast.Compare):
        left = node.left
        for op, comp in zip(node.ops, node.comparators):
            self._try_pair(left, op, comp, node)
            flipped_cls = _FLIP.get(type(op))
            if flipped_cls:
                self._try_pair(comp, flipped_cls(), left, node)
            left = comp
        self.generic_visit(node)

    def _try_pair(self, var_node, op, val_node, ctx):
        name = _name(var_node)
        val = _literal(val_node)
        if name is None or val is None:
            return
        step = 1 if isinstance(val, int) else 0.1
        op_str = _OP.get(type(op), "?")
        self.results.append(Boundary(
            self.filename, ctx.lineno, name, op_str, val,
            (val - step, val, val + step), ast.unparse(ctx),
        ))


def extract_boundaries(source: str, filename: str = "<stdin>") -> list[Boundary]:
    visitor = _Extractor(filename)
    visitor.visit(ast.parse(source))
    return visitor.results


def extract_test_values(source: str) -> set:
    return {n.value for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))}


def find_uncovered(boundaries: list[Boundary], test_values: set) -> list[Boundary]:
    return [b for b in boundaries
            if not all(v in test_values for v in b.triplet)]


def generate_test_file(boundaries: list[Boundary]) -> str:
    parts = ["import pytest"]
    for i, b in enumerate(boundaries):
        safe = b.variable.replace(".", "_").replace("(", "").replace(")", "")
        safe = safe.replace("[", "").replace("]", "").replace(" ", "")
        vals = ", ".join(repr(v) for v in b.triplet)
        parts.append(
            f'@pytest.mark.parametrize("val", [{vals}])\n'
            f"def test_boundary_{safe}_{i}(val):\n"
            f'    """Boundary: {b.expression} at {b.file}:{b.line}"""\n'
            f"    result = val {b.operator} {b.value!r}\n"
            f"    assert isinstance(result, bool)"
        )
    return "\n\n\n".join(parts) + "\n"


def scan_path(path: Path) -> list[Boundary]:
    results = []
    for f in sorted(path.rglob("*.py")):
        if f.name.startswith("test_") or f.name == "conftest.py":
            continue
        try:
            results.extend(extract_boundaries(f.read_text("utf-8"), str(f)))
        except SyntaxError:
            continue
    return results


def scan_tests(path: Path) -> set:
    values: set = set()
    for f in sorted(path.rglob("*.py")):
        if f.name.startswith("test_") or f.name == "conftest.py":
            try:
                values |= extract_test_values(f.read_text("utf-8"))
            except SyntaxError:
                continue
    return values
