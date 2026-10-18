from pathlib import Path

import pandas as pd


DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "backend" / "data"


def load_data(file_name: str) -> pd.DataFrame:
    name = Path(file_name).name
    if not name or name in {".", ".."}:
        raise ValueError("Enter a CSV file name.")
    if Path(name).suffix.lower() != ".csv":
        name = f"{name}.csv"

    file_path = DATA_DIRECTORY / name
    if not file_path.is_file():
        raise FileNotFoundError(f"CSV file was not found: {file_path}")
    return pd.read_csv(file_path)