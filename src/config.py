import os
from pathlib import Path
from typing import Dict, Any

import yaml


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_env(path: str = None) -> None:
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(path)
    except ImportError:
        pass
