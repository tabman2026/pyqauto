# pyqauto 1.0.0rc2

`1.0.0rc2` is a prerelease candidate for RC validation. It is not the final
`1.0.0` release.

## Fixed

- Fixed GitHub Actions full dependency installation so pytdx is installed for
  full offline test validation.
- Fixed the publish workflow gate so PyPI Trusted Publishing runs only after
  release workflow tests, build, `twine check`, and package content scanning
  succeed.
- Restored the frozen `pyqauto kline` CLI command.
- Added a CLI command snapshot to prevent the installed command set from
  shrinking again.
- Added minimal install and full dependency CI validation.

## Compatibility

- V1 Python API, field meanings, source policy, fallback ordering, and audit log
  structure are unchanged from `1.0.0rc1`.
- `pytdx>=1.72` remains a core dependency for compatibility with the `0.3.1`
  public install contract and the frozen K-line API.
- `1.0.0rc1` remains preserved. Its known CI dependency and installed CLI issues
  are fixed in `1.0.0rc2`.

## Boundaries

- This is still a prerelease candidate, not final `1.0.0`.
- This project provides local market-data infrastructure only.
- It does not provide investment advice.
- It does not connect to trading execution, broker accounts, QMT, order
  placement, position management, strategy signals, or automated trading logic.
