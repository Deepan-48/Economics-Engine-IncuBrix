# IncuBrix Economics Engine v2

Enhancement of v1 — production-grade commercial intelligence layer for video generation cost management.

Builds on v1 (Sprint 1 + Sprint 2) and adds:
- Multi-component cost normalization with modifier chains
- Budget reservations, settlement, and release
- Margin and markup simulation
- Scenario simulator with CSV export
- Cost ledger with actual cost import and variance tracking
- Spend forecasting and anomaly detection
- Config versioning with stage → validate → approve → activate → rollback workflow
- Integration adapters for routing, execution, and billing services

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts_v2/seed_v2.py
```

## Run tests

```
pytest tests_v2/test_v2_sprint1.py -v
```

## Start server

```
uvicorn main:app --reload --port 8000
```

## Endpoints

Open http://localhost:8000/docs

v1 endpoints still work at /api/video-economics/
v2 endpoints are at /api/economics/v2/
