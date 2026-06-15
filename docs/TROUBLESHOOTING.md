# Troubleshooting

Start with local diagnostics:

```bash
aquote-router diagnose --json
```

The command does not connect to upstream providers. It checks local config shape
and returns fields such as:

- `aquote_router_version`
- `source_policy_parseable`
- `source_policy_error_code`
- `pytdx_server_config_parseable`
- `enabled_sources`
- `supported_apis`
- `supported_kline_periods`
- `recent_trace_id`

## Common Checks

- Confirm `config/source_policy.example.yaml` parses.
- Confirm `config/pytdx_servers.example.json` contains enabled servers.
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
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass that pool explicitly:

```bash
aquote-router kline 000001 --period 15m --count 10 \
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
