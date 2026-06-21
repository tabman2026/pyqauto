from __future__ import annotations

from pyqauto.adapters.easyquotation_tencent_adapter import EasyQuotationTencentAdapter


def test_easyquotation_tencent_uses_trade_summary_units() -> None:
    adapter = EasyQuotationTencentAdapter()
    rows = adapter.normalize_to_standard(
        {
            "600519": {
                "name": "贵州茅台",
                "now": 1215,
                "close": 1240,
                "open": 1235,
                "high": 1238.87,
                "low": 1211.22,
                "价格/成交量(手)/成交额": "1215.00/57472/7016713941",
                "成交量(手)": 1,
                "成交额(万)": 2,
                "datetime": "2026-06-18 16:14:04",
            }
        },
        symbols=["600519"],
        fetch_time="2026-06-21T02:00:00Z",
    )

    assert rows[0]["volume_shares"] == 5747200
    assert rows[0]["amount_yuan"] == 7016713941
