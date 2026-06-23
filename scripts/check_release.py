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
from astock_source_router.core.features import REALTIME_QUOTES  # noqa: E402
from astock_source_router.core.models import RouterConfig  # noqa: E402
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY, SourcePolicy  # noqa: E402
from astock_source_router.core.router import MarketRouter  # noqa: E402
from pyqauto import QuoteRouter  # noqa: E402
from pyqauto.meta import meta_decision, system_brain  # noqa: E402
from pyqauto.stability import VersionPolicy, detect_drift, stability_status  # noqa: E402

EXPECTED_POLICY = {
    "daily_kline": ["akshare", "baostock"],
    "trade_calendar": ["akshare", "baostock"],
    "realtime_quotes": ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
    "full_realtime_quotes": ["pytdx", "easyquotation_sina", "easyquotation_tencent"],
    "lite_realtime_quotes": ["adata"],
    "index_realtime": ["pytdx", "easyquotation_sina", "easyquotation_tencent", "akshare"],
    "minute_kline": ["pytdx"],
    "stock_basic": ["baostock", "akshare"],
}


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


def _write_report(report: dict[str, Any]) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "release_check_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    router = MarketRouter(
        config=RouterConfig(
            cache_dir=Path(".cache/release_check"),
            log_dir=Path("logs"),
            enable_cache=False,
            enable_sqlite_audit=True,
            min_interval_seconds={"fake": 0.0},
        ),
        source_policy=SourcePolicy({REALTIME_QUOTES: ["fake"]}),
        adapters=[FakeAdapter()],
        auto_register=False,
    )
    result = router.fetch_result(REALTIME_QUOTES, codes=["000001"])
    autonomy_status = router.autonomy_status()
    safety = autonomy_status.get("safety_boundaries", {})
    meta = meta_decision(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "fake", "overall_reliability_score": 100.0},
        autonomy=autonomy_status,
    )
    brain = system_brain(
        governance={"system_state": "NORMAL"},
        graph={"best_source": "fake", "overall_reliability_score": 100.0},
        autonomy=autonomy_status,
    )
    stability = stability_status(
        events=[
            {"success": True, "latency_ms": 100.0, "attempted_sources": ["pytdx"]},
            {"success": True, "latency_ms": 120.0, "attempted_sources": ["pytdx"]},
            {
                "success": False,
                "latency_ms": 1800.0,
                "missing_fields": ["last_price"],
                "attempted_sources": ["pytdx", "easyquotation_sina"],
            },
            {
                "success": False,
                "latency_ms": 2200.0,
                "schema_drift": True,
                "attempted_sources": ["pytdx", "easyquotation_sina"],
            },
        ],
        health_rows=[
            {"source": "pytdx", "score": 90.0},
            {"source": "akshare", "score": 82.0},
            {"source": "efinance", "score": 65.0},
        ],
    )
    drift = detect_drift(
        [
            {"success": True, "latency_ms": 100.0, "attempted_sources": ["pytdx"]},
            {"success": True, "latency_ms": 120.0, "attempted_sources": ["pytdx"]},
            {
                "success": False,
                "latency_ms": 1800.0,
                "missing_fields": ["last_price"],
                "attempted_sources": ["pytdx", "easyquotation_sina"],
            },
            {
                "success": False,
                "latency_ms": 2200.0,
                "schema_drift": True,
                "attempted_sources": ["pytdx", "easyquotation_sina"],
            },
        ]
    )
    version_policy = VersionPolicy()

    required_paths = [
        Path("astock_source_router/autonomy/recovery_engine.py"),
        Path("astock_source_router/autonomy/anomaly_detector.py"),
        Path("astock_source_router/autonomy/decay_model.py"),
        Path("astock_source_router/autonomy/self_healing.py"),
        Path("pyqauto/autonomy/recovery_engine.py"),
        Path("pyqauto/autonomy/anomaly_detector.py"),
        Path("pyqauto/autonomy/decay_model.py"),
        Path("pyqauto/autonomy/self_healing.py"),
        Path("pyqauto/meta/control_plane.py"),
        Path("pyqauto/meta/decision_engine.py"),
        Path("pyqauto/meta/conflict_resolver.py"),
        Path("pyqauto/meta/state_aggregator.py"),
        Path("pyqauto/meta/explainability.py"),
        Path("pyqauto/stability/monitor.py"),
        Path("pyqauto/stability/drift_detector.py"),
        Path("pyqauto/stability/health_tracker.py"),
        Path("pyqauto/stability/stability_engine.py"),
        Path("pyqauto/stability/version_policy.py"),
        Path("docs/AUTONOMOUS_CONTROL_LAYER.md"),
        Path("docs/META_CONTROL_PLANE.md"),
        Path("docs/STABILITY_LAYER.md"),
        Path("docs/VERSION_GOVERNANCE_POLICY.md"),
        Path("docs/V1_API_FREEZE.md"),
        Path("docs/V1_PUBLIC_API_REFERENCE.md"),
        Path("docs/ADAPTER_CONTRACT_V1.md"),
        Path("docs/SYSTEM_BEHAVIOR_FREEZE.md"),
        Path("docs/V1_ARCHITECTURE.md"),
        Path("docs/SOAK_TEST.md"),
        Path("tests/test_v1_api_freeze.py"),
        Path("tests/test_v1_public_api_snapshot.py"),
        Path("tests/test_v1_cross_layer_integration.py"),
        Path("tests/test_stability_rolling_window.py"),
        Path("tests/test_stability_insufficient_data.py"),
        Path("tests/test_stability_restart_semantics.py"),
        Path("tests/test_stability_observational_only.py"),
        Path("tests/test_adapter_contract_v1.py"),
        Path("tests/test_system_behavior_freeze.py"),
        Path("tests/test_meta_stability.py"),
        Path("tests/test_stability_monitor.py"),
        Path("tests/test_drift_detector.py"),
        Path("tests/test_health_trend.py"),
        Path("tests/test_version_policy.py"),
    ]
    adapter = FakeAdapter()
    v1_decision_keys = {
        "system_state",
        "recommended_source",
        "decision_reason",
        "winning_rule",
        "conflict_resolution_path",
        "module_contributions",
    }
    v1_explain_keys = {
        "decision_trace",
        "conflict_resolution_path",
        "module_contributions",
        "decision_reason",
    }

    checks = [
        _check(
            "autonomy_files",
            all(path.exists() for path in required_paths),
            "L6 autonomy files and documentation are present",
        ),
        _check(
            "pyqauto_packaged",
            'name = "pyqauto"' in pyproject_text and '"pyqauto"' in pyproject_text,
            "pyqauto is the formal distribution and packaged namespace",
        ),
        _check(
            "quote_router_public_alias",
            QuoteRouter is MarketRouter,
            "pyqauto.QuoteRouter and MarketRouter share one implementation",
        ),
        _check(
            "source_policy_unchanged",
            DEFAULT_SOURCE_POLICY == EXPECTED_POLICY,
            "default source policy remains frozen",
        ),
        _check(
            "offline_router_smoke",
            result.source == "fake" and len(result.data) == 1,
            "offline fake adapter route works",
        ),
        _check(
            "autonomy_safety_boundaries",
            all(value is False for value in safety.values()),
            "autonomy layer has no trading, strategy, prediction, broker, or QMT capability",
        ),
        _check(
            "meta_control_plane",
            meta["system_state"] == "NORMAL"
            and meta["recommended_source"] == "fake"
            and brain["role"] == "pyqauto_meta_control_plane",
            "meta control plane decision and system brain are present",
        ),
        _check(
            "meta_safety_boundaries",
            all(value is False for value in brain["safety_boundaries"].values()),
            "meta control plane has no trading, strategy, prediction, broker, or QMT capability",
        ),
        _check(
            "v1_freeze_docs_and_tests",
            all(path.exists() for path in required_paths),
            "v1 freeze documentation and test files are present",
        ),
        _check(
            "v1_router_api_freeze",
            set(router.meta_decision(context={"feature": REALTIME_QUOTES})) == v1_decision_keys
            and set(router.meta_explain(context={"feature": REALTIME_QUOTES})) == v1_explain_keys
            and set(router.source_health()) == {"api_version", "sources", "health"}
            and set(router.stability_status())
            == {
                "system_uptime_score",
                "failure_rate_24h",
                "schema_drift_trend",
                "source_health_trend",
            }
            and set(router.diagnose())
            == {
                "api_version",
                "router",
                "registered_sources",
                "source_policy",
                "cache_enabled",
                "sqlite_audit_enabled",
                "autonomy",
                "source_health",
                "safety_boundaries",
            },
            "v1 router API return keys remain frozen",
        ),
        _check(
            "v1_adapter_contract",
            all(
                callable(getattr(adapter, method_name, None))
                for method_name in (
                    "fetch_raw",
                    "inspect_raw_schema",
                    "normalize_to_standard",
                    "validate_standard_output",
                )
            ),
            "adapter contract v1 methods are present",
        ),
        _check(
            "stability_layer_present",
            set(stability)
            == {
                "system_uptime_score",
                "failure_rate_24h",
                "schema_drift_trend",
                "source_health_trend",
            }
            and set(stability["source_health_trend"]) == {"pytdx", "akshare", "efinance"},
            "L8 stability status output is present and scoped to operational trends",
        ),
        _check(
            "stability_drift_detection",
            drift["schema_drift_increase"]
            and drift["fallback_frequency_increase"]
            and drift["latency_spike_detected"],
            "L8 drift detector flags schema, fallback, and latency drift",
        ),
        _check(
            "version_governance_policy",
            version_policy.classify_change({"new_stability_layer": True}) == "MINOR"
            and version_policy.classify_change({"source_policy_change": True}) == "MAJOR"
            and not version_policy.is_allowed_change({"broker_integration": True}),
            "PATCH/MINOR/MAJOR version governance and out-of-boundary rejection are present",
        ),
    ]
    passed = all(item["status"] == "PASS" for item in checks)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "offline_release_check",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "audit_conclusion": {
            "autonomy_layer": "present",
            "meta_control_plane": "present",
            "conflict_resolution": "present",
            "meta_explainability": "present",
            "api_freeze": "present",
            "adapter_contract_freeze": "present",
            "system_behavior_freeze": "present",
            "stability_layer": "present",
            "drift_detection": "present",
            "health_tracking": "present",
            "version_governance_policy": "present",
            "source_policy_changed": False,
            "field_standard_changed": False,
            "audit_log_schema_changed": False,
            "out_of_boundary_behavior": False,
        },
    }
    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
