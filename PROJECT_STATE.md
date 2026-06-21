# Project State

Date: 2026-06-21

Version target: `0.3.1`

Current release task status:

- 2026-06-21 live source schema probe task: added the formal package CLI
  `pyqauto source-schema-probe-live`.
- The live probe calls AkShare `stock_zh_a_spot_em`, pytdx quote, pytdx kline,
  easyquotation Sina, and easyquotation Tencent, then writes
  `reports/latest/source_schema_probe_live.json` and
  `logs/source_schema_probe_live.jsonl`.
- The live report records raw columns or keys, dtypes, first row samples,
  `raw_to_standard_mapping`, unit rules, validation results, sample support, and
  adapter status for required samples `600519.SH` and `000001.SZ`.
- Schema drift guards now report `schema_drift` for missing mapped raw fields,
  retain `field_missing` for missing standard output, and record rejection
  reasons in diagnose payloads. Invalid rows are not exposed as public records.
- The live report exposes top-level `overall_status`, `checked_at`, source
  summaries, schema summaries, accepted record counts, and rejected record
  counts. `WARN` is allowed when at least one source passes. `FAIL` exits
  non-zero when no source passes.
- AkShare volume lots continue to convert to shares, AkShare amount remains RMB
  yuan, and easyquotation Tencent composite volume/amount fields are parsed
  before schema validation.
- Validation for this task: root pytest passed (`66 passed in 5.58s`) and root
  ruff passed (`All checks passed!`).
- 2026-06-21 source schema hardening task: implemented adapter-level
  `fetch_raw()`, `inspect_raw_schema()`, `normalize_to_standard()`, and
  `validate_standard_output()` for AkShare Eastmoney spot, pytdx quote/kline,
  and easyquotation Sina/Tencent.
- `akshare_em_spot` is added as an optional realtime quote fallback source
  after pytdx and before easyquotation for `realtime_quotes` and
  `full_realtime_quotes`.
- Raw schema probes write UTF-8 JSON to `reports/latest/source_schema_probe.json`
  and UTF-8 JSONL to `logs/source_schema_probe.jsonl`.
- Standard adapter rows include `symbol`, `symbol_raw`, `market`, `trade_time`,
  `fetch_time`, `last_price`, `pre_close`, `open`, `high`, `low`, `change`,
  `pct_chg`, `volume_shares`, `amount_yuan`, `turnover_rate`, `source_name`,
  `source_api`, `schema_version`, `adapter_status`, and `raw_payload_path`.
- Missing core standard fields now produce `adapter_status=field_missing` and a
  diagnose payload instead of silent zero filling.
- Validation for this task: pytest passed (`97 passed in 11.71s`), ruff passed
  (`All checks passed!`), and `reports/latest/source_schema_probe.json` was
  generated with offline probe records for all requested source families.

- Project brand, PyPI package name, import package, CLI command, and GitHub
  repository are renamed to `pyqauto`.
- The old `aquote-router` package and `aquote_router` import path are no longer
  the recommended installation or import path.
- Default source policy and example pytdx server pool remain bundled as package data.
- The `pyqauto` import package exposes simple module-level functions for default use.
- `QuoteRouter.from_config()` can be called without config path arguments.
- Legacy example paths under `config/` fall back to packaged defaults when the
  caller's project does not have those files.
- Public examples now use the zero-config constructor path by default.

Implemented public APIs:

- `realtime_quotes`
- `full_realtime_quotes`
- `index_realtime`
- `minute_kline`
- `daily_kline`
- `kline`
- `diagnose`
- `probe-pytdx`
- `source-schema-probe-live`

Source policy status:

- Realtime APIs allow source fallback in the documented order.
- K-line APIs are pytdx-only.
- K-line supported periods are documented in source policy and K-line guide.
- `probe-pytdx` writes a local active pytdx pool for diagnostics only.

Validation status:

- v0.3.0 was published to GitHub and PyPI.
- v0.3.1 is required because source schema live probe is now a package CLI and
  package feature, not a parent-directory task script.
- The v0.3.1 task keeps public quote and K-line behavior unchanged under the
  `pyqauto` name.
- The active local pytdx pool is ignored by Git and excluded from release files.
- GitHub repository rename to `tabman2026/pyqauto`: completed.
- GitHub Release v0.3.0: completed.
- PyPI pyqauto 0.3.0: completed.
- GitHub Release v0.3.1: completed.
- PyPI pyqauto 0.3.1: completed through GitHub Actions Trusted Publishing.
- Post-release cold-start smoke test for pyqauto 0.3.1: completed.
