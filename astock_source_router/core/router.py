from __future__ import annotations

import importlib.util
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from astock_source_router.autonomy import AutonomousControlLayer
from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.audit_logger import AuditLogger
from astock_source_router.core.cache import TTLCache
from astock_source_router.core.circuit_breaker import CircuitBreaker
from astock_source_router.core.errors import AllSourcesFailedError, DataQualityError
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    MINUTE_KLINE,
    REALTIME_FEATURES,
    REALTIME_QUOTES,
    STOCK_BASIC,
    TRADE_CALENDAR,
)
from astock_source_router.core.health_score import HealthScoreBoard
from astock_source_router.core.models import MarketDataResult, RouterConfig
from astock_source_router.core.policy import SourcePolicy
from astock_source_router.core.rate_limiter import RateLimiter
from astock_source_router.core.registry import SourceRegistry
from astock_source_router.core.schema import (
    add_source_columns,
    coerce_standard_types,
    ensure_dataframe,
    normalize_codes,
    validate_dataframe,
)


class MarketRouter:
    """Unified market-data router with fallback, health score, cache, and audit."""

    def __init__(
        self,
        config: RouterConfig | None = None,
        source_policy: SourcePolicy | None = None,
        adapters: list[BaseMarketDataAdapter] | None = None,
        *,
        auto_register: bool = True,
    ) -> None:
        self.config = config or RouterConfig()
        self.source_policy = source_policy or SourcePolicy()
        self.registry = SourceRegistry()
        self.cache = TTLCache(self.config.cache_dir)
        self.rate_limiter = RateLimiter()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            cooldown_seconds=self.config.circuit_cooldown_seconds,
        )
        self.autonomy = AutonomousControlLayer()
        self.health_scores = HealthScoreBoard(self.config.log_dir / "source_health.json")
        self.audit_logger = AuditLogger(
            self.config.log_dir,
            enable_sqlite=self.config.enable_sqlite_audit,
        )
        if adapters:
            for adapter in adapters:
                self.register_adapter(adapter)
        if auto_register:
            self.auto_register_optional_adapters()

    def auto_register_optional_adapters(self) -> None:
        """Register optional adapters if their dependencies are installed.

        Missing optional dependencies are silently ignored to keep the base package lightweight.
        """

        candidates = [
            ("pytdx", "astock_source_router.adapters.pytdx_adapter", "PytdxAdapter"),
            ("akshare", "astock_source_router.adapters.akshare_adapter", "AkShareAdapter"),
            ("baostock", "astock_source_router.adapters.baostock_adapter", "BaostockAdapter"),
            ("adata", "astock_source_router.adapters.adata_adapter", "ADataAdapter"),
            ("efinance", "astock_source_router.adapters.efinance_adapter", "EFinanceAdapter"),
            ("mootdx", "astock_source_router.adapters.mootdx_adapter", "MootdxAdapter"),
        ]
        for required_module, module_name, class_name in candidates:
            try:
                if importlib.util.find_spec(required_module) is None:
                    continue
                module = __import__(module_name, fromlist=[class_name])
                adapter_cls = getattr(module, class_name)
                adapter = adapter_cls()
                self.register_adapter(adapter)
            except Exception:
                # Optional dependency unavailable or adapter import failed.
                continue
        if importlib.util.find_spec("easyquotation") is not None:
            try:
                module = __import__(
                    "astock_source_router.adapters.easyquotation_adapter",
                    fromlist=["EasyQuotationAdapter"],
                )
                adapter_cls = module.EasyQuotationAdapter
                self.register_adapter(adapter_cls(provider="sina"))
                self.register_adapter(adapter_cls(provider="tencent"))
            except Exception:
                # Optional dependency unavailable or adapter import failed.
                pass

    def register_adapter(self, adapter: BaseMarketDataAdapter) -> None:
        self.registry.register(adapter)

    def registered_sources(self) -> list[str]:
        return self.registry.names()

    def health_report(self) -> pd.DataFrame:
        return pd.DataFrame(
            self.health_scores.report(timeout_ms=self.config.request_timeout_seconds * 1000)
        )

    def autonomy_status(self) -> dict[str, object]:
        return self.autonomy.status()

    def recovery_state(
        self,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.autonomy.recovery_state(source=source, feature=feature)

    def anomaly_report(
        self,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.autonomy.anomaly_report(source=source, feature=feature)

    def source_weight_decay(
        self,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        return self.autonomy.source_weight_decay(source=source, feature=feature)

    def fetch_result(self, feature: str, **kwargs: Any) -> MarketDataResult:
        """Return full result with fallback trace and metadata."""

        return self._execute(feature, **kwargs)

    def realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        """V1 API alias for realtime quote retrieval."""

        return self.get_realtime_quotes(codes)

    def full_realtime_quotes(
        self,
        codes: list[str] | tuple[str, ...] | str | None = None,
    ) -> pd.DataFrame:
        """V1 API alias for full realtime quote retrieval."""

        return self._execute(FULL_REALTIME_QUOTES, codes=codes).data

    def index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        """V1 API alias for index realtime retrieval."""

        return self.get_index_realtime(codes)

    def minute_kline(
        self,
        code: str,
        *,
        period: str = "5",
        adjust: str = "",
    ) -> pd.DataFrame:
        """V1 API alias for minute K-line retrieval."""

        return self.get_minute_kline(code, period=period, adjust=adjust)

    def daily_kline(
        self,
        code: str,
        *,
        start_date: str,
        end_date: str,
        adjust: str = "",
    ) -> pd.DataFrame:
        """V1 API alias for daily K-line retrieval."""

        return self.get_daily_kline(code, start_date, end_date, adjust=adjust)

    def kline(
        self,
        code: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "daily",
        adjust: str = "",
    ) -> pd.DataFrame:
        """V1 API alias for daily or minute K-line retrieval."""

        normalized_period = str(period).lower()
        if normalized_period in {"daily", "day", "1d", "d"}:
            if start_date is None or end_date is None:
                raise ValueError("start_date and end_date are required for daily kline")
            return self.get_daily_kline(code, start_date, end_date, adjust=adjust)
        if normalized_period in {"1", "5", "15", "30", "60", "1m", "5m", "15m", "30m", "60m"}:
            return self.get_minute_kline(code, period=normalized_period.rstrip("m"), adjust=adjust)
        raise ValueError(f"unsupported kline period: {period}")

    def source_health(self) -> dict[str, Any]:
        """V1 API for local source health without connecting to providers."""

        rows = self.health_scores.report(timeout_ms=self.config.request_timeout_seconds * 1000)
        return {
            "api_version": "v1",
            "sources": self.registered_sources(),
            "health": rows,
        }

    def status(self) -> dict[str, Any]:
        """V1 API for local governance-style system status."""

        system_state = self._system_state()
        return {
            "api_version": "v1",
            "system_state": system_state,
            "state": system_state,
            "registered_sources": self.registered_sources(),
            "active_recovery": [
                row for row in self.recovery_state() if str(row.get("state")) != "NORMAL"
            ],
            "latest_decision_trace": self.decision_trace(),
            "safety_boundaries": self._safety_boundaries(),
        }

    def health(self) -> dict[str, Any]:
        """V1 API for combined local source and autonomy health."""

        return {
            "api_version": "v1",
            "system_state": self._system_state(),
            "source_health": self.source_health(),
            "autonomy": self.autonomy_status(),
        }

    def decision_trace(self) -> dict[str, Any]:
        """V1 API for explainable local routing state without provider calls."""

        feature = REALTIME_QUOTES
        return {
            "api_version": "v1",
            "system_state": self._system_state(),
            "feature": feature,
            "ranked_sources": self._ranked_source_scores(feature),
            "recovery": self.recovery_state(),
            "anomalies": self.anomaly_report(),
        }

    def get_system_state(self) -> str:
        """V1 API for the current local system state."""

        return self._system_state()

    def source_scores(self, feature: str | None = None) -> dict[str, Any]:
        """V1 API for local reliability scores by source."""

        selected_feature = feature or REALTIME_QUOTES
        ranked_sources = self._ranked_source_scores(selected_feature)
        overall_score = float(ranked_sources[0]["reliability_score"]) if ranked_sources else 0.0
        return {
            "api_version": "v1",
            "feature": selected_feature,
            "overall_reliability_score": round(overall_score, 3),
            "ranked_sources": ranked_sources,
        }

    def select_best_source(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """V1 API for read-only best-source selection."""

        payload = dict(context or {})
        feature = str(payload.get("feature") or payload.get("api_name") or REALTIME_QUOTES)
        system_state = self._system_state()
        ranked_sources = self._ranked_source_scores(feature)
        blocked = system_state in {"BLOCKED", "READONLY"} or not ranked_sources
        recommended_source = None if blocked else str(ranked_sources[0]["source"])
        return {
            "api_version": "v1",
            "feature": feature,
            "system_state": system_state,
            "recommended_source": recommended_source,
            "best_source": recommended_source,
            "selection_status": "blocked" if blocked else "selected",
            "ranked_sources": ranked_sources,
            "reason": "system_state_blocks_selection" if blocked else "highest_ranked_reliability_score",
        }

    def reliability_graph(self) -> dict[str, Any]:
        """V1 API for a read-only reliability graph snapshot."""

        features = sorted(self.source_policy.policy)
        return {
            "api_version": "v1",
            "system_state": self._system_state(),
            "features": {
                feature: {
                    "source_scores": self.source_scores(feature),
                    "selection": self.select_best_source({"feature": feature}),
                }
                for feature in features
            },
            "source_health": self.source_health(),
        }

    def diagnose(self) -> dict[str, Any]:
        """V1 API for local router diagnostics without connecting to providers."""

        return {
            "api_version": "v1",
            "router": "MarketRouter",
            "registered_sources": self.registered_sources(),
            "source_policy": {feature: self.source_policy.sources_for(feature) for feature in sorted(self.source_policy.policy)},
            "cache_enabled": self.config.enable_cache,
            "sqlite_audit_enabled": self.config.enable_sqlite_audit,
            "autonomy": self.autonomy_status(),
            "source_health": self.source_health(),
            "safety_boundaries": {
                "trading_system": False,
                "strategy_or_prediction": False,
                "investment_advice": False,
                "broker_or_qmt_control": False,
                "auto_trade": False,
            },
        }

    def meta_decision(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """V1 API for read-only meta decision."""

        from pyqauto.meta import meta_decision

        payload = dict(context or {})
        feature = str(payload.get("feature") or REALTIME_QUOTES)
        return meta_decision(
            governance=self._meta_governance_snapshot(),
            graph=self._meta_graph_snapshot(feature),
            autonomy=self.autonomy_status(),
            context=payload,
        )

    def meta_state(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """V1 API for read-only meta state aggregation."""

        from pyqauto.meta import meta_state

        payload = dict(context or {})
        feature = str(payload.get("feature") or REALTIME_QUOTES)
        return meta_state(
            governance=self._meta_governance_snapshot(),
            graph=self._meta_graph_snapshot(feature),
            autonomy=self.autonomy_status(),
            context=payload,
        )

    def meta_explain(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """V1 API for read-only meta decision explanation."""

        from pyqauto.meta import meta_explain

        payload = dict(context or {})
        feature = str(payload.get("feature") or REALTIME_QUOTES)
        return meta_explain(
            governance=self._meta_governance_snapshot(),
            graph=self._meta_graph_snapshot(feature),
            autonomy=self.autonomy_status(),
            context=payload,
        )

    def system_brain(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """V1 API for the read-only meta control-plane snapshot."""

        from pyqauto.meta import system_brain

        payload = dict(context or {})
        feature = str(payload.get("feature") or REALTIME_QUOTES)
        return system_brain(
            governance=self._meta_governance_snapshot(),
            graph=self._meta_graph_snapshot(feature),
            autonomy=self.autonomy_status(),
            context=payload,
        )

    def stability_status(self, *, current_time: datetime | None = None) -> dict[str, Any]:
        """V1 API for the observational Stability Layer status."""

        from pyqauto.stability import stability_status

        return stability_status(
            events=self._audit_events(),
            health_rows=self.health_scores.report(timeout_ms=self.config.request_timeout_seconds * 1000),
            current_time=current_time,
        )

    def get_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self._execute(REALTIME_QUOTES, codes=codes).data

    def get_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self._execute(INDEX_REALTIME, codes=codes).data

    def get_daily_kline(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: str = "",
    ) -> pd.DataFrame:
        return self._execute(
            DAILY_KLINE,
            code=code,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        ).data

    def get_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return self._execute(TRADE_CALENDAR, start_date=start_date, end_date=end_date).data

    def get_minute_kline(
        self,
        code: str,
        period: str = "5",
        adjust: str = "",
    ) -> pd.DataFrame:
        return self._execute(MINUTE_KLINE, code=code, period=period, adjust=adjust).data

    def get_stock_basic(self) -> pd.DataFrame:
        return self._execute(STOCK_BASIC).data

    def _cache_ttl(self, feature: str) -> float:
        if feature in REALTIME_FEATURES:
            return self.config.realtime_cache_seconds
        if feature == TRADE_CALENDAR:
            return self.config.calendar_cache_seconds
        return self.config.daily_cache_seconds

    def _ordered_sources(self, feature: str) -> list[str]:
        policy_sources = self.source_policy.sources_for(feature)
        available = [s for s in policy_sources if self.registry.supports(s, feature)]
        ranked = self.autonomy.rank_sources(feature=feature, sources=available)
        return ranked[: self.config.max_fallback_sources]

    def _meta_graph_snapshot(self, feature: str) -> dict[str, Any]:
        ranked_sources = self._ranked_source_scores(feature)
        recommended_source = str(ranked_sources[0]["source"]) if ranked_sources else None
        graph_score = float(ranked_sources[0]["reliability_score"]) if ranked_sources else 100.0
        return {
            "overall_reliability_score": graph_score,
            "recommended_source": recommended_source,
            "ranked_sources": ranked_sources,
            "selection_status": "selected" if recommended_source else "not_selected",
        }

    def _system_state(self) -> str:
        if not self.registered_sources():
            return "BLOCKED"
        recovery_rows = self.recovery_state()
        non_normal = [row for row in recovery_rows if str(row.get("state")) != "NORMAL"]
        if any(str(row.get("state")) == "BLOCKED" for row in recovery_rows):
            return "BLOCKED"
        if non_normal:
            has_normal_source = any(str(row.get("state")) == "NORMAL" for row in recovery_rows)
            has_recovery_success = any(int(row.get("success_count") or 0) > 0 for row in non_normal)
            if recovery_rows and not has_normal_source and not has_recovery_success:
                return "READONLY"
            return "DEGRADED"
        return "NORMAL"

    def _safety_boundaries(self) -> dict[str, bool]:
        return {
            "trading_system": False,
            "strategy_or_prediction": False,
            "investment_advice": False,
            "broker_or_qmt_control": False,
            "auto_trade": False,
        }

    def _meta_governance_snapshot(self) -> dict[str, Any]:
        system_state = self._system_state()
        return {
            "system_state": system_state,
            "latest_decision_trace": {
                "system_state": system_state,
                "recovery": self.recovery_state(),
                "selection": self.select_best_source({"feature": REALTIME_QUOTES}),
            },
        }

    def _ranked_source_scores(self, feature: str) -> list[dict[str, Any]]:
        timeout_ms = self.config.request_timeout_seconds * 1000
        health_rows = [
            row
            for row in self.health_scores.report(timeout_ms=timeout_ms)
            if row.get("feature") == feature
        ]
        health_by_source = {str(row["source"]): row for row in health_rows if row.get("source")}
        rows: list[dict[str, Any]] = []
        for position, source in enumerate(self._ordered_sources(feature)):
            health = health_by_source.get(source, {})
            rows.append(
                {
                    "source": source,
                    "feature": feature,
                    "reliability_score": round(float(health.get("score", 100.0)), 3),
                    "policy_rank": position,
                    "success_rate": health.get("success_rate", 1.0),
                    "avg_latency_ms": health.get("avg_latency_ms", 0.0),
                    "p95_latency_ms": health.get("p95_latency_ms", 0.0),
                }
            )
        rows.sort(key=lambda row: (-float(row["reliability_score"]), int(row["policy_rank"])))
        return rows

    def _audit_events(self) -> list[dict[str, Any]]:
        if not self.audit_logger.jsonl_path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.audit_logger.jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    events.append(payload)
        return events

    def _record_autonomy_attempt(
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
    ) -> None:
        self.autonomy.record_attempt(
            source=source,
            feature=feature,
            success=success,
            status=status,
            latency_ms=latency_ms,
            row_count=row_count,
            missing_fields=missing_fields,
            warnings=warnings,
            error_type=error_type,
        )

    def _target_from_kwargs(self, feature: str, kwargs: dict[str, Any]) -> str:
        return json.dumps({"function_name": feature, "params": kwargs}, ensure_ascii=False, sort_keys=True, default=str)

    def _quality_context(self, feature: str, kwargs: dict[str, Any]) -> dict[str, object]:
        context: dict[str, object] = {
            "realtime_stale_after_seconds": self.config.realtime_stale_seconds,
        }
        if "start_date" in kwargs:
            context["start_date"] = kwargs["start_date"]
        if "end_date" in kwargs:
            context["end_date"] = kwargs["end_date"]
        if feature in {REALTIME_QUOTES, FULL_REALTIME_QUOTES, LITE_REALTIME_QUOTES, INDEX_REALTIME} and kwargs.get(
            "codes"
        ) is not None:
            context["min_expected_rows"] = len(normalize_codes(kwargs.get("codes")))
        elif feature in {DAILY_KLINE, TRADE_CALENDAR}:
            context["min_expected_rows"] = 1
        return context

    def _fetch_with_timeout(
        self,
        adapter: BaseMarketDataAdapter,
        feature: str,
        kwargs: dict[str, Any],
    ) -> pd.DataFrame:
        timeout_seconds = self.config.request_timeout_seconds
        if timeout_seconds <= 0:
            return adapter.fetch(feature, **kwargs)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(adapter.fetch, feature, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"{adapter.name} timed out after {timeout_seconds} seconds") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _attempted_sources(self, trace: list[dict[str, Any]]) -> list[str]:
        return [str(item["source"]) for item in trace if item.get("source")]

    def _field_missing(self, trace: list[dict[str, Any]]) -> list[str]:
        fields: list[str] = []
        for item in trace:
            for field in item.get("missing_fields", []) or []:
                if field not in fields:
                    fields.append(field)
        return fields

    def _fallback_reason(self, trace: list[dict[str, Any]]) -> str | None:
        for item in trace:
            status = item.get("status")
            if status in {"success", "hit", "cache_hit"}:
                continue
            warnings = item.get("warnings") or []
            if warnings:
                return str(warnings[0])
            if item.get("fallback_reason"):
                return str(item["fallback_reason"])
            if status:
                return str(status)
        return None

    def _pytdx_metadata_from_frame(self, frame: Any) -> dict[str, Any] | None:
        if not isinstance(frame, pd.DataFrame):
            return None
        metadata = frame.attrs.get("pytdx_runtime_failover")
        return dict(metadata) if isinstance(metadata, dict) else None

    def _pytdx_metadata_from_exception(self, exc: Exception, feature: str) -> dict[str, Any] | None:
        attempts = getattr(exc, "attempts", None)
        if not isinstance(attempts, list):
            return None
        failed_attempts = [attempt for attempt in attempts if attempt.get("status") != "success"]
        first_failure = failed_attempts[0] if failed_attempts else {}
        return {
            "function_name": feature,
            "pytdx_server_ip": None,
            "pytdx_server_port": None,
            "pytdx_server_role": None,
            "pytdx_server_latency_ms": None,
            "pytdx_failover_attempts": attempts,
            "attempted_servers": attempts,
            "selected_server": None,
            "selected_server_role": None,
            "selected_server_latency_ms": None,
            "failover_reason": first_failure.get("error_type"),
            "failover_count": len(failed_attempts),
            "pytdx_all_failed": True,
            "server_pool_warnings": list(getattr(exc, "warnings", []) or []),
        }

    def _add_pytdx_trace_metadata(
        self,
        trace_item: dict[str, Any],
        metadata: dict[str, Any] | None,
    ) -> None:
        if not metadata:
            return
        trace_item["pytdx_runtime_failover"] = metadata
        trace_item["pytdx_server_ip"] = metadata.get("pytdx_server_ip")
        trace_item["pytdx_server_port"] = metadata.get("pytdx_server_port")
        trace_item["pytdx_server_role"] = metadata.get("pytdx_server_role")
        trace_item["pytdx_server_latency_ms"] = metadata.get("pytdx_server_latency_ms")
        trace_item["pytdx_failover_attempts"] = metadata.get("pytdx_failover_attempts", [])

    def _pytdx_audit_metadata(
        self,
        trace: list[dict[str, Any]],
        *,
        feature: str,
        target: str,
        selected_source: str | None,
        success: bool,
        error_type: str | None,
    ) -> dict[str, Any] | None:
        for item in trace:
            metadata = item.get("pytdx_runtime_failover")
            if not isinstance(metadata, dict):
                continue
            out = dict(metadata)
            out["function_name"] = feature
            out["target"] = target
            out["fallback_to_source"] = (
                selected_source if metadata.get("pytdx_all_failed") and selected_source else None
            )
            out["success"] = bool(success)
            out["error_type"] = error_type or item.get("error_type") or metadata.get("failover_reason")
            return out
        return None

    def _audit_payload(
        self,
        payload: dict[str, Any],
        trace: list[dict[str, Any]],
        *,
        selected_source: str | None,
        success: bool,
        error_type: str | None,
    ) -> dict[str, Any]:
        pytdx_metadata = self._pytdx_audit_metadata(
            trace,
            feature=str(payload.get("feature") or payload.get("function_name") or ""),
            target=str(payload.get("target") or ""),
            selected_source=selected_source,
            success=success,
            error_type=error_type,
        )
        if pytdx_metadata is not None:
            payload = dict(payload)
            payload["pytdx_runtime_failover"] = pytdx_metadata
        return payload

    def _health_rows(self, feature: str) -> list[dict[str, object]]:
        timeout_ms = self.config.request_timeout_seconds * 1000
        return [
            row
            for row in self.health_scores.report(timeout_ms=timeout_ms)
            if row.get("feature") == feature
        ]

    def _execute(self, feature: str, **kwargs: Any) -> MarketDataResult:
        request_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        target = self._target_from_kwargs(feature, kwargs)
        cache_key = self.cache.build_key(feature, kwargs)
        if self.config.enable_cache:
            cached = self.cache.get(cache_key, self._cache_ttl(feature))
            if cached is not None:
                cached_source = (
                    str(cached["source"].iloc[0])
                    if "source" in cached.columns and len(cached)
                    else "cache"
                )
                trace = [{"source": "cache", "status": "cache_hit"}]
                self.audit_logger.log(
                    {
                        "request_id": request_id,
                        "feature": feature,
                        "function_name": feature,
                        "target": target,
                        "selected_source": cached_source,
                        "attempted_sources": ["cache"],
                        "fallback_reason": None,
                        "success": True,
                        "latency_ms": 0.0,
                        "row_count": len(cached),
                        "field_missing": [],
                        "missing_fields": [],
                        "fallback_trace": trace,
                        "quality_checks": [],
                        "health_scores": self._health_rows(feature),
                        "error_type": None,
                        "error_message": None,
                        "created_at": created_at,
                    }
                )
                return MarketDataResult(
                    request_id=request_id,
                    feature=feature,
                    data=cached,
                    source=cached_source,
                    latency_ms=0.0,
                    fallback_trace=trace,
                    created_at=created_at,
                )

        trace: list[dict[str, Any]] = []
        quality_checks: list[dict[str, Any]] = []
        candidates = self._ordered_sources(feature)
        if not candidates:
            trace.append({"source": "<none>", "status": "no_registered_source"})
            self.autonomy.record_request(feature=feature, trace=trace, success=False)
            self.audit_logger.log(
                {
                    "request_id": request_id,
                    "feature": feature,
                    "function_name": feature,
                    "target": target,
                    "selected_source": None,
                    "attempted_sources": self._attempted_sources(trace),
                    "fallback_reason": self._fallback_reason(trace),
                    "success": False,
                    "latency_ms": None,
                    "row_count": 0,
                    "field_missing": [],
                    "missing_fields": [],
                    "fallback_trace": trace,
                    "quality_checks": quality_checks,
                    "health_scores": self._health_rows(feature),
                    "error_type": "NoRegisteredSource",
                    "error_message": f"No registered source supports {feature}",
                    "created_at": created_at,
                }
            )
            raise AllSourcesFailedError(feature, trace)

        last_error_type: str | None = None
        last_error_message: str | None = None

        for source in candidates:
            adapter = self.registry.get(source)
            if adapter is None:
                continue
            if not self.circuit_breaker.allow(source, feature):
                trace.append({"source": source, "status": "circuit_open", "fallback_reason": "circuit_open"})
                continue

            min_interval = self.config.min_interval_seconds.get(
                source,
                adapter.default_min_interval_seconds,
            )
            self.rate_limiter.wait(source, min_interval)
            started = time.perf_counter()
            try:
                raw = self._fetch_with_timeout(adapter, feature, kwargs)
                pytdx_metadata = self._pytdx_metadata_from_frame(raw) if source == "pytdx" else None
                latency_ms = (time.perf_counter() - started) * 1000
                df = ensure_dataframe(raw)
                df = add_source_columns(df, source=source, latency_ms=latency_ms)
                df = coerce_standard_types(df)
                quality = validate_dataframe(feature, df, context=self._quality_context(feature, kwargs))
                quality_checks.append(
                    {
                        "source": source,
                        "is_valid": quality.is_valid,
                        "row_count": quality.row_count,
                        "missing_fields": quality.missing_fields,
                        "warnings": quality.warnings,
                    }
                )
                trace_item = {
                    "source": source,
                    "status": "success" if quality.is_valid else "quality_failed",
                    "latency_ms": round(latency_ms, 3),
                    "row_count": quality.row_count,
                    "missing_fields": quality.missing_fields,
                    "warnings": quality.warnings,
                    "fallback_reason": quality.warnings[0] if quality.warnings else None,
                }
                self._add_pytdx_trace_metadata(trace_item, pytdx_metadata)
                trace.append(trace_item)
                if not quality.is_valid:
                    self.health_scores.record_failure(
                        source,
                        feature,
                        empty=quality.row_count == 0,
                        field_missing=bool(quality.missing_fields),
                        stale=any(warning.startswith("realtime_stale") for warning in quality.warnings),
                        latency_ms=latency_ms,
                    )
                    self.circuit_breaker.record_failure(source, feature)
                    self._record_autonomy_attempt(
                        source=source,
                        feature=feature,
                        success=False,
                        status="quality_failed",
                        latency_ms=latency_ms,
                        row_count=quality.row_count,
                        missing_fields=quality.missing_fields,
                        warnings=quality.warnings,
                        error_type=DataQualityError.__name__,
                    )
                    last_error_type = DataQualityError.__name__
                    last_error_message = (
                        f"source={source} feature={feature} quality_failed: "
                        f"{quality.warnings}; missing={quality.missing_fields}"
                    )
                    trace[-1]["error_type"] = DataQualityError.__name__
                    trace[-1]["error_message"] = last_error_message
                    continue

                self.health_scores.record_success(source, feature, latency_ms)
                self.circuit_breaker.record_success(source, feature)
                self._record_autonomy_attempt(
                    source=source,
                    feature=feature,
                    success=True,
                    status="success",
                    latency_ms=latency_ms,
                    row_count=quality.row_count,
                    missing_fields=quality.missing_fields,
                    warnings=quality.warnings,
                    error_type=None,
                )
                self.autonomy.record_request(feature=feature, trace=trace, success=True)
                if self.config.enable_cache:
                    self.cache.set(cache_key, df)
                self.audit_logger.log(
                    self._audit_payload(
                        {
                            "request_id": request_id,
                            "feature": feature,
                            "function_name": feature,
                            "target": target,
                            "selected_source": source,
                            "attempted_sources": self._attempted_sources(trace),
                            "fallback_reason": self._fallback_reason(trace),
                            "success": True,
                            "latency_ms": round(latency_ms, 3),
                            "row_count": len(df),
                            "field_missing": self._field_missing(trace),
                            "missing_fields": [],
                            "fallback_trace": trace,
                            "quality_checks": quality_checks,
                            "health_scores": self._health_rows(feature),
                            "error_type": None,
                            "error_message": None,
                            "created_at": created_at,
                        },
                        trace,
                        selected_source=source,
                        success=True,
                        error_type=None,
                    )
                )
                return MarketDataResult(
                    request_id=request_id,
                    feature=feature,
                    data=df,
                    source=source,
                    latency_ms=latency_ms,
                    fallback_trace=trace,
                    created_at=created_at,
                    metadata={"pytdx_runtime_failover": pytdx_metadata} if pytdx_metadata else {},
                )
            except Exception as exc:
                latency_ms = (time.perf_counter() - started) * 1000
                last_error_type = type(exc).__name__
                last_error_message = str(exc)
                status = "timeout" if isinstance(exc, TimeoutError) else "failed"
                pytdx_metadata = self._pytdx_metadata_from_exception(exc, feature) if source == "pytdx" else None
                if not trace or trace[-1].get("source") != source:
                    trace_item = {
                        "source": source,
                        "status": status,
                        "latency_ms": round(latency_ms, 3),
                        "error_type": last_error_type,
                        "error_message": last_error_message,
                        "fallback_reason": status,
                    }
                    self._add_pytdx_trace_metadata(trace_item, pytdx_metadata)
                    trace.append(trace_item)
                elif trace[-1].get("status") != "quality_failed":
                    trace[-1].update(
                        {
                            "status": status,
                            "error_type": last_error_type,
                            "error_message": last_error_message,
                            "fallback_reason": status,
                        }
                    )
                    self._add_pytdx_trace_metadata(trace[-1], pytdx_metadata)
                self.health_scores.record_failure(source, feature, latency_ms=latency_ms)
                self.circuit_breaker.record_failure(source, feature)
                self._record_autonomy_attempt(
                    source=source,
                    feature=feature,
                    success=False,
                    status=status,
                    latency_ms=latency_ms,
                    row_count=None,
                    missing_fields=[],
                    warnings=[],
                    error_type=last_error_type,
                )
                continue

        self.autonomy.record_request(feature=feature, trace=trace, success=False)
        self.audit_logger.log(
            self._audit_payload(
                {
                    "request_id": request_id,
                    "feature": feature,
                    "function_name": feature,
                    "target": target,
                    "selected_source": None,
                    "attempted_sources": self._attempted_sources(trace),
                    "fallback_reason": self._fallback_reason(trace),
                    "success": False,
                    "latency_ms": None,
                    "row_count": 0,
                    "field_missing": self._field_missing(trace),
                    "missing_fields": self._field_missing(trace),
                    "fallback_trace": trace,
                    "quality_checks": quality_checks,
                    "health_scores": self._health_rows(feature),
                    "error_type": last_error_type or "AllSourcesFailedError",
                    "error_message": last_error_message,
                    "created_at": created_at,
                },
                trace,
                selected_source=None,
                success=False,
                error_type=last_error_type or "AllSourcesFailedError",
            )
        )
        raise AllSourcesFailedError(feature, trace)
