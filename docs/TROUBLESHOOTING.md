# Troubleshooting

Start with local diagnostics:

```bash
pyqauto diagnose --json
```

The command does not connect to upstream providers. It checks local config shape
and returns fields such as:

- `pyqauto_version`
- `source_policy_parseable`
- `source_policy_error_code`
- `pytdx_server_config_parseable`
- `enabled_sources`
- `supported_apis`
- `supported_kline_periods`
- `source_schema_probe.latest_live_probe`
- `recent_trace_id`

## Common Checks

- Run `pyqauto diagnose --json` to confirm bundled or overridden config parses.
- If you pass custom config paths, confirm the source policy parses and pytdx
  config contains enabled servers.
- Use `--json` on quote commands when table output is too narrow.
- Use audit `trace_id` to match CLI output to JSONL or SQLite records.
- For K-line failures, inspect pytdx attempts. K-line APIs do not use
  easyquotation fallback.

## K-line Timeouts

K-line APIs are pytdx-only. Realtime APIs can fall back to
`easyquotation_sina` or `easyquotation_tencent`, but K-line failures do not use
easyquotation fallback.

If K-line calls time out, refresh a local active pytdx pool:

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass that pool explicitly:

```bash
pyqauto kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

`config/pytdx_servers.active.local.json` is a local diagnostic result and
should not be committed. Free pytdx server availability changes by network,
region, and time, so a successful probe is not a guarantee for all
environments or future runs.

## Offline and Live Checks

Default tests are offline:

```bash
python -X utf8 -m pytest
```

Live smoke tests must be explicitly enabled:

```bash
set ENABLE_LIVE_SMOKE_TEST=1
python -X utf8 scripts/smoke_test.py
```

## Source Schema Live Probe

Run live source schema validation explicitly:

```bash
pyqauto source-schema-probe-live --json
```

`PASS` means every probed source passed schema validation. `WARN` means at least
one source passed and at least one source failed or was rejected; this is useful
for diagnosing partial upstream availability. `FAIL` means no source passed and
the CLI exits with a non-zero status.

If AkShare is closed by the remote side, read `error_message` as an upstream or
network availability event. If pytdx times out, refresh the active local pool
with `pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json`
and retry from the same network.

Only schema-validated rows become public records. Rows with missing core fields
or schema drift are rejected and recorded in `rejected_reason` and
`schema_drift_fields`.
