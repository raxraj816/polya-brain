"""Bounded alpha-renaming of verified expression edits; proposals, not proofs."""

import ast
import copy
import textwrap
from dataclasses import dataclass
from itertools import islice

VERSION = "expression_repair_transfer@0.1.0"
MAX_NODES = 4096
_ALLOWED = (
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Eq,
    ast.NotEq,
)
_ROOTS = (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare)


@dataclass(frozen=True)
class StructuralEdit:
    old_text: str
    new_text: str
    names: dict[str, str]


def _expression(fragment: str) -> ast.expr | None:
    try:
        tree = ast.parse(textwrap.dedent(fragment).strip())
    except SyntaxError, ValueError, RecursionError:
        return None
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.Return, ast.Expr)):
        return None
    value = tree.body[0].value
    if not isinstance(value, _ROOTS):
        return None
    nodes = list(islice(ast.walk(value), 129))
    if len(nodes) > 128 or any(not isinstance(n, _ALLOWED) for n in nodes):
        return None
    return value


def _match(pattern: ast.AST, target: ast.AST, names: dict[str, str]) -> bool:
    if type(pattern) is not type(target):
        return False
    if isinstance(pattern, ast.Name) and isinstance(target, ast.Name):
        if pattern.id in names:
            return names[pattern.id] == target.id
        if target.id in names.values():
            return False
        names[pattern.id] = target.id
        return True
    for field, value in ast.iter_fields(pattern):
        other = getattr(target, field)
        if isinstance(value, ast.AST):
            if not isinstance(other, ast.AST) or not _match(value, other, names):
                return False
        elif isinstance(value, list):
            if not isinstance(other, list) or len(value) != len(other):
                return False
            for child, counterpart in zip(value, other, strict=True):
                if (
                    not isinstance(child, ast.AST)
                    or not isinstance(counterpart, ast.AST)
                    or not _match(child, counterpart, names)
                ):
                    return False
        elif type(value) is not type(other) or value != other:
            return False
    return True


class _Rename(ast.NodeTransformer):
    def __init__(self, names: dict[str, str]) -> None:
        self.names = names

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return ast.copy_location(ast.Name(id=self.names[node.id], ctx=ast.Load()), node)


def structural_candidates(source: str, old: str, new: str) -> list[StructuralEdit] | None:
    """Zero or one candidate; None marks ambiguity and forbids selecting a site."""
    if len(source) > 100_000 or max(len(old), len(new)) > 800:
        return []
    before, after = _expression(old), _expression(new)
    if before is None or after is None:
        return []
    before_names = {n.id for n in ast.walk(before) if isinstance(n, ast.Name)}
    after_names = {n.id for n in ast.walk(after) if isinstance(n, ast.Name)}
    if not before_names or not after_names.issubset(before_names):
        return []
    try:
        tree = ast.parse(source)
        nodes = list(islice(ast.walk(tree), MAX_NODES + 1))
    except SyntaxError, ValueError, RecursionError:
        return []
    if len(nodes) > MAX_NODES:
        return []
    edits = []
    for node in nodes:
        if not isinstance(node, type(before)):
            continue
        names: dict[str, str] = {}
        if not _match(before, node, names):
            continue
        segment = ast.get_source_segment(source, node)
        if not segment or source.count(segment) != 1:
            return None
        replacement = _Rename(names).visit(copy.deepcopy(after))
        if ast.dump(replacement) == ast.dump(node):
            continue
        new_text = f"({ast.unparse(replacement)})"
        if max(len(segment), len(new_text)) > 800:
            continue
        edits.append(StructuralEdit(segment, new_text, names))
        if len(edits) == 2:
            return None
    return edits
