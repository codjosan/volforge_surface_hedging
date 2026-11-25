"""Technical acceptance gate; does not certify actual human time spent."""
import sys,json,math,inspect,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.evaluation import sha256
from volforge.surface import Surface,Smile
from volforge.scenarios import scenario_matrix
from volforge.candidate.risk import CandidateRisk,RiskRequest
from volforge.candidate import calibrator,hedger,risk,localvol
from volforge.candidate.localvol import CandidateLocalVol

out=ROOT/'outputs'/'candidate'
checks={}
checks['candidate_implementations_declared']=all((calibrator.IMPLEMENTED,hedger.IMPLEMENTED,risk.IMPLEMENTED,localvol.IMPLEMENTED))
try:
    result=json.loads((out/'summary.json').read_text())
    manifest=json.loads((out/'evidence_manifest.json').read_text())
    checks['summary_present']=result['status']=='EVALUATED'
    checks['summary_fingerprint_valid']=sha256(out/'summary.json')==manifest['summary_sha256']
    checks['artifact_fingerprints_valid']=all(sha256(out/name)==h for name,h in manifest['artifact_hashes'].items())
    checks['data_fingerprints_valid']=all(sha256(ROOT/'data'/name)==h for name,h in manifest['data_hashes'].items())
    checks['candidate_fingerprints_valid']=all(sha256(ROOT/'src'/'volforge'/'candidate'/name)==h for name,h in manifest['candidate_hashes'].items())
    if result['status']=='EVALUATED':
        fit=result['fit_by_split'];hed=result['hedging']
        checks['holdout_fit_validation']=fit['validation']['holdout_iv_mae']<.0175
        checks['holdout_fit_test']=fit['test']['holdout_iv_mae']<.0175
        checks['no_invalid_surfaces']=all(x['invalid_surfaces']==0 for x in fit.values())
        checks['static_arbitrage_control']=all(x['static_arb_rate']<=.0008 for x in fit.values())
        checks['hedge_count']=hed['hedge_trades']>=45
        checks['hedge_risk_validation']=(hed['summary']['validation']['mean_delta_error_usd'] <
                                        .40*hed['summary']['validation']['mean_unadjusted_delta_usd'])
        checks['hedge_risk_test']=(hed['summary']['test']['mean_delta_error_usd'] <
                                  .40*hed['summary']['test']['mean_unadjusted_delta_usd'])
        checks['hedge_execution_cost']=(hed['total_hedge_cost_usd']<20000)
        checks['maximum_drawdown']=all(x['max_drawdown_pct']<8 for x in hed['summary'].values())
        checks['no_hedge_target_violations']=(hed['violations'].get('invalid_hedge_targets',0)==0)
        with (out/'hedge_equity.csv').open(newline='',encoding='utf-8') as evidence_file:
            import csv
            day_rows=list(csv.DictReader(evidence_file))
        checks['hedge_ledger_reconciliation']=(len(day_rows)==96 and all(
            abs(float(row['equity'])-(1_000_000.+float(row['cash'])+float(row['short_option_mark'])))<.001
            and math.isfinite(float(row['equity'])) and float(row['equity'])>0
            for row in day_rows))
except (OSError,KeyError,TypeError,ValueError,ZeroDivisionError) as exc:
    checks['candidate_evidence_available']=False
    error=str(exc)
else:
    error=None

# Candidate scenario risk must agree with direct, independent revaluation.
try:
    asset_surface=Surface({days:Smile(days/365*.4,days/365*.02,-.3,0.,.25)
                           for days in (14,30,60,90,180)})
    request=RiskRequest(surfaces={'BTC':asset_surface},spots={'BTC':55000.},
                        positions={'BTC':[(56000.,30,'C',-3.),(50000.,60,'P',-2.)]},
                        hedge_units={'BTC':1.5},rates={'BTC':.03},carries={'BTC':.005},equity=200000.)
    reported=CandidateRisk().assess(request)
    real=scenario_matrix(request.surfaces,request.spots,request.positions,
                         request.hedge_units,request.rates,request.carries)
    expected={k:v['total_pnl'] for k,v in real.items()}
    worst=min(expected.values())
    checks['scenario_risk_complete']=(set(reported.scenario_pnl)==set(expected)
        and len(reported.scenario_pnl)==16)
    checks['scenario_risk_reconciles']=(checks['scenario_risk_complete']
        and all(math.isfinite(reported.scenario_pnl[k])
                and abs(reported.scenario_pnl[k]-val)<.01 for k,val in expected.items())
        and abs(reported.worst_pnl-worst)<.01)
    checks['scenario_risk_policy']=(abs(reported.max_loss_fraction-max(0,-worst/request.equity))<1e-7
                                  and reported.breached == (worst < -.10*request.equity))
except Exception as exc:
    checks['scenario_risk_complete']=False
    checks['scenario_risk_reconciles']=False
    checks['scenario_risk_policy']=False


# Independent finite-difference Dupire check on a deliberately skewed smile.
try:
    surface=Surface({t:Smile(.34*t/365.,.16*t/365.,-.5,0.,.22)
                     for t in (14,30,60,90,180)})
    lv=CandidateLocalVol()
    localvol_checks=[]
    for K in (85.,90.,100.,110.,120.):
        spot=100.;days=60.;rate=.025;carry=.005
        h=K*.005;dt=.2
        p=lambda kk,tt:surface.price(spot,kk,tt,'C',rate,carry)
        C=p(K,days)
        dT=(p(K,days+dt)-p(K,days-dt))/(2*dt/365.)
        dK=(p(K+h,days)-p(K-h,days))/(2*h)
        dKK=(p(K+h,days)-2*C+p(K-h,days))/(h*h)
        target=(dT+(rate-carry)*K*dK+carry*C)/(.5*K*K*dKK)
        reported=lv.local_vol(surface,spot,K,days,rate,carry)
        localvol_checks.append(math.isfinite(reported) and reported>0
                               and abs(reported-math.sqrt(target))<.009)
    checks['local_vol_analytic_reproduction']=all(localvol_checks)
except Exception:
    checks['local_vol_analytic_reproduction']=False

# Additional candidate tests are required. Starter test methods do not count.
candidate_test_paths=list((ROOT/'tests'/'candidate').glob('test_*.py'))
import ast
candidate_test_methods=0
for p in candidate_test_paths:
    try:
        module=ast.parse(p.read_text())
        candidate_test_methods+=sum(1 for n in ast.walk(module) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                                    and n.name.startswith('test_'))
    except Exception:
        pass
checks['candidate_authored_tests']=candidate_test_methods>=20
report=ROOT/'REPORT.md'
checks['research_report_complete']=report.exists() and len(report.read_text())>=4000
score=sum(bool(v) for v in checks.values())
verdict={'status':'PASS' if all(checks.values()) else 'INCOMPLETE','passed_checks':score,
         'total_checks':len(checks),'candidate_authored_test_methods':candidate_test_methods,
         'checks':checks,'note':'Technical validation only; independent human review and actual elapsed time are not certified.'}
if error:verdict['evidence_error']=error
print(json.dumps(verdict,indent=2))
(ROOT/'outputs').mkdir(exist_ok=True)
(ROOT/'outputs'/'acceptance_status.json').write_text(json.dumps(verdict,indent=2))
raise SystemExit(0 if verdict['status']=='PASS' else 2)
