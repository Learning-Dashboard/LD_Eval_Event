# LD Eval – Metric Recalculation Service

**LD Eval** is the second stage of the Learning Dashboard pipeline.  
It receives event notifications from **LD Connect** (`POST /api/event`) and:

1. **Maps** the event to the triggered metrics, factors and indicators of the active *quality model*  
2. **Recomputes** only the affected artefacts (student‑level or team‑level)  
3. **Stores** the results in MongoDB for retrieval by the dashboard front‑end  
4. **Responds immediately** (HTTP 200) so ingestion remains low‑latency

A daily background job can refresh *all* metrics to ensure data consistency.

---

## Key features

| Feature | What it does | Where to look |
| --- | --- | --- |
| Event‑driven recomputation | Recalculates the specific triggered metrics/factors/indicators on each incoming event | `logic/*_recalculation.py` |
| Quality model plug‑ins | Each QM lives in `QUALITY_MODELS/<model_name>`; auto‑discovery at startup | `app.py` |
| Asynchronous processing | Events are handled in background threads → API returns instantly | `app.py` |
| Daily full refresh | `apscheduler` kicks `ld_refresh.py` at a configurable time window | `ld_refresh.py` |
| Docker‑first | Lightweight image, Gunicorn (4 workers × 25 threads) | `dockerfile`, `docker‑compose.yml` |

---

## Architecture

```text
┌────────────┐   POST /api/event   ┌────────────┐            ┌──────────────┐
│ LD Connect │ ───────────────────▶│   LD Eval  │── write ──▶│   MongoDB    │
└────────────┘                      └────────────┘            └──────────────┘
                                        ▲
                                        │ REST pull
                                        ▼
                               Learning Dashboard UI
```

---

## Folder layout

```text
LD_Eval_Event/
├─ API_calls/       # REST clients (dashboard, external services)
├─ QUALITY_MODELS/  # Plug‑in folder (one sub‑dir per QM)
├─ config/          # logging, settings, source metadata
├─ config_files/    # per‑instance JSON/YAML (HMAC keys, etc.)
├─ database/        # Mongo wrapper
├─ logic/           # *_logic packages for metrics, factors, indicators
├─ utils/           # helpers, CLI, stress‑test inputs
├─ ld_refresh.py    # full nightly recomputation job
└─ app.py           # Flask factory – entry‑point for Gunicorn
```

---

## Quick start (local)

> Requires **Python ≥ 3.10** and **MongoDB ≥ 5.0**.

```bash
git clone https://github.com/PabloGomezNa/LD_Eval_Event.git
cd LD_Eval_Event
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp template.env .env        # edit credentials & scheduler time
python app.py               # development server on :5001
```

Send a test envelope:

```bash
curl -X POST http://127.0.0.1:5001/api/event      -H 'Content-Type: application/json'      -d '{"event_type":"PullRequestEvent","prj":"TeamA","author_login":"alice"}'
```

You should get `{"status":"received"}` and see the background logs.

---

## Production with Docker Compose

```bash
docker compose up -d --build ld_eval
```

* Exposes port **5001**  
* Uses the same `mongo_data` volume and `qrapids` network as LD Connect

---

## Environment variables

| Variable | Description |
| --- | --- |
| `MONGO_HOST` / `MONGO_PORT` | MongoDB host & port |
| `MONGO_USER` / `MONGO_PASS` | Credentials (leave blank for local dev) |
| `MONGO_AUTHSRC` | Auth DB (usually `admin`) |
| `BASE_GESSI_URL` | REST endpoint of the public dashboard |
| `QUALITY_MODELS_DIR` | Path to `QUALITY_MODELS` folder |
| Scheduler: `_Start_scheduler_date`, `_End_scheduler_date`, `_Hour_scheduler` … | Daily refresh window (see `config_files/config_variables.py`) |

All vars can be placed in `.env` and are loaded automatically.

---

## API reference

### `POST /api/event`

| Body field | Type | Notes |
| --- | --- | --- |
| `event_type` | string | Matches one of the sources defined in `config/sources_config.json` |
| `prj` | string | External team identifier |
| `author_login` | string | GitHub/Taiga username |
| `quality_model` | *optional* string | Override the default QM for the team |

Immediate response:

```json
{ "status": "received" }
```

Heavy computation runs in a separate thread.

---

## Testing

```bash
pytest             # unit tests (TODO)
locust -f tests/   # optional load test scripts
```

---

## License

Released under the **Apache License 2.0** – see [`LICENSE`](./LICENSE).

Part of the Master’s Thesis **“Redefinition of the Intake and Processing of Learning Dashboard Data”** (UPC · 2025).

---


