# EASYQUOTATION_CHANNEL_REPORT

生成时间：2026-06-11T18:40:43.286142+00:00

## 1. 结论

easyquotation 已拆分为 `easyquotation_sina` 与 `easyquotation_tencent` 两个底层通道。二者若均通过，只表示同一 Python 库下的不同上游通道通过，不等价于完全独立库级双源。

| 通道 | realtime_quotes | index_realtime |
|---|---:|---:|
| easyquotation_sina | PASS | PASS |
| easyquotation_tencent | PASS | PASS |

## 2. 明细

| case | provider | feature | status | rows | columns | duration_ms | missing_fields | warnings | reason |
|---|---|---|---:|---:|---|---:|---|---|---|
| raw | sina | realtime_quotes | PASS | 2 | name, open, close, now, high, low, buy, sell, turnover, volume, bid1_volume, bid1, bid2_volume, bid2, bid3_volume, bid3, bid4_volume, bid4, bid5_volume, bid5, ask1_volume, ask1, ask2_volume, ask2, ask3_volume, ask3, ask4_volume, ask4, ask5_volume, ask5, date, time, code | 91.527 |  |  | raw_non_empty |
| router | sina | realtime_quotes | PASS | 2 | date, time, code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg, source, source_latency_ms, source_status, data_timestamp | 223.099 |  |  | router_quality_gate_pass |
| raw | sina | index_realtime | PASS | 2 | name, open, close, now, high, low, buy, sell, turnover, volume, bid1_volume, bid1, bid2_volume, bid2, bid3_volume, bid3, bid4_volume, bid4, bid5_volume, bid5, ask1_volume, ask1, ask2_volume, ask2, ask3_volume, ask3, ask4_volume, ask4, ask5_volume, ask5, date, time, code | 50.505 |  |  | raw_non_empty |
| router | sina | index_realtime | PASS | 2 | date, time, code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg, source, source_latency_ms, source_status, data_timestamp | 150.503 |  |  | router_quality_gate_pass |
| raw | tencent | realtime_quotes | PASS | 2 | name, code, now, close, open, volume, bid_volume, ask_volume, bid1, bid1_volume, bid2, bid2_volume, bid3, bid3_volume, bid4, bid4_volume, bid5, bid5_volume, ask1, ask1_volume, ask2, ask2_volume, ask3, ask3_volume, ask4, ask4_volume, ask5, ask5_volume, 最近逐笔成交, datetime, 涨跌, 涨跌(%), high, low, 价格/成交量(手)/成交额, 成交量(手), 成交额(万), turnover, PE, unknown, high_2, low_2, 振幅, 流通市值, 总市值, PB, 涨停价, 跌停价, 量比, 委差, 均价, 市盈(动), 市盈(静) | 98.679 |  |  | raw_non_empty |
| router | tencent | realtime_quotes | PASS | 2 | date, time, code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg, source, source_latency_ms, source_status, data_timestamp | 227.457 |  |  | router_quality_gate_pass |
| raw | tencent | index_realtime | PASS | 2 | name, code, now, close, open, volume, bid_volume, ask_volume, bid1, bid1_volume, bid2, bid2_volume, bid3, bid3_volume, bid4, bid4_volume, bid5, bid5_volume, ask1, ask1_volume, ask2, ask2_volume, ask3, ask3_volume, ask4, ask4_volume, ask5, ask5_volume, 最近逐笔成交, datetime, 涨跌, 涨跌(%), high, low, 价格/成交量(手)/成交额, 成交量(手), 成交额(万), turnover, PE, unknown, high_2, low_2, 振幅, 流通市值, 总市值, PB, 涨停价, 跌停价, 量比, 委差, 均价, 市盈(动), 市盈(静) | 97.214 |  |  | raw_non_empty |
| router | tencent | index_realtime | PASS | 2 | date, time, code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg, source, source_latency_ms, source_status, data_timestamp | 250.256 |  |  | router_quality_gate_pass |

## 3. 抽样

### raw sina realtime_quotes

```text
name    open   close    now    high     low     buy   sell  turnover       volume  bid1_volume    bid1  bid2_volume    bid2  bid3_volume    bid3  bid4_volume    bid4  bid5_volume    bid5  ask1_volume   ask1  ask2_volume    ask2  ask3_volume    ask3  ask4_volume    ask4  ask5_volume    ask5       date     time   code
平安银行   11.32   11.32   11.3   11.39   11.25   11.29   11.3 115622222 1.308134e+09       471400   11.29       609729   11.28       434000   11.27       533200   11.26       351000   11.25       133700   11.3       512900   11.31      1292200   11.32       897920   11.33       966001   11.34 2026-06-11 15:00:00 000001
贵州茅台 1272.12 1275.88 1279.0 1282.88 1266.91 1278.99 1279.0   2535198 3.230008e+09         1500 1278.99          400 1278.98          100 1278.97          100 1278.52          100 1278.29         5701 1279.0          100 1279.01          400 1279.02          300 1279.10          100 1279.18 2026-06-11 15:00:00 600519
```

### router sina realtime_quotes

```text
      date     time   code name  last_price  pre_close    open    high     low    volume       amount   pct_chg             source  source_latency_ms source_status                   data_timestamp
2026-06-11 15:00:00 000001 平安银行        11.3      11.32   11.32   11.39   11.25 115622222 1.308134e+09 -0.176678 easyquotation_sina            121.328            ok 2026-06-11T18:40:34.941318+00:00
2026-06-11 15:00:00 600519 贵州茅台      1279.0    1275.88 1272.12 1282.88 1266.91   2535198 3.230008e+09  0.244537 easyquotation_sina            121.328            ok 2026-06-11T18:40:34.941318+00:00
```

### raw sina index_realtime

```text
name       open      close        now       high        low  buy  sell    turnover       volume  bid1_volume  bid1  bid2_volume  bid2  bid3_volume  bid3  bid4_volume  bid4  bid5_volume  bid5  ask1_volume  ask1  ask2_volume  ask2  ask3_volume  ask3  ask4_volume  ask4  ask5_volume  ask5       date     time   code
上证指数  3979.7057  3993.2258  3987.0147  3997.4777  3958.4371  0.0   0.0   568545244 1.185555e+12            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0 2026-06-11 15:30:39 000001
深证成指 14889.5670 14954.1010 14851.9760 15062.7480 14706.0860  0.0   0.0 66981768618 1.366467e+12            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0 2026-06-11 15:00:03 399001
```

### router sina index_realtime

```text
      date     time   code name  last_price  pre_close       open       high        low      volume       amount   pct_chg             source  source_latency_ms source_status                   data_timestamp
2026-06-11 15:30:39 000001 上证指数   3987.0147  3993.2258  3979.7057  3997.4777  3958.4371   568545244 1.185555e+12 -0.155541 easyquotation_sina             67.758            ok 2026-06-11T18:40:37.239100+00:00
2026-06-11 15:00:03 399001 深证成指  14851.9760 14954.1010 14889.5670 15062.7480 14706.0860 66981768618 1.366467e+12 -0.682923 easyquotation_sina             67.758            ok 2026-06-11T18:40:37.239100+00:00
```

### raw tencent realtime_quotes

```text
name   code    now   close    open      volume  bid_volume  ask_volume    bid1  bid1_volume    bid2  bid2_volume    bid3  bid3_volume    bid4  bid4_volume    bid5  bid5_volume   ask1  ask1_volume    ask2  ask2_volume    ask3  ask3_volume    ask4  ask4_volume    ask5  ask5_volume 最近逐笔成交            datetime    涨跌  涨跌(%)    high     low            价格/成交量(手)/成交额    成交量(手)       成交额(万)  turnover    PE unknown  high_2   low_2   振幅     流通市值      总市值   PB     涨停价     跌停价   量比       委差      均价  市盈(动)  市盈(静)
平安银行 000001   11.3   11.32   11.32 115622200.0    58865800  56756400.0   11.29       471400   11.28       609700   11.27       434000   11.26       533200   11.25       351000   11.3       133700   11.31       512900   11.32      1292200   11.33       897900   11.34       966000        2026-06-11 16:14:09 -0.02  -0.18   11.39   11.25 11.30/1156222/1308133972 115622200 1308130000.0       0.6  5.09           11.39   11.25 1.24  2192.83  2192.87 0.47   12.45   10.19 1.02 -14034.0   11.31   3.77   5.14
贵州茅台 600519 1279.0 1275.88 1272.12   2535200.0     1307500   1227700.0 1278.99         1500 1278.98          400 1278.97          100 1278.52          100 1278.29          100 1279.0         5700 1279.01          100 1279.02          400 1279.10          300 1279.18          100        2026-06-11 16:14:07  3.12   0.24 1282.88 1266.91 1279.00/25352/3230008220   2535200 3230010000.0       0.2 19.33         1282.88 1266.91 1.25 15988.54 15988.54 5.97 1403.47 1148.29 0.78    -44.0 1274.07  14.67  19.42
```

### router tencent realtime_quotes

```text
      date     time   code name  last_price  pre_close    open    high     low      volume       amount  pct_chg                source  source_latency_ms source_status                   data_timestamp
2026-06-11 16:14:09 000001 平安银行        11.3      11.32   11.32   11.39   11.25 115622200.0 1308130000.0    -0.18 easyquotation_tencent            127.439            ok 2026-06-11T18:40:39.669436+00:00
2026-06-11 16:14:07 600519 贵州茅台      1279.0    1275.88 1272.12 1282.88 1266.91   2535200.0 3230010000.0     0.24 easyquotation_tencent            127.439            ok 2026-06-11T18:40:39.669436+00:00
```

### raw tencent index_realtime

```text
name   code      now    close     open       volume  bid_volume  ask_volume  bid1  bid1_volume  bid2  bid2_volume  bid3  bid3_volume  bid4  bid4_volume  bid5  bid5_volume  ask1  ask1_volume  ask2  ask2_volume  ask3  ask3_volume  ask4  ask4_volume  ask5  ask5_volume 最近逐笔成交            datetime      涨跌  涨跌(%)     high      low                    价格/成交量(手)/成交额      成交量(手)       成交额(万)  turnover    PE unknown   high_2    low_2   振幅      流通市值       总市值  PB  涨停价  跌停价   量比  委差       均价 市盈(动) 市盈(静)
上证指数 000001  3987.01  3993.23  3979.71 5.685452e+10           0         0.0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0        2026-06-11 16:14:16   -6.22  -0.16  3997.48  3958.44  3987.01/568545244/1185554610734 56854524400 1.185555e+12      1.18 17.64          3997.48  3958.44 0.98 616427.60 664964.51 0.0 -1.0 -1.0 0.91 0.0  3978.73  None  None
深证成指 399001 14851.98 14954.10 14889.57 6.698177e+10           0         0.0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0   0.0            0        2026-06-11 16:14:09 -102.12  -0.68 15062.75 14706.09 14851.98/669817686/1366466938778 66981768600 1.366467e+12      2.75 49.19         15062.75 14706.09 2.39 397083.96 463633.22 0.0 -1.0 -1.0 0.89 0.0 14869.38  None  None
```

### router tencent index_realtime

```text
      date     time   code name  last_price  pre_close     open     high      low       volume       amount  pct_chg                source  source_latency_ms source_status                   data_timestamp
2026-06-11 16:14:16 000001 上证指数     3987.01    3993.23  3979.71  3997.48  3958.44 5.685452e+10 1.185555e+12    -0.16 easyquotation_tencent            133.939            ok 2026-06-11T18:40:42.120578+00:00
2026-06-11 16:14:09 399001 深证成指    14851.98   14954.10 14889.57 15062.75 14706.09 6.698177e+10 1.366467e+12    -0.68 easyquotation_tencent            133.939            ok 2026-06-11T18:40:42.120578+00:00
```

## 4. 验收

- `logs/easyquotation_channel_report.json` 已使用 `ensure_ascii=False` 写入。
- 本脚本未接入 S0，未输出交易建议。
