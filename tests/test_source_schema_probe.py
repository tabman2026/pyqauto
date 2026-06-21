from __future__ import annotations

import json
from pathlib import Path

from pyqauto.adapters.akshare_em_spot_adapter import AkShareEmSpotAdapter


def test_source_schema_probe_writes_latest_report_and_jsonl(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    adapter = AkShareEmSpotAdapter()
    raw = [
        {
            "代码": "600519",
            "名称": "贵州茅台",
            "最新价": 1200,
            "昨收": 1190,
            "今开": 1195,
            "最高": 1210,
            "最低": 1188,
            "成交量": 123,
            "成交额": 456789,
            "涨跌幅": 0.84,
        }
    ]

    probe = adapter.inspect_raw_schema(raw=raw, fetch_time="2026-06-21T00:00:00Z")

    report_path = tmp_path / "reports" / "latest" / "source_schema_probe.json"
    log_path = tmp_path / "logs" / "source_schema_probe.jsonl"
    assert report_path.exists()
    assert log_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["probes"][0]["source_name"] == "akshare_em_spot"
    for field in [
        "source_name",
        "source_api",
        "raw_type",
        "raw_columns",
        "raw_dtypes",
        "first_row_sample",
        "row_count",
        "fetch_time",
        "error_message",
    ]:
        assert field in probe
    assert "成交量" in probe["raw_columns"]
    assert probe["row_count"] == 1
    assert probe["raw_payload_path"]

