"""Read-only access to two versions of one Python module in a local git repository."""

from __future__ import annotations

import ast
import difflib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_SOURCE_CHARS = 24_000


class ChangeSourceError(ValueError):
    """The requested change cannot be read or isolated; the message is user-facing."""


@dataclass(frozen=True)
class ModuleVersions:
    repository: Path
    module_path: str
    base_ref: str
    head_ref: str | None
    old_source: str
    new_source: str

    @property
    def head_label(self) -> str:
        return self.head_ref or "working tree"


def _git(repository: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603 - fixed executable, argument vector, no shell
            ["git", "-C", str(repository), *args],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ChangeSourceError(f"git could not be run: {type(exc).__name__}") from exc
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip().splitlines()
        raise ChangeSourceError(message[0][:200] if message else "git command failed")
    return result.stdout.decode()


def _bounded(text: str, label: str) -> str:
    if len(text) > MAX_SOURCE_CHARS:
        raise ChangeSourceError(
            f"{label} has {len(text)} characters; verified changes currently support modules "
            f"up to {MAX_SOURCE_CHARS} characters."
        )
    return text


def read_versions(
    repository: Path, module_path: str, *, base_ref: str = "HEAD", head_ref: str | None = None
) -> ModuleVersions:
    """Read the base and changed module text without touching the repository."""
    for ref in (base_ref, head_ref):
        if ref is not None and (not ref.strip() or ref.startswith("-")):
            raise ChangeSourceError("Revisions must be plain git revision names.")
    root = Path(_git(repository, "rev-parse", "--show-toplevel").strip()).resolve()
    relative = Path(module_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".py":
        raise ChangeSourceError(
            "The module must be a relative path to a .py file inside the repository."
        )
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ChangeSourceError("The module path resolves outside the repository.")
    spec = relative.as_posix()
    old = _bounded(_git(root, "show", f"{base_ref}:{spec}"), f"{spec} at {base_ref}")
    if head_ref is None:
        if not target.is_file():
            raise ChangeSourceError(f"{spec} does not exist in the working tree.")
        new = _bounded(target.read_text(encoding="utf-8"), f"{spec} in the working tree")
    else:
        new = _bounded(_git(root, "show", f"{head_ref}:{spec}"), f"{spec} at {head_ref}")
    return ModuleVersions(root, spec, base_ref, head_ref, old, new)


@dataclass(frozen=True)
class FunctionChange:
    name: str
    class_name: str | None
    old_function: str
    new_function: str
    function_diff: str
    module_diff_lines: int


def _locate(tree: ast.Module, source: str, qualified: str) -> str:
    class_name, _, name = qualified.rpartition(".")
    scope: list[ast.stmt] = tree.body
    if class_name:
        owner = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
            ),
            None,
        )
        if owner is None:
            raise ChangeSourceError(f"Class {class_name} was not found.")
        scope = owner.body
    node = next(
        (
            item
            for item in scope
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
        ),
        None,
    )
    if node is None:
        raise ChangeSourceError(f"Function {qualified} was not found.")
    if isinstance(node, ast.AsyncFunctionDef):
        raise ChangeSourceError("Async functions are not supported yet.")
    return ast.get_source_segment(source, node) or ""


def _non_stdlib_imports(tree: ast.Module) -> list[str]:
    allowed = set(sys.stdlib_module_names) | {"__future__"}
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.add("." * node.level + (node.module or ""))
            elif node.module:
                found.add(node.module.split(".")[0])
    return sorted(name for name in found if name not in allowed)


def analyse(versions: ModuleVersions, qualified: str) -> FunctionChange:
    """Locate the function in both versions and refuse modules the sandbox cannot load."""
    trees = []
    for label, source in (("base", versions.old_source), ("changed", versions.new_source)):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ChangeSourceError(
                f"The {label} module does not parse: line {exc.lineno}."
            ) from exc
        blocked = _non_stdlib_imports(tree)
        if blocked:
            raise ChangeSourceError(
                f"The {label} module imports {', '.join(blocked)}; verified changes currently "
                "support modules that import only the Python standard library."
            )
        trees.append(tree)
    old_function = _locate(trees[0], versions.old_source, qualified)
    new_function = _locate(trees[1], versions.new_source, qualified)
    class_name, _, name = qualified.rpartition(".")
    diff = "".join(
        difflib.unified_diff(
            old_function.splitlines(keepends=True),
            new_function.splitlines(keepends=True),
            fromfile=f"{qualified} ({versions.base_ref})",
            tofile=f"{qualified} ({versions.head_label})",
        )
    )
    module_diff = [
        line
        for line in difflib.unified_diff(
            versions.old_source.splitlines(), versions.new_source.splitlines(), lineterm=""
        )
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    return FunctionChange(
        name=name,
        class_name=class_name or None,
        old_function=old_function,
        new_function=new_function,
        function_diff=diff,
        module_diff_lines=len(module_diff),
    )
