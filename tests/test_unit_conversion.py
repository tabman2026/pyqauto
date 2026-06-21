from __future__ import annotations

from pyqauto.adapters.akshare_em_spot_adapter import AkShareEmSpotAdapter


def test_akshare_volume_lots_convert_to_shares_and_amount_stays_yuan() -> None:
    adapter = AkShareEmSpotAdapter()
    rows = adapter.normalize_to_standard(
        [
            {
                "代码": "000001",
                "名称": "平安银行",
                "最新价": 10.48,
                "昨收": 10.0,
                "今开": 10.1,
                "最高": 10.6,
                "最低": 9.9,
                "涨跌幅": 4.8,
                "成交量": 321,
                "成交额": 654321,
            }
        ],
        symbols=["000001"],
        fetch_time="2026-06-21T02:00:00Z",
    )

    assert rows[0]["symbol"] == "000001.SZ"
    assert rows[0]["volume_shares"] == 32100
    assert rows[0]["amount_yuan"] == 654321
    assert rows[0]["pct_chg"] == 4.8
