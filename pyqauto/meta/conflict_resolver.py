from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

BLOCKED = "BLOCKED"
READONLY = "READONLY"
RECOVERY = "RECOVERY"
NORMAL = "NORMAL"


@dataclass(frozen=True)
class ConflictResolution:
    system_state: str
    recommended_source: str | None
    decision_reason: str
    winning_rule: str
    conflict_resolution_path: list[dict[str, Any]]
    module_contributions: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConflictResolver:
    """Apply meta control-plane priority rules across subsystem signals."""

    def resolve(self, meta_state: dict[str, Any]) -> ConflictResolution:
        governance = dict(meta_state.get("governance") or {})
        graph = dict(meta_state.get("graph") or {})
        autonomy = dict(meta_state.get("autonomy") or {})
        governance_state = _state_value(governance.get("state"))
        autonomy_state = _state_value(autonomy.get("state"))
        graph_source = _optional_str(graph.get("recommended_source"))
        graph_score = _optional_float(graph.get("overall_reliability_score"))

        blocked = governance_state == BLOCKED or autonomy_state == BLOCKED
        readonly = governance_state == READONLY
        autonomy_recovery = autonomy_state in {RECOVERY, "DEGRADED"}
        has_graph_source = graph_source is not None

        path = [
            _path_item(
                "BLOCKED",
                blocked,
                "governance or autonomy reported a blocking state",
            ),
            _path_item(
                "READONLY",
                readonly,
                "governance requires read-only operation",
            ),
            _path_item(
                "AUTONOMY_RECOVERY",
                autonomy_recovery,
                "autonomy recovery is active for at least one source",
            ),
            _path_item(
                "GRAPH_SCORE",
                has_graph_source,
                "reliability graph supplied the top ranked allowed source",
            ),
            _path_item(
                "GOVERNANCE_NORMAL",
                governance_state == NORMAL,
                "governance has no blocking signal",
            ),
        ]

        if blocked:
            return self._result(
                system_state=BLOCKED,
                recommended_source=None,
                reason="BLOCKED signal has highest priority; source selection is disabled.",
                winning_rule="BLOCKED",
                path=path,
                governance=governance,
                graph=graph,
                autonomy=autonomy,
            )
        if readonly:
            return self._result(
                system_state=READONLY,
                recommended_source=None,
                reason="READONLY governance state blocks runtime source selection.",
                winning_rule="READONLY",
                path=path,
                governance=governance,
                graph=graph,
                autonomy=autonomy,
            )
        if autonomy_recovery:
            return self._result(
                system_state=RECOVERY,
                recommended_source=graph_source,
                reason=(
                    "Autonomy recovery is active; graph recommendation is retained "
                    "only as an allowed data-source candidate."
                ),
                winning_rule="AUTONOMY_RECOVERY",
                path=path,
                governance=governance,
                graph=graph,
                autonomy=autonomy,
            )
        if has_graph_source:
            state = governance_state if governance_state not in {"", "UNKNOWN"} else NORMAL
            return self._result(
                system_state=state,
                recommended_source=graph_source,
                reason=(
                    "Reliability graph selected the highest ranked allowed source"
                    + _score_suffix(graph_score)
                    + "."
                ),
                winning_rule="GRAPH_SCORE",
                path=path,
                governance=governance,
                graph=graph,
                autonomy=autonomy,
            )
        return self._result(
            system_state=governance_state if governance_state != "UNKNOWN" else NORMAL,
            recommended_source=None,
            reason="No blocking signal is active, and no graph source was available.",
            winning_rule="GOVERNANCE_NORMAL",
            path=path,
            governance=governance,
            graph=graph,
            autonomy=autonomy,
        )

    def _result(
        self,
        *,
        system_state: str,
        recommended_source: str | None,
        reason: str,
        winning_rule: str,
        path: list[dict[str, Any]],
        governance: dict[str, Any],
        graph: dict[str, Any],
        autonomy: dict[str, Any],
    ) -> ConflictResolution:
        return ConflictResolution(
            system_state=system_state,
            recommended_source=recommended_source,
            decision_reason=reason,
            winning_rule=winning_rule,
            conflict_resolution_path=path,
            module_contributions=_module_contributions(governance, graph, autonomy),
        )


def _module_contributions(
    governance: dict[str, Any],
    graph: dict[str, Any],
    autonomy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "governance": {
            "state": _state_value(governance.get("state")),
            "effect": "blocks" if _state_value(governance.get("state")) in {BLOCKED, READONLY} else "allows",
        },
        "graph": {
            "overall_reliability_score": graph.get("overall_reliability_score"),
            "recommended_source": graph.get("recommended_source"),
            "ranked_source_count": len(graph.get("ranked_sources") or []),
            "effect": "recommends_source" if graph.get("recommended_source") else "no_source",
        },
        "autonomy": {
            "state": _state_value(autonomy.get("state")),
            "active_recovery_count": len(autonomy.get("active_recovery") or []),
            "effect": "recovery_active"
            if _state_value(autonomy.get("state")) in {BLOCKED, RECOVERY, "DEGRADED"}
            else "stable",
        },
    }


def _path_item(rule: str, matched: bool, detail: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "matched": matched,
        "detail": detail,
    }


def _state_value(value: Any) -> str:
    if value is None:
        return NORMAL
    raw_value = getattr(value, "value", value)
    return str(raw_value or NORMAL).upper()


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
    text = str(value)
    return text if text else None


def _score_suffix(score: float | None) -> str:
    if score is None:
        return ""
    return f" with overall reliability score {score:g}"
