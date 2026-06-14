"""Public quote router implementation."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from aquote_router.adapters.base import BaseQuoteAdapter, source_id
from aquote_router.adapters.easyquotation_sina_adapter import EasyQuotationSinaAdapter
from aquote_router.adapters.easyquotation_tencent_adapter import EasyQuotationTencentAdapter
from aquote_router.adapters.pytdx_adapter import PytdxAdapter
from aquote_router.audit import AuditLogger
from aquote_router.exceptions import ConfigurationError, NoAvailableSourceError
from aquote_router.models import AuditAttempt, AuditRecord, QuoteRecord, utc_now_iso
from aquote_router.policy import SourcePolicy, load_pytdx_servers, load_source_policy


class QuoteRouter:
    """Route A-share quote calls across configured data sources."""

    def __init__(
        self,
        *,
        policy: SourcePolicy,
        pytdx_adapters: list[BaseQuoteAdapter],
        easyquotation_sina_adapter: BaseQuoteAdapter | None = None,
        easyquotation_tencent_adapter: BaseQuoteAdapter | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.policy = policy
        self.pytdx_adapters = pytdx_adapters
        self.easyquotation_sina_adapter = easyquotation_sina_adapter
        self.easyquotation_tencent_adapter = easyquotation_tencent_adapter
        self.audit_logger = audit_logger

    @classmethod
    def from_config(
        cls,
        *,
        pytdx_servers_path: str | Path,
        source_policy_path: str | Path,
        audit_jsonl_path: str | Path | None = None,
        audit_sqlite_path: str | Path | None = None,
    ) -> "QuoteRouter":
        """Create a router from JSON/YAML config files."""

        policy = load_source_policy(source_policy_path)
        servers = load_pytdx_servers(pytdx_servers_path)
        pytdx_adapters = [PytdxAdapter(server) for server in servers]
        return cls(
            policy=policy,
            pytdx_adapters=pytdx_adapters,
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
    ) -> list[QuoteRecord]:
        return self._route_quotes(
            "minute_kline",
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
            "easyquotation_sina_enabled": self.easyquotation_sina_adapter is not None,
            "easyquotation_tencent_enabled": self.easyquotation_tencent_adapter
            is not None,
            "jsonl_audit_enabled": bool(
                self.audit_logger and self.audit_logger.jsonl_path
            ),
            "sqlite_audit_enabled": bool(
                self.audit_logger and self.audit_logger.sqlite_path
            ),
        }

    def _route_quotes(
        self,
        api_name: str,
        symbols: list[str],
        **kwargs: Any,
    ) -> list[QuoteRecord]:
        trace_id = uuid.uuid4().hex
        call_started_at = utc_now_iso()
        call_started = time.perf_counter()
        attempts: list[AuditAttempt] = []
        fallback_chain: list[str] = []
        last_failed_source: str | None = None
        last_error: BaseException | None = None

        try:
            adapters = self._adapters_for_api(api_name)
            if not adapters:
                raise ConfigurationError(f"no enabled source for {api_name}")

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
            error = NoAvailableSourceError(message)
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
            elif source_name == "easyquotation_sina" and self.easyquotation_sina_adapter:
                adapters.append(self.easyquotation_sina_adapter)
            elif (
                source_name == "easyquotation_tencent"
                and self.easyquotation_tencent_adapter
            ):
                adapters.append(self.easyquotation_tencent_adapter)
        if api_name == "minute_kline":
            return [adapter for adapter in adapters if adapter.source == "pytdx"]
        return adapters

    def _call_adapter(
        self,
        api_name: str,
        adapter: BaseQuoteAdapter,
        symbols: list[str],
        **kwargs: Any,
    ) -> list[QuoteRecord]:
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
        method = getattr(adapter, api_name)
        return method(symbols, include_raw=bool(kwargs.get("include_raw", False)))

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
