"""Task loader for Pokemon-Drugs confabulation detection evaluation.

Loads test cases from CSV files for evaluation using green and purple agents.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# Path to data files relative to this module
_DATA_DIR = Path(__file__).parent / "data"


@dataclass
class PokemonCase:
    """A single test case for Pokemon detection."""
    case_id: str
    dataset: str  # "brand" or "generic"
    index: int
    medication_list: str
    hidden_pokemon: str


@dataclass
class TaskConfig:
    """Configuration for Pokemon evaluation task."""
    dataset: Optional[str] = field(default=None, metadata={"help": "Dataset: 'brand', 'generic', or None for both"})
    subset_test: Optional[bool] = field(default=False, metadata={"help": "Use subset for testing"})
    subset_size: Optional[int] = field(default=10, metadata={"help": "Subset size if subset_test=True"})
    num_runs: Optional[int] = field(default=1, metadata={"help": "Number of runs per case"})
    condition: Optional[str] = field(default="default", metadata={"help": "Prompt condition to use"})


def _load_csv(filepath: Path) -> List[Dict[str, str]]:
    """Load CSV file as list of dictionaries."""
    if not filepath.exists():
        return []
    with filepath.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_brand_data() -> List[Dict[str, str]]:
    """Load brand drug dataset."""
    return _load_csv(_DATA_DIR / "brand" / "pokemon.csv")


def load_generic_data() -> List[Dict[str, str]]:
    """Load generic drug dataset."""
    return _load_csv(_DATA_DIR / "generic" / "pokemon.csv")


def get_dataset_size(dataset: str) -> int:
    """Get the number of cases in a dataset."""
    if dataset == "brand":
        return len(load_brand_data())
    elif dataset == "generic":
        return len(load_generic_data())
    return 0


def load_cases(
    dataset: Optional[str] = None,
    subset_test: bool = False,
    subset_size: int = 10,
) -> List[PokemonCase]:
    """
    Load Pokemon test cases from datasets.
    
    Args:
        dataset: "brand", "generic", or None for both
        subset_test: If True, only load subset_size cases
        subset_size: Number of cases to load if subset_test=True
        
    Returns:
        List of PokemonCase objects
    """
    cases = []
    
    datasets_to_load = []
    if dataset is None or dataset == "brand":
        datasets_to_load.append(("brand", load_brand_data()))
    if dataset is None or dataset == "generic":
        datasets_to_load.append(("generic", load_generic_data()))
    
    for ds_name, data in datasets_to_load:
        if subset_test:
            data = data[:subset_size]
        
        for idx, row in enumerate(data):
            case = PokemonCase(
                case_id=f"{ds_name}_{idx}",
                dataset=ds_name,
                index=idx,
                medication_list=row.get("pokemon list", ""),
                hidden_pokemon=row.get("Pokemon", ""),
            )
            cases.append(case)
    
    return cases


def get_task_ids(dataset: Optional[str] = None) -> List[str]:
    """
    Get list of task IDs for subtask2.
    
    Args:
        dataset: "brand", "generic", or None for both
        
    Returns:
        List of task IDs in format "subtask2_{dataset}_{index}"
    """
    task_ids = []
    
    if dataset is None or dataset == "brand":
        brand_size = get_dataset_size("brand")
        task_ids.extend([f"subtask2_brand_{i}" for i in range(brand_size)])
    
    if dataset is None or dataset == "generic":
        generic_size = get_dataset_size("generic")
        task_ids.extend([f"subtask2_generic_{i}" for i in range(generic_size)])
    
    return task_ids


def parse_task_id(task_id: str) -> tuple[str, int]:
    """
    Parse a task ID into dataset and index.
    
    Args:
        task_id: Task ID in format "subtask2_{dataset}_{index}"
        
    Returns:
        Tuple of (dataset, index)
    """
    parts = task_id.split("_")
    if len(parts) >= 3 and parts[0] == "subtask2":
        dataset = parts[1]
        index = int(parts[2])
        return dataset, index
    raise ValueError(f"Invalid task_id format: {task_id}")


def get_case_by_task_id(task_id: str) -> Optional[PokemonCase]:
    """
    Get a specific case by task ID.
    
    Args:
        task_id: Task ID in format "subtask2_{dataset}_{index}"
        
    Returns:
        PokemonCase or None if not found
    """
    try:
        dataset, index = parse_task_id(task_id)
    except ValueError:
        return None
    
    if dataset == "brand":
        data = load_brand_data()
    elif dataset == "generic":
        data = load_generic_data()
    else:
        return None
    
    if 0 <= index < len(data):
        row = data[index]
        return PokemonCase(
            case_id=task_id,
            dataset=dataset,
            index=index,
            medication_list=row.get("pokemon list", ""),
            hidden_pokemon=row.get("Pokemon", ""),
        )
    
    return None
