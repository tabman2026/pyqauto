# Source Schema Live Probe

`source-schema-probe-live` verifies that upstream source payloads can still be
normalized into pyqauto's standard public quote schema. It is explicit-only
because it connects to upstream providers.

```bash
pyqauto source-schema-probe-live --json
pyqauto source-schema-probe-live --symbols 000001 600000 --json
pyqauto source-schema-probe-live --output reports/latest/source_schema_probe_live.json
pyqauto source-schema-probe-live --jsonl logs/source_schema_probe_live.jsonl
```

The command writes UTF-8 JSON to
`reports/latest/source_schema_probe_live.json` and UTF-8 JSONL to
`logs/source_schema_probe_live.jsonl`. These are local live outputs and should
not be committed.

## Why It Exists

Public upstream payloads can change field names, units, nesting, or required
values without notice. The live probe detects this schema drift before
unvalidated rows can become public records.

Each adapter report includes:

- `source_status`
- `schema_status`
- `missing_fields`
- `schema_drift_fields`
- `rejected_reason`
- `error_message`
- `accepted_record_count`
- `rejected_record_count`

## Status Meaning

- `PASS`: every probed source normalized required sample symbols and passed the
  standard schema guard.
- `WARN`: at least one source passed, while one or more sources were unavailable
  or rejected by schema validation. This does not make the command fail.
- `FAIL`: no source passed. The CLI exits with a non-zero status.
- Provider errors are stored in `error_message`. If every provider errors or is
  rejected, the top-level status becomes `FAIL`.

## Public Record Guard

Only rows that pass the standard schema guard are counted as public records.
Rows with missing core fields, schema drift, or provider errors are not exposed
in `standard_sample`; their reasons are recorded in `rejected_reason` and
`error_message`.

## Source Notes

- `easyquotation_sina` passing means the Sina payload for required sample
  symbols was fetched, normalized, and schema-validated.
- `easyquotation_tencent` passing means the Tencent payload was fetched,
  normalized, and schema-validated, including its composite
  `价格/成交量(手)/成交额` field.
- AkShare connection resets or remote closes are upstream/network availability
  events. They should be read from `error_message`, not treated as a standard
  field mapping success.
- pytdx timeouts are server availability events. Refresh a local active pool
  with `pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json`
  and retry from the same network.

## Unit Rules

- AkShare `stock_zh_a_spot_em` raw `成交量` is in lots and becomes
  `volume_shares = 成交量 * 100`.
- AkShare `stock_zh_a_spot_em` raw `成交额` is already RMB yuan and is not divided
  by `100`.
- Tencent composite `价格/成交量(手)/成交额` is parsed as price, volume in lots, and
  amount in RMB yuan. The second part is multiplied by `100`; the third part is
  kept as yuan.

## Boundary

The live probe is a read-only data-quality check. pyqauto does not provide
investment advice and does not connect to order execution.
