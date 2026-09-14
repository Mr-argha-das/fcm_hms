import os
import pymongo
from mongoengine import connect

def init_db():
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGO_HOST") or "mongodb+srv://infozodex_db_user:absolutions@data.yycywiw.mongodb.net"
    use_mock = os.getenv("USE_MOCK_DB", "").lower() in ("true", "1", "yes")

    if not use_mock:
        try:
            test_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            test_client.admin.command('ping')
            connect(db="hms_db10", host=mongo_uri)
            print("Connected to remote MongoDB")
            return
        except Exception as e:
            print(f"Notice: Could not connect to remote MongoDB ({e}), falling back to mongomock...")

    try:
        import mongomock
        connect("hms_db10", mongo_client_class=mongomock.MongoClient)
        print("Connected to in-memory MongoDB (mongomock)")
    except Exception as e:
        print(f"Error connecting to database: {e}")

