from __future__ import annotations

import json

from astock_source_router.core.audit_logger import AuditLogger


def test_jsonl_utf8_keeps_chinese_text(tmp_path):
    logger = AuditLogger(tmp_path, enable_sqlite=False)
    logger.log(
        {
            "request_id": "utf8-test",
            "feature": "realtime_quotes",
            "function_name": "realtime_quotes",
            "target": "平安银行",
            "selected_source": "fake",
            "attempted_sources": ["fake"],
            "fallback_reason": None,
            "success": True,
            "latency_ms": 1.0,
            "row_count": 1,
            "field_missing": [],
            "missing_fields": [],
            "fallback_trace": [],
            "error_type": None,
            "error_message": None,
        }
    )

    text = (tmp_path / "source_router.jsonl").read_text(encoding="utf-8")

    assert "平安银行" in text
    assert "\\u5e73" not in text
    assert json.loads(text)["target"] == "平安银行"


def test_windows_script_uses_utf8_codepage():
    with open("scripts/run_tests_windows.bat", encoding="utf-8") as f:
        text = f.read()

    assert "chcp 65001 >nul" in text
    assert r'set "VENV_PY=.venv\Scripts\python.exe"' in text
    assert r'"%VENV_PY%" -X utf8 -m pytest -q' in text
    assert r'"%VENV_PY%" -X utf8 -m compileall -q astock_source_router tests examples' in text
    assert r'"%VENV_PY%" -X utf8 scripts\smoke_test_offline.py' in text
    assert r'"%VENV_PY%" -X utf8 scripts\doctor_env.py' in text
    assert r"Please run scripts\setup_dev_windows.bat first." in text


def test_stability_watch_windows_scripts_use_utf8_codepage():
    for path in [
        "scripts/run_stability_watch_windows.bat",
        "scripts/install_stability_watch_task_windows.bat",
        "scripts/uninstall_stability_watch_task_windows.bat",
    ]:
        with open(path, encoding="utf-8") as f:
            text = f.read()

        assert "chcp 65001 >nul" in text

    with open("scripts/run_stability_watch_windows.bat", encoding="utf-8") as f:
        runner = f.read()

    assert "set ENABLE_STABILITY_WATCH=1" in runner
    assert r'"%VENV_PY%" -X utf8 scripts\daily_stability_watch.py' in runner
    assert r'"%VENV_PY%" -X utf8 scripts\stability_summary.py' in runner
