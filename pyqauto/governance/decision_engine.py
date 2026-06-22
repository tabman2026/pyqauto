"""Decision engine for runtime governance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from pyqauto.adapters.base import source_id
from pyqauto.governance.health_monitor import source_family
from pyqauto.governance.state_machine import SystemState


@dataclass(frozen=True)
class DecisionTrace:
    """Explain one governance decision."""

    state: SystemState
    why_this_state: str
    failed_sources: list[str]
    fallback_chain: list[str]
    schema_validation_result: dict[str, Any]
    pytdx_failed: bool
    fallback_success: bool
    all_sources_failed: bool
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


class DecisionEngine:
    """Convert runtime context into a SystemState."""

    def __init__(self, *, schema_drift_threshold: float = 0.0) -> None:
        self.schema_drift_threshold = schema_drift_threshold

    def decide(self, context: Mapping[str, Any] | Any) -> SystemState:
        return self.evaluate(context).state

    def evaluate(self, context: Mapping[str, Any] | Any) -> DecisionTrace:
        payload = _context_dict(context)
        attempts = _attempt_dicts(payload.get("attempts"))
        fallback_chain = _string_list(payload.get("fallback_chain"))
        failed_sources = _failed_sources(attempts)
        schema_validation_result = _schema_validation_result(payload)
        schema_drift_value = _schema_drift_value(payload, schema_validation_result)
        route_success = bool(payload.get("success", True))
        all_attempts_failed = bool(
            attempts
            and not route_success
            and all(not attempt["success"] for attempt in attempts)
        )
        all_sources_failed = bool(payload.get("all_sources_failed") or all_attempts_failed)
        pytdx_failed = bool(
            payload.get("pytdx_failed")
            or any(source_family(source) == "pytdx" for source in failed_sources)
            or any(source_family(source) == "pytdx" for source in fallback_chain)
        )
        fallback_success = bool(
            payload.get("fallback_success") or (route_success and bool(fallback_chain))
        )

        if schema_drift_value > self.schema_drift_threshold:
            return DecisionTrace(
                state=SystemState.BLOCKED,
                why_this_state=(
                    "schema drift exceeded threshold "
                    f"{self.schema_drift_threshold}: {schema_drift_value}"
                ),
                failed_sources=failed_sources,
                fallback_chain=fallback_chain,
                schema_validation_result=schema_validation_result,
                pytdx_failed=pytdx_failed,
                fallback_success=fallback_success,
                all_sources_failed=all_sources_failed,
                trace_id=_optional_str(payload.get("trace_id")),
            )

        if all_sources_failed:
            return DecisionTrace(
                state=SystemState.READONLY,
                why_this_state="all configured data sources failed",
                failed_sources=failed_sources,
                fallback_chain=fallback_chain,
                schema_validation_result=schema_validation_result,
                pytdx_failed=pytdx_failed,
                fallback_success=fallback_success,
                all_sources_failed=True,
                trace_id=_optional_str(payload.get("trace_id")),
            )

        if pytdx_failed and fallback_success:
            return DecisionTrace(
                state=SystemState.DEGRADED,
                why_this_state="pytdx failed and a fallback source returned data",
                failed_sources=failed_sources,
                fallback_chain=fallback_chain,
                schema_validation_result=schema_validation_result,
                pytdx_failed=True,
                fallback_success=True,
                all_sources_failed=False,
                trace_id=_optional_str(payload.get("trace_id")),
            )

        return DecisionTrace(
            state=SystemState.NORMAL,
            why_this_state="runtime inputs are within normal thresholds",
            failed_sources=failed_sources,
            fallback_chain=fallback_chain,
            schema_validation_result=schema_validation_result,
            pytdx_failed=pytdx_failed,
            fallback_success=fallback_success,
            all_sources_failed=False,
            trace_id=_optional_str(payload.get("trace_id")),
        )


def decide(context: Mapping[str, Any] | Any) -> SystemState:
    """Return the runtime SystemState for a context."""

    return DecisionEngine().decide(context)


def _context_dict(context: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(context, Mapping):
        return dict(context)
    if hasattr(context, "to_dict"):
        value = context.to_dict()
        if isinstance(value, dict):
            return value
    return {
        key: getattr(context, key)
        for key in dir(context)
        if not key.startswith("_") and not callable(getattr(context, key))
    }


def _attempt_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    attempts = []
    for attempt in value:
        if isinstance(attempt, dict):
            row = dict(attempt)
        else:
            row = {
                "source": getattr(attempt, "source", None),
                "source_level": getattr(attempt, "source_level", None),
                "success": getattr(attempt, "success", None),
            }
        row["source_id"] = source_id(str(row.get("source")), row.get("source_level"))
        row["success"] = bool(row.get("success"))
        attempts.append(row)
    return attempts


def _failed_sources(attempts: list[dict[str, Any]]) -> list[str]:
    return [attempt["source_id"] for attempt in attempts if not attempt["success"]]


def _schema_validation_result(payload: dict[str, Any]) -> dict[str, Any]:
    schema_validation = payload.get("schema_validation_result")
    if schema_validation is None:
        schema_validation = payload.get("schema_validation")
    if isinstance(schema_validation, dict):
        return schema_validation
    return {
        "status": "not_checked",
        "schema_drift_fields": [],
        "source_status": {},
        "schema_status": {},
    }


def _schema_drift_value(
    payload: dict[str, Any],
    schema_validation_result: dict[str, Any],
) -> float:
    explicit_rate = _optional_float(payload.get("schema_drift_rate"))
    explicit_count = _optional_float(payload.get("schema_drift_count"))
    values = [
        value
        for value in (explicit_rate, explicit_count)
        if value is not None
    ]
    values.append(float(_count_schema_drift(schema_validation_result)))
    return max(values)


def _count_schema_drift(schema_validation_result: dict[str, Any]) -> int:
    count = 0
    status = str(schema_validation_result.get("status") or "").lower()
    if status == "schema_drift":
        count += 1
    drift_fields = schema_validation_result.get("schema_drift_fields")
    if isinstance(drift_fields, list) and drift_fields:
        count += len(drift_fields)
    schema_status = schema_validation_result.get("schema_status")
    if isinstance(schema_status, dict):
        count += sum(1 for value in schema_status.values() if str(value) == "schema_drift")
    return count


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
