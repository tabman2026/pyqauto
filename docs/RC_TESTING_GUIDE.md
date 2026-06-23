# pyqauto 1.0.0rc2 RC Testing Guide

`pyqauto==1.0.0rc2` is a prerelease candidate. It is not the final `1.0.0`
release.

Install the exact RC:

```bash
python -X utf8 -m pip install pyqauto==1.0.0rc2 -i https://pypi.org/simple
```

Install the latest prerelease candidate:

```bash
python -X utf8 -m pip install --pre pyqauto -i https://pypi.org/simple
```

Rollback to the current stable release:

```bash
python -X utf8 -m pip install --force-reinstall pyqauto==0.3.1 -i https://pypi.org/simple
```

Focus RC testing on:

- Installed CLI command availability, including `pyqauto kline --help`.
- QuoteRouter core quote APIs.
- Governance.
- Reliability Graph.
- Autonomy.
- Meta Control Plane.
- Stability Layer.
- `diagnose`.
- Source schema live probe.
- pytdx probe.

Submit RC issues at:

https://github.com/tabman2026/pyqauto/issues

Include:

- pyqauto version.
- Python version.
- Operating system.
- `trace_id` if available.
- `pyqauto diagnose --json` output.
- Minimal reproduction steps.

Do not upload tokens, cookies, local filesystem paths, account identifiers,
broker login state, or complete sensitive logs. Redact local paths and secrets
before attaching excerpts.

This project provides local market-data infrastructure only. It does not provide
investment advice, trading execution, strategy signals, stock picking, broker
integration, QMT integration, account access, return promises, or automated
trading logic.
