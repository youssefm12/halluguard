"""
Knowledge Verifier module.
Checks imported packages against PyPI.
"""
import requests
import builtins
import sys
from typing import Dict, Any

# Simple in-memory cache to prevent redundant HTTP requests 
# (simulating the 24h TTL cache required in MVP)
_PYPI_CACHE: Dict[str, bool] = {}

def is_standard_library(package_name: str) -> bool:
    """Check if a module is part of the Python standard library."""
    if package_name in sys.builtin_module_names:
        return True
    
    # Simple heuristic for stdlib using sys.stdlib_module_names (Python 3.10+)
    if hasattr(sys, 'stdlib_module_names'):
        return package_name in sys.stdlib_module_names
        
    return False

def check_package(package_name: str) -> dict:
    """
    Verifies if a specific Python package exists on PyPI.
    
    Args:
        package_name: The name of the package to verify.
        
    Returns:
        dict: A structured result indicating if the package exists.
    """
    result = {
        "package": package_name,
        "exists": False
    }
    
    # 1. Skip check for standard library modules
    if is_standard_library(package_name):
        result["exists"] = True
        result["type"] = "stdlib"
        return result
        
    # 2. Check local cache
    if package_name in _PYPI_CACHE:
        result["exists"] = _PYPI_CACHE[package_name]
        result["type"] = "pypi_cached"
        return result
        
    # 3. Request PyPI JSON API
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=5)
        exists = response.status_code == 200
        
        # Update cache
        _PYPI_CACHE[package_name] = exists
        
        result["exists"] = exists
        result["type"] = "pypi_api"
    except requests.RequestException:
        # If API fails (e.g. network error), we might fail open or fail closed. 
        # For hallucination detection, lacking proof means it might be an issue.
        result["exists"] = False
        result["type"] = "error"
        result["error"] = "Network request failed"
        
    return result

def check(tokens: dict) -> Dict[str, Any]:
    """
    Checks all found imports against external knowledge sources.
    
    Args:
        tokens: Output from the parser `extract()` method.
        
    Returns:
        dict: The mapped verification results for each import.
    """
    imports = tokens.get("imports", [])
    verified_modules = {}
    
    for imp in imports:
        verification = check_package(imp)
        verified_modules[imp] = verification
        
    return {
        "verified_imports": verified_modules
    }
