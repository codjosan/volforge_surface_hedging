# Synthetic Market Data and Trust Boundaries

## `underlying_daily.csv`

288 rows = 96 weekday dates × BTC/ETH/SOL. The fields are:

| Field | Description |
|---|---|
| `date` | ISO 8601 simulation date |
| `asset` | BTC, ETH or SOL |
| `spot` | USD spot mark at the daily decision time |
| `rate` | continuously compounded annualized USD reference rate, decimal |
| `carry` | annualized underlying carry/dividend proxy, decimal |
| `daily_volume_usd` | synthetic dollar volume used for futures participation/impact |
| `future_spread_bps` | full synthetic futures bid/ask spread in basis points |
| `future_impact_bps` | square-root impact coefficient in basis points |
| `split` | chronological reporting-only label (`train`, `validation`, `test`) |

## `option_quotes.csv`

51,840 rows = 96 × 3 underlyings × 5 tenors × 9 strikes × 2 rights × 2 venues.

| Field | Description |
|---|---|
| `date`, `asset` | Session and underlying |
| `tenor_days` | Rolling constant-calendar-day option tenor: 14/30/60/90/180 |
| `right` | `C` for call, `P` for put |
| `strike` | Positive USD strike |
| `spot` | Underlying USD spot, repeated for convenience |
| `rate`, `carry` | Continuously compounded annual decimal, repeated |
| `venue` | Synthetic `A` calibration, `B` held out for evaluation |
| `bid`, `ask` | Option premium in USD per one underlying unit |
| `quote_age_ms` | Last quote age, synthetic milliseconds |
| `depth_usd` | Approximate displayed dollar liquidity at quote |
| `split` | Chronological reporting-only partition label |

**Data defects:** crossed quotes, widened markets, negative-quality or near-zero bids, age spikes, bad depth and distorted prices. Filtering is part of the exercise, not grounds for deleting inconvenient data. Samples are synthetic and do not correspond to observed quotes from any real crypto derivatives exchange.

**Split:** 56 train + 20 validation + 20 test trading dates. Futures hedge replay is chronological and must never use future prices in a target decision.

**Access:** `volforge.data.load_sessions` returns `EvaluationSession` objects only to the evaluator. Candidate callbacks receive `Snapshot` objects containing **venue A only** and `HedgeContext` objects without venue-B marks or split labels. The event evaluator may access all data for scoring and independent marking; candidate code must not read the raw files to bypass this boundary.

**Options conventions:** theoretical Black-forward European cash-settled call/put premiums; forward is `spot * exp((rate-carry)*tenor/365)`; discount factor is `exp(-rate*tenor/365)`. Model volatility is per square root of year and all implied-vol errors are absolute decimal vol, e.g. `0.02` = two volatility percentage points.

**Important simplifications:** Rolling constant-tenor quotes are not actual option-series identifiers; the hedging runner constructs artificial fixed-strike 28-calendar-day short straddles and values them from held-out venue-B interpolated IV marks. A research dataset of this kind does not justify trading with real funds.
