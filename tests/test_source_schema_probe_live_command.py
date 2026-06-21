from __future__ import annotations

import json

from click.testing import CliRunner

import pyqauto.cli as cli


def test_source_schema_probe_live_help_can_run() -> None:
    result = CliRunner().invoke(cli.main, ["source-schema-probe-live", "--help"])

    assert result.exit_code == 0
    assert "--json" in result.output
    assert "--output" in result.output
    assert "--jsonl" in result.output


def test_source_schema_probe_live_json_mock_run(monkeypatch) -> None:
    payload = {
        "overall_status": "WARN",
        "checked_at": "2026-06-21T00:00:00.000+00:00",
        "sources": [],
        "source_status": {"easyquotation_sina::easyquotation.sina.stocks": "ok"},
        "schema_status": {"easyquotation_sina::easyquotation.sina.stocks": "ok"},
        "missing_fields": {},
        "schema_drift_fields": {},
        "rejected_reason": {},
        "error_message": {},
        "accepted_record_count": 1,
        "rejected_record_count": 0,
    }
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return payload

    monkeypatch.setattr(cli, "run_source_schema_probe_live", fake_runner)

    result = CliRunner().invoke(
        cli.main,
        ["source-schema-probe-live", "--symbols", "000001", "600000", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == payload
    assert seen["symbols"] == ["000001", "600000"]


def test_source_schema_probe_live_all_failed_exits_nonzero(monkeypatch) -> None:
    payload = {
        "overall_status": "FAIL",
        "checked_at": "2026-06-21T00:00:00.000+00:00",
        "sources": [],
        "source_status": {},
        "schema_status": {},
        "missing_fields": {},
        "schema_drift_fields": {},
        "rejected_reason": {},
        "error_message": {},
        "accepted_record_count": 0,
        "rejected_record_count": 0,
    }
    monkeypatch.setattr(cli, "run_source_schema_probe_live", lambda **kwargs: payload)

    result = CliRunner().invoke(cli.main, ["source-schema-probe-live", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output)["overall_status"] == "FAIL"
