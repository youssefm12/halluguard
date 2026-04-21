# HalluGuard AI — LLM Truth Guard

> Detect, explain, and correct hallucinations in AI-generated code.

An open-source AI reliability layer powered by AST parsing, knowledge verification, and RWKV local inference.

---

## Features (Phase 1 MVP)

| Module | Description |
|---|---|
| **Python Parser** | Tree-sitter AST: imports, functions, methods, decorators, async, classes |
| **JS/TS Parser** | Tree-sitter AST: ES6 imports, require(), fetch/axios, method calls |
| **PyPI Verifier** | Live package validation with stdlib detection and TTL cache |
| **npm Verifier** | Live registry validation with Node.js built-in detection and TTL cache |
| **RWKV Engine** | Lazy model loader, inference engine, hybrid routing (local + cloud) |
| **Scorer** | Weighted blend of AST + Knowledge + RWKV signals with severity levels |
| **Corrector** | Fuzzy match suggestions, common hallucination pattern dictionary |
| **Pipeline** | Single `analyze()` entry point orchestrating all modules |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the demo
python main.py

# 3. Run tests
# On Windows (bypass langsmith plugin conflict):
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest tests/ -v
```

## Usage

```python
from core.pipeline import analyze

code = '''
import requests
import fake_library
fake_library.do_magic()
fetchUserData("http://example.com")
'''

report = analyze(code, language="python")
print(report.to_dict())
```

## Output Format

```json
{
  "file": "snippet.py",
  "risk_score": 42,
  "confidence": "MEDIUM",
  "hallucinations": [
    {
      "line": 0,
      "type": "unknown_import",
      "token": "fake_library",
      "explanation": "Package 'fake_library' was not found on the package registry.",
      "suggestion": "Verify package spelling or find a valid alternative.",
      "severity": "HIGH"
    }
  ],
  "suggestions": [
    {
      "token": "fetchUserData",
      "suggestion": "requests.get(url)",
      "explanation": "Common LLM hallucination; use requests.get().",
      "confidence": "HIGH"
    }
  ]
}
```

## Project Structure

```
halluguard-ai/
├── core/
│   ├── parser/          # AST parsing (Python + JS/TS)
│   ├── rwkv_engine/     # RWKV model loader, inference, hybrid router
│   ├── verifier/        # PyPI + npm knowledge verification
│   ├── scorer/          # Hallucination risk scoring
│   ├── corrector/       # Correction suggestion engine
│   └── pipeline.py      # End-to-end orchestrator
├── tests/               # 70 unit + integration tests
├── api/                 # REST API (FastAPI) — Phase 4
├── cli/                 # CLI tool — Phase 4
├── vscode-extension/    # VSCode Extension — Phase 2
├── github-action/       # GitHub Action Bot — Phase 3
├── benchmarks/          # Benchmark suite — Phase 5
├── docs/                # Architecture documentation
└── models/              # Local RWKV model files
```

## Tech Stack

- **Python 3.11+**
- **Tree-sitter** — AST parsing (Python, JavaScript, TypeScript grammars)
- **PyPI / npm APIs** — Knowledge verification
- **RWKV** — Local inference engine (optional, graceful fallback)
- **FastAPI** — REST API layer (Phase 4)

## License

MIT License. See [LICENSE](LICENSE).
