import sys
from pathlib import Path

import mongomock
import pytest
import pymongo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Replace PyMongo's client before importing app.main so the complete test
# suite uses an isolated in-memory MongoDB. No real AegisDesk data is touched.
_ORIGINAL_MONGO_CLIENT = pymongo.MongoClient
pymongo.MongoClient = mongomock.MongoClient

import app.main as main  # noqa: E402

pymongo.MongoClient = _ORIGINAL_MONGO_CLIENT

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def app_module():
    return main


@pytest.fixture(scope="session")
def client(app_module):
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def clean_test_database(app_module):
    # This is the isolated mongomock database, never the user's MongoDB Atlas DB.
    app_module.tickets_collection.delete_many({})
    app_module.audit_collection.delete_many({})
    app_module.users_collection.delete_many({})
    app_module.seed_demo_users()
    yield
