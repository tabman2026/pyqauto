# PYTDX SERVER POOL EXPANSION REPORT

## 结论

- 生成时间：`2026-06-12T09:44:27.947438+00:00`
- live refresh 启用：`True`
- 候选服务器数量：`103`
- PASS 服务器数量：`34`
- server_pool_status：`server_pool_ready`
- single_server_warning：`False`
- server_pool_ready：`True`
- primary server：`{'ip': '58.63.254.191', 'port': 7709, 'source': 'pytdx_hq_hosts', 'grade': 'primary', 'latency_ms': 124.418, 'tested_at': '2026-06-12T09:44:18.073462+00:00'}`
- hot backup server：`{'ip': '183.60.224.177', 'port': 7709, 'source': 'pytdx_hq_hosts', 'grade': 'hot_backup', 'latency_ms': 146.867, 'tested_at': '2026-06-12T09:43:39.450957+00:00'}`

## 候选来源

| 来源 | 状态 | 数量/原因 |
| --- | --- | --- |
| verified_current | PASS | 1 |
| pytdx_hq_hosts | PASS | 104 |
| config/pytdx_servers_extra.json | PASS | 2 |

## 服务器明细

| grade | ip | port | source | connect | quote | index_quote | latency_ms | row_count | error |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| primary | 58.63.254.191 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 124.418 | 2 |  |
| hot_backup | 183.60.224.177 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 146.867 | 2 |  |
| backup | 119.29.19.242 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 146.956 | 2 |  |
| backup | 183.60.224.178 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 149.164 | 2 |  |
| backup | 58.63.254.217 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 149.189 | 2 |  |
| backup | 59.36.5.11 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 175.152 | 2 |  |
| backup | 202.96.138.90 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 181.781 | 2 |  |
| backup | 175.6.5.153 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 205.839 | 2 |  |
| backup | 115.238.56.198 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 224.617 | 2 |  |
| backup | 220.178.55.86 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 247.847 | 2 |  |
| backup | 180.153.18.172 | 80 | pytdx_hq_hosts | PASS | PASS | PASS | 269.244 | 2 |  |
| backup | 218.75.126.9 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 270.886 | 2 |  |
| backup | 115.238.90.165 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 274.502 | 2 |  |
| backup | 60.191.117.167 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 282.271 | 2 |  |
| backup | 180.153.18.170 | 7709 | verified_current+pytdx_hq_hosts | PASS | PASS | PASS | 286.299 | 2 |  |
| backup | 117.34.114.27 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 292.934 | 2 |  |
| backup | 117.34.114.15 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 293.813 | 2 |  |
| backup | 117.34.114.14 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 294.658 | 2 |  |
| backup | 117.34.114.17 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 295.908 | 2 |  |
| backup | 60.12.136.250 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 296.191 | 2 |  |
| backup | 117.34.114.13 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 296.237 | 2 |  |
| backup | 218.106.92.182 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 296.924 | 2 |  |
| backup | 182.131.3.245 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 297.039 | 2 |  |
| backup | 218.106.92.183 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 297.947 | 2 |  |
| backup | 117.34.114.16 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 298.785 | 2 |  |
| backup | 117.34.114.18 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 300.186 | 2 |  |
| backup | 220.178.55.71 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 301.54 | 2 |  |
| backup | 117.34.114.20 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 306.142 | 2 |  |
| backup | 218.6.170.47 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 309.631 | 2 |  |
| backup | 202.108.253.139 | 80 | pytdx_hq_hosts | PASS | PASS | PASS | 317.28 | 2 |  |
| backup | 182.118.47.151 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 430.274 | 2 |  |
| backup | 123.125.108.90 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 430.587 | 2 |  |
| backup | 202.100.166.27 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 535.2 | 2 |  |
| backup | 123.125.108.14 | 7709 | pytdx_hq_hosts | PASS | PASS | PASS | 735.058 | 2 |  |
| disabled | 218.85.139.19 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1802.272 | 0 | TimeoutError: timed out |
| disabled | 218.85.139.20 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1832.111 | 0 | TimeoutError: timed out |
| disabled | 58.23.131.163 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1809.199 | 0 | TimeoutError: timed out |
| disabled | 180.153.18.171 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1803.215 | 0 | TimeoutError: timed out |
| disabled | 202.108.253.130 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1823.147 | 0 | TimeoutError: timed out |
| disabled | 202.108.253.131 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1799.279 | 0 | TimeoutError: timed out |
| disabled | 124.160.88.183 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1820.434 | 0 | TimeoutError: timed out |
| disabled | 218.108.98.244 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1813.727 | 0 | TimeoutError: timed out |
| disabled | 218.108.47.69 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1802.516 | 0 | TimeoutError: timed out |
| disabled | 223.94.89.115 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1821.692 | 0 | TimeoutError: timed out |
| disabled | 218.57.11.101 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1844.049 | 0 | TimeoutError: timed out |
| disabled | 58.58.33.123 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1799.703 | 0 | TimeoutError: timed out |
| disabled | 14.17.75.71 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1836.277 | 0 | TimeoutError: timed out |
| disabled | 114.80.63.12 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1800.224 | 0 | TimeoutError: timed out |
| disabled | 114.80.63.35 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1838.723 | 0 | TimeoutError: timed out |
| disabled | 180.153.39.51 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1815.331 | 0 | TimeoutError: timed out |
| disabled | 119.147.212.81 | 7709 | pytdx_hq_hosts+manual_seed | FAIL | SKIP | SKIP | 1849.974 | 0 | TimeoutError: timed out |
| disabled | 221.231.141.60 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1814.957 | 0 | TimeoutError: timed out |
| disabled | 101.227.73.20 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1801.866 | 0 | TimeoutError: timed out |
| disabled | 101.227.77.254 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1850.677 | 0 | TimeoutError: timed out |
| disabled | 14.215.128.18 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1846.178 | 0 | TimeoutError: timed out |
| disabled | 59.173.18.140 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1813.525 | 0 | TimeoutError: timed out |
| disabled | 60.28.23.80 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1833.215 | 0 | TimeoutError: timed out |
| disabled | 218.60.29.136 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1803.176 | 0 | TimeoutError: timed out |
| disabled | 122.192.35.44 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1820.489 | 0 | TimeoutError: timed out |
| disabled | 112.95.140.74 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1833.809 | 0 | TimeoutError: timed out |
| disabled | 112.95.140.92 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1810.455 | 0 | TimeoutError: timed out |
| disabled | 112.95.140.93 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1831.727 | 0 | TimeoutError: timed out |
| disabled | 114.80.149.19 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 44.934 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 114.80.149.21 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 49.01 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 114.80.149.22 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 51.268 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 114.80.149.91 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 48.536 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 114.80.149.92 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 461.562 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 121.14.104.60 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1829.543 | 0 | TimeoutError: timed out |
| disabled | 121.14.104.66 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1815.492 | 0 | TimeoutError: timed out |
| disabled | 123.126.133.13 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1827.972 | 0 | TimeoutError: timed out |
| disabled | 123.126.133.14 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1833.523 | 0 | TimeoutError: timed out |
| disabled | 123.126.133.21 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1800.153 | 0 | TimeoutError: timed out |
| disabled | 211.139.150.61 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1810.361 | 0 | TimeoutError: timed out |
| disabled | 123.138.29.107 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1827.317 | 0 | TimeoutError: timed out |
| disabled | 123.138.29.108 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1847.167 | 0 | TimeoutError: timed out |
| disabled | 124.232.142.29 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 52.344 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 183.57.72.11 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1815.609 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.12 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1813.292 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.13 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1815.253 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.15 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1812.148 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.21 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1844.29 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.22 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1816.707 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.23 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1811.961 | 0 | TimeoutError: timed out |
| disabled | 183.57.72.24 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1800.825 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.100 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1835.514 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.101 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1816.766 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.102 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1834.517 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.103 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1816.57 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.104 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1804.772 | 0 | TimeoutError: timed out |
| disabled | 113.105.92.99 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1826.851 | 0 | TimeoutError: timed out |
| disabled | 117.34.114.30 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 58.589 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 117.34.114.31 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 43.205 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 182.131.3.252 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 53.003 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 183.60.224.11 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1821.526 | 0 | TimeoutError: timed out |
| disabled | 58.210.106.91 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1825.493 | 0 | TimeoutError: timed out |
| disabled | 58.63.254.216 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 16.209 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 58.63.254.219 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 25.711 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 58.63.254.247 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 29.217 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| disabled | 222.161.249.156 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1850.66 | 0 | TimeoutError: timed out |
| disabled | 42.123.69.62 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1817.592 | 0 | TimeoutError: timed out |
| disabled | 120.55.172.97 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1835.455 | 0 | TimeoutError: timed out |
| disabled | 139.217.20.27 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 1819.896 | 0 | TimeoutError: timed out |
| disabled | 202.100.166.21 | 7709 | pytdx_hq_hosts | FAIL | SKIP | SKIP | 86.962 | 0 | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |

## 审计结论

- 所有可用服务器均来自 live probe，未测试服务器不会标记为可用。
- `config/pytdx_servers_active.json` 仅写入本地排序结果；source policy 未改变。
- easyquotation fallback 保留；0 个 PASS 时 pytdx fail-fast，由路由 fallback。
- 未接入 S0、QMT、券商账户或自动交易。
- 未输出候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。
