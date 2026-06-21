# Task 022 Final Report

Date: 2026-06-21

## Scope

- Audited the real pyqauto repository root and confirmed the remote is
  `https://github.com/tabman2026/pyqauto.git`.
- Removed the parent-directory temporary task entry point from the public path.
- Added the formal package CLI `pyqauto source-schema-probe-live`.
- Kept `pyqauto/source_schema_live.py` inside the `pyqauto` package.
- Added live probe report fields for top-level status, source status, schema
  status, missing fields, drift fields, rejection reasons, errors, and
  accepted/rejected record counts.
- Added diagnose support for latest live probe summaries.
- Preserved AkShare volume lots-to-shares and amount-yuan rules.
- Fixed easyquotation Tencent composite volume/amount parsing.

## Audit Conclusion

- The package remains read-only data access infrastructure.
- No investment advice, order execution, account login state, or data
  redistribution service was added.
- All JSON and JSONL writes use explicit UTF-8 and `ensure_ascii=False`.
- Invalid standard rows are rejected before public records are exposed.
- Live outputs remain local and ignored by Git.

## Acceptance Results

- `python -X utf8 -m pytest -q`: passed.
- `python -X utf8 -m ruff check .`: passed.
- `python -X utf8 scripts/check_release.py`: passed.
- `python -X utf8 scripts/smoke_test.py`: passed.
- `python -X utf8 -m build`: passed after allowing build-isolation package
  download for local validation.
- `pyqauto --help`: passed against local 0.3.1 editable install.
- `pyqauto diagnose --json`: passed and shows latest live probe summary after
  the live run.
- `pyqauto source-schema-probe-live --help`: passed.
- Live run: `WARN`; easyquotation Sina and Tencent passed, AkShare remote closed
  the connection, and pytdx servers timed out. No unvalidated public records
  were emitted.
