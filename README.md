# VolForge — Arbitrage-Aware Volatility Surface & Dynamic Hedging Study

VolForge is an offline quantitative finance research environment for cross-asset option volatility surface calibration, Dupire local volatility computation, scenario risk analysis, and transaction-cost-aware dynamic delta hedging under imperfect market data.

**Requirements:** Python 3.10 or later.  
**External dependencies:** None (standard library only).  
**Network access:** Not required.

---

## Project Overview

The study covers three crypto assets (**BTC**, **ETH**, **SOL**) across **96 trading dates** (partitioned chronologically into 56 training, 20 validation, and 20 test dates), five rolling constant-calendar-day tenors (**14, 30, 60, 90, 180 days**), nine log-moneyness strike points, and both Call (`C`) and Put (`P`) contracts.

- **Point-in-time calibration:** Surfaces are calibrated exclusively from venue **A** bid/ask option quotes (`Snapshot`), which include realistic feed defects (crossed quotes, wide spreads, stale timestamps, low depth, and distorted wing prices).
- **Independent out-of-sample evaluation:** Venue **B** quotes are held out from calibration and used independently to evaluate implied-volatility fit accuracy and mark rolling 28-day short straddles during hedging replays.
- **Core research components (`src/volforge/candidate/`):**
  1. `CandidateCalibrator` (`calibrator.py`): Robust, arbitrage-aware SVI implied-volatility surface calibration across tenors.
  2. `CandidateLocalVol` (`localvol.py`): Numerically stable Dupire local volatility computation with density safeguards.
  3. `CandidateRisk` (`risk.py`): Portfolio revaluation across 16 deterministic market shock scenarios and equity drawdown breach checks.
  4. `CandidateHedger` (`hedger.py`): Cost-aware dynamic underlying futures hedging subject to per-asset (30% equity) and gross (75% equity) exposure limits.

---

## Repository Structure

```text
volforge_surface_hedging/
├── README.md                     # Project overview, script commands, and test instructions
├── BASELINE_REFERENCE.md         # Benchmark metrics for the flat-ATM / unhedged baseline
├── data/
│   ├── underlying_daily.csv      # 288 daily market records (96 dates × 3 assets)
│   ├── option_quotes.csv         # 51,840 synthetic option quotes across venues A and B
│   └── DATA_DICTIONARY.md        # Schema definitions, conventions, and data isolation rules
├── docs/
│   ├── ARCHITECTURE.md           # Component pipeline, event ordering, and trust boundaries
│   ├── MATHEMATICAL_NOTES.md     # Black-76 pricing, SVI parameterization, Dupire & hedging math
│   └── OPERATIONS_AND_INCIDENTS.md # Fault diagnosis playbook and stress-testing guidelines
├── src/volforge/
│   ├── __init__.py
│   ├── black.py                  # Black-76 option pricing, Greeks, and bisection IV solver
│   ├── data.py                   # Point-in-time data gateway, dataset loader, and audit utilities
│   ├── surface.py                # SVI smile representation and total-variance surface interpolation
│   ├── diagnostics.py            # Out-of-sample fit metrics and static arbitrage checks
│   ├── numerics.py               # Robust statistics, isotonic regression, and finite differences
│   ├── tca.py                    # Transaction cost model, no-trade band, and PnL reconciliation
│   ├── hedging.py                # Independent daily short-straddle hedging replay engine
│   ├── scenarios.py              # 16 deterministic price, volatility, skew, and liquidity shocks
│   ├── faults.py                 # 12 synthetic quote-feed corruption injectors
│   ├── evaluation.py             # End-to-end calibration, hedging, and risk runner
│   ├── baseline.py               # Reference FlatATMCalibrator and NoHedge implementations
│   └── candidate/
│       ├── __init__.py
│       ├── calibrator.py         # Candidate volatility surface calibrator
│       ├── localvol.py           # Candidate Dupire local volatility calculator
│       ├── risk.py               # Candidate scenario risk engine
│       └── hedger.py             # Candidate dynamic futures hedger
├── scripts/
│   ├── audit_data.py             # Inspect dataset dimensions, splits, and quote quality counts
│   ├── run_unit_tests.py         # Execute the unit test suite
│   ├── run_baseline.py           # Run baseline calibration, hedging replay, and risk matrix
│   ├── run_candidate.py          # Run candidate pipeline and generate evidence fingerprints
│   ├── run_stress.py             # Run 12 quote-fault stress probes and 16 market scenarios
│   ├── verify_outputs.py         # Verify daily cash, option mark, and equity ledger reconciliation
│   ├── benchmark_runtime.py      # Measure per-session calibration latency percentiles
│   └── check_acceptance.py       # Validate technical acceptance criteria across all modules
├── tests/
│   ├── test_black.py             # Black-76 pricing, delta, and IV inversion tests
│   ├── test_data_faults.py       # Data gateway isolation and fault injection tests
│   ├── test_hedging.py           # Hedging accounting, limits, and determinism tests
│   ├── test_numerics_tca.py      # Robust statistics, execution cost, and reconciliation tests
│   ├── test_scenarios.py         # Deterministic shock scenario tests
│   ├── test_surface.py           # SVI parameter validation and surface interpolation tests
│   └── candidate/
│       └── README.md             # Guidelines for candidate unit tests (`test_*.py`)
└── outputs/                      # Generated JSON/CSV artifacts for baseline, candidate, and stress runs
```

---

## Running the Study (Script Commands)

Run all commands from the project root directory (`volforge_surface_hedging/`). Each script configures `sys.path` automatically (optionally set `PYTHONPATH=src` on macOS/Linux or `$env:PYTHONPATH='src'` on Windows PowerShell).

### 1. Data Audit & Baseline Execution
```bash
# Audit dataset row counts, chronological splits, and usable quote statistics
python scripts/audit_data.py

# Run the flat-ATM / unhedged baseline and write artifacts to outputs/baseline/
python scripts/run_baseline.py

# Verify accounting ledger reconciliation for baseline outputs
python scripts/verify_outputs.py

# Run baseline quote-fault and market-shock stress probes
python scripts/run_stress.py
```

### 2. Candidate Execution & Verification
```bash
# Run the candidate calibration, hedging replay, and risk matrix (outputs/candidate/)
python scripts/run_candidate.py

# Verify accounting ledger reconciliation for candidate outputs
python scripts/verify_outputs.py --candidate

# Run candidate quote-fault and market-shock stress probes (outputs/candidate_stress/)
python scripts/run_stress.py --candidate

# Measure calibration latency percentiles across all 288 asset-date sessions
python scripts/benchmark_runtime.py --candidate

# Run full technical verification gates (fit, arbitrage, hedging, local vol, risk, tests)
python scripts/check_acceptance.py
```

---

## Running Tests

The repository includes **189 starter unit tests** covering Black-76 pricing, SVI surfaces, data isolation, fault injection, numerical routines, transaction costs, scenario shocks, and hedging ledger accounting. Additional candidate tests should be placed in `tests/candidate/test_*.py`.

```bash
# Run the complete unit test suite (starter + candidate tests)
python scripts/run_unit_tests.py

# Alternatively, run via standard library unittest discovery
python -m unittest discover -s tests -t tests -p "test_*.py" -v
```
