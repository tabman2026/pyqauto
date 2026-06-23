from astock_source_router import MarketRouter

router = MarketRouter(auto_register=True)
print(router.health_report())
