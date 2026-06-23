from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PATCH = "PATCH"
MINOR = "MINOR"
MAJOR = "MAJOR"
REJECTED = "REJECTED"

VERSION_RULES = {
    PATCH: [
        "bug fix with no public API, source policy, field standard, or audit schema change",
        "documentation, tests, release checks, or internal stability threshold tuning",
        "internal refactor that preserves existing behavior",
    ],
    MINOR: [
        "new optional module or read-only capability that does not alter existing APIs",
        "new optional adapter guarded by tests and field normalization checks",
        "new diagnostics, health reporting, or stability reporting surface",
    ],
    MAJOR: [
        "breaking public API or router return-key change",
        "source policy, field standard, audit log schema, or governance state change",
        "behavior-freeze change that requires an explicit migration",
    ],
}

FORBIDDEN_FLAGS = {
    "trading_system",
    "strategy_or_prediction",
    "investment_advice",
    "broker_or_qmt_control",
    "auto_trade",
    "broker_integration",
    "qmt_integration",
    "stock_selection",
    "return_prediction",
}
MAJOR_FLAGS = {
    "breaking_api",
    "router_return_key_change",
    "source_policy_change",
    "field_standard_change",
    "audit_log_schema_change",
    "governance_state_change",
    "graph_behavior_change",
    "autonomy_behavior_change",
    "meta_behavior_change",
    "behavior_freeze_change",
    "migration_required",
}
MINOR_FLAGS = {
    "new_optional_adapter",
    "new_public_module",
    "new_readonly_api",
    "new_stability_layer",
    "new_health_report",
    "non_breaking_capability",
}
PATCH_FLAGS = {
    "bugfix",
    "docs",
    "tests",
    "release_check",
    "internal_refactor",
    "threshold_tuning",
}


@dataclass(frozen=True, slots=True)
class VersionDecision:
    level: str
    reason: str
    allowed: bool = True


def _flag_enabled(change: Mapping[str, Any], flag: str) -> bool:
    return bool(change.get(flag))


def _text_has_any(text: str, terms: set[str]) -> bool:
    normalized = text.lower().replace("-", "_").replace(" ", "_")
    return any(term in normalized for term in terms)


class VersionPolicy:
    """Classify version impact under the frozen pyqauto boundary."""

    def rules(self) -> dict[str, list[str]]:
        return {level: list(rules) for level, rules in VERSION_RULES.items()}

    def evaluate_change(self, change: Mapping[str, Any] | str) -> VersionDecision:
        if isinstance(change, str):
            return self._evaluate_text(change)
        if any(_flag_enabled(change, flag) for flag in FORBIDDEN_FLAGS):
            return VersionDecision(
                level=REJECTED,
                reason="out_of_boundary_capability_is_not_versionable",
                allowed=False,
            )
        if any(_flag_enabled(change, flag) for flag in MAJOR_FLAGS):
            return VersionDecision(level=MAJOR, reason="breaking_or_freeze_sensitive_change")
        if any(_flag_enabled(change, flag) for flag in MINOR_FLAGS):
            return VersionDecision(level=MINOR, reason="new_non_breaking_capability")
        if any(_flag_enabled(change, flag) for flag in PATCH_FLAGS):
            return VersionDecision(level=PATCH, reason="compatible_maintenance_change")
        return VersionDecision(level=PATCH, reason="default_compatible_change")

    def _evaluate_text(self, text: str) -> VersionDecision:
        if _text_has_any(text, FORBIDDEN_FLAGS):
            return VersionDecision(
                level=REJECTED,
                reason="out_of_boundary_capability_is_not_versionable",
                allowed=False,
            )
        if _text_has_any(text, MAJOR_FLAGS):
            return VersionDecision(level=MAJOR, reason="breaking_or_freeze_sensitive_change")
        if _text_has_any(text, MINOR_FLAGS):
            return VersionDecision(level=MINOR, reason="new_non_breaking_capability")
        if _text_has_any(text, PATCH_FLAGS):
            return VersionDecision(level=PATCH, reason="compatible_maintenance_change")
        return VersionDecision(level=PATCH, reason="default_compatible_change")

    def classify_change(self, change: Mapping[str, Any] | str) -> str:
        return self.evaluate_change(change).level

    def is_allowed_change(self, change: Mapping[str, Any] | str) -> bool:
        return self.evaluate_change(change).allowed
