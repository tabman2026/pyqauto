from __future__ import annotations

from astock_source_router.core.adapter_base import BaseMarketDataAdapter


class SourceRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseMarketDataAdapter] = {}

    def register(self, adapter: BaseMarketDataAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseMarketDataAdapter | None:
        return self._adapters.get(name)

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def supports(self, source: str, feature: str) -> bool:
        adapter = self.get(source)
        return bool(adapter and feature in adapter.supported_features)
