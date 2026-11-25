# Operational Fault Playbook

This document is a research-engineering review aid. It is not an exchange runbook.

## Typical incident triggers

- **Mass stale quote:** all bid/ask observations are old, or one tenor has no usable prices. A safe calibrator must not interpret zero usable data as a market flattening or fake a confident fit.
- **Crossed market:** bid exceeds ask for one or more contracts. Reject crossed quotes and investigate whether market-side data or timestamp alignment is at fault.
- **Wing poisoning:** a subset of deep OTM strikes is materially mispriced. An unbounded least-squares objective can produce negative implied density or unstable local volatility.
- **Term inconsistency:** independent per-tenor optimizers produce decreasing total variance at the same forward moneyness. Penalize or project violations and validate on a wider mesh after the repair.
- **Unhedgeable shock:** spot moves and funding/futures liquidity evaporate before the candidate can rebalance. A delta-neutral current mark can still sustain material gamma, vega, skew and jump losses.
- **Risk engine inconsistency:** scenarios are computed at one underlying unit convention but reported in futures contracts or USD without conversion. Require exact documented units and an independent repricing reconciliation.

## Suggested diagnosis and containment

1. Preserve input evidence, isolate the bad venue, record the exact date/asset/tenor/strike and reject unsafe quotes.
2. Compute usable-quote counts and cross-check put/call parity before fitting.
3. Run per-maturity IV residuals; check finite SVI parameters and positivity.
4. Check call monotonicity, convexity and calendar total variance across an extended grid.
5. Stress local-vol numerical derivative scales; reject zero/negative densities or nonfinite rates.
6. Reprice all sixteen risk scenarios, including hedging cost under reduced liquidity.
7. Re-run the independent daily hedge ledger and report any change to equity, exposure and costs.
8. Fingerprint outputs, add a regression test for the exact fault and document the remaining uncertainty.

## Audit requirements

For each severe incident, save a short postmortem containing: trigger, raw and filtered quote counts, affected portfolios/surfaces, reproduction command, observed residuals/arb failures, mitigations, limitations and unresolved risks. The final `REPORT.md` should include at least two such analyses.
