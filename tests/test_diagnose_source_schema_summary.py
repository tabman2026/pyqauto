from __future__ import annotations

import json
from pathlib import Path

from pyqauto.source_schema import source_schema_diagnostics


def test_diagnose_source_schema_summary_reads_latest_live_probe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "reports" / "latest" / "source_schema_probe_live.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(
            {
                "overall_status": "WARN",
                "checked_at": "2026-06-21T00:00:00.000+00:00",
                "source_status": {
                    "easyquotation_sina::easyquotation.sina.stocks": "ok",
                    "pytdx::pytdx.get_security_quotes": "failed",
                },
                "schema_status": {
                    "easyquotation_sina::easyquotation.sina.stocks": "ok",
                    "pytdx::pytdx.get_security_quotes": "failed",
                },
                "accepted_record_count": 2,
                "rejected_record_count": 0,
                "acceptance": {"overall_status": "WARN"},
                "probes": [
                    {
                        "source_name": "pytdx",
                        "source_api": "pytdx.get_security_quotes",
                        "adapter_status": "failed",
                        "validate_result": {
                            "missing_fields": [],
                            "diagnose": {
                                "schema_drift_fields": [],
                                "rejection_reason": "mock timeout",
                            },
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    latest = source_schema_diagnostics()["latest_live_probe"]

    assert latest["exists"] is True
    assert latest["overall_status"] == "WARN"
    assert latest["checked_at"] == "2026-06-21T00:00:00.000+00:00"
    assert latest["source_status"]["pytdx::pytdx.get_security_quotes"] == "failed"
    assert latest["accepted_record_count"] == 2
    assert latest["rejected_record_count"] == 0
