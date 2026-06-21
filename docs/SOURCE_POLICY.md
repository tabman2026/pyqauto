# Source Policy

Source policy defines which adapter family may serve each public API and in what
order.

## Default Policy

The default policy is bundled as package data and is used by the simple
`pyqauto` functions and by `QuoteRouter.from_config()` when no custom
`source_policy_path` is provided.

```yaml
apis:
  realtime_quotes:
    allow_fallback: true
    fallback_order:
      - pytdx
      - akshare_em_spot
      - easyquotation_sina
      - easyquotation_tencent

  full_realtime_quotes:
    allow_fallback: true
    fallback_order:
      - pytdx
      - akshare_em_spot
      - easyquotation_sina
      - easyquotation_tencent

  index_realtime:
    allow_fallback: true
    fallback_order:
      - pytdx
      - easyquotation_sina
      - easyquotation_tencent

  minute_kline:
    allow_fallback: false
    fallback_order:
      - pytdx
    supported_periods:
      - 1m
      - 5m
      - 15m
      - 30m
      - 60m

  daily_kline:
    allow_fallback: false
    fallback_order:
      - pytdx
    supported_periods:
      - 1d

  kline:
    allow_fallback: false
    fallback_order:
      - pytdx
    supported_periods:
      - 1m
      - 5m
      - 15m
      - 30m
      - 60m
      - 1d
```

## pytdx Server Order

pytdx server entries are expanded by role:

1. `primary`
2. `hot_backup`
3. `backup`

Servers in the same role are sorted by `latency_ms` ascending.

## K-line Rule

`minute_kline`, `daily_kline`, and `kline` must remain pytdx-only. If all pytdx
servers fail, pyqauto raises `NoAvailableSourceError` and writes an audit
record with attempts and `fallback_chain`.

## Adapter Schema Rule

Adapters must not expose raw upstream field names to the router as the public
contract. Each source adapter implements `fetch_raw()`, `inspect_raw_schema()`,
`normalize_to_standard()`, and `validate_standard_output()`. Realtime quote
adapters normalize to the standard schema recorded by `diagnose` under
`source_schema_probe`.

The live schema probe is explicit-only and is run from the repository root:

```bash
pyqauto source-schema-probe-live --json
```

It writes `reports/latest/source_schema_probe_live.json` and
`logs/source_schema_probe_live.jsonl`. Core field drift or missing mapped raw
fields must produce `adapter_status=schema_drift` or `field_missing`, with
`validate_result.diagnose` recording the drift fields and rejection reason.
Invalid standard rows must not be exposed as public records. Optional ETF or
Beijing Stock Exchange samples that a provider does not support are recorded as
`unsupported`, not as provider failures.

`WARN` is allowed when at least one source passes and another source is
unavailable or rejected. `FAIL` means no source passed and the CLI exits with a
non-zero status.
