from __future__ import annotations

import json

from aquote_router.policy import load_pytdx_servers, load_source_policy


def test_source_policy_example_parses() -> None:
    policy = load_source_policy("config/source_policy.example.yaml")

    assert policy.api("realtime_quotes").allow_fallback is True
    assert policy.api("realtime_quotes").fallback_order == [
        "pytdx",
        "easyquotation_sina",
        "easyquotation_tencent",
    ]
    assert policy.api("minute_kline").allow_fallback is False
    assert policy.api("minute_kline").fallback_order == ["pytdx"]


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
