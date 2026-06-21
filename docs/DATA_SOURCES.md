# Data Sources

This project does not produce market data. It only calls upstream public Python
libraries through adapters and records which source returned each response.

## Current Adapters

| Source | Dependency | Used by | Default role |
|---|---|---|---|
| `pytdx` | `pytdx` | realtime APIs and all K-line APIs | primary source |
| `akshare_em_spot` | `akshare` | realtime API fallback via `stock_zh_a_spot_em` | backup source |
| `easyquotation_sina` | `easyquotation` | realtime API fallback | backup source |
| `easyquotation_tencent` | `easyquotation` | realtime API fallback | backup source |

## Fallback Rules

The default source policy and example pytdx server pool are bundled with the
package, so users can call `import pyqauto as aq` and use `aq.quote(...)` without
copying config files into their own project.

```text
realtime_quotes: pytdx -> akshare_em_spot -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes: pytdx -> akshare_em_spot -> easyquotation_sina -> easyquotation_tencent
index_realtime: pytdx -> easyquotation_sina -> easyquotation_tencent
minute_kline: pytdx only
daily_kline: pytdx only
kline: pytdx only
```

K-line APIs never use easyquotation fallback. If all configured pytdx servers
fail, the router raises a structured error and writes audit attempts plus
`fallback_chain`.

Free pytdx server availability changes by network, region, and time. Use
`pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json`
to generate an observed active local pool when pytdx calls time out. The active
local file is a diagnostic result for the current environment and should not be
committed.

Realtime quote failures may fall back to `akshare_em_spot`,
`easyquotation_sina`, or `easyquotation_tencent` according to source policy.
K-line failures do not use easyquotation fallback.

## Source Schema Live Probe

Run the explicit live schema probe when validating upstream field shape:

```bash
pyqauto source-schema-probe-live --json
```

The report detects schema drift, missing core fields, provider errors, and unit
normalization issues. `WARN` means at least one source passed while another
source failed or was rejected. `FAIL` means no source passed.

Rows rejected by the schema guard are not exposed as public records. Their
reasons are recorded in `rejected_reason`, `schema_drift_fields`, and
`error_message`.

## Source Field Values

- `source="pytdx"` for pytdx realtime and K-line records.
- `source="akshare_em_spot"` for AkShare Eastmoney spot fallback realtime
  records.
- `source="easyquotation_sina"` for Sina fallback realtime records.
- `source="easyquotation_tencent"` for Tencent fallback realtime records.
- `source_level` is `primary`, `hot_backup`, or `backup` for pytdx server
  roles. It is usually empty for easyquotation adapters.

## Guarantees and Limits

- No guarantee is made for accuracy, freshness, completeness, or availability.
- This project does not claim official exchange-authorized data.
- Upstream licenses and service terms belong to each upstream project.
- No fabricated quote or K-line records are returned.
- All source adapters keep raw provider fields behind the adapter boundary and
  expose a standard schema validation step before public records are returned.
- AkShare `成交量` is converted from lots to shares, while AkShare `成交额` stays
  in RMB yuan.
- Tencent `价格/成交量(手)/成交额` is parsed as price, volume in lots, and amount
  in RMB yuan.
- The package is read-only, does not provide investment advice, and does not
  connect to order execution.

See [UPSTREAM_LICENSE_AND_RISK.md](UPSTREAM_LICENSE_AND_RISK.md).
