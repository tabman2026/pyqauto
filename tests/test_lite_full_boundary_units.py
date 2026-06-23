from __future__ import annotations

from astock_source_router.adapters.adata_adapter import ADataAdapter
from astock_source_router.core.errors import UnsupportedFeatureError
from astock_source_router.core.features import (
    FULL_REALTIME_QUOTES,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)
from astock_source_router.core.policy import DEFAULT_SOURCE_POLICY
from astock_source_router.core.unit_policy import source_feature_policy


def test_adata_lite_unit_policy_does_not_create_full_capability():
    adapter = ADataAdapter()

    assert LITE_REALTIME_QUOTES in adapter.supported_features
    assert FULL_REALTIME_QUOTES not in adapter.supported_features
    assert REALTIME_QUOTES not in adapter.supported_features
    assert DEFAULT_SOURCE_POLICY[LITE_REALTIME_QUOTES] == ["adata"]
    assert "adata" not in DEFAULT_SOURCE_POLICY[FULL_REALTIME_QUOTES]
    assert "adata" not in DEFAULT_SOURCE_POLICY[REALTIME_QUOTES]

    try:
        adapter.fetch_full_realtime_quotes(["000001"])
    except UnsupportedFeatureError:
        pass
    else:  # pragma: no cover
        raise AssertionError("adata full realtime call must be rejected")


def test_adata_source_unit_policy_is_lite_only_low_confidence():
    lite_policy = source_feature_policy("adata", LITE_REALTIME_QUOTES)
    full_policy = source_feature_policy("adata", FULL_REALTIME_QUOTES)

    assert lite_policy["confidence"] == "low"
    assert lite_policy["volume_unit"] == "share_or_lot_to_confirm"
    assert full_policy == {}
