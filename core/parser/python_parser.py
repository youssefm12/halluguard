"""
Python AST Parser module using tree-sitter.
Extracts imports, function calls, and method calls.
"""
import tree_sitter_python
from tree_sitter import Language, Parser

# Initialize the language and parser
PY_LANGUAGE = Language(tree_sitter_python.language())

def extract(code: str, language: str = "python") -> dict:
    """
    Parses the provided code snippet and extracts imports and function/method calls.
    
    Args:
        code: The source code snippet to parse.
        language: The programming language of the snippet (only "python" supported currently).
        
    Returns:
        dict: containing sets of imports, function_calls, and method_calls.
    """
    if language.lower() != "python":
        raise ValueError(f"Language '{language}' is not yet supported. Only 'python' is supported in the current version.")
        
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(code, "utf8"))
    
    imports = set()
    function_calls = set()
    method_calls = set()
    
    def traverse(node):
        # Handle simple import: `import requests`
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.add(code[child.start_byte:child.end_byte].split('.')[0])
                    
        # Handle from import: `from requests import get`
        elif node.type == "import_from_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.add(code[child.start_byte:child.end_byte].split('.')[0])
                    break # Just grab the root module
                    
        # Handle function and method calls
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node is not None:
                if func_node.type == "identifier":
                    function_calls.add(code[func_node.start_byte:func_node.end_byte])
                elif func_node.type == "attribute":
                    # It's a method call like `requests.get`
                    method_calls.add(code[func_node.start_byte:func_node.end_byte])
                    
        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    
    return {
        "imports": list(imports),
        "function_calls": list(function_calls),
        "method_calls": list(method_calls)
    }
