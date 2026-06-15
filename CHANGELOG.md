# Changelog

## 0.2.1 - 2026-06-15

- Added and documented pytdx server probe diagnostics.
- Added `aquote-router probe-pytdx`.
- Strengthened K-line timeout troubleshooting docs.
- Strengthened live check docs for active local pytdx pools.
- Clarified that active local server pools are not committed to Git.
- Kept the project boundary unchanged and added no investment advice workflow.

## 0.2.0 - 2026-06-15

- Added `daily_kline`.
- Added unified `kline`.
- Documented all supported minute K-line periods including `15m`.
- Added `DATA_SOURCES`, `API_REFERENCE`, `KLINE_GUIDE`, `RETURN_FIELDS`, and `CLI_REFERENCE`.
- Added troubleshooting, error code, symbol, time, unit, upstream risk, roadmap and adapter contributor docs.
- Added stable error codes and enhanced `aquote-router diagnose --json`.
- Added issue templates for bug reports, data source failures, adapter requests and documentation issues.
- Added offline tests for open-source maintenance and diagnostics workflows.

## 0.1.0 - 2026-06-14

- Initial open-source release.
- Added pytdx server pool routing with primary, hot backup and backup roles.
- Added easyquotation Sina and Tencent fallback for realtime APIs.
- Added pytdx-only minute kline routing.
- Added source policy, normalized quote model, JSONL audit and SQLite audit.
- Added CLI, examples, tests, GitHub Actions and release checklist.
