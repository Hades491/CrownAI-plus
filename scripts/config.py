import os
from pathlib import Path

# Loads a .env file if present (simple, no external dependency)
def _load_dotenv():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

_load_dotenv()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "db" / "pulse.db"))

if not YOUTUBE_API_KEY:
    print("WARNING: YOUTUBE_API_KEY is not set. Create a .env file (see .env.example).")
