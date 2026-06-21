from __future__ import annotations

import json
from importlib.resources import files

from pyqauto.policy import load_pytdx_servers, load_source_policy
from pyqauto.router import QuoteRouter


def test_source_policy_example_parses() -> None:
    policy = load_source_policy("config/source_policy.example.yaml")

    assert policy.api("realtime_quotes").allow_fallback is True
    assert policy.api("realtime_quotes").fallback_order == [
        "pytdx",
        "akshare_em_spot",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert policy.api("minute_kline").allow_fallback is False
    assert policy.api("minute_kline").fallback_order == ["pytdx"]
    assert policy.api("minute_kline").supported_periods == [
        "1m",
        "5m",
        "15m",
        "30m",
        "60m",
    ]
    assert policy.api("daily_kline").fallback_order == ["pytdx"]
    assert policy.api("daily_kline").supported_periods == ["1d"]
    assert policy.api("kline").fallback_order == ["pytdx"]
    assert policy.api("kline").supported_periods == [
        "1m",
        "5m",
        "15m",
        "30m",
        "60m",
        "1d",
    ]


def test_packaged_default_configs_load_without_project_config(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    policy = load_source_policy()
    servers = load_pytdx_servers()
    router = QuoteRouter.from_config()

    assert policy.api("realtime_quotes").fallback_order[0] == "pytdx"
    assert [server.role for server in servers] == ["primary", "hot_backup", "backup"]
    assert router.diagnose()["pytdx_servers"][0]["source"] == "pytdx"


def test_legacy_example_paths_fall_back_to_packaged_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    policy = load_source_policy("config/source_policy.example.yaml")
    servers = load_pytdx_servers("config/pytdx_servers.example.json")

    assert policy.api("daily_kline").fallback_order == ["pytdx"]
    assert len(servers) == 3


def test_packaged_default_config_resources_exist() -> None:
    config_files = files("pyqauto.config")

    assert config_files.joinpath("source_policy.example.yaml").is_file()
    assert config_files.joinpath("pytdx_servers.example.json").is_file()


def test_pytdx_servers_sorted_by_role_and_latency(tmp_path) -> None:
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            [
                {"host": "b", "port": 7709, "role": "backup", "latency_ms": 1},
                {"host": "p2", "port": 7709, "role": "primary", "latency_ms": 20},
                {"host": "h", "port": 7709, "role": "hot_backup", "latency_ms": 1},
                {"host": "p1", "port": 7709, "role": "primary", "latency_ms": 10},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    servers = load_pytdx_servers(path)

    assert [server.host for server in servers] == ["p1", "p2", "h", "b"]
