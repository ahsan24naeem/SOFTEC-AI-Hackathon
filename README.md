# Email Classifier – AI Backend

> **Hackathon-ready** modular Python backend that parses `.eml` files, extracts structured data via **Gemini LLM**, scores them with an **ML ensemble** (Random Forests), and provides **SHAP-based explainability**.

---

## Architecture

```
email-classifier/
├── src/
│   ├── core/               # All parsing, LLM, ML, and utility logic
│   │   ├── parser.py        ← EMLParser (stdlib email)
│   │   ├── extractor.py     ← LLMExtractor (Gemini)
│   │   ├── feature_engine.py← FeatureTransformer (→ numpy vector)
│   │   ├── scorer.py        ← EnsembleScorer (Random Forests)
│   │   ├── explainer.py     ← SHAPExplainer (TreeExplainer)
│   │   └── link_checker.py  ← LinkChecker (trust scoring)
│   ├── models/
│   │   ├── schemas.py       ← Pydantic v2 data models
│   │   └── artifacts/       ← Serialized .pkl model files
│   └── api/
│       └── controller.py    ← EmailController (façade for frontend)
├── frontend/                # Reserved for Streamlit (teammate)
├── data/
│   ├── raw_eml/             # Sample .eml files
│   └── synthetic/           # Training data
├── pipeline.py              # CLI entry point
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
copy .env.example .env
# Edit .env and set GOOGLE_API_KEY

# 4. Run the pipeline
python pipeline.py data/raw_eml/sample_admission.eml --pretty
```

## Pipeline Flow

```
.eml file
  │
  ├─► EMLParser          → RawEmailEnvelope
  ├─► LLMExtractor       → BaseEmailData (typed: Admission/Job/Event/Misc)
  ├─► FeatureTransformer  → numpy vector (17 features)
  ├─► EnsembleScorer      → MLScores (urgency, fit, importance)
  ├─► SHAPExplainer       → feature contributions per dimension
  └─► LinkChecker         → LinkTrust (1-10 per URL)
         │
         ▼
    PipelineResult (unified JSON payload)
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Pydantic v2 schemas** | Strong validation between every pipeline stage; the frontend gets a typed contract |
| **Gemini `response_mime_type: application/json`** | Forces structured JSON output, eliminating regex parsing |
| **Synthetic RF training** | Bootstrap models instantly; swap in real data later without code changes |
| **SHAP TreeExplainer** | Exact (not approximate) feature attributions for tree-based models |
| **Offline link checking** | Domain reputation heuristics run in <1ms; optional HTTP probes for production |
| **Controller façade** | Frontend imports only `EmailController` — zero coupling to internals |

## Frontend Integration

```python
from src.api import EmailController

controller = EmailController()
result = controller.process("path/to/email.eml")

# result.extracted_data   → typed email data
# result.scores           → urgency / fit / importance
# result.shap_explanations→ per-feature contributions
# result.link_trust       → trust scores for every URL
# result.next_steps       → 1-3 actionable items

# Serialize to JSON for display
print(result.model_dump_json(indent=2))
```

## CLI Usage

```bash
# Basic
python pipeline.py email.eml

# Pretty-print + write to file
python pipeline.py email.eml --pretty --output result.json

# Enable HTTP link probes
python pipeline.py email.eml --probe-links

# Override model
python pipeline.py email.eml --model gemini-2.0-pro

# Verbose logging
python pipeline.py email.eml -v -p
```
