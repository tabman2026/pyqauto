from __future__ import annotations

from pyqauto.adapters.akshare_em_spot_adapter import AkShareEmSpotAdapter


def test_akshare_em_spot_normalizes_chinese_raw_fields_to_standard() -> None:
    adapter = AkShareEmSpotAdapter()
    raw = [
        {
            "代码": "600519",
            "名称": "贵州茅台",
            "最新价": 1200,
            "昨收": 1190,
            "今开": 1195,
            "最高": 1210,
            "最低": 1188,
            "涨跌额": 10,
            "涨跌幅": 0.84,
            "成交量": 123,
            "成交额": 456789,
            "换手率": 1.2,
        }
    ]

    rows = adapter.normalize_to_standard(
        raw,
        symbols=["600519"],
        fetch_time="2026-06-21T02:00:00Z",
    )
    validation = adapter.validate_standard_output(rows)

    assert validation.is_valid
    assert rows[0]["symbol"] == "600519.SH"
    assert rows[0]["symbol_raw"] == "600519"
    assert rows[0]["market"] == "SH"
    assert rows[0]["name"] == "贵州茅台"
    assert rows[0]["last_price"] == 1200
    assert rows[0]["pre_close"] == 1190
    assert rows[0]["volume_shares"] == 12300
    assert rows[0]["amount_yuan"] == 456789
    assert rows[0]["pct_chg"] == 0.84
    assert rows[0]["source_name"] == "akshare_em_spot"
    assert rows[0]["source_api"] == "akshare.stock_zh_a_spot_em"
