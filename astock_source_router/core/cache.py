from __future__ import annotations

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any

import pandas as pd


class TTLCache:
    """Tiny file-based cache for DataFrames."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def build_key(self, feature: str, args: dict[str, Any]) -> str:
        safe_args = json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{feature}:{safe_args}".encode()).hexdigest()
        return digest

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.pkl"

    def get(self, key: str, ttl_seconds: float) -> pd.DataFrame | None:
        path = self._path(key)
        if not path.exists():
            return None
        if ttl_seconds <= 0:
            return None
        age = time.time() - path.stat().st_mtime
        if age > ttl_seconds:
            return None
        with path.open("rb") as f:
            value = pickle.load(f)
        if isinstance(value, pd.DataFrame):
            return value.copy()
        return None

    def set(self, key: str, df: pd.DataFrame) -> None:
        path = self._path(key)
        with path.open("wb") as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
