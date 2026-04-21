"""
Main entrypoint for HalluGuard AI core testing.
"""
from core import pipeline
import json

def main():
    print("Running HalluGuard AI Pipeline (Phase 1 MVP)...\\n")
    
    example_code = """
import requests
import this_library_does_not_exist_at_all
import sys

def main():
    print(sys.version)
    response = requests.get("https://api.github.com")
    this_library_does_not_exist_at_all.make_magic()
"""
    print("Code Snippet to analyze:")
    print("-" * 40)
    print(example_code.strip())
    print("-" * 40 + "\\n")
    
    try:
        report = pipeline.analyze(example_code, language="python")
        print("Analysis Complete!")
        print(json.dumps(report, indent=2))
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    main()
