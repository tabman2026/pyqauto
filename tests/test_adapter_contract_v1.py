from __future__ import annotations

from astock_source_router.adapters.fake_adapter import FakeAdapter
from astock_source_router.core.features import REALTIME_QUOTES


def test_adapter_contract_v1_methods_exist() -> None:
    adapter = FakeAdapter()
    for method_name in (
        "fetch_raw",
        "inspect_raw_schema",
        "normalize_to_standard",
        "validate_standard_output",
    ):
        assert callable(getattr(adapter, method_name))


def test_adapter_contract_v1_normalizes_source_units_and_trace_id() -> None:
    adapter = FakeAdapter()
    raw = adapter.fetch_raw(REALTIME_QUOTES, codes=["000001"])

    schema = adapter.inspect_raw_schema(raw, feature=REALTIME_QUOTES)
    assert schema["source"] == "fake"
    assert schema["feature"] == REALTIME_QUOTES
    assert "code" in schema["columns"]

    normalized = adapter.normalize_to_standard(
        REALTIME_QUOTES,
        raw,
        latency_ms=1.25,
        trace_id="trace-v1",
    )
    assert normalized.loc[0, "source"] == "fake"
    assert normalized.loc[0, "source_latency_ms"] == 1.25
    assert normalized.loc[0, "trace_id"] == "trace-v1"
    assert normalized.loc[0, "last_price_unit"] == "yuan"
    assert "volume_normalized_unit" in normalized.columns
    assert "amount_normalized_unit" in normalized.columns

    validation = adapter.validate_standard_output(REALTIME_QUOTES, normalized)
    assert validation["is_valid"] is True
    assert validation["schema_drift"] is False
    assert validation["public_record_count"] == 1
    assert validation["rejected_record_count"] == 0


def test_adapter_contract_v1_rejects_schema_drift_from_public_records() -> None:
    adapter = FakeAdapter()
    raw = adapter.fetch_raw(REALTIME_QUOTES, codes=["000001"])
    normalized = adapter.normalize_to_standard(REALTIME_QUOTES, raw)
    drifted = normalized.drop(columns=["last_price"])

    validation = adapter.validate_standard_output(REALTIME_QUOTES, drifted)
    assert validation["is_valid"] is False
    assert validation["schema_drift"] is True
    assert validation["missing_fields"] == ["last_price"]
    assert validation["public_record_count"] == 0
    assert validation["rejected_record_count"] == 1
    assert validation["public_records"].empty
    assert not validation["rejected_records"].empty
