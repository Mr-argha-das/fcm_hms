"""Local dev shim: run the app with an in-memory MongoDB (mongomock)
that PERSISTS to local_db.json.

The production MongoDB Atlas cluster is not reachable from this sandbox
(its IP allowlist rejects our address), so this swaps the MongoClient class
for mongomock's BEFORE the app connects. Data is saved to local_db.json
every 30s and on shutdown, and restored automatically on the next start.

Run with:
    ./venv/bin/uvicorn run_local:app --host 0.0.0.0 --port 8000
"""
import mongomock
import mongoengine.connection

mongoengine.connection.MongoClient = mongomock.MongoClient  # type: ignore[misc]

from main import app  # noqa: E402  (init_db() runs at import time)
from local_persist import dump_db, restore_db, start_background_dumper  # noqa: E402


def _shutdown_dump():
    try:
        n = dump_db()
        print(f"💾 Saved {n} documents to local_db.json")
    except Exception as e:  # pragma: no cover
        print("💾 Save failed:", e)


_restored = restore_db()
if _restored:
    print(f"📦 Restored {_restored} documents from local_db.json")

app.on_event("shutdown")(lambda: _shutdown_dump())
start_background_dumper()
