# PYTDX Server Pool Report

## 结论

- 生成时间：`2026-06-12T07:03:09.351914+00:00`
- live 启用：`True`
- pytdx 安装：`True`
- 可用服务器数量：`1`
- server_pool_status：`primary_with_single_server_warning`
- pytdx 是否允许作为实时主源候选：`True`

## 服务器明细

| ip | port | connect_status | latency_ms | quote_status | error_summary |
| --- | ---: | --- | ---: | --- | --- |
| 180.153.18.170 | 7709 | PASS | 247.528 | PASS |  |
| 101.227.73.20 | 7709 | FAIL | 5019.026 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| 101.227.77.254 | 7709 | FAIL | 5027.5 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| 14.215.128.18 | 7709 | FAIL | 5020.804 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| 202.108.253.130 | 7709 | FAIL | 5006.08 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| 218.85.139.19 | 7709 | FAIL | 5022.792 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |
| 119.147.212.81 | 7709 | FAIL | 5025.229 | SKIP | ResponseHeaderRecvFails: head_buf is not 0x10 : b'' |

## 审计结论

- 本脚本只连接公开 TDX 行情服务器并读取测试代码行情，不接入券商账户、QMT 或 S0。
- 未内置 cookie、token、账号或券商登录态。
- 不输出交易建议、仓位建议、收益率承诺或自动交易逻辑。
- JSON 报告使用 UTF-8 和 `ensure_ascii=False` 写入。
