# VoxFlow — voice operations, automated

Production code for the VoxFlow voice agent. See the top-level [README](../README.md).

- `voxflow_api/` — FastAPI app, voice pipeline, agent, LLM adapters
- `tests/` — pytest suite (LLM is faked; no API key needed to run tests)
- `Dockerfile` — production image
- `requirements.txt` — pinned deps

## Run locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m voxflow_api.seed --reset
uvicorn voxflow_api.main:app --reload --port 8000
```

## Test

```bash
pytest -q
```
