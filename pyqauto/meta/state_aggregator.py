from __future__ import annotations

from collections.abc import Mapping
from typing import Any

NORMAL = "NORMAL"
UNKNOWN = "UNKNOWN"


class StateAggregator:
    """Collect public subsystem snapshots for the meta control plane."""

    def aggregate(
        self,
        *,
        governance: Any = None,
        graph: Any = None,
        autonomy: Any = None,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(context or {})
        governance_state = collect_governance_state(governance)
        graph_state = collect_graph_state(graph, payload)
        autonomy_state = collect_autonomy_state(autonomy)
        return {
            "governance": governance_state,
            "graph": graph_state,
            "autonomy": autonomy_state,
            "merged": {
                "context": payload,
                "governance_state": governance_state["state"],
                "graph_score": graph_state["overall_reliability_score"],
                "graph_recommended_source": graph_state["recommended_source"],
                "autonomy_state": autonomy_state["state"],
                "autonomy_recovery_active": bool(autonomy_state["active_recovery"]),
            },
        }


def aggregate_state(
    *,
    governance: Any = None,
    graph: Any = None,
    autonomy: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a merged read-only view of governance, graph, and autonomy signals."""

    return StateAggregator().aggregate(
        governance=governance,
        graph=graph,
        autonomy=autonomy,
        context=context,
    )


def collect_governance_state(governance: Any = None) -> dict[str, Any]:
    snapshot = _snapshot_from(
        governance,
        methods=("status", "decision_trace"),
        object_fields=("current_state", "system_state", "state"),
    )
    state = _state_value(
        _first_present(
            snapshot,
            (
                "system_state",
                "state",
                "governance_state",
                "current_state",
            ),
        ),
        default=NORMAL,
    )
    decision_trace = snapshot.get("latest_decision_trace")
    if decision_trace is None:
        decision_trace = snapshot.get("decision_trace")
    return {
        "state": state,
        "raw": snapshot,
        "decision_trace": decision_trace if isinstance(decision_trace, Mapping) else {},
    }


def collect_graph_state(
    graph: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(context or {})
    snapshot = _graph_snapshot(graph, payload)
    selection = _mapping_from(snapshot.get("selection"))
    source_scores = _mapping_from(snapshot.get("source_scores"))
    ranked_sources = _ranked_sources(
        snapshot.get("ranked_sources")
        or selection.get("ranked_sources")
        or source_scores.get("ranked_sources")
    )
    best_source = _optional_str(
        snapshot.get("best_source")
        or snapshot.get("recommended_source")
        or selection.get("best_source")
    )
    if best_source is None and ranked_sources:
        best_source = _optional_str(ranked_sources[0].get("source"))
    score = _optional_float(
        snapshot.get("overall_reliability_score")
        or snapshot.get("graph_score")
        or source_scores.get("overall_reliability_score")
    )
    if score is None and ranked_sources:
        score = _optional_float(ranked_sources[0].get("reliability_score"))
    return {
        "overall_reliability_score": 100.0 if score is None else score,
        "recommended_source": best_source,
        "ranked_sources": ranked_sources,
        "selection_status": _optional_str(
            snapshot.get("selection_status") or selection.get("selection_status")
        )
        or "not_selected",
        "blocked_by_governance": bool(
            snapshot.get("blocked_by_governance") or selection.get("blocked_by_governance")
        ),
        "raw": snapshot,
    }


def collect_autonomy_state(autonomy: Any = None) -> dict[str, Any]:
    snapshot = _snapshot_from(autonomy, methods=("status",), object_fields=("state",))
    recovery = _list_of_mappings(snapshot.get("recovery") or snapshot.get("recovery_state"))
    active_recovery = [
        row
        for row in recovery
        if _state_value(row.get("state"), default=NORMAL) != NORMAL
    ]
    state = NORMAL
    if any(_state_value(row.get("state"), default=NORMAL) == "BLOCKED" for row in recovery):
        state = "BLOCKED"
    elif active_recovery:
        state = "RECOVERY"
    explicit_state = _state_value(snapshot.get("state"), default=UNKNOWN)
    if explicit_state in {"BLOCKED", "READONLY", "RECOVERY", "DEGRADED"}:
        state = "RECOVERY" if explicit_state == "DEGRADED" else explicit_state
    return {
        "state": state,
        "active_recovery": active_recovery,
        "recovery": recovery,
        "anomalies": _list_of_mappings(snapshot.get("anomalies")),
        "safety_boundaries": _mapping_from(snapshot.get("safety_boundaries")),
        "raw": snapshot,
    }


def _graph_snapshot(graph: Any, context: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(graph, Mapping):
        return dict(graph)
    snapshot: dict[str, Any] = {}
    if graph is None:
        return snapshot

    selection = _call_optional(graph, "select_best_source", context)
    if isinstance(selection, Mapping):
        snapshot["selection"] = dict(selection)
        snapshot.update({key: value for key, value in selection.items() if key not in snapshot})

    source_scores = _call_optional(graph, "source_scores")
    if isinstance(source_scores, Mapping):
        snapshot["source_scores"] = dict(source_scores)

    graph_snapshot = _call_optional(graph, "snapshot")
    if isinstance(graph_snapshot, Mapping):
        for key, value in graph_snapshot.items():
            snapshot.setdefault(key, value)

    source_health = _call_optional(graph, "source_health")
    if isinstance(source_health, Mapping):
        snapshot.setdefault("source_health", dict(source_health))
        snapshot.setdefault("ranked_sources", source_health.get("ranked_sources"))

    ranked_sources = _call_optional(graph, "ranked_sources", context)
    if isinstance(ranked_sources, list):
        snapshot.setdefault("ranked_sources", ranked_sources)

    return snapshot


def _snapshot_from(
    value: Any,
    *,
    methods: tuple[str, ...],
    object_fields: tuple[str, ...],
) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    for method in methods:
        result = _call_optional(value, method)
        if isinstance(result, Mapping):
            return dict(result)
    return {
        field: getattr(value, field)
        for field in object_fields
        if hasattr(value, field)
    }


def _call_optional(value: Any, method: str, *args: Any) -> Any:
    candidate = getattr(value, method, None)
    if not callable(candidate):
        return None
    try:
        return candidate(*args)
    except TypeError:
        if args:
            return candidate()
        raise


def _first_present(snapshot: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in snapshot and snapshot[key] is not None:
            return snapshot[key]
    return None


def _state_value(value: Any, *, default: str = NORMAL) -> str:
    if value is None:
        return default
    raw_value = getattr(value, "value", value)
    return str(raw_value or default).upper()


def _mapping_from(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _ranked_sources(value: Any) -> list[dict[str, Any]]:
    rows = _list_of_mappings(value)
    return [row for row in rows if row.get("source") is not None]


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
