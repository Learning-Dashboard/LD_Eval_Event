import sys
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

os.environ.setdefault("LD_API_KEY", "test-ld-api-key")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
