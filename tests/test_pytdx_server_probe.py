from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from aquote_router import pytdx_probe


def _load_probe_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "pytdx_server_probe.py"
    spec = importlib.util.spec_from_file_location("pytdx_server_probe", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_config_candidates_skips_disabled_entries(tmp_path) -> None:
    probe = _load_probe_module()
    path = tmp_path / "servers.json"
    path.write_text(
        json.dumps(
            [
                {"host": "1.1.1.1", "port": 7709, "role": "primary", "latency_ms": 10},
                {"host": "2.2.2.2", "port": 7709, "enabled": False},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    total_count, candidates = probe._load_config_candidates(
        path,
        source="test",
        optional=False,
    )

    assert total_count == 2
    assert [(candidate.host, candidate.role) for candidate in candidates] == [
        ("1.1.1.1", "primary")
    ]


def test_dedupe_candidates_preserves_first_source() -> None:
    probe = _load_probe_module()
    candidates = [
        probe.ServerCandidate("1.1.1.1", 7709, "official"),
        probe.ServerCandidate("1.1.1.1", 7709, "local"),
        probe.ServerCandidate("2.2.2.2", 7709, "local"),
    ]

    deduped = probe._dedupe_candidates(candidates)

    assert [(candidate.host, candidate.source) for candidate in deduped] == [
        ("1.1.1.1", "official"),
        ("2.2.2.2", "local"),
    ]


def test_build_active_config_uses_successful_sorted_results() -> None:
    probe = _load_probe_module()
    results = [
        {
            "host": "fast.example",
            "port": 7709,
            "connect_success": True,
            "realtime_quote_success": True,
            "minute_kline_success": True,
            "daily_kline_success": True,
            "latency_ms": 10.4,
        },
        {
            "host": "slow.example",
            "port": 7709,
            "connect_success": True,
            "realtime_quote_success": True,
            "minute_kline_success": False,
            "daily_kline_success": False,
            "latency_ms": 30.1,
        },
    ]

    active = probe._build_active_config(results, active_count=2)

    assert active == [
        {
            "host": "fast.example",
            "port": 7709,
            "role": "primary",
            "latency_ms": 10,
            "enabled": True,
        },
        {
            "host": "slow.example",
            "port": 7709,
            "role": "hot_backup",
            "latency_ms": 30,
            "enabled": True,
        },
    ]


def test_run_probe_writes_required_result_fields_without_network(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "servers.json"
    output_path = tmp_path / "active.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "host": "1.1.1.1",
                    "port": 7709,
                    "role": "primary",
                    "latency_ms": 10,
                    "enabled": True,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_probe_candidates(candidates, **kwargs):
        assert kwargs["timeout"] == 3.0
        assert kwargs["minute_period"] == "15m"
        return [
            {
                "host": candidates[0].host,
                "port": candidates[0].port,
                "role": candidates[0].role,
                "source": candidates[0].source,
                "connect_success": True,
                "realtime_success": True,
                "realtime_quote_success": True,
                "minute_kline_success": True,
                "daily_kline_success": True,
                "kline_success": True,
                "latency_ms": 12.4,
                "total_latency_ms": 18.1,
                "realtime_count": 1,
                "realtime_quote_count": 1,
                "minute_kline_count": 10,
                "daily_kline_count": 10,
                "error": None,
                "errors": {},
            }
        ]

    monkeypatch.setattr(pytdx_probe, "_load_official_pytdx_servers", lambda: ([], [], None))
    monkeypatch.setattr(pytdx_probe, "_probe_candidates", fake_probe_candidates)

    summary = pytdx_probe.run_probe(
        config_path=config_path,
        output_path=output_path,
        local_config_path=None,
        timeout=3,
        limit=0,
        workers=1,
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == [
        {
            "host": "1.1.1.1",
            "port": 7709,
            "role": "primary",
            "latency_ms": 12,
            "enabled": True,
        }
    ]
    result = summary["results"][0]
    for key in [
        "host",
        "port",
        "role",
        "connect_success",
        "realtime_success",
        "minute_kline_success",
        "daily_kline_success",
        "latency_ms",
        "error",
    ]:
        assert key in result
    assert summary["active_config_path"].endswith("active.json")
