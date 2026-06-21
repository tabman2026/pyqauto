# CLI Reference

Global options:

```bash
pyqauto --audit-jsonl logs/pyqauto_audit.jsonl \
  --audit-sqlite logs/pyqauto_audit.sqlite3 \
  COMMAND
```

The package includes default source policy and pytdx server config. Use
`--config` and `--pytdx-servers` only to override them.

Python users normally do not need these options:

```python
import pyqauto as aq

print(aq.quote("000001").to_dict())
```

`--json` can be passed globally before the command or on supported commands
after command arguments.

## Commands

```bash
pyqauto realtime 000001 600000
pyqauto full 000001 600000
pyqauto full-realtime 000001 600000
pyqauto index 000001 399001
pyqauto minute 000001 --period 15m --count 120
pyqauto daily 000001 --count 120
pyqauto kline 000001 --period 15m --count 120
pyqauto kline 000001 --period 1d --count 120
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
pyqauto source-schema-probe-live --json
pyqauto source-schema-probe-live --symbols 000001 600000 --json
pyqauto diagnose --json
```

All commands support `--help`. Quote, K-line, and probe commands support
`--json`. JSON output includes `source`, `source_level`, and `trace_id` for
quote and K-line rows.

Failures return a non-zero exit code and include the project error code, for
example `[UNSUPPORTED_PERIOD]`.

## Source Schema Live Probe

```bash
pyqauto source-schema-probe-live --json
pyqauto source-schema-probe-live --symbols 000001 600000 --json
pyqauto source-schema-probe-live --output reports/latest/source_schema_probe_live.json
pyqauto source-schema-probe-live --jsonl logs/source_schema_probe_live.jsonl
```

The live probe connects to upstream providers and verifies that raw payloads can
still be normalized into the standard public quote schema. `--json` prints the
full report contract. Without `--json`, the CLI prints a short summary.

`WARN` means at least one source passed while another source failed or was
rejected by schema validation; the command exits successfully. `FAIL` means no
source passed and the command exits with a non-zero status.

Invalid rows are not exposed as public records. Rejection reasons are recorded
in `rejected_reason` and provider exceptions in `error_message`.

## pytdx Probe

```bash
pyqauto probe-pytdx \
  --output config/pytdx_servers.active.local.json \
  --timeout 3 \
  --limit 0 \
  --json
```

The probe checks connect, realtime, minute K-line, and daily K-line availability
for pytdx servers and writes an active local pool sorted by K-line availability,
connect success, and latency. `--limit 0` means no server-count limit.

The output file defaults to `config/pytdx_servers.active.local.json`. It is a
local diagnostic result and should not be committed.

## K-line Active Pool

K-line APIs are pytdx-only and do not use easyquotation fallback. If pytdx K-line
calls time out, refresh the local pool and pass it to the K-line command:

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
pyqauto kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

Free pytdx server availability changes by network, region, and time. A
successful probe is not a guarantee for all environments or future runs.
