from astock_source_router import MarketRouter

router = MarketRouter(auto_register=True)
print("registered sources:", router.registered_sources())

try:
    df = router.get_daily_kline("600519", start_date="20250101", end_date="20250611")
    print(df)
except Exception as exc:
    print("获取日K失败：", exc)

print(router.health_report())
