"""Health scoring for runtime governance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

REQUIRED_SCORE_SOURCES = ("pytdx", "akshare", "efinance")
TIMEOUT_MARKERS = ("timeout", "timed out", "read timed", "connect timed")


@dataclass
class SourceHealthStats:
    """Aggregated runtime health inputs for one source family."""

    source: str
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    schema_checks: int = 0
    schema_drifts: int = 0
    fallback_count: int = 0
    total_duration_ms: float = 0.0

    def record_attempt(
        self,
        *,
        success: bool,
        duration_ms: float | None = None,
        timeout: bool = False,
    ) -> None:
        self.attempts += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        if timeout:
            self.timeouts += 1
        if duration_ms is not None:
            self.total_duration_ms += float(duration_ms)

    def record_schema_check(self, *, schema_drift: bool) -> None:
        self.schema_checks += 1
        if schema_drift:
            self.schema_drifts += 1

    def record_fallback(self) -> None:
        self.fallback_count += 1

    def success_rate(self) -> float:
        if self.attempts == 0:
            return 1.0
        return self.successes / self.attempts

    def timeout_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.timeouts / self.attempts

    def schema_drift_rate(self) -> float:
        if self.schema_checks == 0:
            return 0.0
        return self.schema_drifts / self.schema_checks

    def fallback_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return min(1.0, self.fallback_count / self.attempts)

    def average_duration_ms(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.total_duration_ms / self.attempts

    def score(self) -> float:
        """Return a 0-100 score from success, timeout, drift, and fallback rates."""

        score = (
            self.success_rate() * 45
            + (1 - self.timeout_rate()) * 15
            + (1 - self.schema_drift_rate()) * 30
            + (1 - self.fallback_rate()) * 10
        )
        return round(max(0.0, min(100.0, score)), 3)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["success_rate"] = round(self.success_rate(), 4)
        data["timeout_rate"] = round(self.timeout_rate(), 4)
        data["schema_drift_rate"] = round(self.schema_drift_rate(), 4)
        data["fallback_rate"] = round(self.fallback_rate(), 4)
        data["average_duration_ms"] = round(self.average_duration_ms(), 3)
        data["health_score"] = self.score()
        data["observed"] = self.attempts > 0 or self.schema_checks > 0
        return data


class HealthMonitor:
    """Observe runtime events and expose source health scores."""

    def __init__(self) -> None:
        self._stats: dict[str, SourceHealthStats] = {
            source: SourceHealthStats(source=source) for source in REQUIRED_SCORE_SOURCES
        }

    def observe_attempts(
        self,
        attempts: list[Any],
        *,
        fallback_chain: list[str],
        route_success: bool,
    ) -> None:
        for attempt in attempts:
            source = source_family(_field(attempt, "source"))
            stats = self._source(source)
            stats.record_attempt(
                success=bool(_field(attempt, "success")),
                duration_ms=_optional_float(_field(attempt, "duration_ms")),
                timeout=_is_timeout_attempt(attempt),
            )

        if route_success:
            for source_id_value in fallback_chain:
                self._source(source_family(source_id_value)).record_fallback()

    def observe_schema_validation(
        self,
        *,
        source_name: str,
        adapter_status: str | None,
        schema_drift_fields: list[str] | None = None,
        error_message: str | None = None,
    ) -> None:
        stats = self._source(source_family(source_name))
        status = str(adapter_status or "").lower()
        drift_fields = schema_drift_fields or []
        schema_drift = status == "schema_drift" or bool(drift_fields)
        if status in {"ok", "schema_drift", "field_missing"}:
            stats.record_schema_check(schema_drift=schema_drift)
        if status == "failed":
            stats.record_attempt(
                success=False,
                timeout=_contains_timeout(error_message),
            )

    def observe_live_probe(self, payload: dict[str, Any]) -> None:
        sources = payload.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                self.observe_schema_validation(
                    source_name=str(source.get("source_name") or "unknown"),
                    adapter_status=str(
                        source.get("schema_status") or source.get("source_status") or ""
                    ),
                    schema_drift_fields=_string_list(source.get("schema_drift_fields")),
                    error_message=_optional_str(source.get("error_message")),
                )
            return

        probes = payload.get("probes")
        if not isinstance(probes, list):
            return
        for probe in probes:
            if not isinstance(probe, dict):
                continue
            validate_result = probe.get("validate_result")
            if not isinstance(validate_result, dict):
                validate_result = {}
            diagnose = validate_result.get("diagnose")
            if not isinstance(diagnose, dict):
                diagnose = {}
            self.observe_schema_validation(
                source_name=str(probe.get("source_name") or "unknown"),
                adapter_status=str(
                    validate_result.get("adapter_status")
                    or probe.get("adapter_status")
                    or ""
                ),
                schema_drift_fields=_string_list(diagnose.get("schema_drift_fields")),
                error_message=_optional_str(probe.get("error_message")),
            )

    def score(self, source: str) -> float:
        return self._source(source_family(source)).score()

    def scores(self) -> dict[str, float]:
        return {
            "pytdx_health_score": self.score("pytdx"),
            "akshare_health_score": self.score("akshare"),
            "efinance_health_score": self.score("efinance"),
            "overall_data_health_score": self.overall_score(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            **self.scores(),
            "score_basis": {
                "timeout": "timeout_rate reduces score",
                "schema_drift": "schema_drift_rate reduces score",
                "fallback_rate": "fallback participation reduces score",
                "success_rate": "successful attempts increase score",
            },
            "sources": {
                source: stats.to_dict()
                for source, stats in sorted(self._stats.items(), key=lambda item: item[0])
            },
        }

    def overall_score(self) -> float:
        observed = [
            stats.score()
            for stats in self._stats.values()
            if stats.attempts > 0 or stats.schema_checks > 0
        ]
        if not observed:
            return 100.0
        return round(sum(observed) / len(observed), 3)

    def _source(self, source: str) -> SourceHealthStats:
        if source not in self._stats:
            self._stats[source] = SourceHealthStats(source=source)
        return self._stats[source]


def source_family(value: Any) -> str:
    raw = str(value or "unknown").lower()
    if "pytdx" in raw:
        return "pytdx"
    if "akshare" in raw:
        return "akshare"
    if "efinance" in raw:
        return "efinance"
    if "easyquotation_sina" in raw:
        return "easyquotation_sina"
    if "easyquotation_tencent" in raw:
        return "easyquotation_tencent"
    return raw.split(":", maxsplit=1)[0] or "unknown"


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_timeout_attempt(attempt: Any) -> bool:
    return _contains_timeout(_field(attempt, "error_type")) or _contains_timeout(
        _field(attempt, "error_message")
    )


def _contains_timeout(value: Any) -> bool:
    text = str(value or "").lower()
    return any(marker in text for marker in TIMEOUT_MARKERS)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
