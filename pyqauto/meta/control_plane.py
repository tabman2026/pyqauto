from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pyqauto.meta.decision_engine import MetaDecisionEngine
from pyqauto.meta.explainability import MetaExplainability
from pyqauto.meta.state_aggregator import StateAggregator

SAFETY_BOUNDARIES = {
    "trading_system": False,
    "strategy_or_prediction": False,
    "investment_advice": False,
    "broker_or_qmt_control": False,
    "auto_trade": False,
}


class MetaControlPlane:
    """Unified read-only decision entry for governance, graph, and autonomy."""

    def __init__(
        self,
        *,
        governance: Any = None,
        graph: Any = None,
        autonomy: Any = None,
        state_aggregator: StateAggregator | None = None,
        decision_engine: MetaDecisionEngine | None = None,
        explainability: MetaExplainability | None = None,
    ) -> None:
        self.governance = governance
        self.graph = graph
        self.autonomy = autonomy
        self.state_aggregator = state_aggregator or StateAggregator()
        self.decision_engine = decision_engine or MetaDecisionEngine()
        self.explainability = explainability or MetaExplainability()

    def meta_state(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self.state_aggregator.aggregate(
            governance=self.governance,
            graph=self.graph,
            autonomy=self.autonomy,
            context=context,
        )

    def meta_decision(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = self.meta_state(context=context)
        decision = self.decision_engine.decide(state)
        return {
            "system_state": decision["system_state"],
            "recommended_source": decision["recommended_source"],
            "decision_reason": decision["decision_reason"],
            "winning_rule": decision["winning_rule"],
            "conflict_resolution_path": decision["conflict_resolution_path"],
            "module_contributions": decision["module_contributions"],
        }

    def meta_explain(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = self.meta_state(context=context)
        decision = self.decision_engine.decide(state)
        return self.explainability.explain(meta_state=state, decision=decision)

    def system_brain(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = self.meta_state(context=context)
        decision = self.decision_engine.decide(state)
        explanation = self.explainability.explain(meta_state=state, decision=decision)
        return {
            "role": "pyqauto_meta_control_plane",
            "system_state": decision["system_state"],
            "recommended_source": decision["recommended_source"],
            "decision_reason": decision["decision_reason"],
            "meta_state": state,
            "meta_decision": decision,
            "meta_explain": explanation,
            "safety_boundaries": dict(SAFETY_BOUNDARIES),
        }


def meta_state(
    *,
    governance: Any = None,
    graph: Any = None,
    autonomy: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return governance, graph, autonomy, and merged meta state."""

    return MetaControlPlane(
        governance=governance,
        graph=graph,
        autonomy=autonomy,
    ).meta_state(context=context)


def meta_decision(
    *,
    governance: Any = None,
    graph: Any = None,
    autonomy: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the meta system decision."""

    return MetaControlPlane(
        governance=governance,
        graph=graph,
        autonomy=autonomy,
    ).meta_decision(context=context)


def meta_explain(
    *,
    governance: Any = None,
    graph: Any = None,
    autonomy: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the trace, conflict path, and module contribution explanation."""

    return MetaControlPlane(
        governance=governance,
        graph=graph,
        autonomy=autonomy,
    ).meta_explain(context=context)


def system_brain(
    *,
    governance: Any = None,
    graph: Any = None,
    autonomy: Any = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the global meta control-plane view."""

    return MetaControlPlane(
        governance=governance,
        graph=graph,
        autonomy=autonomy,
    ).system_brain(context=context)
