from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.adapters.fake_adapter import FakeAdapter  # noqa: E402
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import SourcePolicy  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402


def _write_report(report: dict[str, Any]) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "smoke_test_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    config = RouterConfig(
        cache_dir=Path(".cache/smoke_offline"),
        log_dir=Path("logs"),
        enable_cache=False,
        enable_sqlite_audit=True,
        min_interval_seconds={"fake": 0.0},
    )
    policy = SourcePolicy(
        {
            "realtime_quotes": ["fake"],
            "daily_kline": ["fake"],
            "trade_calendar": ["fake"],
        }
    )
    router = MarketRouter(config=config, source_policy=policy, adapters=[FakeAdapter()], auto_register=False)
    checks = [
        ("FakeAdapter", "realtime_quotes", lambda: router.get_realtime_quotes(["000001"])),
        ("FakeAdapter", "daily_kline", lambda: router.get_daily_kline("000001", "20260611", "20260611")),
        ("FakeAdapter", "trade_calendar", lambda: router.get_trade_calendar("20260611", "20260611")),
    ]

    results: list[dict[str, Any]] = []
    for source, feature, runner in checks:
        try:
            df = runner()
            results.append(
                {
                    "source": source,
                    "feature": feature,
                    "status": "PASS",
                    "row_count": int(len(df)),
                    "reason": "offline_fake_adapter_ok",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "source": source,
                    "feature": feature,
                    "status": "FAIL",
                    "row_count": 0,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "offline",
        "live_enabled": False,
        "results": results,
    }
    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
