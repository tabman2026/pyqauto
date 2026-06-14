# Source Policy

Source policy defines which provider family may serve each public API and in what order.

The default policy:

```yaml
apis:
  realtime_quotes:
    allow_fallback: true
    fallback_order:
      - pytdx
      - easyquotation_sina
      - easyquotation_tencent

  minute_kline:
    allow_fallback: false
    fallback_order:
      - pytdx
```

pytdx server entries are expanded internally by role:

1. `primary`
2. `hot_backup`
3. `backup`

Servers in the same role are sorted by `latency_ms` ascending.

`minute_kline` must remain pytdx-only. If all pytdx servers fail, aquote-router raises `NoAvailableSourceError` and writes an audit record.
