"""Runtime governance engine that links audit, health, decisions, and state."""

from __future__ import annotations

import json
from typing import Any

from pyqauto.governance.decision_engine import DecisionEngine, DecisionTrace
from pyqauto.governance.health_monitor import HealthMonitor
from pyqauto.governance.state_machine import RuntimeStateMachine, SystemState
from pyqauto.models import AuditRecord


class RuntimeGovernanceEngine:
    """L5 runtime governance layer for read-only router state inspection."""

    def __init__(
        self,
        *,
        health_monitor: HealthMonitor | None = None,
        decision_engine: DecisionEngine | None = None,
        state_machine: RuntimeStateMachine | None = None,
    ) -> None:
        self.health_monitor = health_monitor or HealthMonitor()
        self.decision_engine = decision_engine or DecisionEngine()
        self.state_machine = state_machine or RuntimeStateMachine()
        self._decision_history: list[dict[str, Any]] = []
        self._observed_live_probe_ids: set[str] = set()

    def observe_audit_record(self, record: AuditRecord) -> dict[str, Any]:
        """Observe one existing audit record and update governance state."""

        self.health_monitor.observe_attempts(
            record.attempts,
            fallback_chain=record.fallback_chain,
            route_success=record.success,
        )
        context = {
            "trace_id": record.trace_id,
            "api_name": record.api_name,
            "attempts": record.attempts,
            "fallback_chain": record.fallback_chain,
            "selected_source": record.selected_source,
            "selected_source_level": record.selected_source_level,
            "success": record.success,
            "error_type": record.error_type,
            "error_message": record.error_message,
            "record_count": record.record_count,
            "schema_validation_result": {
                "status": "not_checked",
                "schema_drift_fields": [],
                "source_status": {},
                "schema_status": {},
            },
        }
        return self._evaluate(context)

    def observe_live_probe(self, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        """Observe the latest live probe report without running network probes."""

        if not payload:
            return None
        probe_id = self._live_probe_id(payload)
        if probe_id in self._observed_live_probe_ids:
            return self.decision_trace()
        self._observed_live_probe_ids.add(probe_id)

        self.health_monitor.observe_live_probe(payload)
        sources = _source_rows(payload)
        attempts = [
            {
                "source": str(source.get("source_name") or "unknown"),
                "source_level": None,
                "success": _source_ok(source),
                "error_message": source.get("error_message"),
            }
            for source in sources
        ]
        selected_source = _first_ok_source(sources)
        failed_sources = [
            str(source.get("source_name") or "unknown")
            for source in sources
            if not _source_ok(source)
        ]
        context = {
            "trace_id": probe_id,
            "api_name": "source_schema_probe_live",
            "attempts": attempts,
            "fallback_chain": failed_sources if selected_source else [],
            "selected_source": selected_source,
            "success": selected_source is not None,
            "all_sources_failed": bool(sources) and selected_source is None,
            "pytdx_failed": any(source.startswith("pytdx") for source in failed_sources),
            "fallback_success": selected_source is not None and bool(failed_sources),
            "schema_drift_count": _schema_drift_count(sources),
            "schema_validation_result": {
                "status": "schema_drift" if _schema_drift_count(sources) else "ok",
                "overall_status": payload.get("overall_status"),
                "source_status": payload.get("source_status") or {},
                "schema_status": payload.get("schema_status") or {},
                "schema_drift_fields": _schema_drift_fields(sources),
            },
        }
        return self._evaluate(context)

    def status(self) -> dict[str, Any]:
        return {
            "runtime_layer": "L5 Runtime Governance Layer",
            "system_state": self.get_system_state().value,
            "health": self.health(),
            "latest_decision_trace": self.decision_trace(),
            "state_history": self.state_machine.history(),
        }

    def health(self) -> dict[str, Any]:
        return self.health_monitor.snapshot()

    def decision_trace(self) -> dict[str, Any]:
        if self._decision_history:
            return dict(self._decision_history[-1])
        return {
            "state": self.get_system_state().value,
            "system_state": self.get_system_state().value,
            "why_this_state": "no runtime decisions recorded yet",
            "failed_sources": [],
            "fallback_chain": [],
            "schema_validation_result": {
                "status": "not_checked",
                "schema_drift_fields": [],
                "source_status": {},
                "schema_status": {},
            },
            "health_scores": self.health_monitor.scores(),
        }

    def decision_history(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._decision_history]

    def get_system_state(self) -> SystemState:
        return self.state_machine.current_state

    def _evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        decision = self.decision_engine.evaluate(context)
        transition = self.state_machine.apply_decision(
            decision.state,
            reason=decision.why_this_state,
            trace_id=decision.trace_id,
        )
        trace = _trace_payload(decision)
        trace["decision_state"] = decision.state.value
        trace["system_state"] = self.state_machine.current_state.value
        trace["state_transition"] = transition.to_dict()
        trace["health_scores"] = self.health_monitor.scores()
        self._decision_history.append(trace)
        self._decision_history = self._decision_history[-100:]
        return trace

    def _live_probe_id(self, payload: dict[str, Any]) -> str:
        value = payload.get("run_id") or payload.get("checked_at") or payload.get("generated_at")
        if value is not None:
            return str(value)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _trace_payload(decision: DecisionTrace) -> dict[str, Any]:
    return decision.to_dict()


def _source_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources = payload.get("sources")
    if isinstance(sources, list):
        return [source for source in sources if isinstance(source, dict)]

    probes = payload.get("probes")
    if not isinstance(probes, list):
        return []
    rows: list[dict[str, Any]] = []
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        validate_result = probe.get("validate_result")
        if not isinstance(validate_result, dict):
            validate_result = {}
        diagnose = validate_result.get("diagnose")
        if not isinstance(diagnose, dict):
            diagnose = {}
        rows.append(
            {
                "source_name": probe.get("source_name"),
                "source_status": probe.get("adapter_status"),
                "schema_status": validate_result.get("adapter_status"),
                "schema_drift_fields": diagnose.get("schema_drift_fields") or [],
                "error_message": probe.get("error_message"),
            }
        )
    return rows


def _source_ok(source: dict[str, Any]) -> bool:
    return str(source.get("source_status") or source.get("schema_status") or "") == "ok"


def _first_ok_source(sources: list[dict[str, Any]]) -> str | None:
    for source in sources:
        if _source_ok(source):
            return str(source.get("source_name") or "unknown")
    return None


def _schema_drift_count(sources: list[dict[str, Any]]) -> int:
    count = 0
    for source in sources:
        if str(source.get("schema_status")) == "schema_drift":
            count += 1
        fields = source.get("schema_drift_fields")
        if isinstance(fields, list):
            count += len(fields)
    return count


def _schema_drift_fields(sources: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for source in sources:
        source_name = str(source.get("source_name") or "unknown")
        raw_fields = source.get("schema_drift_fields")
        if not isinstance(raw_fields, list):
            continue
        for field in raw_fields:
            fields.append(f"{source_name}:{field}")
    return fields
