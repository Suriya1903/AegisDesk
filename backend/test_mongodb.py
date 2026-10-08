import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, PyMongoError


# ============================================================
# AegisDesk AI - MongoDB Atlas Connection Test
# ============================================================

# Get the directory containing this Python file.
# This will always be:
# D:\AegisDesk\backend
BASE_DIR = Path(__file__).resolve().parent

# Explicitly load:
# D:\AegisDesk\backend\.env
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


def test_mongodb_connection():
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE")

    print("=" * 60)
    print("        AegisDesk AI - MongoDB Connection Test")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Check .env file
    # --------------------------------------------------------
    print(f"\n.env location:")
    print(f"   {ENV_FILE}")

    if not ENV_FILE.exists():
        print("\n❌ .env file was not found.")
        print(f"Expected location: {ENV_FILE}")
        sys.exit(1)

    print("✅ .env file found")

    # --------------------------------------------------------
    # 2. Check environment variables
    # --------------------------------------------------------
    if not mongodb_uri:
        print("\n❌ MONGODB_URI is missing.")
        print("Please check backend/.env")
        sys.exit(1)

    if not database_name:
        print("\n❌ MONGODB_DATABASE is missing.")
        print("Please check backend/.env")
        sys.exit(1)

    print("✅ MONGODB_URI found")
    print(f"✅ Database name: {database_name}")

    # --------------------------------------------------------
    # 3. Connect to MongoDB Atlas
    # --------------------------------------------------------
    client = None

    try:
        print("\nConnecting to MongoDB Atlas...")

        client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=10000,
        )

        # ----------------------------------------------------
        # 4. Ping MongoDB
        # ----------------------------------------------------
        client.admin.command("ping")

        print("✅ MongoDB Atlas connection successful!")
        print("✅ Ping successful!")

        # ----------------------------------------------------
        # 5. Access AegisDesk database
        # ----------------------------------------------------
        database = client[database_name]

        print(f"✅ Database accessible: {database_name}")

        # ----------------------------------------------------
        # 6. Check collections
        # ----------------------------------------------------
        collections = database.list_collection_names()

        print("\nExisting collections:")

        if collections:
            for collection in collections:
                print(f"   • {collection}")
        else:
            print("   No collections yet.")
            print("   This is expected for a new AegisDesk database.")

        print("\n" + "=" * 60)
        print("        ✅ MONGODB TEST PASSED")
        print("=" * 60)

    except ConfigurationError as error:
        print("\n❌ MongoDB configuration error.")
        print(error)
        sys.exit(1)

    except ConnectionFailure as error:
        print("\n❌ Could not connect to MongoDB Atlas.")
        print(error)

        print("\nCheck:")
        print("1. MongoDB Atlas cluster is active")
        print("2. Database username/password are correct")
        print("3. Atlas network access/IP configuration")
        print("4. MONGODB_URI in backend/.env")

        sys.exit(1)

    except PyMongoError as error:
        print("\n❌ MongoDB error.")
        print(error)
        sys.exit(1)

    finally:
        if client is not None:
            client.close()
            print("\nMongoDB connection closed.")


if __name__ == "__main__":
    test_mongodb_connection()