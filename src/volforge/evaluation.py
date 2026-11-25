"""Independent offline run of surface calibration, hedging, and stress evidence."""
from __future__ import annotations
from pathlib import Path
import csv,hashlib,json,math,time
from .data import load_sessions,audit_dataset
from .baseline import FlatATMCalibrator,NoHedge
from .diagnostics import summarize_fits
from .hedging import HedgeRunner
from .scenarios import scenario_matrix


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(262144),b''):
            h.update(block)
    return h.hexdigest()


def collect_surfaces(sessions,calibrator):
    surfaces={};failures=[]
    for item in sessions:
        s=item.snapshot
        try:
            v=calibrator.calibrate(s)
            v.validate()
            surfaces[(s.date,s.asset)]=v
        except Exception as e:
            failures.append({'date':s.date,'asset':s.asset,'reason':type(e).__name__+': '+str(e)[:150]})
    return surfaces,failures


def latest_risk_matrix(sessions,surfaces):
    final=sorted({s.snapshot.date for s in sessions})[-1]
    latest={s.snapshot.asset:s for s in sessions if s.snapshot.date==final}
    spots={a:s.snapshot.market.spot for a,s in latest.items()}
    rates={a:s.snapshot.market.rate for a,s in latest.items()}
    carries={a:s.snapshot.market.carry for a,s in latest.items()}
    opts={a:[(m.spot,30,'C',-{'BTC':1.,'ETH':15.,'SOL':350.}[a]),
             (m.spot*.92,60,'P',-{'BTC':.6,'ETH':8.,'SOL':180.}[a])]
          for a,m in ((a,s.snapshot.market) for a,s in latest.items())}
    future={a:0. for a in spots}
    return scenario_matrix({a:surfaces[(final,a)] for a in spots},spots,opts,future,rates,carries)


def run_full(data_dir:str|Path,out_dir:str|Path,calibrator,hedger,run_type:str)->dict:
    data_dir=Path(data_dir);out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    sessions=load_sessions(data_dir)
    surfaces,failures=collect_surfaces(sessions,calibrator)
    if failures:
        summary={'run_type':run_type,'surface_failures':failures,
                 'status':'FAILED','reason':'invalid or missing model surfaces'}
        (out/'summary.json').write_text(json.dumps(summary,indent=2))
        return summary
    fits=summarize_fits(sessions,surfaces)
    hedge=HedgeRunner().run(sessions,surfaces,hedger,out)
    risk=latest_risk_matrix(sessions,surfaces)
    with (out/'sample_surfaces.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['date','asset','tenor_days','a','b','rho','m','sigma'])
        for (ds,a),surface in sorted(surfaces.items()):
            for tenor,smile in surface.smiles.items():
                w.writerow([ds,a,tenor,smile.a,smile.b,smile.rho,smile.m,smile.sigma])
    (out/'risk_matrix.json').write_text(json.dumps(risk,indent=2))
    summary={'run_type':run_type,'status':'EVALUATED','data_audit':audit_dataset(data_dir),
             'fit_by_split':fits,
             'hedging':{k:v for k,v in hedge.items() if k not in ('daily','trades')},
             'risk_scenario_count':len(risk),'surface_failures':[],
             'elapsed_runtime_seconds':round(time.perf_counter()-started,2)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    return summary
