from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from astock_source_router.core.adapter_base import BaseMarketDataAdapter
from astock_source_router.core.errors import (
    PytdxAllServersFailed,
    SourceUnavailableError,
    UnsupportedFeatureError,
)
from astock_source_router.core.features import (
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    MINUTE_KLINE,
    REALTIME_QUOTES,
)
from astock_source_router.core.schema import normalize_code, normalize_codes, safe_pct_chg

DEFAULT_PYTDX_SERVER_POOL: list[tuple[str, int]] = [
    ("180.153.18.170", 7709),
    ("101.227.73.20", 7709),
    ("101.227.77.254", 7709),
    ("14.215.128.18", 7709),
    ("202.108.253.130", 7709),
    ("218.85.139.19", 7709),
    ("119.147.212.81", 7709),
]

ACTIVE_SERVER_POOL_PATH = Path(__file__).resolve().parents[2] / "config" / "pytdx_servers_active.json"

ROLE_ORDER = {
    "primary": 0,
    "hot_backup": 1,
    "backup": 2,
    "backup_pool": 2,
    "fallback": 3,
    "manual": 3,
}

REALTIME_COLUMNS = [
    "date",
    "time",
    "code",
    "name",
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "volume",
    "amount",
    "pct_chg",
]

MINUTE_COLUMNS = ["datetime", "code", "open", "high", "low", "close", "volume", "amount"]

REALTIME_RUNTIME_REQUIRED_COLUMNS = [
    "code",
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "volume",
    "amount",
    "pct_chg",
]

MINUTE_RUNTIME_REQUIRED_COLUMNS = ["datetime", "code", "open", "high", "low", "close", "volume", "amount"]

RUNTIME_NUMERIC_COLUMNS = {
    "last_price",
    "pre_close",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
}

KNOWN_INDEX_NAMES: dict[tuple[int, str], str] = {
    (1, "000001"): "上证指数",
    (0, "399001"): "深证成指",
    (0, "399006"): "创业板指",
    (1, "000300"): "沪深300",
}


@dataclass(frozen=True)
class PytdxServer:
    ip: str
    port: int = 7709
    role: str = "backup"
    latency_ms: float | None = None
    connect_status: str = "PASS"
    quote_status: str = "PASS"
    disabled: bool = False
    fake_fail: bool = False
    source: str = ""
    order: int = 0

    @property
    def endpoint(self) -> str:
        return f"{self.ip}:{self.port}"


class _PytdxAttemptFailed(Exception):
    def __init__(self, error_type: str, message: str) -> None:
        self.error_type = error_type
        self.message = message
        super().__init__(message)


def _active_server_pool_path(active_config_path: Path | None = None) -> Path:
    if active_config_path is not None:
        return active_config_path
    env_path = os.environ.get("PYTDX_ACTIVE_SERVER_POOL_PATH")
    if env_path:
        return Path(env_path)
    return ACTIVE_SERVER_POOL_PATH


def _normalize_status(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_role(value: Any) -> str:
    role = str(value or "backup").strip().lower()
    if role in {"primary_server", "main"}:
        return "primary"
    if role in {"hot", "hotbackup", "hot-backup"}:
        return "hot_backup"
    if role in {"backup_pool", "pool"}:
        return "backup"
    if role not in ROLE_ORDER:
        return "backup"
    return role


def _as_float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _server_is_runtime_candidate(server: PytdxServer) -> bool:
    return not server.disabled and server.connect_status == "PASS" and server.quote_status == "PASS"


def _server_sort_key(server: PytdxServer) -> tuple[int, float, int]:
    latency = server.latency_ms if server.latency_ms is not None else float("inf")
    return (ROLE_ORDER.get(server.role, ROLE_ORDER["backup"]), latency, server.order)


def _dedupe_servers(servers: Iterable[PytdxServer]) -> list[PytdxServer]:
    deduped: dict[tuple[str, int], PytdxServer] = {}
    for server in servers:
        deduped.setdefault((server.ip, server.port), server)
    return list(deduped.values())


def _server_from_config(item: dict[str, Any], order: int) -> PytdxServer | None:
    try:
        ip = str(item["ip"]).strip()
        port = int(item.get("port", 7709))
    except (KeyError, TypeError, ValueError):
        return None
    if not ip:
        return None

    raw_role = item.get("role", item.get("grade", "backup"))
    role = _normalize_role(raw_role)
    disabled = (
        _as_bool(item.get("disabled"))
        or str(item.get("grade") or "").strip().lower() == "disabled"
        or str(item.get("status") or "").strip().lower() == "disabled"
        or str(item.get("enabled") or "").strip().lower() == "false"
    )
    if role == "disabled":
        role = "backup"
        disabled = True

    return PytdxServer(
        ip=ip,
        port=port,
        role=role,
        latency_ms=_as_float_or_none(item.get("latency_ms")),
        connect_status=_normalize_status(item.get("connect_status")),
        quote_status=_normalize_status(item.get("quote_status")),
        disabled=disabled,
        fake_fail=_as_bool(item.get("fake_fail")),
        source=str(item.get("source") or ""),
        order=order,
    )


def _default_server_records(warning: str) -> tuple[list[PytdxServer], list[str]]:
    records = [
        PytdxServer(ip=ip, port=port, role="fallback", source="default_pytdx_server_pool", order=index)
        for index, (ip, port) in enumerate(DEFAULT_PYTDX_SERVER_POOL)
    ]
    return records, [warning]


def _parse_manual_server_pool(raw: str) -> list[PytdxServer]:
    servers: list[PytdxServer] = []
    for index, item in enumerate(raw.split(",")):
        text = item.strip()
        if not text:
            continue
        if ":" not in text:
            servers.append(PytdxServer(ip=text, role="manual", source="PYTDX_SERVER_POOL", order=index))
            continue
        host, port_text = text.rsplit(":", 1)
        servers.append(
            PytdxServer(
                ip=host.strip(),
                port=int(port_text.strip()),
                role="manual",
                source="PYTDX_SERVER_POOL",
                order=index,
            )
        )
    return _dedupe_servers(servers)


def load_pytdx_server_pool_records(
    value: str | None = None,
    *,
    active_config_path: Path | None = None,
) -> tuple[list[PytdxServer], list[str]]:
    raw = value if value is not None else os.environ.get("PYTDX_SERVER_POOL")
    if raw:
        return _parse_manual_server_pool(raw), []

    path = _active_server_pool_path(active_config_path)
    if not path.exists():
        return _default_server_records("active_pool_missing_fallback_default")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_server_records("active_pool_invalid_fallback_default")

    if isinstance(payload, dict):
        raw_servers = payload.get("servers", [])
    elif isinstance(payload, list):
        raw_servers = payload
    else:
        return _default_server_records("active_pool_invalid_fallback_default")

    records: list[PytdxServer] = []
    for index, item in enumerate(raw_servers):
        if not isinstance(item, dict):
            continue
        server = _server_from_config(item, index)
        if server is not None and _server_is_runtime_candidate(server):
            records.append(server)

    records = sorted(_dedupe_servers(records), key=_server_sort_key)
    if not records:
        return _default_server_records("active_pool_empty_fallback_default")
    return records, []


def parse_pytdx_server_pool(value: str | None = None) -> list[tuple[str, int]]:
    """Parse PYTDX_SERVER_POOL values like "ip:port,ip:port"."""

    records, _warnings = load_pytdx_server_pool_records(value)
    return [(server.ip, server.port) for server in records]


def _looks_connected(api: Any, connect_result: Any) -> bool:
    return connect_result is True or connect_result is api or hasattr(connect_result, "get_security_quotes")


class PytdxAdapter(BaseMarketDataAdapter):
    """Optional pytdx adapter for TDX realtime quotes and minute bars."""

    name = "pytdx"
    supported_features = {REALTIME_QUOTES, FULL_REALTIME_QUOTES, INDEX_REALTIME, MINUTE_KLINE}
    default_min_interval_seconds = 0.5

    def __init__(
        self,
        *,
        server_pool: Iterable[tuple[str, int] | PytdxServer] | None = None,
        connect_timeout_seconds: float = 5.0,
        api_factory: Callable[[], Any] | None = None,
        name_lookup_enabled: bool = True,
        active_config_path: Path | None = None,
    ) -> None:
        if server_pool is None:
            self.server_records, self.server_pool_warnings = load_pytdx_server_pool_records(
                active_config_path=active_config_path
            )
        else:
            self.server_records = sorted(
                [self._coerce_server_record(item, index) for index, item in enumerate(server_pool)],
                key=_server_sort_key,
            )
            self.server_pool_warnings = []
        self.server_pool = [(server.ip, server.port) for server in self.server_records]
        self.connect_timeout_seconds = connect_timeout_seconds
        self.api_factory = api_factory
        self.name_lookup_enabled = name_lookup_enabled
        self._name_cache: dict[tuple[int, str], str] = {}
        self.last_server: tuple[str, int] | None = None
        self.last_server_record: PytdxServer | None = None
        self.last_failover_attempts: list[dict[str, Any]] = []
        self.last_failover_metadata: dict[str, Any] = {}

    def _coerce_server_record(self, item: tuple[str, int] | PytdxServer, order: int) -> PytdxServer:
        if isinstance(item, PytdxServer):
            return PytdxServer(
                ip=item.ip,
                port=item.port,
                role=item.role,
                latency_ms=item.latency_ms,
                connect_status=item.connect_status,
                quote_status=item.quote_status,
                disabled=item.disabled,
                fake_fail=item.fake_fail,
                source=item.source,
                order=item.order if item.order else order,
            )
        ip, port = item
        return PytdxServer(ip=str(ip), port=int(port), role="backup", source="manual_server_pool", order=order)

    def _tdx(self) -> Any:
        try:
            from pytdx.hq import TdxHq_API, TDXParams  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise SourceUnavailableError("pytdx is not installed. Install astock-source-router[tdx].") from exc
        return TdxHq_API, TDXParams

    def _new_api(self) -> Any:
        if self.api_factory is not None:
            return self.api_factory()
        TdxHq_API, _ = self._tdx()
        return TdxHq_API(raise_exception=False)

    def _market_for_stock_code(self, code: str) -> int:
        _, TDXParams = self._tdx()
        code6 = normalize_code(code)
        return TDXParams.MARKET_SH if code6.startswith(("6", "9")) else TDXParams.MARKET_SZ

    def _market_for_index_code(self, code: str) -> int:
        _, TDXParams = self._tdx()
        code6 = normalize_code(code)
        return TDXParams.MARKET_SZ if code6.startswith("399") else TDXParams.MARKET_SH

    def _connect_first_available(self) -> tuple[Any, tuple[str, int]]:
        errors: list[str] = []
        for server in self.server_records:
            ip, port = server.ip, server.port
            api = self._new_api()
            try:
                result = api.connect(ip, port, time_out=self.connect_timeout_seconds)
            except Exception as exc:
                errors.append(f"{ip}:{port} {type(exc).__name__}: {exc}")
                continue
            if _looks_connected(api, result):
                self.last_server = (ip, port)
                self.last_server_record = server
                return api, (ip, port)
            with suppress(Exception):
                api.disconnect()
            errors.append(f"{ip}:{port} connect_failed: {result}")
        summary = "; ".join(errors[:5])
        raise SourceUnavailableError(f"no usable pytdx server in pool: {summary}")

    def _timeout_error_type(self, exc: Exception, *, stage: str) -> str:
        text = f"{type(exc).__name__}: {exc}".lower()
        if isinstance(exc, TimeoutError) or "timeout" in text or "timed out" in text:
            return f"{stage}_timeout"
        return f"{stage}_failed" if stage == "connect" else "unknown_error"

    def _server_attempt_base(self, server: PytdxServer) -> dict[str, Any]:
        return {
            "ip": server.ip,
            "port": server.port,
            "endpoint": server.endpoint,
            "role": server.role,
            "latency_ms": server.latency_ms,
            "source": server.source,
        }

    def _selected_server_metadata(
        self,
        function_name: str,
        attempts: list[dict[str, Any]],
        server: PytdxServer | None,
    ) -> dict[str, Any]:
        failed_attempts = [attempt for attempt in attempts if attempt.get("status") != "success"]
        first_failure = failed_attempts[0] if failed_attempts else {}
        selected_server = server.endpoint if server is not None else None
        return {
            "function_name": function_name,
            "pytdx_server_ip": server.ip if server is not None else None,
            "pytdx_server_port": server.port if server is not None else None,
            "pytdx_server_role": server.role if server is not None else None,
            "pytdx_server_latency_ms": server.latency_ms if server is not None else None,
            "pytdx_failover_attempts": attempts,
            "attempted_servers": attempts,
            "selected_server": selected_server,
            "selected_server_role": server.role if server is not None else None,
            "selected_server_latency_ms": server.latency_ms if server is not None else None,
            "failover_reason": first_failure.get("error_type"),
            "failover_count": len(failed_attempts),
            "pytdx_all_failed": server is None,
            "server_pool_warnings": list(self.server_pool_warnings),
        }

    def _attach_metadata(
        self,
        frame: pd.DataFrame,
        function_name: str,
        attempts: list[dict[str, Any]],
        server: PytdxServer,
    ) -> pd.DataFrame:
        metadata = self._selected_server_metadata(function_name, attempts, server)
        frame.attrs["pytdx_runtime_failover"] = metadata
        self.last_server = (server.ip, server.port)
        self.last_server_record = server
        self.last_failover_attempts = attempts
        self.last_failover_metadata = metadata
        return frame

    def _raise_all_servers_failed(self, function_name: str, attempts: list[dict[str, Any]]) -> None:
        metadata = self._selected_server_metadata(function_name, attempts, None)
        self.last_server = None
        self.last_server_record = None
        self.last_failover_attempts = attempts
        self.last_failover_metadata = metadata
        raise PytdxAllServersFailed(function_name, attempts, list(self.server_pool_warnings))

    def _validate_runtime_frame(
        self,
        frame: pd.DataFrame,
        *,
        function_name: str,
        expected_rows: int,
    ) -> None:
        if frame.empty:
            raise _PytdxAttemptFailed("quote_empty", "pytdx returned empty data")
        if expected_rows > 0 and len(frame) < expected_rows:
            raise _PytdxAttemptFailed("quote_empty", f"pytdx returned {len(frame)}/{expected_rows} rows")

        required = (
            MINUTE_RUNTIME_REQUIRED_COLUMNS
            if function_name == MINUTE_KLINE
            else REALTIME_RUNTIME_REQUIRED_COLUMNS
        )
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise _PytdxAttemptFailed("quote_schema_missing", f"missing columns: {missing}")

        numeric_columns = RUNTIME_NUMERIC_COLUMNS.intersection(required).intersection(frame.columns)
        for column in numeric_columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.isna().any():
                raise _PytdxAttemptFailed("quote_invalid_value", f"invalid numeric value in {column}")
            if column in {"last_price", "pre_close", "open", "high", "low", "close"} and (values == 0).any():
                raise _PytdxAttemptFailed("quote_invalid_value", f"zero price in {column}")

    def _fetch_with_runtime_failover(
        self,
        *,
        function_name: str,
        request: Callable[[Any], pd.DataFrame],
        expected_rows: int,
    ) -> pd.DataFrame:
        attempts: list[dict[str, Any]] = []
        for server in self.server_records:
            attempt = self._server_attempt_base(server)
            if server.disabled or server.connect_status != "PASS" or server.quote_status != "PASS":
                attempt.update(
                    {
                        "status": "skipped",
                        "error_type": "server_disabled",
                        "error_message": "server disabled or status is not PASS",
                    }
                )
                attempts.append(attempt)
                continue
            if server.fake_fail:
                attempt.update(
                    {
                        "status": "failed",
                        "error_type": "connect_failed",
                        "error_message": "fake_fail enabled for runtime failover test",
                    }
                )
                attempts.append(attempt)
                continue

            api = self._new_api()
            try:
                connect_result = api.connect(server.ip, server.port, time_out=self.connect_timeout_seconds)
            except Exception as exc:
                attempt.update(
                    {
                        "status": "failed",
                        "error_type": self._timeout_error_type(exc, stage="connect"),
                        "error_message": str(exc),
                    }
                )
                attempts.append(attempt)
                continue

            if not _looks_connected(api, connect_result):
                attempt.update(
                    {
                        "status": "failed",
                        "error_type": "connect_failed",
                        "error_message": str(connect_result),
                    }
                )
                attempts.append(attempt)
                with suppress(Exception):
                    api.disconnect()
                continue

            try:
                frame = request(api)
                self._validate_runtime_frame(
                    frame,
                    function_name=function_name,
                    expected_rows=expected_rows,
                )
            except _PytdxAttemptFailed as exc:
                attempt.update(
                    {
                        "status": "failed",
                        "error_type": exc.error_type,
                        "error_message": exc.message,
                    }
                )
                attempts.append(attempt)
                with suppress(Exception):
                    api.disconnect()
                continue
            except Exception as exc:
                attempt.update(
                    {
                        "status": "failed",
                        "error_type": self._timeout_error_type(exc, stage="quote"),
                        "error_message": str(exc),
                    }
                )
                attempts.append(attempt)
                with suppress(Exception):
                    api.disconnect()
                continue

            attempt.update({"status": "success", "error_type": None, "error_message": None})
            attempts.append(attempt)
            with suppress(Exception):
                api.disconnect()
            return self._attach_metadata(frame, function_name, attempts, server)

        self._raise_all_servers_failed(function_name, attempts)

    def _lookup_names(self, api: Any, targets: list[tuple[int, str]]) -> dict[tuple[int, str], str]:
        if not self.name_lookup_enabled:
            return {}

        for key in targets:
            normalized_key = (key[0], normalize_code(key[1]))
            if normalized_key in KNOWN_INDEX_NAMES:
                self._name_cache.setdefault(normalized_key, KNOWN_INDEX_NAMES[normalized_key])

        missing_by_market: dict[int, set[str]] = {}
        for market, code in targets:
            key = (market, normalize_code(code))
            if key not in self._name_cache:
                missing_by_market.setdefault(market, set()).add(key[1])

        for market, missing_codes in missing_by_market.items():
            if not missing_codes:
                continue
            try:
                count = int(api.get_security_count(market) or 0)
            except Exception:
                count = 30000
            max_count = max(count, 30000)
            for start in range(0, max_count + 1000, 1000):
                if not missing_codes:
                    break
                try:
                    rows = api.get_security_list(market, start) or []
                except Exception:
                    continue
                for row in rows:
                    code = normalize_code(row.get("code"))
                    if code not in missing_codes:
                        continue
                    name = row.get("name")
                    if name is not None and str(name).strip():
                        self._name_cache[(market, code)] = str(name).strip()
                        missing_codes.discard(code)

        return {key: self._name_cache[key] for key in targets if key in self._name_cache}

    def _quotes_to_standard_frame(
        self,
        raw: Any,
        targets: list[tuple[int, str]],
        names: dict[tuple[int, str], str],
    ) -> pd.DataFrame:
        rows = []
        today = datetime.now().strftime("%Y-%m-%d")
        for item in raw or []:
            if not isinstance(item, dict):
                raise _PytdxAttemptFailed("quote_schema_missing", "quote row is not a dict")
            required_raw = ["market", "code", "price", "last_close", "open", "high", "low", "vol", "amount"]
            missing_raw = [column for column in required_raw if column not in item]
            if missing_raw:
                raise _PytdxAttemptFailed("quote_schema_missing", f"missing raw fields: {missing_raw}")
            try:
                market = int(item.get("market"))
                code = normalize_code(item.get("code"))
            except Exception as exc:
                raise _PytdxAttemptFailed("quote_schema_missing", f"invalid market/code: {exc}") from exc
            row = {
                "date": today,
                "time": item.get("servertime"),
                "code": code,
                "name": names.get((market, code), pd.NA),
                "last_price": item.get("price"),
                "pre_close": item.get("last_close"),
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "volume": item.get("vol"),
                "amount": item.get("amount"),
            }
            row["pct_chg"] = safe_pct_chg(
                pd.Series([row["last_price"]]),
                pd.Series([row["pre_close"]]),
            ).iloc[0]
            rows.append(row)
        out = pd.DataFrame(rows)
        if out.empty:
            return out
        target_codes = [normalize_code(code) for _, code in targets]
        out = out[out["code"].isin(target_codes)].copy()
        return out[[column for column in REALTIME_COLUMNS if column in out.columns]]

    def _fetch_quotes(
        self,
        codes: list[str] | tuple[str, ...] | str | None,
        *,
        index: bool = False,
        function_name: str = REALTIME_QUOTES,
    ) -> pd.DataFrame:
        target_codes = normalize_codes(codes)
        if not target_codes:
            raise UnsupportedFeatureError("pytdx realtime requires explicit codes")
        market_func = self._market_for_index_code if index else self._market_for_stock_code
        targets = [(market_func(code), normalize_code(code)) for code in target_codes]

        def request(api: Any) -> pd.DataFrame:
            names = self._lookup_names(api, targets)
            raw = api.get_security_quotes(targets)
            return self._quotes_to_standard_frame(raw, targets, names)

        return self._fetch_with_runtime_failover(
            function_name=function_name,
            request=request,
            expected_rows=len(targets),
        )

    def fetch_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self._fetch_quotes(codes, index=False, function_name=REALTIME_QUOTES)

    def fetch_full_realtime_quotes(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        return self._fetch_quotes(codes, index=False, function_name=FULL_REALTIME_QUOTES)

    def fetch_index_realtime(self, codes: list[str] | tuple[str, ...] | str | None = None) -> pd.DataFrame:
        target_codes = normalize_codes(codes) if codes is not None else ["000001", "399001", "399006", "000300"]
        return self._fetch_quotes(target_codes, index=True, function_name=INDEX_REALTIME)

    def fetch_minute_kline(self, code: str, period: str = "5", adjust: str = "") -> pd.DataFrame:
        if adjust:
            raise UnsupportedFeatureError("pytdx minute_kline does not support adjusted bars")
        _, TDXParams = self._tdx()
        category_map = {
            "1": TDXParams.KLINE_TYPE_1MIN,
            "5": TDXParams.KLINE_TYPE_5MIN,
            "15": TDXParams.KLINE_TYPE_15MIN,
            "30": TDXParams.KLINE_TYPE_30MIN,
            "60": TDXParams.KLINE_TYPE_1HOUR,
        }
        category = category_map.get(str(period))
        if category is None:
            raise UnsupportedFeatureError(f"unsupported pytdx minute period: {period}")
        code6 = normalize_code(code)
        market = self._market_for_stock_code(code6)

        def request(api: Any) -> pd.DataFrame:
            df = pd.DataFrame(api.get_security_bars(category, market, code6, 0, 200) or [])
            if df.empty:
                return df
            out = df.rename(columns={"vol": "volume"}).copy()
            out["code"] = code6
            return out[[column for column in MINUTE_COLUMNS if column in out.columns]]

        return self._fetch_with_runtime_failover(
            function_name=MINUTE_KLINE,
            request=request,
            expected_rows=1,
        )
