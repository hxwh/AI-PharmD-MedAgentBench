"""Data loading for Pokemon/drug name evaluation datasets."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Path to data files relative to this module
_DATA_DIR = Path(__file__).parent.parent.parent / "tasks" / "subtask2" / "data"

# Cached data
_brand_data: List[Dict[str, str]] = []
_generic_data: List[Dict[str, str]] = []
_pokemon_names: Set[str] = set()


def _load_csv(filepath: Path) -> List[Dict[str, str]]:
    """Load CSV file as list of dictionaries."""
    if not filepath.exists():
        return []
    with filepath.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_brand_data() -> List[Dict[str, str]]:
    """Get brand drug dataset (medication lists with hidden Pokemon names)."""
    global _brand_data
    if not _brand_data:
        _brand_data = _load_csv(_DATA_DIR / "brand" / "pokemon.csv")
    return _brand_data


def get_generic_data() -> List[Dict[str, str]]:
    """Get generic drug dataset (medication lists with hidden Pokemon names)."""
    global _generic_data
    if not _generic_data:
        _generic_data = _load_csv(_DATA_DIR / "generic" / "pokemon.csv")
    return _generic_data


def get_all_pokemon_names() -> Set[str]:
    """Extract all Pokemon names from both datasets (lowercase)."""
    global _pokemon_names
    if not _pokemon_names:
        names = set()
        for row in get_brand_data():
            pokemon = row.get("Pokemon", "").strip()
            if pokemon:
                names.add(pokemon.lower())
        for row in get_generic_data():
            pokemon = row.get("Pokemon", "").strip()
            if pokemon:
                names.add(pokemon.lower())
        _pokemon_names = names
    return _pokemon_names


def get_case_by_index(dataset: str, index: int) -> Dict[str, str]:
    """
    Get a specific case by index from the dataset.
    
    Args:
        dataset: "brand" or "generic"
        index: 0-based row index
        
    Returns:
        Dictionary with keys: pokemon_list, Pokemon (and drug_list for generic)
    """
    if dataset == "brand":
        data = get_brand_data()
    elif dataset == "generic":
        data = get_generic_data()
    else:
        return {}
    
    if 0 <= index < len(data):
        return data[index]
    return {}


def get_dataset_size(dataset: str) -> int:
    """Get the number of cases in a dataset."""
    if dataset == "brand":
        return len(get_brand_data())
    elif dataset == "generic":
        return len(get_generic_data())
    return 0


def is_pokemon_name(name: str) -> bool:
    """Check if a name is a Pokemon (case-insensitive)."""
    return name.lower().strip() in get_all_pokemon_names()
