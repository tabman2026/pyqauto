from __future__ import annotations

from pathlib import Path

import pytest

from astock_source_router.core.models import RouterConfig


@pytest.fixture
def test_config(tmp_path: Path) -> RouterConfig:
    return RouterConfig(
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        enable_cache=False,
        enable_sqlite_audit=True,
        circuit_failure_threshold=2,
        circuit_cooldown_seconds=1,
        min_interval_seconds={"fake": 0.0, "broken": 0.0},
    )
