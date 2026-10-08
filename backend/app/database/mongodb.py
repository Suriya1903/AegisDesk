import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


# ---------------------------------------------------------
# Locate backend/.env reliably
# ---------------------------------------------------------
# mongodb.py is located at:
#
# D:\AegisDesk\backend\app\database\mongodb.py
#
# parents[0] -> database
# parents[1] -> app
# parents[2] -> backend
#
# Therefore:
# backend/.env = parents[2] / ".env"
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIRECTORY = CURRENT_FILE.parents[2]
ENV_FILE = BACKEND_DIRECTORY / ".env"

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "aegisdesk")


# ---------------------------------------------------------
# Validate configuration
# ---------------------------------------------------------

if not MONGODB_URI:
    raise RuntimeError(
        f"MONGODB_URI is not configured. "
        f"Please check: {ENV_FILE}"
    )


# ---------------------------------------------------------
# MongoDB client
# ---------------------------------------------------------

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
)


# ---------------------------------------------------------
# AegisDesk database
# ---------------------------------------------------------

database: Database = client[MONGODB_DATABASE]


# ---------------------------------------------------------
# Database helper functions
# ---------------------------------------------------------

def get_database() -> Database:
    """
    Return the AegisDesk MongoDB database.
    """
    return database


def check_database_connection() -> bool:
    """
    Check whether MongoDB Atlas is reachable.
    """
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False


def close_database_connection() -> None:
    """
    Close the MongoDB client connection.
    """
    client.close()