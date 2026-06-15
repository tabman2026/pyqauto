# Data Sources

This project does not produce market data. It only calls upstream public Python
libraries through adapters and records which source returned each response.

## Current Adapters

| Source | Dependency | Used by | Default role |
|---|---|---|---|
| `pytdx` | `pytdx` | realtime APIs and all K-line APIs | primary source |
| `easyquotation_sina` | `easyquotation` | realtime API fallback | backup source |
| `easyquotation_tencent` | `easyquotation` | realtime API fallback | backup source |

## Fallback Rules

```text
realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
index_realtime: pytdx -> easyquotation_sina -> easyquotation_tencent
minute_kline: pytdx only
daily_kline: pytdx only
kline: pytdx only
```

K-line APIs never use easyquotation fallback. If all configured pytdx servers
fail, the router raises a structured error and writes audit attempts plus
`fallback_chain`.

Free pytdx server availability changes by network, region, and time. Use
`aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json`
to generate an observed active local pool when pytdx calls time out. The active
local file is a diagnostic result for the current environment and should not be
committed.

Realtime failures may fall back to `easyquotation_sina` or
`easyquotation_tencent` according to source policy.
K-line failures do not use easyquotation fallback.

## Source Field Values

- `source="pytdx"` for pytdx realtime and K-line records.
- `source="easyquotation_sina"` for Sina fallback realtime records.
- `source="easyquotation_tencent"` for Tencent fallback realtime records.
- `source_level` is `primary`, `hot_backup`, or `backup` for pytdx server
  roles. It is usually empty for easyquotation adapters.

## Guarantees and Limits

- No guarantee is made for accuracy, freshness, completeness, or availability.
- This project does not claim official exchange-authorized data.
- Upstream licenses and service terms belong to each upstream project.
- No fabricated quote or K-line records are returned.

See [UPSTREAM_LICENSE_AND_RISK.md](UPSTREAM_LICENSE_AND_RISK.md).
