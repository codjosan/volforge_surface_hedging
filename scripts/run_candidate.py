import sys,json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.evaluation import run_full,sha256
from volforge.candidate.calibrator import CandidateCalibrator
from volforge.candidate.hedger import CandidateHedger
OUT=ROOT/'outputs'/'candidate'
result=run_full(ROOT/'data',OUT,CandidateCalibrator(),CandidateHedger(),'candidate')
manifest={'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'candidate_hashes':{name:sha256(ROOT/'src'/'volforge'/'candidate'/name)
                              for name in ('calibrator.py','hedger.py','risk.py','localvol.py')},
          'data_hashes':{name:sha256(ROOT/'data'/name)
                         for name in ('option_quotes.csv','underlying_daily.csv')},
          'summary_sha256':sha256(OUT/'summary.json'),
          'artifact_hashes':{name:sha256(OUT/name) for name in
                             ('summary.json','hedge_equity.csv','hedge_trades.csv',
                              'risk_matrix.json','sample_surfaces.csv','hedge_summary.json')}}
(OUT/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'status':result['status'],'fit_by_split':result.get('fit_by_split'),
                  'hedging':result.get('hedging',{}).get('summary')},indent=2))
