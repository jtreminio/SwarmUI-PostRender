import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable


_DATA_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load_catalog(file_name: str) -> dict:
    catalog_path = _DATA_DIR / file_name
    with catalog_path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    if not isinstance(catalog, dict):
        raise ValueError(f"{catalog_path.name} must contain a JSON object")
    return catalog


def get_catalog_list(file_name: str, key: str) -> list[str]:
    values = load_catalog(file_name).get(key)
    if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"{file_name}:{key} must be a non-empty string list")
    return list(values)


def get_catalog_default(file_name: str, key: str) -> str:
    defaults = load_catalog(file_name).get("defaults")
    if not isinstance(defaults, dict):
        raise ValueError(f"{file_name}:defaults must be an object")
    value = defaults.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{file_name}:defaults.{key} must be a non-empty string")
    return value


def validate_catalog_entries(label: str, values: list[str], expected: Iterable[str]) -> list[str]:
    expected_values = list(expected)
    unknown = [value for value in values if value not in expected_values]
    missing = [value for value in expected_values if value not in values]
    if unknown or missing:
        raise ValueError(
            f"{label} catalog drift detected. Unknown: {unknown or 'none'}. Missing: {missing or 'none'}."
        )
    return values


def validate_catalog_default(label: str, default_value: str, values: list[str]) -> str:
    if default_value not in values:
        raise ValueError(f"{label} default '{default_value}' is not present in the catalog list")
    return default_value
