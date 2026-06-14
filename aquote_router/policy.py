"""Source policy and pytdx server configuration loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aquote_router.adapters.base import PytdxServer
from aquote_router.exceptions import ConfigurationError, SourcePolicyError

ROLE_ORDER = {"primary": 0, "hot_backup": 1, "backup": 2}
SUPPORTED_APIS = {
    "realtime_quotes",
    "full_realtime_quotes",
    "index_realtime",
    "minute_kline",
}
SUPPORTED_SOURCES = {"pytdx", "easyquotation_sina", "easyquotation_tencent"}


@dataclass(frozen=True)
class ApiPolicy:
    """Fallback policy for one public API."""

    allow_fallback: bool
    fallback_order: list[str]


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
            )

        missing = sorted(SUPPORTED_APIS - set(apis))
        if missing:
            raise SourcePolicyError(f"missing API policy: {missing[0]}")
        if apis["minute_kline"].fallback_order != ["pytdx"]:
            raise SourcePolicyError("minute_kline must be pytdx-only")
        if apis["minute_kline"].allow_fallback:
            raise SourcePolicyError("minute_kline must disable cross-source fallback")
        return cls(apis=apis)

    def api(self, api_name: str) -> ApiPolicy:
        try:
            return self.apis[api_name]
        except KeyError as exc:
            raise SourcePolicyError(f"unsupported API: {api_name}") from exc


def load_source_policy(path: str | Path) -> SourcePolicy:
    """Load and validate source policy from YAML."""

    data = _load_yaml(Path(path))
    return SourcePolicy.from_dict(data)


def load_pytdx_servers(path: str | Path) -> list[PytdxServer]:
    """Load enabled pytdx servers sorted by role and latency."""

    config_path = Path(path)
    if not config_path.exists():
        raise ConfigurationError("pytdx server config file was not found")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError("pytdx server config is not valid JSON") from exc

    if not isinstance(raw, list):
        raise ConfigurationError("pytdx server config must be a JSON list")

    servers: list[PytdxServer] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigurationError("pytdx server entry must be an object")
        role = str(item.get("role", "backup"))
        if role not in ROLE_ORDER:
            raise ConfigurationError(f"unsupported pytdx server role: {role}")
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
            raise ConfigurationError("invalid pytdx server entry") from exc

    return sorted(servers, key=lambda server: (ROLE_ORDER[server.role], server.latency_ms))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError("source policy file was not found")

    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except Exception:
        return _load_simple_policy_yaml(text)

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SourcePolicyError("source policy YAML must be a mapping")
    return data


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
