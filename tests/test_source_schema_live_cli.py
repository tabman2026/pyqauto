from __future__ import annotations

from click.testing import CliRunner

import pyqauto.cli as cli


def test_source_schema_probe_live_warn_is_success(monkeypatch) -> None:
    payload = {
        "overall_status": "WARN",
        "checked_at": "2026-06-21T00:00:00.000+00:00",
        "sources": [],
        "source_status": {
            "easyquotation_sina::easyquotation.sina.stocks": "ok",
            "pytdx::pytdx.get_security_quotes": "failed",
        },
        "schema_status": {
            "easyquotation_sina::easyquotation.sina.stocks": "ok",
            "pytdx::pytdx.get_security_quotes": "failed",
        },
        "missing_fields": {},
        "schema_drift_fields": {},
        "rejected_reason": {},
        "error_message": {
            "pytdx::pytdx.get_security_quotes": "mock timeout",
        },
        "accepted_record_count": 2,
        "rejected_record_count": 0,
    }
    monkeypatch.setattr(cli, "run_source_schema_probe_live", lambda **kwargs: payload)

    result = CliRunner().invoke(cli.main, ["source-schema-probe-live"])

    assert result.exit_code == 0
    assert "overall_status: WARN" in result.output
    assert "accepted_record_count: 2" in result.output


def test_source_schema_probe_live_summary_redacts_absolute_paths(monkeypatch, tmp_path) -> None:
    payload = {
        "overall_status": "PASS",
        "checked_at": "2026-06-21T00:00:00.000+00:00",
        "sources": [],
        "source_status": {},
        "schema_status": {},
        "missing_fields": {},
        "schema_drift_fields": {},
        "rejected_reason": {},
        "error_message": {},
        "accepted_record_count": 1,
        "rejected_record_count": 0,
    }
    monkeypatch.setattr(cli, "run_source_schema_probe_live", lambda **kwargs: payload)

    output_path = tmp_path / "source_schema_probe_live.json"
    result = CliRunner().invoke(
        cli.main,
        ["source-schema-probe-live", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "<absolute-path-redacted>/source_schema_probe_live.json" in result.output
    assert "C:\\Users" not in result.output
    assert "Desktop/CODEX" not in result.output
