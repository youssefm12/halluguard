"""
Python AST Parser module using Tree-sitter.

Extracts imports, function calls, method calls, class definitions,
decorators, and async functions from Python source code.
Handles edge cases: nested calls, decorators, async/await, comprehensions.
"""
from __future__ import annotations

import tree_sitter_python
from tree_sitter import Language, Parser, Node
from typing import Any

# ── Language singleton ──────────────────────────────────────────────
PY_LANGUAGE = Language(tree_sitter_python.language())


def _node_text(code: str, node: Node) -> str:
    """Return the source text corresponding to a tree-sitter node."""
    return code[node.start_byte : node.end_byte]


def _extract_dotted_root(code: str, node: Node) -> str:
    """Return the top-level module name from a dotted_name node."""
    return _node_text(code, node).split(".")[0]


def extract(code: str, language: str = "python") -> dict[str, Any]:
    """
    Parse a Python code snippet and extract structured token information.

    Args:
        code: The Python source code string.
        language: Must be ``"python"`` (validated at call site).

    Returns:
        A dictionary with the following keys:

        - **imports** – list of top-level module names.
        - **from_imports** – list of ``{"module": ..., "names": [...]}`` dicts.
        - **function_calls** – list of bare function call identifiers.
        - **method_calls** – list of attribute-style calls (e.g. ``requests.get``).
        - **decorators** – list of decorator names.
        - **async_functions** – list of async function names.
        - **classes** – list of class names.
    """
    if language.lower() != "python":
        raise ValueError(
            f"Language '{language}' is not supported by the Python parser."
        )

    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(code, "utf8"))

    imports: list[str] = []
    from_imports: list[dict[str, Any]] = []
    function_calls: list[str] = []
    method_calls: list[str] = []
    decorators: list[str] = []
    async_functions: list[str] = []
    classes: list[str] = []

    # Track uniqueness while preserving insertion order
    _seen_imports: set[str] = set()
    _seen_fcalls: set[str] = set()
    _seen_mcalls: set[str] = set()

    def _add_import(name: str) -> None:
        if name and name not in _seen_imports:
            _seen_imports.add(name)
            imports.append(name)

    def _add_fcall(name: str) -> None:
        if name and name not in _seen_fcalls:
            _seen_fcalls.add(name)
            function_calls.append(name)

    def _add_mcall(name: str) -> None:
        if name and name not in _seen_mcalls:
            _seen_mcalls.add(name)
            method_calls.append(name)

    def traverse(node: Node) -> None:
        # ── import X / import X.Y ──────────────────────────────
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    _add_import(_extract_dotted_root(code, child))
                elif child.type == "aliased_import":
                    for sub in child.children:
                        if sub.type == "dotted_name":
                            _add_import(_extract_dotted_root(code, sub))
                            break

        # ── from X import Y, Z ─────────────────────────────────
        elif node.type == "import_from_statement":
            module_name: str | None = None
            names: list[str] = []
            for child in node.children:
                if child.type == "dotted_name" and module_name is None:
                    module_name = _node_text(code, child)
                    _add_import(module_name.split(".")[0])
                elif child.type == "import_list":
                    for item in child.children:
                        if item.type in ("dotted_name", "aliased_import"):
                            # Get the actual imported name
                            name_node = item
                            if item.type == "aliased_import":
                                for sub in item.children:
                                    if sub.type == "dotted_name":
                                        name_node = sub
                                        break
                            names.append(_node_text(code, name_node))
                elif child.type == "dotted_name" and module_name is not None:
                    names.append(_node_text(code, child))
            if module_name:
                from_imports.append({"module": module_name, "names": names})

        # ── function / method calls (handles nested) ───────────
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node is not None:
                if func_node.type == "identifier":
                    _add_fcall(_node_text(code, func_node))
                elif func_node.type == "attribute":
                    _add_mcall(_node_text(code, func_node))

        # ── decorators ─────────────────────────────────────────
        elif node.type == "decorator":
            for child in node.children:
                if child.type == "identifier":
                    decorators.append(_node_text(code, child))
                elif child.type == "attribute":
                    decorators.append(_node_text(code, child))
                elif child.type == "call":
                    inner = child.child_by_field_name("function")
                    if inner is not None:
                        decorators.append(_node_text(code, inner))

        # ── async function definitions ─────────────────────────
        elif node.type == "function_definition":
            # Check if parent is decorated or if it's async
            name_node = node.child_by_field_name("name")
            if name_node:
                # Walk upward in source to detect 'async' keyword
                # Tree-sitter wraps async defs in their own node type
                pass  # handled below in normal traversal

        # ── class definitions ──────────────────────────────────
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                classes.append(_node_text(code, name_node))

        # Recurse into all children (handles nesting naturally)
        for child in node.children:
            traverse(child)

    # Also handle top-level async scanning by walking raw bytes
    traverse(tree.root_node)

    # ── Post-pass: detect async functions via raw tree walk ────
    def _find_async(node: Node) -> None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                # Check the preceding sibling or parent for "async"
                prev = node.prev_sibling
                if prev and _node_text(code, prev) == "async":
                    async_functions.append(_node_text(code, name_node))
                # Also check if wrapped as child of a block with async keyword
                parent = node.parent
                if parent and parent.type == "block":
                    pass  # decorators already handled
        for child in node.children:
            _find_async(child)

    _find_async(tree.root_node)

    return {
        "imports": imports,
        "from_imports": from_imports,
        "function_calls": function_calls,
        "method_calls": method_calls,
        "decorators": decorators,
        "async_functions": async_functions,
        "classes": classes,
    }
