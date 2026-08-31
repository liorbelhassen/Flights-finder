import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


DUFFEL_API_KEY = os.environ.get("DUFFEL_API_KEY", "")
DUFFEL_API_URL = os.environ.get("DUFFEL_API_URL", "https://api.duffel.com")

CHECK_INTERVAL_MINUTES = _int("CHECK_INTERVAL_MINUTES", 15)
DATABASE_PATH = os.environ.get("DATABASE_PATH", "flights.db")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = _int("SMTP_PORT", 587)
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "") or SMTP_USERNAME
SMTP_USE_TLS = (os.environ.get("SMTP_USE_TLS", "true").lower() != "false")

RUN_SCHEDULER = (os.environ.get("RUN_SCHEDULER", "true").lower() != "false")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = _int("PORT", 5000)
