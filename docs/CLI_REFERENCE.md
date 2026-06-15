# CLI Reference

Global options:

```bash
aquote-router --config config/source_policy.example.yaml \
  --pytdx-servers config/pytdx_servers.example.json \
  --audit-jsonl logs/aquote_router_audit.jsonl \
  --audit-sqlite logs/aquote_router_audit.sqlite3 \
  COMMAND
```

`--json` can be passed globally before the command or on supported commands
after command arguments.

## Commands

```bash
aquote-router realtime 000001 600000
aquote-router full 000001 600000
aquote-router full-realtime 000001 600000
aquote-router index 000001 399001
aquote-router minute 000001 --period 15m --count 120
aquote-router daily 000001 --count 120
aquote-router kline 000001 --period 15m --count 120
aquote-router kline 000001 --period 1d --count 120
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
aquote-router diagnose --json
```

All commands support `--help`. Quote, K-line, and probe commands support
`--json`. JSON output includes `source`, `source_level`, and `trace_id` for
quote and K-line rows.

Failures return a non-zero exit code and include the project error code, for
example `[UNSUPPORTED_PERIOD]`.

## pytdx Probe

```bash
aquote-router probe-pytdx \
  --config config/pytdx_servers.example.json \
  --output config/pytdx_servers.active.local.json \
  --timeout 3 \
  --limit 0 \
  --json
```

The probe checks connect, realtime, minute K-line, and daily K-line availability
for pytdx servers and writes an active local pool sorted by K-line availability,
connect success, and latency. `--limit 0` means no candidate limit.

The output file defaults to `config/pytdx_servers.active.local.json`. It is a
local diagnostic result and should not be committed.

## K-line Active Pool

K-line APIs are pytdx-only and do not use easyquotation fallback. If pytdx K-line
calls time out, refresh the local pool and pass it to the K-line command:

```bash
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
aquote-router kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

Free pytdx server availability changes by network, region, and time. A
successful probe is not a guarantee for all environments or future runs.
