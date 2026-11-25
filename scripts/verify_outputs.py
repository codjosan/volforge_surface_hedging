"""Read-only extra audit of replay artifacts and daily cash/mark accounting."""
import argparse,csv,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--candidate',action='store_true')
a=p.parse_args();out=ROOT/'outputs'/('candidate' if a.candidate else 'baseline')
with (out/'hedge_equity.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
with (out/'hedge_trades.csv').open(newline='',encoding='utf-8') as f:
    trades=list(csv.DictReader(f))
if len(rows)!=96:
    raise SystemExit('FAILED: expected 96 daily accounting rows')
residuals=[float(r['equity'])-1e6-float(r['cash'])-float(r['short_option_mark']) for r in rows]
if max(abs(r) for r in residuals)>1e-5:
    raise SystemExit('FAILED: ledger residual exceeds tolerance')
if any(not math.isfinite(float(r['equity'])) or float(r['equity'])<=0 for r in rows):
    raise SystemExit('FAILED: nonfinite or negative equity')
if any(float(t['cost'])<0 for t in trades):
    raise SystemExit('FAILED: negative trading cost')
summary=json.loads((out/'summary.json').read_text())
if abs(summary['hedging']['final_equity']-float(rows[-1]['equity']))>.0001:
    raise SystemExit('FAILED: final equity mismatch')
print(json.dumps({'status':'RECONCILED','days':len(rows),'trade_entries':len(trades),
                  'max_abs_equity_residual':max(abs(r) for r in residuals),
                  'final_equity':float(rows[-1]['equity'])},indent=2))
