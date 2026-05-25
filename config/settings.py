import os
from dotenv import load_dotenv
from pathlib import Path

# Determine the base directory (adjust if needed)
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent


# Load centralized root configuration first, then module-local values for
# standalone runs. Existing environment variables keep priority.
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Please set it in the root .env or this module's .env file."
        )
    return value


QUALITY_MODELS_DIR = os.getenv("QUALITY_MODELS_DIR", "QUALITY_MODELS")
BASE_GESSI_URL = os.getenv("BASE_GESSI_URL", "")
LD_API_KEY = _require_env("LD_API_KEY")
LD_API_KEY_HEADER = "X-LD-API-Key"


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
