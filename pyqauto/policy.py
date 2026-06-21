"""Source policy and pytdx server configuration loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from pyqauto.adapters.base import PytdxServer
from pyqauto.exceptions import ConfigurationError, ErrorCode, SourcePolicyError

DEFAULT_PYTDX_SERVERS_PATH = "config/pytdx_servers.example.json"
DEFAULT_SOURCE_POLICY_PATH = "config/source_policy.example.yaml"
PACKAGED_CONFIG_PACKAGE = "pyqauto.config"
PYTDX_SERVERS_RESOURCE = "pytdx_servers.example.json"
SOURCE_POLICY_RESOURCE = "source_policy.example.yaml"
ROLE_ORDER = {"primary": 0, "hot_backup": 1, "backup": 2}
SUPPORTED_APIS = {
    "realtime_quotes",
    "full_realtime_quotes",
    "index_realtime",
    "minute_kline",
    "daily_kline",
    "kline",
}
SUPPORTED_MINUTE_KLINE_PERIODS = ("1m", "5m", "15m", "30m", "60m")
SUPPORTED_DAILY_KLINE_PERIODS = ("1d",)
SUPPORTED_KLINE_PERIODS = SUPPORTED_MINUTE_KLINE_PERIODS + SUPPORTED_DAILY_KLINE_PERIODS
SUPPORTED_SOURCES = {
    "pytdx",
    "akshare_em_spot",
    "easyquotation_sina",
    "easyquotation_tencent",
}


@dataclass(frozen=True)
class ApiPolicy:
    """Fallback policy for one public API."""

    allow_fallback: bool
    fallback_order: list[str]
    supported_periods: list[str] | None = None


@dataclass(frozen=True)
class SourcePolicy:
    """Configured source policy for all APIs."""

    apis: dict[str, ApiPolicy]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourcePolicy":
        raw_apis = data.get("apis")
        if not isinstance(raw_apis, dict):
            raise SourcePolicyError("source policy must contain an apis mapping")

        apis: dict[str, ApiPolicy] = {}
        for api_name, raw_policy in raw_apis.items():
            if api_name not in SUPPORTED_APIS:
                raise SourcePolicyError(f"unsupported API in source policy: {api_name}")
            if not isinstance(raw_policy, dict):
                raise SourcePolicyError(f"invalid policy for API: {api_name}")

            fallback_order = raw_policy.get("fallback_order")
            if not isinstance(fallback_order, list) or not fallback_order:
                raise SourcePolicyError(f"fallback_order is required for {api_name}")
            unknown_sources = [
                source for source in fallback_order if source not in SUPPORTED_SOURCES
            ]
            if unknown_sources:
                raise SourcePolicyError(
                    f"unsupported source in {api_name}: {unknown_sources[0]}"
                )
            apis[api_name] = ApiPolicy(
                allow_fallback=bool(raw_policy.get("allow_fallback", False)),
                fallback_order=[str(source) for source in fallback_order],
                supported_periods=_optional_str_list(raw_policy.get("supported_periods")),
            )

        missing = sorted(SUPPORTED_APIS - set(apis))
        if missing:
            raise SourcePolicyError(f"missing API policy: {missing[0]}")
        for api_name in ("minute_kline", "daily_kline", "kline"):
            if apis[api_name].fallback_order != ["pytdx"]:
                raise SourcePolicyError(f"{api_name} must be pytdx-only")
            if apis[api_name].allow_fallback:
                raise SourcePolicyError(
                    f"{api_name} must disable cross-source fallback"
                )
        _validate_supported_periods(
            "minute_kline",
            apis["minute_kline"].supported_periods,
            SUPPORTED_MINUTE_KLINE_PERIODS,
        )
        _validate_supported_periods(
            "daily_kline",
            apis["daily_kline"].supported_periods,
            SUPPORTED_DAILY_KLINE_PERIODS,
        )
        _validate_supported_periods(
            "kline",
            apis["kline"].supported_periods,
            SUPPORTED_KLINE_PERIODS,
        )
        return cls(apis=apis)

    def api(self, api_name: str) -> ApiPolicy:
        try:
            return self.apis[api_name]
        except KeyError as exc:
            raise SourcePolicyError(f"unsupported API: {api_name}") from exc


def load_source_policy(path: str | Path | None = None) -> SourcePolicy:
    """Load and validate source policy from YAML."""

    data = _load_yaml_text(read_source_policy_text(path))
    return SourcePolicy.from_dict(data)


def load_pytdx_servers(path: str | Path | None = None) -> list[PytdxServer]:
    """Load enabled pytdx servers sorted by role and latency."""

    try:
        raw = json.loads(read_pytdx_servers_text(path))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            "pytdx server config is not valid JSON",
            code=ErrorCode.CONFIG_PARSE_FAILED,
        ) from exc

    if not isinstance(raw, list):
        raise ConfigurationError(
            "pytdx server config must be a JSON list",
            code=ErrorCode.CONFIG_PARSE_FAILED,
        )

    servers: list[PytdxServer] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigurationError(
                "pytdx server entry must be an object",
                code=ErrorCode.CONFIG_PARSE_FAILED,
            )
        role = str(item.get("role", "backup"))
        if role not in ROLE_ORDER:
            raise ConfigurationError(
                f"unsupported pytdx server role: {role}",
                code=ErrorCode.CONFIG_PARSE_FAILED,
            )
        enabled = bool(item.get("enabled", True))
        if not enabled:
            continue
        try:
            servers.append(
                PytdxServer(
                    host=str(item["host"]),
                    port=int(item.get("port", 7709)),
                    role=role,
                    latency_ms=int(item.get("latency_ms", 999999)),
                    enabled=enabled,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(
                "invalid pytdx server entry",
                code=ErrorCode.CONFIG_PARSE_FAILED,
            ) from exc

    return sorted(servers, key=lambda server: (ROLE_ORDER[server.role], server.latency_ms))


def read_source_policy_text(path: str | Path | None = None) -> str:
    """Read source policy YAML from a path or the bundled default resource."""

    return _read_config_text(
        path,
        default_path=DEFAULT_SOURCE_POLICY_PATH,
        resource_name=SOURCE_POLICY_RESOURCE,
        not_found_message="source policy file was not found",
        not_found_code=ErrorCode.SOURCE_POLICY_NOT_FOUND,
        read_error_message="source policy file could not be read",
        read_error_code=ErrorCode.SOURCE_POLICY_INVALID,
    )


def read_pytdx_servers_text(path: str | Path | None = None) -> str:
    """Read pytdx server JSON from a path or the bundled default resource."""

    return _read_config_text(
        path,
        default_path=DEFAULT_PYTDX_SERVERS_PATH,
        resource_name=PYTDX_SERVERS_RESOURCE,
        not_found_message="pytdx server config file was not found",
        not_found_code=ErrorCode.CONFIG_NOT_FOUND,
        read_error_message="pytdx server config could not be read",
        read_error_code=ErrorCode.CONFIG_PARSE_FAILED,
    )


def _load_yaml_text(text: str) -> dict[str, Any]:
    try:
        import yaml
    except Exception:
        return _load_simple_policy_yaml(text)

    try:
        data = yaml.safe_load(text)
    except Exception as exc:
        raise SourcePolicyError(
            "source policy YAML could not be parsed",
            code=ErrorCode.SOURCE_POLICY_INVALID,
        ) from exc
    if not isinstance(data, dict):
        raise SourcePolicyError("source policy YAML must be a mapping")
    return data


def _read_config_text(
    path: str | Path | None,
    *,
    default_path: str,
    resource_name: str,
    not_found_message: str,
    not_found_code: ErrorCode,
    read_error_message: str,
    read_error_code: ErrorCode,
) -> str:
    if path is None:
        return _read_packaged_config(resource_name, read_error_message, read_error_code)

    config_path = Path(path)
    if config_path.exists():
        try:
            return config_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                read_error_message,
                code=read_error_code,
            ) from exc

    if _is_default_config_path(config_path, default_path):
        return _read_packaged_config(resource_name, read_error_message, read_error_code)

    raise ConfigurationError(not_found_message, code=not_found_code)


def _read_packaged_config(
    resource_name: str,
    read_error_message: str,
    read_error_code: ErrorCode,
) -> str:
    try:
        return (
            files(PACKAGED_CONFIG_PACKAGE)
            .joinpath(resource_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError) as exc:
        raise ConfigurationError(read_error_message, code=read_error_code) from exc


def _is_default_config_path(path: Path, default_path: str) -> bool:
    return str(path).replace("\\", "/") == default_path


def _load_simple_policy_yaml(text: str) -> dict[str, Any]:
    """Parse the project example YAML when PyYAML is not installed."""

    data: dict[str, Any] = {"apis": {}}
    current_api: str | None = None
    current_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped = raw_line.strip()
        if stripped == "apis:":
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    "):
            if not stripped.endswith(":"):
                raise SourcePolicyError("invalid simple source policy YAML")
            current_api = stripped[:-1]
            data["apis"][current_api] = {}
            current_key = None
            continue
        if current_api and raw_line.startswith("    ") and not raw_line.startswith("      "):
            key, _, raw_value = stripped.partition(":")
            value = raw_value.strip()
            current_key = key
            if value == "":
                data["apis"][current_api][key] = []
            elif value.lower() in {"true", "false"}:
                data["apis"][current_api][key] = value.lower() == "true"
            else:
                data["apis"][current_api][key] = value
            continue
        if current_api and current_key and raw_line.startswith("      - "):
            data["apis"][current_api][current_key].append(stripped[2:].strip())
            continue
        raise SourcePolicyError("invalid simple source policy YAML")

    return data


def _optional_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise SourcePolicyError("supported_periods must be a list when provided")
    return [str(item) for item in value]


def _validate_supported_periods(
    api_name: str,
    configured: list[str] | None,
    expected: tuple[str, ...],
) -> None:
    if configured is None:
        return
    if tuple(configured) != expected:
        expected_text = ", ".join(expected)
        raise SourcePolicyError(
            f"{api_name} supported_periods must be exactly: {expected_text}"
        )
