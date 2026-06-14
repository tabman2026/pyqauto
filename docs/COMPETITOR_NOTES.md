# Competitor Notes

This project is intentionally narrow.

- AKShare: broad financial data collection toolkit. aquote-router does not try to replace it.
- efinance: useful user-side quote library. It is not a default source in v0.1.0.
- easyquotation: used as the fallback provider family for realtime APIs.
- pytdx: used as the primary provider family and the only provider family for minute kline.

The core value of aquote-router is deterministic source selection, fallback visibility and auditability.
