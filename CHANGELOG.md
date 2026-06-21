# Changelog

## 0.3.1 - 2026-06-21

- Added the `pyqauto source-schema-probe-live` CLI.
- Added live schema drift firewall reporting with source status, schema status,
  missing fields, drift fields, rejection reasons, errors, and accepted/rejected
  record counts.
- Added `diagnose` support for reading the latest source schema live probe
  summary.
- Preserved AkShare unit rules: raw volume lots convert to shares, and raw
  amount remains RMB yuan without division.
- Fixed easyquotation Tencent composite volume/amount field parsing for current
  real payload shape.
- Kept the package read-only: no investment advice and no order execution.

## 0.3.0 - 2026-06-18

- Renamed the PyPI package, Python import package, CLI command, and GitHub
  repository to `pyqauto`.
- Replaced the former `aquote-router` package name and `aquote_router` import
  path with `pyqauto`.
- Kept the public quote, K-line, source policy, diagnostics, and audit behavior
  unchanged.
- Added migration documentation for users moving from the old package name.
- Kept the release path on GitHub Actions Trusted Publishing only; no local
  twine upload or password-based PyPI publishing is used.

## 0.2.2 - 2026-06-17

- Bundled default source policy and pytdx server config as package data.
- Added the short `aquote` import alias and simple module-level functions such as
  `quote`, `quotes`, `kline`, and `daily`.
- Allowed `QuoteRouter.from_config()` to run without user-supplied config paths.
- Preserved compatibility for legacy `config/source_policy.example.yaml` and
  `config/pytdx_servers.example.json` example paths when local files are absent.
- Updated public examples and quickstart docs to avoid requiring copied config files.

## 0.2.1 - 2026-06-15

- Added and documented pytdx server probe diagnostics.
- Added `pyqauto probe-pytdx`.
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
- Added stable error codes and enhanced `pyqauto diagnose --json`.
- Added issue templates for bug reports, data source failures, adapter requests and documentation issues.
- Added offline tests for open-source maintenance and diagnostics workflows.

## 0.1.0 - 2026-06-14

- Initial open-source release.
- Added pytdx server pool routing with primary, hot backup and backup roles.
- Added easyquotation Sina and Tencent fallback for realtime APIs.
- Added pytdx-only minute kline routing.
- Added source policy, normalized quote model, JSONL audit and SQLite audit.
- Added CLI, examples, tests, GitHub Actions and release checklist.
