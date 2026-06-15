# Project State

Date: 2026-06-15

Version target: `0.2.1`

Implemented public APIs:

- `realtime_quotes`
- `full_realtime_quotes`
- `index_realtime`
- `minute_kline`
- `daily_kline`
- `kline`
- `diagnose`
- `probe-pytdx`

Source policy status:

- Realtime APIs allow source fallback in the documented order.
- K-line APIs are pytdx-only.
- K-line supported periods are documented in source policy and K-line guide.
- `probe-pytdx` writes a local active pytdx pool for diagnostics only.

Validation status:

- pytest passed locally for v0.2.1.
- ruff passed locally for v0.2.1.
- Release scan passed locally for v0.2.1.
- Offline smoke test passed locally for v0.2.1.
- Build passed locally for v0.2.1.
- The v0.2.1 task keeps public quote and K-line APIs unchanged.
- The active local pytdx pool is ignored by Git and excluded from release files.
- GitHub Release, PyPI publication, and post-release cold-start smoke are pending.
