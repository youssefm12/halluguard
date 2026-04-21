"""
HalluGuard AI — CLI Analyzer Wrapper

Designed specifically for headless operation and CI/CD pipelines.
Takes a list of files, runs analysis, and prints the raw JSON array of reports to stdout.
"""
import sys
import json
import os
import argparse
from typing import Any

from core.pipeline import analyze


def ext_to_lang(ext: str) -> str | None:
    if ext in (".py",):
        return "python"
    elif ext in (".js", ".mjs", ".cjs"):
        return "javascript"
    elif ext in (".ts", ".tsx"):
        return "typescript"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="HalluGuard Analysis CLI")
    parser.add_argument("files", nargs="+", help="List of files to analyze")
    args = parser.parse_args()

    reports: list[dict[str, Any]] = []

    for file_path in args.files:
        if not os.path.isfile(file_path):
            continue

        _, ext = os.path.splitext(file_path)
        lang = ext_to_lang(ext.lower())

        if not lang:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            report = analyze(code, language=lang, file_name=file_path)
            reports.append(report.to_dict())

        except Exception as e:
            # Inject error directly into the report format for debugging
            reports.append({
                "file": file_path,
                "risk_score": 0,
                "confidence": "LOW",
                "hallucinations": [],
                "suggestions": [],
                "error": str(e)
            })

    # Output strictly the JSON array so the GitHub Action can parse it
    print(json.dumps(reports, ensure_ascii=False))


if __name__ == "__main__":
    main()
