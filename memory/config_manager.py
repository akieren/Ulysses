import json
import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def ensure_dirs() -> None:
    """Gereken klasörleri (config, memory) otomatik oluşturur."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "memory").mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {"lm_studio_url": "http://localhost:1234/v1/chat/completions"}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\033[31m[ERROR] Failed to load settings: {e}\033[0m")
        return {"lm_studio_url": "http://localhost:1234/v1/chat/completions"}


def get_url() -> str:
    return load_settings().get("lm_studio_url")
