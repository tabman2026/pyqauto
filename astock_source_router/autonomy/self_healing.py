from __future__ import annotations

from dataclasses import asdict, dataclass

SCHEMA_DRIFT_WARNINGS = {
    "missing_required_columns",
    "schema_drift",
    "field_missing",
}


@dataclass(slots=True)
class HealingSnapshot:
    source: str
    feature: str
    drift_score: float = 0.0
    peak_drift_score: float = 0.0
    blocked: bool = False
    consecutive_recovery_observations: int = 0
    observations: int = 0
    last_action: str = "observe"


class SelfHealingMonitor:
    """Track schema-drift recovery and unblock only after drift decreases."""

    def __init__(
        self,
        *,
        block_threshold: float = 1.0,
        unblock_ratio: float = 0.5,
        clean_observations_to_unblock: int = 1,
    ) -> None:
        self.block_threshold = float(block_threshold)
        self.unblock_ratio = float(unblock_ratio)
        self.clean_observations_to_unblock = clean_observations_to_unblock
        self._states: dict[tuple[str, str], HealingSnapshot] = {}

    def _get(self, source: str, feature: str) -> HealingSnapshot:
        key = (source, feature)
        if key not in self._states:
            self._states[key] = HealingSnapshot(source=source, feature=feature)
        return self._states[key]

    def drift_score(self, missing_fields: list[str], warnings: list[str]) -> float:
        score = float(len(missing_fields))
        for warning in warnings:
            warning_head = warning.split(":", 1)[0]
            if warning_head in SCHEMA_DRIFT_WARNINGS:
                score += 1.0
        return score

    def record(
        self,
        *,
        source: str,
        feature: str,
        success: bool = False,
        missing_fields: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> HealingSnapshot:
        state = self._get(source, feature)
        previous_peak = state.peak_drift_score
        missing_fields = missing_fields or []
        warnings = warnings or []
        score = self.drift_score(missing_fields, warnings)
        has_schema_observation = bool(success or missing_fields or score > 0)
        state.observations += 1
        state.drift_score = score
        state.peak_drift_score = max(state.peak_drift_score, score)

        if state.blocked and not has_schema_observation:
            state.last_action = "observe"
            return state

        if score >= self.block_threshold:
            state.blocked = True
            state.consecutive_recovery_observations = 0
            state.last_action = "block_schema_drift"
            return state

        decrease_boundary = previous_peak * self.unblock_ratio
        drift_decreased = previous_peak > 0 and score <= decrease_boundary
        if state.blocked and drift_decreased:
            state.consecutive_recovery_observations += 1
            if state.consecutive_recovery_observations >= self.clean_observations_to_unblock:
                state.blocked = False
                state.peak_drift_score = score
                state.last_action = "unblock_system"
            else:
                state.last_action = "observe_schema_recovery"
            return state

        if drift_decreased:
            state.last_action = "schema_drift_decreased"
        else:
            state.last_action = "observe"
        return state

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
