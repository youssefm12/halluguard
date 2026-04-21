# HalluGuard AI (LLM Truth Guard)

This is the Core Engine MVP for HalluGuard AI, an open-source AI reliability layer that detects, explains, and corrects hallucinations in AI-generated code.

## Phase 1 Implementation

Includes:
- Python AST Parsing (via Tree-sitter)
- PyPI Knowledge Verification
- Hallucination Scoring
- End-to-End Pipeline

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the MVP pipeline check on an example:
   ```bash
   python main.py
   ```
