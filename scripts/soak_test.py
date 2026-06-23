from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.fake_adapter import FakeAdapter  # noqa: E402
from astock_source_router.core.features import REALTIME_QUOTES  # noqa: E402
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import SourcePolicy  # noqa: E402
from pyqauto import QuoteRouter  # noqa: E402


def _finite_numbers(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, int | float):
        return math.isfinite(float(value))
    if isinstance(value, dict):
        return all(_finite_numbers(item) for item in value.values())
    if isinstance(value, list | tuple):
        return all(_finite_numbers(item) for item in value)
    return True


def _audit_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_router(root: Path) -> QuoteRouter:
    return QuoteRouter(
        config=RouterConfig(
            cache_dir=root / "cache",
            log_dir=root / "logs",
            enable_cache=False,
            enable_sqlite_audit=False,
            min_interval_seconds={"fake": 0.0},
        ),
        source_policy=SourcePolicy({REALTIME_QUOTES: ["fake"]}),
        adapters=[FakeAdapter()],
        auto_register=False,
    )


def run_soak(*, iterations: int | None, duration_seconds: float, max_memory_growth_mb: float) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    states: list[str] = []
    row_counts: list[int] = []
    tracemalloc.start()
    start_current, _ = tracemalloc.get_traced_memory()

    with tempfile.TemporaryDirectory(prefix="pyqauto_soak_") as tmp:
        root = Path(tmp)
        router = _build_router(root)
        started = time.monotonic()
        loops = 0
        while True:
            data = router.realtime_quotes(["000001"])
            state = router.get_system_state()
            graph = router.reliability_graph()
            stability = router.stability_status(current_time=datetime.now(timezone.utc))

            if state not in {"NORMAL", "DEGRADED", "READONLY", "BLOCKED"}:
                raise AssertionError(f"illegal system state: {state}")
            if not _finite_numbers(graph) or not _finite_numbers(stability):
                raise AssertionError("non-finite reliability graph or stability metric")
            states.append(state)
            row_counts.append(int(len(data)))
            loops += 1

            if iterations is not None and loops >= iterations:
                break
            if iterations is None and time.monotonic() - started >= duration_seconds:
                break

        rows = _audit_rows(root / "logs" / "source_router.jsonl")

    end_current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory_growth_mb = max(0.0, (end_current - start_current) / 1024 / 1024)
    request_ids = [str(row.get("request_id")) for row in rows if row.get("request_id")]
    passed = (
        len(rows) == loops
        and len(request_ids) == loops
        and len(set(request_ids)) == loops
        and memory_growth_mb <= max_memory_growth_mb
        and set(states).issubset({"NORMAL", "DEGRADED", "READONLY", "BLOCKED"})
        and all(count > 0 for count in row_counts)
    )
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at,
        "mode": "offline_fake_adapter_soak",
        "network_used": False,
        "iterations": loops,
        "duration_seconds": round(time.monotonic() - started, 3),
        "status": "PASS" if passed else "FAIL",
        "memory_growth_mb": round(memory_growth_mb, 3),
        "memory_peak_mb": round(peak / 1024 / 1024, 3),
        "max_memory_growth_mb": max_memory_growth_mb,
        "system_states_seen": sorted(set(states)),
        "audit_record_count": len(rows),
        "trace_id_field": "request_id",
        "unique_trace_id_count": len(set(request_ids)),
        "reliability_graph_finite": True,
        "stability_metrics_finite": True,
        "audit_conclusion": "offline soak test used only fake adapters and emitted no persistent run log",
        "acceptance_result": "PASS" if passed else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an offline pyqauto soak test with fake adapters.")
    parser.add_argument("--iterations", type=int, default=None, help="Run a fixed number of loops.")
    parser.add_argument("--duration-seconds", type=float, default=1800.0, help="Run duration when iterations is unset.")
    parser.add_argument("--max-memory-growth-mb", type=float, default=32.0)
    args = parser.parse_args()

    report = run_soak(
        iterations=args.iterations,
        duration_seconds=args.duration_seconds,
        max_memory_growth_mb=args.max_memory_growth_mb,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
