# IncuBrix Economics Engine

Cost estimation layer for IncuBrix video generation. Before a job is sent to any provider, this engine figures out which provider is cheapest, checks if it fits within budget, and returns a recommendation with a reason.

Built as part of the Video Gen Services platform - Capability 4.

---

## What it does

- Estimates cost across 5 providers (OpenAI, Runway, fal, Replicate, PiAPI)
- Each provider charges differently - per second, credits, runtime etc. The engine normalizes all of them to USD so they can be compared
- Blocks jobs that exceed budget cap, warns when close
- Recommends async/batch mode when it saves more than 15%
- Calculates fallback cost if the primary provider fails
- Supports margin simulation for pass-through, markup, and protected-margin modes
- Admin console to edit provider pricing without touching code
- All decisions are stored and can be retrieved later

---

## Project structure

```
economics_engine/
├── main.py                          entry point
├── config.py                        settings
├── requirements.txt
├── .env.example                     
│
├── api/
│   ├── economics_router.py          main API endpoints
│   └── admin_router.py              admin endpoints
│
├── services/
│   ├── cost_normalizer.py           per-provider pricing math
│   ├── estimation_engine.py         runs cost estimation for all providers
│   ├── policy_engine.py             budget block, warning, async savings rules
│   ├── route_ranker.py              scores and ranks routes
│   ├── fallback_estimator.py        retry and fallback cost
│   ├── margin_engine.py             markup and margin simulation
│   ├── analytics_service.py         event tracking
│   └── pricing_registry_service.py  loads provider profiles
│
├── models/                          database table definitions
├── schemas/                         input/output validation
├── data/
│   ├── pricing_registry.json        mock pricing for all 5 providers
│   ├── sample_requests.json         sample test requests
│   └── sample_requests_uat.json     UAT scenarios
│
├── migrations/
│   └── 001_init.sql                 raw SQL schema
│
├── scripts/
│   └── seed_pricing_data.py         loads provider data into DB
│
├── tests/
│   ├── test_sprint1.py              50 tests
│   └── test_sprint2.py              28 tests
│
└── frontend/
    ├── simulation_ui.html           cost estimation form
    └── admin_console.html           provider management UI
```

---

## Setup

Needs Python 3.10 or above.

```bash
# create virtual environment
python -m venv venv

# activate it
source venv/bin/activate        # mac/linux
venv\Scripts\activate           # windows

# install packages
pip install -r requirements.txt

```


```bash
# load provider pricing data into DB (run once)
python scripts/seed_pricing_data.py
```

---

## Running

```bash
uvicorn main:app --reload --port 8000
```

---

## Testing

```bash
# run all tests
pytest tests/ -v

# sprint 1 only
pytest tests/test_sprint1.py -v

# sprint 2 only
pytest tests/test_sprint2.py -v
```

78 tests total — 50 from sprint 1, 28 from sprint 2.

---

## API endpoints

| Method | URL | What it does |
|---|---|---|
| POST | /api/video-economics/estimate | run a cost estimate |
| POST | /api/video-economics/simulate | same but sandbox mode |
| GET | /api/video-economics/estimate/{id} | get a past estimate |
| POST | /api/video-economics/estimate/{id}/override | override recommendation |
| GET | /api/video-economics/providers | list active providers |
| GET | /api/video-economics/admin/providers | all providers including inactive |
| PATCH | /api/video-economics/admin/providers/{key} | update provider pricing |
| POST | /api/video-economics/admin/providers/{key}/rollback | roll back to previous version |
| POST | /api/video-economics/admin/providers/{key}/toggle | activate or deactivate |
| GET | /api/video-economics/admin/thresholds | get policy thresholds |
| PATCH | /api/video-economics/admin/thresholds | update thresholds |
| GET | /api/video-economics/admin/analytics | view analytics events |

Full interactive docs at `http://localhost:8000/docs`

---

## Frontend

Open these directly in a browser while the server is running:

- `frontend/simulation_ui.html` — submit a job request and see the cost recommendation
- `frontend/admin_console.html` — manage provider profiles, update thresholds, view analytics events

---

## Notes

- Uses SQLite by default. To switch to PostgreSQL change `DATABASE_URL` in `.env`
- All estimates are stored in the database for audit purposes
- `simulation_mode` is always true for MVP — no real provider calls are made
- Provider pricing profiles are versioned — every edit creates a new version and the old one is kept
