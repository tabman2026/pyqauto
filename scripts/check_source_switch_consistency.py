from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.core.source_switch_consistency import (  # noqa: E402
    run_source_switch_consistency,
)

ENABLE_ENV = "ENABLE_SOURCE_SWITCH_CONSISTENCY_TEST"
REPORT_PATH = PROJECT_ROOT / "logs" / "source_switch_consistency_report.json"
MARKDOWN_PATH = PROJECT_ROOT / "SOURCE_SWITCH_CONSISTENCY_REPORT.md"


def write_json(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# SOURCE_SWITCH_CONSISTENCY_REPORT",
        "",
        f"- generated_at: `{report['created_at']}`",
        f"- overall_status: `{report['overall_status']}`",
        f"- has_block: `{report.get('has_block', False)}`",
        f"- mode: `{report['mode']}`",
        "- source policy changed: `no`",
        "- raw source data overwritten: `no`",
        "",
        "## Switch Paths",
        "",
        "| path | feature | status | block | issue_count |",
        "|---|---|---:|---:|---:|",
    ]
    for item in report.get("results", []):
        lines.append(
            f"| `{item['left_source']} -> {item['right_source']}` | `{item['feature']}` | "
            f"`{item['status']}` | `{item['has_block']}` | `{len(item['issues'])}` |"
        )
    lines.extend(
        [
            "",
            "## Block Rules",
            "",
            "- BLOCK when OHLC, last_price, code, date, or source is missing.",
            "- BLOCK when daily_kline adjust_type conflicts across a switch path.",
            "- BLOCK when lite_realtime_quotes is used as full_realtime_quotes.",
            "- WARN when known unit differences are marked and not required for strong consistency.",
            "",
            "## Gate",
            "",
            "- source switch consistency: `PASS` or `WARN without BLOCK` is acceptable for task016.",
            "- continue 5-day stability watch: `yes` if no BLOCK exists.",
            "- allow S0 production: `no`.",
            "",
        ]
    )
    MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    enabled = os.environ.get(ENABLE_ENV) == "1"
    report = run_source_switch_consistency(enabled)
    write_json(report)
    write_markdown(report)
    for item in report.get("results", []):
        print(f"{item['path']}: {item['status']} block={item['has_block']}")
    print(f"overall_status: {report['overall_status']}")
    print(f"has_block: {report.get('has_block', False)}")
    print(f"report_path: {REPORT_PATH}")
    print(f"markdown_path: {MARKDOWN_PATH}")
    return 1 if report["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
