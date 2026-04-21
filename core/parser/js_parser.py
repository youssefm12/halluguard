"""
JavaScript / TypeScript AST Parser module using Tree-sitter.

Extracts ES6 imports, CommonJS require() calls, function calls,
method calls (including ``fetch`` / ``axios`` patterns).
"""
from __future__ import annotations

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser, Node
from typing import Any

# ── Language singletons ─────────────────────────────────────────────
JS_LANGUAGE = Language(tree_sitter_javascript.language())
TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())


def _node_text(code: str, node: Node) -> str:
    """Return the source text corresponding to a tree-sitter node."""
    return code[node.start_byte : node.end_byte]


def _get_language(language: str) -> Language:
    """Resolve language string to a tree-sitter Language object."""
    lang = language.lower()
    if lang in ("javascript", "js"):
        return JS_LANGUAGE
    elif lang in ("typescript", "ts"):
        return TS_LANGUAGE
    else:
        raise ValueError(
            f"Language '{language}' is not supported by the JS/TS parser. "
            "Use 'javascript' or 'typescript'."
        )


def extract(code: str, language: str = "javascript") -> dict[str, Any]:
    """
    Parse a JavaScript or TypeScript snippet and extract structured tokens.

    Args:
        code: The JS/TS source code string.
        language: ``"javascript"`` / ``"js"`` or ``"typescript"`` / ``"ts"``.

    Returns:
        A dictionary with the following keys:

        - **imports** – list of module specifiers from ES6 imports.
        - **require_calls** – list of module specifiers from ``require()``.
        - **function_calls** – list of bare function call identifiers.
        - **method_calls** – list of attribute-style calls (e.g. ``axios.get``).
        - **fetch_calls** – list of URLs or expressions passed to ``fetch()``.
    """
    lang_obj = _get_language(language)
    parser = Parser(lang_obj)
    tree = parser.parse(bytes(code, "utf8"))

    imports: list[str] = []
    require_calls: list[str] = []
    function_calls: list[str] = []
    method_calls: list[str] = []
    fetch_calls: list[str] = []

    _seen_imports: set[str] = set()
    _seen_fcalls: set[str] = set()
    _seen_mcalls: set[str] = set()

    def _add_import(name: str) -> None:
        cleaned = name.strip("'\"")
        if cleaned and cleaned not in _seen_imports:
            _seen_imports.add(cleaned)
            imports.append(cleaned)

    def _add_require(name: str) -> None:
        cleaned = name.strip("'\"")
        if cleaned and cleaned not in _seen_imports:
            _seen_imports.add(cleaned)
            require_calls.append(cleaned)

    def _add_fcall(name: str) -> None:
        if name and name not in _seen_fcalls:
            _seen_fcalls.add(name)
            function_calls.append(name)

    def _add_mcall(name: str) -> None:
        if name and name not in _seen_mcalls:
            _seen_mcalls.add(name)
            method_calls.append(name)

    def traverse(node: Node) -> None:
        # ── ES6 import: import X from 'module' ────────────────
        if node.type == "import_statement":
            source = node.child_by_field_name("source")
            if source:
                _add_import(_node_text(code, source))

        # ── call_expression: require() / fetch() / others ─────
        elif node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node is not None:
                func_text = _node_text(code, func_node)

                # Handle require('module')
                if func_text == "require":
                    args = node.child_by_field_name("arguments")
                    if args:
                        for arg_child in args.children:
                            if arg_child.type == "string":
                                _add_require(_node_text(code, arg_child))

                # Handle fetch('url') / fetch(variable)
                elif func_text == "fetch":
                    _add_fcall("fetch")
                    args = node.child_by_field_name("arguments")
                    if args:
                        for arg_child in args.children:
                            if arg_child.type in ("string", "template_string"):
                                fetch_calls.append(
                                    _node_text(code, arg_child).strip("'\"`")
                                )
                                break
                            elif arg_child.type == "identifier":
                                fetch_calls.append(_node_text(code, arg_child))
                                break

                # Handle bare function calls
                elif func_node.type == "identifier":
                    _add_fcall(func_text)

                # Handle method calls (e.g. axios.get, console.log)
                elif func_node.type == "member_expression":
                    _add_mcall(func_text)

        # Recurse into all children
        for child in node.children:
            traverse(child)

    traverse(tree.root_node)

    return {
        "imports": imports,
        "require_calls": require_calls,
        "function_calls": function_calls,
        "method_calls": method_calls,
        "fetch_calls": fetch_calls,
    }
