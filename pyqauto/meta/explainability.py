from __future__ import annotations

from typing import Any


class MetaExplainability:
    """Build explainable traces for meta decisions."""

    def explain(
        self,
        *,
        meta_state: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "decision_trace": [
                {
                    "step": "state_aggregation",
                    "governance_state": meta_state["merged"]["governance_state"],
                    "graph_score": meta_state["merged"]["graph_score"],
                    "autonomy_state": meta_state["merged"]["autonomy_state"],
                },
                {
                    "step": "conflict_resolution",
                    "winning_rule": decision["winning_rule"],
                    "system_state": decision["system_state"],
                    "recommended_source": decision["recommended_source"],
                },
            ],
            "conflict_resolution_path": list(decision["conflict_resolution_path"]),
            "module_contributions": dict(decision["module_contributions"]),
            "decision_reason": decision["decision_reason"],
        }


def explain(meta_state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Return a trace that explains a meta decision."""

    return MetaExplainability().explain(meta_state=meta_state, decision=decision)
