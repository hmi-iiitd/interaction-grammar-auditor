# Interaction Contract Auditor

LLM-assisted interface for Human-Robot Interaction auditing pipeline.

## Quick Start

### Local Development

```bash
# 1. Backend
cd app/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Frontend (separate terminal)
cd app/frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker

```bash
cd app
docker-compose up --build
# → http://localhost:5173 (frontend)
# → http://localhost:8000/docs (backend API docs)
```

## Architecture

```
app/
├── .env                           # NIM API keys (gitignored)
├── docker-compose.yml
├── backend/                       # FastAPI Python
│   ├── main.py                    # Entry point
│   ├── config.py                  # Settings from .env
│   ├── routers/                   # API endpoints
│   ├── modules/                   # A–H pipeline modules
│   ├── llm/                       # NIM + mock providers
│   ├── transformer/               # AuditResult → PDF schema
│   └── schemas/                   # JSON schemas
├── frontend/                      # Vite + React
│   └── src/pages/                 # 6 UI pages
└── dataset/                       # 18 scenario fixtures
```

## Modules

| Module | File | Purpose |
|--------|------|---------|
| A | `loader.py` | Load scenario folders |
| B | `schema_validator.py` | Validate against JSON schemas |
| C | `evidence_extractor.py` | Extract evidence windows |
| D | `prompt_builder.py` | Build constrained LLM prompts |
| E | `explanation.py` | Generate LLM explanations |
| F | `grounded_qa.py` | Grounded Q&A (LLM + safety) |
| G | `report_generator.py` | Markdown/JSON report generation |
| H | `batch_runner.py` | Batch processing |

## LLM Configuration

- **Provider**: NVIDIA NIM (OpenAI-compatible)
- **Primary**: `deepseek-ai/deepseek-v4-flash`
- **Fallback**: `nvidia/nemotron-3-super-120b-a12b`
- **Key rotation**: Automatic on rate-limit/403

## Dataset

18 scenarios (6 SAT, 12 UNSAT) derived from NAO S3 turn-taking traces.
Each scenario folder: `raw/ traces/ contracts/ audits/ metadata.yaml`

## Tests

```bash
cd app/backend && pytest tests/ -v
```
