# Architecture and Trust Boundaries

## Component graph

```text
Synthetic A/B option files + underlying data
          |
          v
  Reference data gateway ----------------------------------+
          |                                                |
          | Snapshot: A, one date/asset                     | Holdout B
          v                                                |
 CandidateCalibrator                                        v
          |                                        independent fit diagnostics
          v                                        independent option marks
    Surface API                                             |
          |                                                 |
   +------+--------+                                        |
   |               |                                        |
   v               v                                        |
CandidateLocalVol  CandidateRisk                             |
                   (16 scenario PnLs)                       |
         |                                                   |
         +---------------------+-----------------------------+
                               |
                               v
                   independent hedging runner
                               |
                               v
               equity, trades, risk and cost evidence
                               |
                               v
                   technical acceptance gate
```

### In-sample and out-of-sample separation

- Dates are partitioned chronologically (`train`, `validation`, `test`). Parameter selection and calibration tuning should happen only on train/validation.
- Each `Snapshot` is restricted to a single day's asset and venue-A quotes; quote fields and market fields do not include a `split` attribute.
- The holdout venue-B quotes are used for numerical accuracy assessment and independent marking, and are not provided to the candidate calibrator.
- Candidate modules are not sandboxed from the local filesystem; trust boundary compliance is enforced by design and code review.

### API and event ordering

1. The runner loads the current day's A quote snapshot; candidate calibrates a `Surface`.
2. Independent quote-fit metrics compare the resulting surface to usable B mids. Invalid market observations are filtered before computing the score.
3. The hedge runner marks open short options to independently built B reference prices and settles prior futures close-to-close PnL.
4. On each twentieth trading day, the runner closes old short straddles and opens new ones. Both opening and closing costs are charged.
5. The candidate receives current surface, already-open option legs, current futures exposure and past/current spot prices.
6. Candidate returns target underlying futures units. The runner checks finite values, 30%-per-asset and 75%-gross exposure; fills at the current daily mark with explicit cost. Future hedge PnL starts next day.
7. The runner writes split metrics and evidence manifest, and the technical gate checks for missing modules, fit, static arbitrage, local vol, scenario risk, hedge trades, costs, candidate tests and report.

### Core technical challenges

A naive optimizer can lower sample bid/ask residuals but introduce crossed term structures; an unconstrained SVI fit can generate negative local densities; aggressive delta hedging can reduce directional risk but increase execution costs and liquidation sensitivity. The study requires balancing correlated constraints and quantifying uncertainty across regimes.

### Recovery and reproducibility

All reference simulations are deterministic with fixed synthetic datasets and no external dependencies. Evidence manifests fingerprint quote files, underlying data, candidate source files and summary artifacts to ensure reproducible results.
