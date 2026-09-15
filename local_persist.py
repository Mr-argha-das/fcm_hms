"""Persistence for the local in-memory MongoDB (mongomock) runs.

run_local.py swaps MongoEngine's client for mongomock, so data would be lost
on every restart. This module snapshots the whole database to a JSON file:

  - restore_db()   : called once at startup — reloads all collections
                     (ObjectIds are preserved, so existing references/JWTs
                     stay valid)
  - dump_db()      : full snapshot, written atomically (tmp file + replace)
  - start_background_dumper(): re-snapshots every 30s, plus on shutdown

Data file: <repo>/local_db.json (gitignored).
"""
import base64
import datetime as dt
import json
import os
import threading
import time

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_db.json")
DUMP_INTERVAL_SECONDS = 30


def _encode(obj):
    """JSON encoder fallback for BSON-ish types."""
    from bson import ObjectId

    if isinstance(obj, ObjectId):
        return {"__t": "ObjectId", "v": str(obj)}
    if isinstance(obj, dt.datetime):
        return {"__t": "DateTime", "v": obj.isoformat()}
    if isinstance(obj, dt.date):
        return {"__t": "Date", "v": obj.isoformat()}
    if isinstance(obj, bytes):
        return {"__t": "Bytes", "v": base64.b64encode(obj).decode("ascii")}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _decode(obj):
    """JSON object_hook that reverses _encode()."""
    from bson import ObjectId

    t = obj.get("__t") if isinstance(obj, dict) else None
    if t == "ObjectId":
        return ObjectId(obj["v"])
    if t == "DateTime":
        return dt.datetime.fromisoformat(obj["v"])
    if t == "Date":
        return dt.date.fromisoformat(obj["v"])
    if t == "Bytes":
        return base64.b64decode(obj["v"])
    return obj


def get_db():
    from mongoengine import get_db

    return get_db()


def dump_db() -> int:
    """Snapshot every collection to DB_FILE (atomic write). Returns doc count."""
    db = get_db()
    data = {}
    total = 0
    for name in db.list_collection_names():
        docs = list(db[name].find({}))
        data[name] = docs
        total += len(docs)

    tmp = DB_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, default=_encode)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DB_FILE)
    return total


def restore_db() -> int:
    """Load every collection from DB_FILE. Returns doc count restored."""
    if not os.path.exists(DB_FILE):
        return 0
    try:
        with open(DB_FILE) as f:
            data = json.load(f, object_hook=_decode)
    except (json.JSONDecodeError, OSError):
        return 0

    db = get_db()
    total = 0
    for name, docs in data.items():
        if not docs:
            continue
        db[name].insert_many(docs)
        total += len(docs)
    return total


def start_background_dumper() -> threading.Thread:
    def _loop():
        while True:
            time.sleep(DUMP_INTERVAL_SECONDS)
            try:
                dump_db()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="db-dumper")
    t.start()
    return t
