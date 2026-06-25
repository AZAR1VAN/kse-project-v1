"""Завантаження історичного датасету повітряних тривог (Vadimkin, MIT) з локальним кешем."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

RAW_URL = (
    "https://raw.githubusercontent.com/Vadimkin/"
    "ukrainian-air-raid-sirens-dataset/main/datasets/volunteer_data_en.csv"
)

# data_cache/ у корені проєкту (../../../../data_cache відносно цього файлу)
CACHE_DIR = Path(__file__).resolve().parents[3] / "data_cache"
CACHE_PATH = CACHE_DIR / "volunteer_data_en.csv"


def _download(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(RAW_URL, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def load(force: bool = False) -> pd.DataFrame:
    """Повернути сирий DataFrame тривог; завантажити з мережі лише за відсутності кешу або force."""
    if force or not CACHE_PATH.exists():
        _download(CACHE_PATH)
    return pd.read_csv(CACHE_PATH)
