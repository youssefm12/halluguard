"""
Pipeline module for HalluGuard AI.
Coordinates parser, verifier, scorer, and corrector.
"""
from core.parser import python_parser
from core.verifier import pypi_verifier
from core.scorer import hallucination_scorer

def analyze(code: str, language: str = "python") -> dict:
    """
    Analyzes a given code snippet for hallucinations.
    
    Args:
        code: The source code to analyze.
        language: The programming language (currently only python).
        
    Returns:
        dict: The complete hallucination report.
    """
    # 1. Parse the AST
    tokens = python_parser.extract(code, language)
    
    # 2. Verify knowledge
    knowledge = pypi_verifier.check(tokens)
    
    # 3. Compute Risk Score
    report = hallucination_scorer.compute(tokens, knowledge)
    
    # Append the file name for completeness
    report["file"] = "snippet." + ("py" if language == "python" else "txt")
    
    return report
