from __future__ import annotations

import pytest

from astock_source_router.adapters.adata_adapter import ADataAdapter
from astock_source_router.core.errors import UnsupportedFeatureError
from astock_source_router.core.features import (
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)


def test_adata_realtime_is_lite_only_boundary():
    adapter = ADataAdapter()

    assert LITE_REALTIME_QUOTES in adapter.supported_features
    assert FULL_REALTIME_QUOTES not in adapter.supported_features
    assert REALTIME_QUOTES not in adapter.supported_features

    with pytest.raises(UnsupportedFeatureError, match="lite-only"):
        adapter.fetch_full_realtime_quotes(["000001"])
