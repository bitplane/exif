"""
Filter management utilities
"""

import os
import json


def save_filters(filter_data: dict) -> None:
    """Save filter configuration to JSON file"""
    temp_file = "./scripts/filters.json.tmp"
    with open(temp_file, "w") as f:
        json.dump(filter_data, f, indent=2)
    os.rename(temp_file, "./scripts/filters.json")


def load_filters() -> dict:
    """Load filter configuration from JSON file"""
    try:
        with open("./scripts/filters.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"files": {"ignore": [], "replace": []}}