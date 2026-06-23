from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PRICE_FIELDS = {"open", "high", "low", "close", "pre_close", "last_price"}
VOLUME_FIELD = "volume"
AMOUNT_FIELD = "amount"
PCT_CHG_FIELD = "pct_chg"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIELD_UNIT_POLICY_PATH = PROJECT_ROOT / "config" / "field_unit_policy.json"
SOURCE_UNIT_POLICY_PATH = PROJECT_ROOT / "config" / "source_unit_policy.json"

STANDARD_UNITS = {
    "price": "yuan",
    "volume": "share",
    "amount": "yuan",
    "pct_chg": "percent",
}

UNKNOWN_UNIT_TOKENS = ("unknown", "to_confirm", "_or_", "or_")
ADJUST_TYPES = {"none", "qfq", "hfq", "unknown"}


@lru_cache(maxsize=4)
def _load_json(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    return json.loads(path.read_text(encoding="utf-8"))


def load_field_unit_policy(path: Path | None = None) -> dict[str, Any]:
    return _load_json(str(path or FIELD_UNIT_POLICY_PATH))


def load_source_unit_policy(path: Path | None = None) -> dict[str, Any]:
    return _load_json(str(path or SOURCE_UNIT_POLICY_PATH))


def _feature_candidates(function_name: str) -> list[str]:
    aliases = {
        "full_realtime_quotes": ["full_realtime_quotes", "realtime_quotes"],
        "realtime_quotes": ["realtime_quotes", "full_realtime_quotes"],
        "index_realtime": ["index_realtime", "realtime_quotes", "full_realtime_quotes"],
        "amount_check": ["amount_check"],
        "pct_check": ["pct_check"],
    }
    return aliases.get(function_name, [function_name])


def source_feature_policy(source: str, function_name: str) -> dict[str, Any]:
    policy = load_source_unit_policy()
    source_policy = policy.get(source, {})
    if not isinstance(source_policy, dict):
        return {}
    for candidate in _feature_candidates(function_name):
        feature_policy = source_policy.get(candidate)
        if isinstance(feature_policy, dict):
            return feature_policy
    return {}


def field_unit_key(field_name: str) -> str:
    if field_name in PRICE_FIELDS:
        return "price_unit"
    return f"{field_name}_unit"


def unit_assumption(source: str, function_name: str, field_name: str) -> dict[str, Any]:
    feature_policy = source_feature_policy(source, function_name)
    unit = feature_policy.get(field_unit_key(field_name), "unknown")
    confidence = str(feature_policy.get(f"{field_name}_unit_confidence", feature_policy.get("confidence", "low")))
    return {
        "source": source,
        "function_name": function_name,
        "field_name": field_name,
        "unit": str(unit),
        "canonical_unit": canonical_unit(str(unit), field_name),
        "confidence": confidence,
        "unit_source": "config/source_unit_policy.json",
        "notes": feature_policy.get("notes", ""),
    }


def canonical_unit(unit: str | None, field_name: str | None = None) -> str:
    text = str(unit or "unknown").strip().lower()
    normalized = text.replace(" ", "_").replace("-", "_")
    aliases = {
        "rmb": "yuan",
        "cny": "yuan",
        "元": "yuan",
        "yuan": "yuan",
        "万元": "wan_yuan",
        "wan": "wan_yuan",
        "wan_yuan": "wan_yuan",
        "亿元": "yi_yuan",
        "yi": "yi_yuan",
        "yi_yuan": "yi_yuan",
        "股": "share",
        "shares": "share",
        "share": "share",
        "手": "lot",
        "lots": "lot",
        "lot": "lot",
        "percent": "percent",
        "percentage": "percent",
        "%": "percent",
        "ratio": "ratio",
        "decimal_ratio": "ratio",
        "percent_derived": "percent_derived",
        "derived_percent": "percent_derived",
    }
    if normalized in aliases:
        return aliases[normalized]
    if field_name == PCT_CHG_FIELD and normalized == "percent_or_derived":
        return "percent"
    if any(token in normalized for token in UNKNOWN_UNIT_TOKENS):
        return "unknown"
    return normalized if normalized else "unknown"


def is_unknown_unit(unit: str | None) -> bool:
    canonical = canonical_unit(unit)
    if canonical == "unknown":
        return True
    text = str(unit or "").lower()
    return any(token in text for token in UNKNOWN_UNIT_TOKENS)


def target_unit(field_name: str) -> str:
    if field_name in PRICE_FIELDS:
        return STANDARD_UNITS["price"]
    if field_name == VOLUME_FIELD:
        return STANDARD_UNITS["volume"]
    if field_name == AMOUNT_FIELD:
        return STANDARD_UNITS["amount"]
    if field_name == PCT_CHG_FIELD:
        return STANDARD_UNITS["pct_chg"]
    return "unknown"


def conversion_factor(field_name: str, source_unit: str | None) -> float | None:
    unit = canonical_unit(source_unit, field_name)
    if field_name in PRICE_FIELDS:
        return 1.0 if unit == "yuan" else None
    if field_name == VOLUME_FIELD:
        return {"share": 1.0, "lot": 100.0}.get(unit)
    if field_name == AMOUNT_FIELD:
        return {"yuan": 1.0, "wan_yuan": 10000.0, "yi_yuan": 100000000.0}.get(unit)
    if field_name == PCT_CHG_FIELD:
        return {"percent": 1.0, "percent_derived": 1.0, "ratio": 100.0}.get(unit)
    return None


def normalize_adjust_type(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"", "no", "none", "3"}:
        return "none"
    if text in {"qfq", "forward", "2"}:
        return "qfq"
    if text in {"hfq", "backward", "1"}:
        return "hfq"
    if text in ADJUST_TYPES:
        return text
    return "unknown"
