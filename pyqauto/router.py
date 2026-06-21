"""Public quote router implementation."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from pyqauto.adapters.akshare_em_spot_adapter import (
    AKSHARE_EM_SPOT_FIELD_MAPPING,
    AkShareEmSpotAdapter,
)
from pyqauto.adapters.base import BaseQuoteAdapter, code_for_symbol, source_id
from pyqauto.adapters.easyquotation_sina_adapter import (
    EASYQUOTATION_FIELD_MAPPING,
    EasyQuotationSinaAdapter,
)
from pyqauto.adapters.easyquotation_tencent_adapter import EasyQuotationTencentAdapter
from pyqauto.adapters.pytdx_adapter import (
    PYTDX_KLINE_FIELD_MAPPING,
    PYTDX_QUOTE_FIELD_MAPPING,
    PytdxAdapter,
)
from pyqauto.audit import AuditLogger
from pyqauto.exceptions import (
    ConfigurationError,
    ErrorCode,
    NoAvailableSourceError,
    UnsupportedPeriodError,
)
from pyqauto.models import AuditAttempt, AuditRecord, KlineBar, QuoteRecord, utc_now_iso
from pyqauto.policy import (
    SUPPORTED_DAILY_KLINE_PERIODS,
    SUPPORTED_KLINE_PERIODS,
    SUPPORTED_MINUTE_KLINE_PERIODS,
    SourcePolicy,
    load_pytdx_servers,
    load_source_policy,
)
from pyqauto.source_schema import source_schema_diagnostics

DAILY_KLINE_ALIASES = {"1d", "daily", "day"}
KLINE_APIS = {"minute_kline", "daily_kline", "kline"}


class QuoteRouter:
    """Route A-share quote calls across configured data sources."""

    def __init__(
        self,
        *,
        policy: SourcePolicy,
        pytdx_adapters: list[BaseQuoteAdapter],
        akshare_em_spot_adapter: BaseQuoteAdapter | None = None,
        easyquotation_sina_adapter: BaseQuoteAdapter | None = None,
        easyquotation_tencent_adapter: BaseQuoteAdapter | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.policy = policy
        self.pytdx_adapters = pytdx_adapters
        self.akshare_em_spot_adapter = akshare_em_spot_adapter
        self.easyquotation_sina_adapter = easyquotation_sina_adapter
        self.easyquotation_tencent_adapter = easyquotation_tencent_adapter
        self.audit_logger = audit_logger

    @classmethod
    def from_config(
        cls,
        *,
        pytdx_servers_path: str | Path | None = None,
        source_policy_path: str | Path | None = None,
        audit_jsonl_path: str | Path | None = None,
        audit_sqlite_path: str | Path | None = None,
    ) -> "QuoteRouter":
        """Create a router from JSON/YAML config files or bundled defaults."""

        policy = load_source_policy(source_policy_path)
        servers = load_pytdx_servers(pytdx_servers_path)
        pytdx_adapters = [PytdxAdapter(server) for server in servers]
        return cls(
            policy=policy,
            pytdx_adapters=pytdx_adapters,
            akshare_em_spot_adapter=AkShareEmSpotAdapter(),
            easyquotation_sina_adapter=EasyQuotationSinaAdapter(),
            easyquotation_tencent_adapter=EasyQuotationTencentAdapter(),
            audit_logger=AuditLogger(
                jsonl_path=audit_jsonl_path,
                sqlite_path=audit_sqlite_path,
            ),
        )

    def realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._route_quotes(
            "realtime_quotes", list(symbols), include_raw=include_raw
        )

    def full_realtime_quotes(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._route_quotes(
            "full_realtime_quotes", list(symbols), include_raw=include_raw
        )

    def index_realtime(
        self, symbols: list[str], *, include_raw: bool = False
    ) -> list[QuoteRecord]:
        return self._route_quotes(
            "index_realtime", list(symbols), include_raw=include_raw
        )

    def minute_kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 240,
        include_raw: bool = False,
    ) -> list[KlineBar]:
        return self._route_quotes(
            "minute_kline",
            [symbol],
            period=period,
            count=count,
            include_raw=include_raw,
        )

    def daily_kline(
        self,
        symbol: str,
        *,
        count: int = 120,
        include_raw: bool = False,
    ) -> list[KlineBar]:
        return self._route_quotes(
            "daily_kline",
            [symbol],
            count=count,
            include_raw=include_raw,
        )

    def kline(
        self,
        symbol: str,
        *,
        period: str = "1m",
        count: int = 120,
        include_raw: bool = False,
    ) -> list[KlineBar]:
        return self._route_quotes(
            "kline",
            [symbol],
            period=period,
            count=count,
            include_raw=include_raw,
        )

    def diagnose(self) -> dict[str, Any]:
        """Return local router configuration without connecting to providers."""

        return {
            "apis": sorted(self.policy.apis),
            "pytdx_servers": [
                {
                    "source": adapter.source,
                    "source_level": adapter.source_level,
                }
                for adapter in self.pytdx_adapters
            ],
            "akshare_em_spot_enabled": self.akshare_em_spot_adapter is not None,
            "easyquotation_sina_enabled": self.easyquotation_sina_adapter is not None,
            "easyquotation_tencent_enabled": self.easyquotation_tencent_adapter
            is not None,
            "jsonl_audit_enabled": bool(
                self.audit_logger and self.audit_logger.jsonl_path
            ),
            "sqlite_audit_enabled": bool(
                self.audit_logger and self.audit_logger.sqlite_path
            ),
            "source_schema_probe": self._source_schema_probe_diagnostics(),
        }

    def _source_schema_probe_diagnostics(self) -> dict[str, Any]:
        payload = source_schema_diagnostics()
        payload["sources"] = {
            "akshare_em_spot": {
                "source_api": "akshare.stock_zh_a_spot_em",
                "field_mapping": AKSHARE_EM_SPOT_FIELD_MAPPING,
            },
            "pytdx_quote": {
                "source_name": "pytdx",
                "source_api": "pytdx.get_security_quotes",
                "field_mapping": PYTDX_QUOTE_FIELD_MAPPING,
            },
            "pytdx_kline": {
                "source_name": "pytdx",
                "source_api": "pytdx.get_security_bars",
                "field_mapping": PYTDX_KLINE_FIELD_MAPPING,
            },
            "easyquotation_sina": {
                "source_api": "easyquotation.sina.stocks",
                "field_mapping": EASYQUOTATION_FIELD_MAPPING,
            },
            "easyquotation_tencent": {
                "source_api": "easyquotation.tencent.stocks",
                "field_mapping": EASYQUOTATION_FIELD_MAPPING,
            },
        }
        return payload

    def _route_quotes(
        self,
        api_name: str,
        symbols: list[str],
        **kwargs: Any,
    ) -> list[QuoteRecord] | list[KlineBar]:
        trace_id = uuid.uuid4().hex
        call_started_at = utc_now_iso()
        call_started = time.perf_counter()
        attempts: list[AuditAttempt] = []
        fallback_chain: list[str] = []
        last_failed_source: str | None = None
        last_error: BaseException | None = None

        try:
            self._validate_request(api_name, symbols, **kwargs)
            adapters = self._adapters_for_api(api_name)
            if not adapters:
                raise ConfigurationError(
                    f"no enabled source for {api_name}",
                    code=ErrorCode.SOURCE_POLICY_BLOCKED,
                )

            for adapter in adapters:
                adapter_source_id = source_id(adapter.source, adapter.source_level)
                attempt_started_at = utc_now_iso()
                attempt_started = time.perf_counter()
                try:
                    records = self._call_adapter(api_name, adapter, symbols, **kwargs)
                    if not records:
                        raise NoAvailableSourceError(
                            f"{adapter_source_id} returned no records for {api_name}"
                        )
                    duration_ms = _elapsed_ms(attempt_started)
                    attempts.append(
                        AuditAttempt(
                            source=adapter.source,
                            source_level=adapter.source_level,
                            started_at=attempt_started_at,
                            finished_at=utc_now_iso(),
                            duration_ms=duration_ms,
                            success=True,
                            record_count=len(records),
                        )
                    )
                    for record in records:
                        record.source = adapter.source
                        record.source_level = adapter.source_level
                        record.trace_id = trace_id
                        record.is_fallback = bool(fallback_chain)
                        record.fallback_from = last_failed_source
                    self._write_audit(
                        trace_id=trace_id,
                        api_name=api_name,
                        symbols=symbols,
                        started_at=call_started_at,
                        duration_ms=_elapsed_ms(call_started),
                        attempts=attempts,
                        fallback_chain=fallback_chain,
                        selected_source=adapter.source,
                        selected_source_level=adapter.source_level,
                        success=True,
                        error=None,
                        record_count=len(records),
                    )
                    return records
                except Exception as exc:
                    last_error = exc
                    duration_ms = _elapsed_ms(attempt_started)
                    attempts.append(
                        AuditAttempt(
                            source=adapter.source,
                            source_level=adapter.source_level,
                            started_at=attempt_started_at,
                            finished_at=utc_now_iso(),
                            duration_ms=duration_ms,
                            success=False,
                            error_type=exc.__class__.__name__,
                            error_message=str(exc),
                            record_count=0,
                        )
                    )
                    fallback_chain.append(adapter_source_id)
                    last_failed_source = adapter_source_id

            message = f"all configured sources failed for {api_name}"
            if last_error:
                message = f"{message}: {last_error.__class__.__name__}: {last_error}"
            error_code = ErrorCode.FALLBACK_EXHAUSTED
            if attempts and all(attempt.source == "pytdx" for attempt in attempts):
                error_code = ErrorCode.PYTDX_ALL_SERVERS_FAILED
            error = NoAvailableSourceError(message, code=error_code)
            self._write_audit(
                trace_id=trace_id,
                api_name=api_name,
                symbols=symbols,
                started_at=call_started_at,
                duration_ms=_elapsed_ms(call_started),
                attempts=attempts,
                fallback_chain=fallback_chain,
                selected_source=None,
                selected_source_level=None,
                success=False,
                error=error,
                record_count=0,
            )
            raise error
        except Exception:
            raise

    def _adapters_for_api(self, api_name: str) -> list[BaseQuoteAdapter]:
        api_policy = self.policy.api(api_name)
        adapters: list[BaseQuoteAdapter] = []
        for source_name in api_policy.fallback_order:
            if source_name == "pytdx":
                adapters.extend(self.pytdx_adapters)
            elif source_name == "akshare_em_spot" and self.akshare_em_spot_adapter:
                adapters.append(self.akshare_em_spot_adapter)
            elif source_name == "easyquotation_sina" and self.easyquotation_sina_adapter:
                adapters.append(self.easyquotation_sina_adapter)
            elif (
                source_name == "easyquotation_tencent"
                and self.easyquotation_tencent_adapter
            ):
                adapters.append(self.easyquotation_tencent_adapter)
        if api_name in KLINE_APIS:
            return [adapter for adapter in adapters if adapter.source == "pytdx"]
        return adapters

    def _validate_request(self, api_name: str, symbols: list[str], **kwargs: Any) -> None:
        for symbol in symbols:
            code_for_symbol(symbol)
        if api_name == "minute_kline":
            period = str(kwargs.get("period", "1m"))
            if period not in SUPPORTED_MINUTE_KLINE_PERIODS:
                supported = ", ".join(SUPPORTED_MINUTE_KLINE_PERIODS)
                raise UnsupportedPeriodError(
                    f"unsupported pytdx minute period: {period}; supported: {supported}"
                )
        if api_name == "kline":
            period = str(kwargs.get("period", "1m"))
            if self._normalize_kline_period(period) not in SUPPORTED_KLINE_PERIODS:
                supported = ", ".join(SUPPORTED_KLINE_PERIODS)
                raise UnsupportedPeriodError(
                    f"unsupported pytdx kline period: {period}; supported: {supported}"
                )

    def _call_adapter(
        self,
        api_name: str,
        adapter: BaseQuoteAdapter,
        symbols: list[str],
        **kwargs: Any,
    ) -> list[QuoteRecord] | list[KlineBar]:
        if api_name == "minute_kline":
            period = str(kwargs.get("period", "1m"))
            count = int(kwargs.get("count", 240))
            include_raw = bool(kwargs.get("include_raw", False))
            return adapter.minute_kline(
                symbols[0],
                period=period,
                count=count,
                include_raw=include_raw,
            )
        if api_name == "daily_kline":
            count = int(kwargs.get("count", 120))
            include_raw = bool(kwargs.get("include_raw", False))
            return adapter.daily_kline(
                symbols[0],
                count=count,
                include_raw=include_raw,
            )
        if api_name == "kline":
            period = self._normalize_kline_period(str(kwargs.get("period", "1m")))
            count = int(kwargs.get("count", 120))
            include_raw = bool(kwargs.get("include_raw", False))
            if period in SUPPORTED_MINUTE_KLINE_PERIODS:
                return adapter.minute_kline(
                    symbols[0],
                    period=period,
                    count=count,
                    include_raw=include_raw,
                )
            if period in SUPPORTED_DAILY_KLINE_PERIODS:
                return adapter.daily_kline(
                    symbols[0],
                    count=count,
                    include_raw=include_raw,
                )
            supported = ", ".join(SUPPORTED_KLINE_PERIODS)
            raise UnsupportedPeriodError(
                f"unsupported pytdx kline period: {period}; supported: {supported}"
            )
        method = getattr(adapter, api_name)
        return method(symbols, include_raw=bool(kwargs.get("include_raw", False)))

    def _normalize_kline_period(self, period: str) -> str:
        normalized = period.lower()
        if normalized in DAILY_KLINE_ALIASES:
            return "1d"
        return normalized

    def _write_audit(
        self,
        *,
        trace_id: str,
        api_name: str,
        symbols: list[str],
        started_at: str,
        duration_ms: float,
        attempts: list[AuditAttempt],
        fallback_chain: list[str],
        selected_source: str | None,
        selected_source_level: str | None,
        success: bool,
        error: BaseException | None,
        record_count: int,
    ) -> None:
        if not self.audit_logger:
            return
        self.audit_logger.log(
            AuditRecord(
                trace_id=trace_id,
                api_name=api_name,
                symbols=symbols,
                started_at=started_at,
                finished_at=utc_now_iso(),
                duration_ms=duration_ms,
                selected_source=selected_source,
                selected_source_level=selected_source_level,
                attempts=attempts,
                fallback_chain=fallback_chain,
                success=success,
                error_type=error.__class__.__name__ if error else None,
                error_message=str(error) if error else None,
                record_count=record_count,
            )
        )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
