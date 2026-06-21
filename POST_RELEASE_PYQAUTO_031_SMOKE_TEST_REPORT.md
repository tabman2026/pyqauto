# Post Release pyqauto 0.3.1 Smoke Test Report

Date: 2026-06-21

## Result

Passed.

## Environment

- Fresh venv: `.venv_pyqauto_031_check`
- Install source: PyPI `https://pypi.org/simple`
- Installed package: `pyqauto==0.3.1`
- Python: 3.14.5

## Checks

- `python -X utf8 -m pip install --upgrade pip`: passed.
- `python -X utf8 -m pip install pyqauto -i https://pypi.org/simple`: passed.
- `python -X utf8 -c "import pyqauto; print(pyqauto.__version__)"`: `0.3.1`.
- `python -X utf8 -c "from pyqauto import QuoteRouter; print(QuoteRouter)"`: passed.
- `pyqauto --help`: passed and lists `source-schema-probe-live`.
- `pyqauto diagnose --json`: passed and reports `pyqauto_version=0.3.1`.
- `pyqauto source-schema-probe-live --help`: passed.

## Live Probe Summary Available During Check

The repository-local latest live probe summary was visible to `diagnose`:

- `overall_status`: `WARN`
- `easyquotation_sina`: `ok`
- `easyquotation_tencent`: `ok`
- `akshare_em_spot`: `failed`
- `pytdx.get_security_quotes`: `failed`
- `pytdx.get_security_bars`: `failed`
- `accepted_record_count`: `10`
- `rejected_record_count`: `0`

The WARN state is acceptable because at least one source passed and no
unvalidated public records were emitted.
