# fcm_hms

Hospital Management System — FastAPI + MongoDB (Atlas) + Firebase.

## Local run

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

**Option A — real MongoDB Atlas** (needs the host IP in your Atlas IP allow-list):
```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

**Option B — offline / sandbox (no Atlas access):** in-memory MongoDB with
file persistence. Data is saved to `local_db.json` (every 30s + on shutdown)
and restored on the next start, so it survives restarts:
```bash
./venv/bin/uvicorn run_local:app --host 0.0.0.0 --port 8000
```

Default admin (see `core/config.py`): phone `8432144275` / password `Shahzain@144275`.

## Deploy (one-click)

The repo ships a `Dockerfile` plus platform blueprints:

- **Render**: New + → Blueprint → select this repo & branch → Deploy.
- **Railway**: New Project → Deploy from GitHub repo (uses `railway.json`).

The app connects to the MongoDB Atlas cluster configured in `core/database.py`.
If the host's IP is not in your Atlas **Network Access → IP Access List**,
add the platform's egress range (e.g. Render: `167.142.112.33/32`,
`159.65.149.142/32`, or `0.0.0.0/0` for any IP).

Env vars (`.env` in the repo is used as fallback): `DIGIKEY_*`, `EMAIL_USER`,
`EMAIL_PASS`, `ADHAR_KEY`, `ADHAR_SECRECT`, `MONGO_URI` (optional override).
