from astock_source_router import MarketRouter

router = MarketRouter(auto_register=True)
print("registered sources:", router.registered_sources())

try:
    df = router.get_realtime_quotes(["000001", "600519"])
    print(df)
except Exception as exc:
    print("获取实时行情失败：", exc)

print(router.health_report())
