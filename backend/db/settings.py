import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SETTINGS_FILE = BASE_DIR / "settings.py"

spec = importlib.util.spec_from_file_location("settings", SETTINGS_FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if not spec or not spec.loader:
    raise ValueError(f"Failed to load settings from {SETTINGS_FILE}")

settings = module.settings

__all__ = ["settings"]
