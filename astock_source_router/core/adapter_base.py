from __future__ import annotations

from typing import Any

import pandas as pd

from astock_source_router.core.errors import UnsupportedFeatureError
from astock_source_router.core.features import (
    DAILY_KLINE,
    FULL_REALTIME_QUOTES,
    INDEX_REALTIME,
    LITE_REALTIME_QUOTES,
    REALTIME_QUOTES,
)
from astock_source_router.core.schema import (
    REQUIRED_COLUMNS,
    add_source_columns,
    coerce_standard_types,
    ensure_dataframe,
    validate_dataframe,
)
from astock_source_router.core.unit_normalizer import (
    normalize_daily_kline_units,
    normalize_index_units,
    normalize_realtime_units,
)


class BaseMarketDataAdapter:
    """Base class for optional data-source adapters."""

    name: str = "base"
    supported_features: set[str] = set()
    default_min_interval_seconds: float = 1.0

    def fetch(self, feature: str, **kwargs: Any) -> pd.DataFrame:
        return self.fetch_raw(feature, **kwargs)

    def fetch_raw(self, feature: str, **kwargs: Any) -> pd.DataFrame:
        if feature not in self.supported_features:
            raise UnsupportedFeatureError(f"{self.name} does not support {feature}")
        method = getattr(self, f"fetch_{feature}", None)
        if method is None:
            raise UnsupportedFeatureError(f"{self.name} has no fetch_{feature} implementation")
        return method(**kwargs)

    def inspect_raw_schema(
        self,
        raw: Any | None = None,
        *,
        feature: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if raw is None:
            if feature is None:
                raise ValueError("feature is required when raw is not supplied")
            raw = self.fetch_raw(feature, **kwargs)
        df = ensure_dataframe(raw)
        return {
            "source": self.name,
            "feature": feature,
            "row_count": int(len(df)),
            "columns": [str(column) for column in df.columns],
            "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        }

    def normalize_to_standard(
        self,
        feature: str,
        raw: Any,
        *,
        source: str | None = None,
        latency_ms: float = 0.0,
        trace_id: str | None = None,
    ) -> pd.DataFrame:
        source_name = source or self.name
        df = ensure_dataframe(raw)
        if feature == DAILY_KLINE:
            out = normalize_daily_kline_units(df, source_name)
        elif feature in {REALTIME_QUOTES, FULL_REALTIME_QUOTES, LITE_REALTIME_QUOTES}:
            out = normalize_realtime_units(df, source_name)
        elif feature == INDEX_REALTIME:
            out = normalize_index_units(df, source_name)
        else:
            out = df.copy()
        out = add_source_columns(out, source=source_name, latency_ms=latency_ms)
        out = coerce_standard_types(out)
        if trace_id is not None:
            out["trace_id"] = str(trace_id)
        return out

    def validate_standard_output(
        self,
        feature: str,
        records: Any,
        *,
        context: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        df = ensure_dataframe(records)
        quality = validate_dataframe(feature, df, context=context)
        public_records = df.copy() if quality.is_valid else df.iloc[0:0].copy()
        rejected_records = df.iloc[0:0].copy() if quality.is_valid else df.copy()
        expected_columns = REQUIRED_COLUMNS.get(feature, [])
        actual_columns = [str(column) for column in df.columns]
        unexpected_columns = [column for column in actual_columns if column not in expected_columns]
        return {
            "source": self.name,
            "feature": feature,
            "is_valid": quality.is_valid,
            "public_records": public_records,
            "rejected_records": rejected_records,
            "record_count": quality.row_count,
            "public_record_count": int(len(public_records)),
            "rejected_record_count": int(len(rejected_records)),
            "missing_fields": quality.missing_fields,
            "warnings": quality.warnings,
            "schema_drift": bool(quality.missing_fields),
            "schema": {
                "expected_columns": list(expected_columns),
                "actual_columns": actual_columns,
                "missing_columns": list(quality.missing_fields),
                "unexpected_columns": unexpected_columns,
                "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
            },
        }

    def healthcheck(self) -> bool:
        return True
