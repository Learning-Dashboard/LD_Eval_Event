import os
from dotenv import load_dotenv
from pathlib import Path

# Determine the base directory (adjust if needed)
BASE_DIR = Path(__file__).resolve().parent.parent


# Load environment variables from the .env file
load_dotenv(BASE_DIR / ".env")


QUALITY_MODELS_DIR = os.getenv("QUALITY_MODELS_DIR", "QUALITY_MODELS")
BASE_GESSI_URL = os.getenv("BASE_GESSI_URL", "")


# Mongo database settings
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "mongo")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASS = os.getenv("MONGO_PASS", "")
MONGO_AUTHSRC = os.getenv("MONGO_AUTHSRC", MONGO_DB)

if MONGO_USER and MONGO_PASS:
    MONGO_URI = (
        f"mongodb://{MONGO_USER}:{MONGO_PASS}"
        f"@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
        f"?authSource={MONGO_AUTHSRC}"
    )
else:
    MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
