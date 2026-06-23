from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from astock_source_router.autonomy.anomaly_detector import AnomalyDetector
from astock_source_router.autonomy.decay_model import ScoreDecayModel
from astock_source_router.autonomy.self_healing import SelfHealingMonitor

NORMAL = "NORMAL"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"


@dataclass(slots=True)
class RecoverySnapshot:
    source: str
    feature: str
    state: str = NORMAL
    failure_count: int = 0
    success_count: int = 0
    last_status: str = "init"
    last_reason: str | None = None
    blocked_by_schema_drift: bool = False


class RecoveryEngine:
    """Source recovery state machine for data-source availability only."""

    def __init__(self, *, required_success_count: int = 2) -> None:
        self.required_success_count = max(1, int(required_success_count))
        self._states: dict[tuple[str, str], RecoverySnapshot] = {}

    def _get(self, source: str, feature: str) -> RecoverySnapshot:
        key = (source, feature)
        if key not in self._states:
            self._states[key] = RecoverySnapshot(source=source, feature=feature)
        return self._states[key]

    def record_attempt(
        self,
        *,
        source: str,
        feature: str,
        success: bool,
        status: str,
        reason: str | None = None,
        schema_blocked: bool = False,
        schema_unblocked: bool = False,
    ) -> RecoverySnapshot:
        state = self._get(source, feature)
        state.last_status = status
        state.last_reason = reason
        if success or schema_unblocked:
            state.success_count += 1
            state.failure_count = 0
            if schema_unblocked or state.state == NORMAL or state.success_count >= self.required_success_count:
                state.state = NORMAL
                state.blocked_by_schema_drift = False
            return state

        state.failure_count += 1
        state.success_count = 0
        if schema_blocked:
            state.state = BLOCKED
            state.blocked_by_schema_drift = True
        else:
            state.state = DEGRADED
        return state

    def state(self, source: str, feature: str) -> dict[str, object]:
        return asdict(self._get(source, feature))

    def report(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        rows = []
        for state in self._states.values():
            if source is not None and state.source != source:
                continue
            if feature is not None and state.feature != feature:
                continue
            rows.append(asdict(state))
        rows.sort(key=lambda row: (str(row["feature"]), str(row["source"])))
        return rows


class AutonomousControlLayer:
    """L6 autonomous control layer for source recovery and stability."""

    def __init__(
        self,
        *,
        recovery_engine: RecoveryEngine | None = None,
        anomaly_detector: AnomalyDetector | None = None,
        decay_model: ScoreDecayModel | None = None,
        self_healing: SelfHealingMonitor | None = None,
    ) -> None:
        self.recovery_engine = recovery_engine or RecoveryEngine()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.decay_model = decay_model or ScoreDecayModel()
        self.self_healing = self_healing or SelfHealingMonitor()

    def record_attempt(
        self,
        *,
        source: str,
        feature: str,
        success: bool,
        status: str,
        latency_ms: float | None = None,
        row_count: int | None = None,
        missing_fields: list[str] | None = None,
        warnings: list[str] | None = None,
        error_type: str | None = None,
    ) -> dict[str, object]:
        del latency_ms, row_count
        warnings = warnings or []
        missing_fields = missing_fields or []
        anomaly = self.anomaly_detector.record_attempt(
            source=source,
            feature=feature,
            success=success,
            status=status,
        )
        decay = self.decay_model.record(source, feature, 1.0 if success else 0.0)
        healing = self.self_healing.record(
            source=source,
            feature=feature,
            success=success,
            missing_fields=missing_fields,
            warnings=warnings,
        )
        recovery = self.recovery_engine.record_attempt(
            source=source,
            feature=feature,
            success=success,
            status=status,
            reason=error_type or (warnings[0] if warnings else status),
            schema_blocked=healing.blocked,
            schema_unblocked=healing.last_action == "unblock_system",
        )
        return {
            "anomaly": asdict(anomaly) if anomaly is not None else None,
            "decay": asdict(decay),
            "healing": asdict(healing),
            "recovery": asdict(recovery),
        }

    def record_request(
        self,
        *,
        feature: str,
        trace: list[dict[str, Any]],
        success: bool,
    ) -> dict[str, object] | None:
        event = self.anomaly_detector.record_request(feature=feature, trace=trace, success=success)
        if event is None:
            return None
        return asdict(event)

    def rank_sources(self, *, feature: str, sources: list[str]) -> list[str]:
        state_priority = {
            NORMAL: 0,
            DEGRADED: 1,
            BLOCKED: 2,
        }
        index = {source: position for position, source in enumerate(sources)}

        def sort_key(source: str) -> tuple[int, float, int]:
            recovery = self.recovery_engine.state(source, feature)
            priority = state_priority.get(str(recovery["state"]), 1)
            return (priority, -self.decay_model.weight(source, feature), index[source])

        return sorted(sources, key=sort_key)

    def status(self) -> dict[str, object]:
        return {
            "layer": "L6_AUTONOMOUS_CONTROL_LAYER",
            "enabled": True,
            "capabilities": [
                "system_auto_recovery",
                "anomaly_detection",
                "score_decay_model",
                "self_healing_mechanism",
            ],
            "safety_boundaries": {
                "trading_system": False,
                "strategy_or_prediction": False,
                "investment_advice": False,
                "broker_or_qmt_control": False,
                "auto_trade": False,
            },
            "recovery": self.recovery_engine.report(),
            "anomalies": self.anomaly_detector.report(),
            "decay": self.decay_model.report(),
            "self_healing": self.self_healing.report(),
        }

    def recovery_state(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.recovery_engine.report(source=source, feature=feature)

    def anomaly_report(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.anomaly_detector.report(source=source, feature=feature)

    def source_weight_decay(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.decay_model.report(source=source, feature=feature)


__all__ = [
    "AutonomousControlLayer",
    "BLOCKED",
    "DEGRADED",
    "NORMAL",
    "RecoveryEngine",
    "RecoverySnapshot",
]
