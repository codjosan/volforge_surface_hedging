# Baseline Reference — VolForge

The baseline uses flat ATM implied volatility at each tenor and **never hedges** the rolling short straddles.
This is a reference benchmark only, and positive sample net returns are not proof of tradable alpha.

## Independent venue-B fit, by chronological split

| Split | Heldout IV MAE (decimal) | Heldout Premium WAPE | Static Arb Violations |
|---|---:|---:|---:|
| Train | 0.019247 | 1.3167% | 0 / 102816 |
| Validation | 0.020438 | 1.3616% | 0 / 36720 |
| Test | 0.020692 | 1.3591% | 0 / 36720 |

## Synthetic short-straddle hedge replay

| Split | Net return | Max drawdown | Mean delta exposure after hedge (USD) | Hedge cost |
|---|---:|---:|---:|---:|
| Train | +3.4574% | 0.4818% | $41,383 | $0.00 |
| Validation | -0.6820% | 1.3826% | $77,751 | $0.00 |
| Test | +1.8379% | 1.0642% | $77,489 | $0.00 |

Total baseline hedge trades: **0**. There is no benchmark claim of neutralized Greeks.

## Interpretation

The baseline can achieve positive option premium returns in short synthetic samples while remaining exposed to large directional and volatility shocks. Candidate implementations should materially improve held-out volatility accuracy, sampled arbitrage constraints and residual delta risk without creating excessive execution costs.

## Reproduction

```bash
python scripts/run_baseline.py
python scripts/verify_outputs.py
python scripts/run_stress.py
```
