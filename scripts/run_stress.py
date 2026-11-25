"""Exercise 12 adversarial feed mutations and 16 deterministic market scenarios."""
import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.data import load_sessions
from volforge.faults import FAULTS,mutate_snapshot
from volforge.diagnostics import static_arbitrage
from volforge.evaluation import collect_surfaces,latest_risk_matrix
from volforge.baseline import FlatATMCalibrator
parser=argparse.ArgumentParser()
parser.add_argument('--candidate',action='store_true')
a=parser.parse_args()
if a.candidate:
    from volforge.candidate.calibrator import CandidateCalibrator
    calibrator=CandidateCalibrator()
else:
    calibrator=FlatATMCalibrator()
sessions=load_sessions(ROOT/'data')
# Sample six assets/dates for each fault, including training, validation, and test.
subset=[sessions[i] for i in (0,1,2,126,127,128,171,172,173,225,226,227,273,274,275)]
results={}
for fault in FAULTS:
    good=0; failed=0;arb=0;total=0;empty=0
    for item in subset:
        snap=mutate_snapshot(item.snapshot,fault)
        if not snap.points():empty+=1
        try:
            surface=calibrator.calibrate(snap)
            surface.validate()
            stat=static_arbitrage(surface,snap.market.spot,snap.market.rate,snap.market.carry)
            good+=1;arb+=stat['violations'];total+=stat['checks']
        except (ValueError,TypeError,ZeroDivisionError,OverflowError):
            failed+=1
    results[fault]={'evaluated':len(subset),'calibrated':good,'failed_closed':failed,
                    'empty_valid_quote_snapshots':empty,'arb_rate':arb/max(1,total)}
selected=[s for s in sessions if s.snapshot.date==sessions[-1].snapshot.date]
surfaces,failures=collect_surfaces(selected,calibrator)
scenario=latest_risk_matrix(selected,surfaces) if not failures else {'ERROR':failures}
mode='candidate' if a.candidate else 'baseline'
out=ROOT/'outputs'/('candidate_stress' if a.candidate else 'baseline_stress')
out.mkdir(parents=True,exist_ok=True)
report={'mode':mode,'quote_faults':results,'market_scenarios':scenario,
        'interpretation':'Simulation probes only; no claim of real-world probability or execution.'}
(out/'stress_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'mode':mode,'quote_faults':results,
                  'market_scenario_count':len(scenario)},indent=2))
