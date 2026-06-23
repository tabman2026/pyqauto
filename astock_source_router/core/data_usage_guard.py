from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from typing import Literal

UsageMode = Literal["intraday", "after_close", "backtest"]

AFTER_CLOSE_VISIBLE_TIME = time(15, 30)


@dataclass(slots=True)
class DataUsageDecision:
    target_trade_date: str
    request_time: str
    data_time: str
    usage_mode: UsageMode
    allow_intraday: bool
    allow_after_close: bool
    allow_backtest: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return datetime.fromisoformat(text).date()


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def assess_data_usage(
    *,
    target_trade_date: str | date | datetime,
    request_time: str | datetime,
    data_time: str | datetime,
    usage_mode: UsageMode,
) -> DataUsageDecision:
    """Assess whether a data row may be used in a given research mode.

    This module only records data visibility and permission decisions. It does not produce
    trading advice, strategy signals, position sizing, return forecasts, or automated actions.
    """

    if usage_mode not in {"intraday", "after_close", "backtest"}:
        raise ValueError(f"Unsupported usage_mode: {usage_mode!r}")

    target_date = _parse_date(target_trade_date)
    request_dt = _parse_datetime(request_time)
    data_dt = _parse_datetime(data_time)
    visible_after_close = datetime.combine(
        target_date,
        AFTER_CLOSE_VISIBLE_TIME,
        tzinfo=request_dt.tzinfo,
    )

    if data_dt > request_dt:
        return DataUsageDecision(
            target_trade_date=target_date.isoformat(),
            request_time=request_dt.isoformat(),
            data_time=data_dt.isoformat(),
            usage_mode=usage_mode,
            allow_intraday=False,
            allow_after_close=False,
            allow_backtest=False,
            reason="data_time_after_request_time",
        )

    is_target_day = data_dt.date() == target_date
    after_close_data = data_dt >= visible_after_close
    request_after_close = request_dt >= visible_after_close

    allow_intraday = is_target_day and not after_close_data and data_dt <= request_dt
    allow_after_close = request_after_close and data_dt <= request_dt
    allow_backtest = data_dt <= request_dt

    reason = "ok"
    if usage_mode == "intraday" and not allow_intraday:
        reason = "after_close_or_non_intraday_data_not_allowed_for_intraday"
    elif usage_mode == "after_close" and not allow_after_close:
        reason = "after_close_data_not_visible_yet"
    elif usage_mode == "backtest" and not allow_backtest:
        reason = "data_not_visible_at_request_time"

    return DataUsageDecision(
        target_trade_date=target_date.isoformat(),
        request_time=request_dt.isoformat(),
        data_time=data_dt.isoformat(),
        usage_mode=usage_mode,
        allow_intraday=allow_intraday,
        allow_after_close=allow_after_close,
        allow_backtest=allow_backtest,
        reason=reason,
    )
