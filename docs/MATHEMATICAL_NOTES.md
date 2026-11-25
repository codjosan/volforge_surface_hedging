# Mathematical Notes

## Forward and Black-76 premiums

For spot `S`, continuous rate `r`, carry `q`, time to expiry `T = days / 365`, forward `F = S exp((r-q)T)`, discount `DF = exp(-rT)`:

- `C = DF [F N(d1) - K N(d2)]`
- `P = DF [K N(-d2) - F N(-d1)]`
- `d1 = [ln(F/K) + 0.5 σ² T] / (σ sqrt(T))`, `d2 = d1 - σ sqrt(T)`
- Put-call parity: `C-P = DF(F-K)`

Implied-volatility inversion uses bounded bisection. The reference implementation handles zero time value, expired options, premiums below intrinsic or above the theoretical cap, and finite input checks.

## Total variance and surface

For log-forward moneyness `k = ln(K/F)`, use per-tenor SVI-style total variance:

`w(k) = a + b [ρ(k-m) + sqrt((k-m)² + σ_SVI²)]`

The implied volatility is `sqrt(w(k,T)/T)`. The given `Surface` interpolates *total variance* between tenors and scales endpoint values in time outside observed tenors. `Smile.validate()` checks basic parameter sanity and variance positivity on a finite grid.

## Arbitrage diagnostics

Discounted European call premiums at a fixed tenor should be:

- bounded by discounted intrinsic and the present value of the forward;
- nonincreasing in strike;
- convex in strike, since the second strike derivative is proportional to a nonnegative risk-neutral density.

At fixed log-forward moneyness, total variance is required to be nondecreasing with maturity for a consistent calendar construction. This is an approximate numerical necessary check, not a proof that an arbitrary SVI surface is everywhere arbitrage-free under nonzero interest/carry.

## Local volatility

For a continuously differentiable discounted call-price surface with rate and carry, local volatility is derived from the Dupire equation. Implementation requires selecting stable differences `ΔT`, `ΔK`, checking positive call strike curvature and avoiding spurious near-zero time derivatives.

## Scenario risk

Reprice *each* signed option leg at a shocked spot and shocked volatility surface, then add the futures delta PnL. The 16 scenarios include spot crashes/rallies, skew and term shocks, volatility changes, and liquidity deterioration. The supplied static scenarios do not simulate jump-time path dependency or a genuine correlation matrix; they are stress probes rather than a full VaR distribution.

## Hedging and accounting

Option cash flows are signed: a short option opens with cash inflow and has a negative mark-to-market liability. Closing it pays current option mark. Underlying futures hedges realize `units * (S_today - S_yesterday)` over the interval for which positions were held. Option and futures trading costs debit cash. Therefore every daily row satisfies

`equity = starting_equity + cumulative_cash + current_option_liability`.

Delta error in USD is `sum_assets abs(option_delta_units + futures_hedge_units) * spot`.

## Calibration stress

No quote-cleaning rule is universally correct: truncating all deep strikes lowers apparent noise but hides tail skew; aggressively fitting all raw quotes can introduce arbitrage. Robust losses, confidence floors, capped weights, deterministic fallbacks and independent holdout assessment are essential for reliable calibration.
