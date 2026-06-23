from __future__ import annotations

from typing import Any

from pyqauto.meta.conflict_resolver import ConflictResolver


class MetaDecisionEngine:
    """Produce the final meta decision from an aggregated state snapshot."""

    def __init__(self, *, conflict_resolver: ConflictResolver | None = None) -> None:
        self.conflict_resolver = conflict_resolver or ConflictResolver()

    def decide(self, meta_state: dict[str, Any]) -> dict[str, Any]:
        resolution = self.conflict_resolver.resolve(meta_state)
        payload = {
            "system_state": resolution.system_state,
            "recommended_source": resolution.recommended_source,
            "decision_reason": resolution.decision_reason,
            "winning_rule": resolution.winning_rule,
            "conflict_resolution_path": resolution.conflict_resolution_path,
            "module_contributions": resolution.module_contributions,
        }
        return payload


def decide(meta_state: dict[str, Any]) -> dict[str, Any]:
    """Return the meta decision for a merged subsystem state."""

    return MetaDecisionEngine().decide(meta_state)
