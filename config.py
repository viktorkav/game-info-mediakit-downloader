import json
import os
import sys
from pathlib import Path


class MissingIGDBCredentialsError(RuntimeError):
    """Raised when IGDB credentials are not configured locally."""


def _config_candidates():
    project_dir = Path(__file__).resolve().parent
    candidates = []

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "local_config.json")

    candidates.append(project_dir / "local_config.json")
    return candidates


def load_igdb_credentials():
    client_id = os.getenv("IGDB_CLIENT_ID")
    client_secret = os.getenv("IGDB_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret

    for path in _config_candidates():
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)

        client_id = data.get("IGDB_CLIENT_ID") or data.get("client_id")
        client_secret = data.get("IGDB_CLIENT_SECRET") or data.get("client_secret")

        if client_id and client_secret:
            return client_id, client_secret

    raise MissingIGDBCredentialsError(
        "Set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET or create a local_config.json file."
    )
