import os
from pathlib import Path


EDGE_CONFIG_FILE = Path(os.environ.get("EDGE_CONFIG_FILE", "/data/edge.env"))
EDGE_CONFIG_KEYS = ("CLOUD_BASE_URL", "EDGE_CLIENT_ID", "EDGE_SECRET")


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in EDGE_CONFIG_KEYS:
            values[key] = value.strip().strip('"').strip("'")
    return values


def read_edge_config() -> dict[str, str]:
    file_values = _parse_env_file(EDGE_CONFIG_FILE)
    return {
        key: (os.environ.get(key) or file_values.get(key) or "").strip()
        for key in EDGE_CONFIG_KEYS
    }


def is_edge_configured() -> bool:
    values = read_edge_config()
    return all(values.get(key) for key in EDGE_CONFIG_KEYS)


def clear_edge_config() -> None:
    """Remove stored edge credentials so the Pi can be paired again."""
    if EDGE_CONFIG_FILE.exists():
        EDGE_CONFIG_FILE.unlink()


def write_edge_config(*, cloud_base_url: str, edge_client_id: str, edge_secret: str) -> None:
    EDGE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        [
            "# Written by the Vendiqo Pi pairing flow.",
            f"CLOUD_BASE_URL={cloud_base_url.rstrip('/')}",
            f"EDGE_CLIENT_ID={edge_client_id}",
            f"EDGE_SECRET={edge_secret}",
            "",
        ],
    )
    EDGE_CONFIG_FILE.write_text(body, encoding="utf-8")
    try:
        EDGE_CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
