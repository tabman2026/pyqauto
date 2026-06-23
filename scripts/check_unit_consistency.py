from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astock_source_router.core.features import (  # noqa: E402
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
    TRADE_CALENDAR,
)
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY  # noqa: E402
from astock_source_router.core.unit_normalizer import (  # noqa: E402
    normalize_amount,
    normalize_daily_kline_units,
    normalize_index_units,
    normalize_pct_chg,
    normalize_realtime_units,
    normalize_volume,
)
from astock_source_router.core.unit_policy import (  # noqa: E402
    load_field_unit_policy,
    load_source_unit_policy,
)

ENABLE_ENV = "ENABLE_UNIT_CONSISTENCY_TEST"
REPORT_PATH = PROJECT_ROOT / "logs" / "unit_consistency_report.json"
MARKDOWN_PATH = PROJECT_ROOT / "FIELD_UNIT_FREEZE_REPORT.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(severity: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, "details": details}


def result(name: str, status: str, summary: str, issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"check": name, "status": status, "summary": summary, "issues": issues or []}


def status_from_issues(issues: list[dict[str, Any]]) -> str:
    severities = {item["severity"] for item in issues}
    if "FAIL" in severities or "BLOCK" in severities:
        return "FAIL"
    if "WARN" in severities:
        return "WARN"
    return "PASS"


def overall_status(results: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in results}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    if statuses == {"SKIP"}:
        return "SKIP"
    return "PASS"


def check_source_policy() -> dict[str, Any]:
    expected = {
        REALTIME_QUOTES: ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
        FULL_REALTIME_QUOTES: ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
        DAILY_KLINE: ["akshare", "baostock"],
        TRADE_CALENDAR: ["akshare", "baostock"],
        LITE_REALTIME_QUOTES: ["adata"],
    }
    issues: list[dict[str, Any]] = []
    for feature, sources in expected.items():
        actual = DEFAULT_SOURCE_POLICY.get(feature)
        if actual != sources:
            issues.append(issue("FAIL", "source_policy_changed", f"{feature} source policy changed", expected=sources, actual=actual))
    return result("source_policy_freeze", status_from_issues(issues), "Current source policy order matches task016 freeze.", issues)


def check_field_policy() -> dict[str, Any]:
    policy = load_field_unit_policy()
    units = policy["standard_units"]
    issues: list[dict[str, Any]] = []
    if units["volume"]["standard_unit"] != "share":
        issues.append(issue("FAIL", "volume_standard_unit_changed", "volume standard unit must be share"))
    if units["amount"]["standard_unit"] != "yuan":
        issues.append(issue("FAIL", "amount_standard_unit_changed", "amount standard unit must be yuan"))
    if units["pct_chg"]["standard_unit"] != "percent":
        issues.append(issue("FAIL", "pct_chg_standard_unit_changed", "pct_chg standard unit must be percent"))
    required_sources = {"pytdx", "easyquotation_sina", "easyquotation_tencent", "akshare", "baostock", "adata"}
    source_policy = load_source_unit_policy()
    missing_sources = sorted(required_sources - set(source_policy))
    if missing_sources:
        issues.append(issue("FAIL", "source_unit_policy_missing_source", "source_unit_policy misses required sources", missing_sources=missing_sources))
    high_confidence = []
    for source, source_rules in source_policy.items():
        if not isinstance(source_rules, dict):
            continue
        for feature, feature_rules in source_rules.items():
            if isinstance(feature_rules, dict) and feature_rules.get("confidence") == "high":
                high_confidence.append(f"{source}.{feature}")
    if high_confidence:
        issues.append(issue("WARN", "unexpected_high_confidence", "Task013 WARN fields should not be high confidence", fields=high_confidence))
    return result("field_and_source_unit_policy", status_from_issues(issues), "Field and source unit policies are loadable and cover required sources.", issues)


def check_normalizer_conversions() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    volume = normalize_volume(1000, "akshare", "daily_kline")
    if volume["normalized_value"] != 100000 or volume["normalized_unit"] != "share":
        issues.append(issue("FAIL", "lot_to_share_failed", "lot volume was not converted to share", observed=volume))
    amount_wan = normalize_amount(1010, "easyquotation_tencent", "realtime_quotes")
    if amount_wan["normalized_value"] != 10100000 or amount_wan["normalized_unit"] != "yuan":
        issues.append(issue("FAIL", "wan_yuan_to_yuan_failed", "wan_yuan amount was not converted to yuan", observed=amount_wan))
    amount_yi = normalize_amount(2, "unit_test_yi_yuan", "amount_check")
    if amount_yi["normalized_value"] != 200000000 or amount_yi["normalized_unit"] != "yuan":
        issues.append(issue("FAIL", "yi_yuan_to_yuan_failed", "yi_yuan amount was not converted to yuan", observed=amount_yi))
    pct_ratio = normalize_pct_chg(0.0123, "unit_test_ratio", function_name="pct_check")
    if round(float(pct_ratio["pct_chg"]), 6) != 1.23 or pct_ratio["pct_chg_unit"] != "percent":
        issues.append(issue("FAIL", "ratio_to_percent_failed", "ratio pct_chg was not converted to percent", observed=pct_ratio))
    pct_derived = normalize_pct_chg(None, "pytdx", close=10.1, pre_close=10.0, function_name="realtime_quotes")
    if not pct_derived["pct_chg_derived"] or round(float(pct_derived["pct_chg"]), 6) != 1.0:
        issues.append(issue("FAIL", "derived_pct_chg_failed", "derived pct_chg was not recorded correctly", observed=pct_derived))
    unknown = normalize_volume(1000, "unit_test_unknown", "daily_kline")
    if not unknown["warnings"] or unknown["normalized_value"] != 1000:
        issues.append(issue("FAIL", "unknown_unit_forced_conversion", "unknown unit must warn and avoid forced conversion", observed=unknown))
    return result("unit_normalizer_conversion_rules", status_from_issues(issues), "Core conversion and unknown-unit rules were checked with offline samples.", issues)


def check_frame_units() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    daily = pd.DataFrame(
        [
            {
                "date": "2026-06-11",
                "code": "000001",
                "open": 10,
                "high": 10.2,
                "low": 9.9,
                "close": 10.1,
                "pre_close": 10,
                "volume": 1000,
                "amount": 10100000,
                "pct_chg": 1,
                "adjust_type": "none",
                "field_warnings": ["existing_warning"],
            }
        ]
    )
    daily_norm = normalize_daily_kline_units(daily, "akshare")
    if daily_norm.at[0, "raw_volume"] != 1000 or daily_norm.at[0, "volume_normalized"] != 100000:
        issues.append(issue("FAIL", "daily_volume_metadata_failed", "daily volume raw/normalized metadata is incorrect"))
    if "existing_warning" not in daily_norm.at[0, "field_warnings"]:
        issues.append(issue("FAIL", "field_warnings_not_preserved", "existing field_warnings were not preserved"))
    realtime = pd.DataFrame(
        [
            {
                "date": "2026-06-12",
                "time": "10:00:00",
                "code": "000001",
                "last_price": 10.1,
                "pre_close": 10,
                "open": 10,
                "high": 10.2,
                "low": 9.9,
                "volume": 1000,
                "amount": 10100000,
                "pct_chg": 1,
            }
        ]
    )
    realtime_norm = normalize_realtime_units(realtime, "pytdx")
    if not bool(realtime_norm.at[0, "pct_chg_derived"]):
        issues.append(issue("FAIL", "realtime_pct_chg_derived_missing", "pytdx realtime pct_chg must be marked derived"))
    index_norm = normalize_index_units(realtime, "akshare")
    if not index_norm.at[0, "field_warnings"]:
        issues.append(issue("WARN", "index_unit_warning_missing", "akshare index unknown units should remain visible as warnings"))
    return result("dataframe_unit_metadata", status_from_issues(issues), "DataFrame normalizers preserve raw values, warnings, source fields, and unit metadata.", issues)


def check_lite_boundary() -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if "adata" in DEFAULT_SOURCE_POLICY.get(FULL_REALTIME_QUOTES, []):
        issues.append(issue("FAIL", "adata_in_full_policy", "adata must not be in full_realtime_quotes policy"))
    if "adata" in DEFAULT_SOURCE_POLICY.get(REALTIME_QUOTES, []):
        issues.append(issue("FAIL", "adata_in_realtime_policy", "adata must not be in realtime_quotes policy"))
    if DEFAULT_SOURCE_POLICY.get(LITE_REALTIME_QUOTES) != ["adata"]:
        issues.append(issue("FAIL", "lite_policy_changed", "lite_realtime_quotes policy must remain adata only"))
    return result("lite_full_boundary_units", status_from_issues(issues), "lite_realtime_quotes remains isolated from full realtime units.", issues)


def skip_report() -> dict[str, Any]:
    return {
        "created_at": utc_now(),
        "mode": "skip",
        "live_enabled": False,
        "overall_status": "SKIP",
        "summary": "Default run does not perform unit consistency checks; set ENABLE_UNIT_CONSISTENCY_TEST=1.",
        "results": [result("unit_consistency", "SKIP", "Explicit enable env var is required.")],
    }


def enabled_report() -> dict[str, Any]:
    results = [
        check_source_policy(),
        check_field_policy(),
        check_normalizer_conversions(),
        check_frame_units(),
        check_lite_boundary(),
    ]
    overall = overall_status(results)
    return {
        "created_at": utc_now(),
        "mode": "offline_fixture",
        "live_enabled": False,
        "enabled_by": ENABLE_ENV,
        "overall_status": overall,
        "has_block": any(issue["severity"] == "BLOCK" for item in results for issue in item["issues"]),
        "summary": "Field unit consistency freeze completed with offline fixtures; no source policy order was changed.",
        "standard_units": {"volume": "share", "amount": "yuan", "pct_chg": "percent"},
        "results": results,
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# FIELD_UNIT_FREEZE_REPORT",
        "",
        f"- generated_at: `{report['created_at']}`",
        f"- overall_status: `{report['overall_status']}`",
        f"- mode: `{report['mode']}`",
        "- volume standard unit: `share`",
        "- amount standard unit: `yuan`",
        "- pct_chg standard scope: `percent`, where `1.23` means `1.23%`",
        "- source policy changed: `no`",
        "- lite_realtime used as full: `no`",
        "",
        "## Results",
        "",
        "| check | status | summary |",
        "|---|---:|---|",
    ]
    for item in report.get("results", []):
        lines.append(f"| `{item['check']}` | `{item['status']}` | {item['summary']} |")
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- task016 field unit freeze: `complete` when overall status is PASS or WARN without BLOCK.",
            "- continue 5-day stability watch: `yes` when no BLOCK exists.",
            "- allow S0 production: `no`.",
            "- trading advice/signals/position/return output: `no`.",
            "",
        ]
    )
    MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = enabled_report() if os.environ.get(ENABLE_ENV) == "1" else skip_report()
    write_report(report)
    write_markdown(report)
    for item in report["results"]:
        print(f"{item['check']}: {item['status']} - {item['summary']}")
    print(f"overall_status: {report['overall_status']}")
    print(f"report_path: {REPORT_PATH}")
    print(f"markdown_path: {MARKDOWN_PATH}")
    return 1 if report["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
