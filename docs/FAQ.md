# FAQ

## Is this a data provider?

No. aquote-router routes calls to user-configured providers and normalizes the result. It does not host or redistribute market data.

## Why is minute_kline pytdx-only?

Minute bars are sensitive to period definition and provider-specific field meaning. The first release keeps a single provider family for this API to avoid unclear mixed-source results.

## Do tests require live network access?

No. Unit tests use fake adapters and local files. Live smoke tests require `ENABLE_LIVE_SMOKE_TEST=1`.

## Can I add another provider?

Yes, but add adapter tests and field normalization tests first.

## Does this project provide investment advice?

No. It is a routing and audit library only.
