# Third Party Notices

本项目通过 optional dependencies 调用第三方开源库的公开 API。用户需要自行确认第三方项目的最新协议、使用边界和源站规则。

可能适配的第三方项目：

- AKShare
- Baostock
- easyquotation
- adata
- efinance
- Ashare
- mootdx
- pytdx

本项目不复制上述项目核心代码，不内置第三方项目数据，不提供第三方数据再分发服务。

说明：

1. 第三方数据源的可用性、准确性、完整性、延迟、权限和使用限制，以第三方项目及源站规则为准。
2. AKShare、Baostock、easyquotation、adata 等源需要用户按需安装 optional dependencies。
3. efinance、mootdx、Ashare、pytdx 等存在学习交流、维护状态或协议边界不确定性，只能作为 optional adapter，不作为默认强依赖。
4. 本项目不内置 cookie、token、账号、券商登录态、QMT 或客户端登录态。
5. 免费公开源可能变动，生产环境必须先运行 `scripts/smoke_test_offline.py` 和显式启用的 `scripts/smoke_test_live.py`。
