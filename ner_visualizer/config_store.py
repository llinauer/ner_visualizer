import json
import os
from typing import Any

# model_config.json is next to app.py (one level above this file)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_CONFIG_PATH = os.path.join(ROOT_DIR, "model_config.json")


def load_configs() -> list[dict[str, Any]]:
    if os.path.exists(MODEL_CONFIG_PATH):
        try:
            with open(MODEL_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON from the config file.")
            return []
    else:
        print("Config file not found.")
        return []


def save_configs(configs: list[dict]) -> None:
    with open(MODEL_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(configs, f, indent=4)
