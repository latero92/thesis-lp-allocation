"""Area-only allocation model: one direct LP solve for each of 594 scenarios.

Authorized 2026-10-30. Uses config_594.json in this directory as its sole model input.
Twelve area slots remain separate for H1, H2, H3 and U. Times are derived.
The 13th solver variable is the epigraph upper bound T, minimized by the LP.
"""
from __future__ import annotations
import csv, hashlib, json, platform, sys, time, uuid, os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / '20261029_594시나리오_면적모형'
DEPENDENCIES = HERE.parent / '20261009_로봇계수민감도' / '_dependencies'
sys.dont_write_bytecode = True
sys.path.insert(0, str(DEPENDENCIES))
import numpy as np
import scipy
from scipy.optimize import linprog

OUT = HERE / 'results'
MEANS = ['H1','H2','H3','U']
TERRAINS = ['양호','제한','고제한']
METHODS = ['equal','proportional','optimal']

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save_json(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def save_csv(p,rows):
    if not rows: return
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def rate_matrix(cfg,k):
    # Each human is an individual row; no combined human resource exists.
    rates=[]
    for d in MEANS:
        if d=='U': rates.append([cfg['ugv_base_rate_m2_h'],cfg['ugv_base_rate_m2_h']*k,0.])
        else: rates.append([cfg['human_base_rate_m2_h']*c for c in cfg['human_terrain_factors']])
    return np.asarray(rates,dtype=float)
def derived_times(a,q):
    # Excluded pairs have zero assigned area and zero derived time, never 0/0.
    return np.divide(a,q,out=np.zeros((4,3)),where=q>0)
def make_model(area,q):
    eq=np.zeros((4,13));rhs=np.r_[area,area.sum()]
    for i in range(3):
        for d in range(4): eq[i,3*d+i]=1.
    # Explicit total-area double sum, redundant with the three terrain balances.
    eq[3,:12]=1.
    ub=np.zeros((4,13))
    for d in range(4):
        for i in range(3):
            if q[d,i]>0:ub[d,3*d+i]=1./q[d,i]
        ub[d,12]=-1.
    bounds=[]
    for d in range(4):
        for i in range(3):
            bounds.append((0.,0.) if q[d,i]==0 or area[i]==0 else (0.,None))
    bounds.append((0.,None))
    objective=np.zeros(13);objective[12]=1.
    return objective,eq,rhs,ub,np.zeros(4),bounds
def baseline_allocations(area,q):
    equal=np.zeros((4,3));proportional=np.zeros((4,3))
    for i in range(3):
        if area[i]==0:continue
        eligible=[d for d in range(4) if q[d,i]>0]
        # Equal and proportional shares are comparator rules, not constraints of LP.
        total_capacity=sum(q[d,i] for d in eligible)
        for d in eligible:
            equal[d,i]=area[i]/len(eligible)
            proportional[d,i]=area[i]*q[d,i]/total_capacity
    return {'equal':equal,'proportional':proportional}
def check_one(a,t,T,area,q,solver_T=None):
    checks={
      'terrain_balance_error_m2':float(np.max(np.abs(a.sum(axis=0)-area))),
      'total_area_error_m2':float(abs(a.sum()-area.sum())),
      'nonnegative_error_m2':float(max(0.,-a.min())),
      'excluded_area_error_m2':float(np.max(np.abs(a[q==0]))),
      'excluded_time_error_h':float(np.max(np.abs(t[q==0]))),
      'absent_terrain_area_error_m2':float(np.max(np.abs(a[:,area==0]))) if np.any(area==0) else 0.,
      'time_definition_error_m2':float(np.max(np.abs(a-q*t))),
      'time_bound_error_h':float(max(0.,(t.sum(axis=1)-T).max())),
      'makespan_error_h':float(abs(T-t.sum(axis=1).max())),
      'solver_objective_error_h':float(abs(T-solver_T)) if solver_T is not None else 0.,
    }
    for name,value in checks.items():
        tol=1e-7 if name.endswith('_h') else 1e-5
        if value>tol:raise ValueError(f'Inconsistent new experiment result: {name}={value}')
    return checks
def structure(a,area):
    result=[]
    for i in range(3):
        if area[i]==0:result.append('absent')
        elif a[3,i]<=1e-5:result.append('none')
        elif a[3,i]>=area[i]-1e-5:result.append('all')
        else:result.append('partial')
    return '/'.join(result)

def main():
    started=time.perf_counter();start_date=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    if (OUT/'run_manifest.json').exists():raise RuntimeError('Completed result already exists; do not rerun without a new request.')
    run_id=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:12]
    source_files=sorted(p for p in PREVIOUS.rglob('*') if p.is_file())
    source_before={str(p.relative_to(PREVIOUS)):digest(p) for p in source_files}
    cfg=json.loads((HERE/'config_594.json').read_text(encoding='utf-8'))
    if cfg['scenario_count']!=594 or cfg['primary_lp_count']!=594:
        raise ValueError('This authorized run requires one direct solve for each of 594 scenarios')
    if cfg['means']!=MEANS or cfg['terrains']!=TERRAINS:
        raise ValueError('Input ordering differs from the model ordering')
    audit_path=HERE/'logs/solver_calls.jsonl'
    if audit_path.exists():raise RuntimeError('Solver audit already exists; do not repeat an attempted run automatically')
    save_json(HERE/'input_snapshot/config_594_executed.json',cfg)
    (HERE/'input_snapshot/run_experiment_executed.py').write_bytes(Path(__file__).read_bytes())
    save_json(HERE/'input_snapshot/prior_source_hashes_before.json',source_before)
    compositions=[]
    for good in range(11):
        for restricted in range(11-good):
            high=10-good-restricted
            n=len(compositions)+1
            compositions.append({'area_pattern':f'P{n:02d}','good_pct':good*10,'restricted_pct':restricted*10,'high_pct':high*10,
              'A1_m2':good*cfg['total_area_m2']/10.,'A2_m2':restricted*cfg['total_area_m2']/10.,'A3_m2':high*cfg['total_area_m2']/10.,'terrain_count':int(good>0)+int(restricted>0)+int(high>0)})
    if len(compositions)!=66:raise ValueError('Area composition enumeration mismatch')
    save_csv(OUT/'area_compositions.csv',compositions)
    options={k:v for k,v in cfg['solver'].items() if k!='method'}
    rows=[];alloc=[];primary=[];checks=[];primary_solutions=[];unitrows=[];solver_calls=[]
    solve_count=0
    for comp in compositions:
        area=np.array([comp['A1_m2'],comp['A2_m2'],comp['A3_m2']])
        for k in cfg['ugv_restricted_levels']:
            sid=f'{comp["area_pattern"]}_k{k:.1f}';q=rate_matrix(cfg,k)
            c,ae,be,au,bu,bounds=make_model(area,q)
            solve_count+=1
            call_id=f'{run_id}-{solve_count:04d}'
            call_start=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
            call_clock=time.perf_counter()
            model_record={'c':c.tolist(),'A_eq':ae.tolist(),'b_eq':be.tolist(),'A_ub':au.tolist(),
                'b_ub':bu.tolist(),'bounds':bounds,'method':cfg['solver']['method'],'options':options}
            model_sha256=hashlib.sha256(json.dumps(model_record,sort_keys=True).encode()).hexdigest()
            try:
                res=linprog(c,A_eq=ae,b_eq=be,A_ub=au,b_ub=bu,bounds=bounds,method=cfg['solver']['method'],options=options)
                audit={'run_id':run_id,'solver_call_id':call_id,'call_number':solve_count,'scenario':sid,
                  'area_pattern':comp['area_pattern'],'k':k,'started_at_Asia_Seoul':call_start,
                  'finished_at_Asia_Seoul':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                  'elapsed_seconds':time.perf_counter()-call_clock,'success':bool(res.success),'status':int(res.status),
                  'message':res.message,'objective_h':float(res.fun) if res.fun is not None else None,
                  'solver_iterations':int(res.nit),'model_sha256':model_sha256}
            except Exception as exc:
                audit={'run_id':run_id,'solver_call_id':call_id,'call_number':solve_count,'scenario':sid,
                  'area_pattern':comp['area_pattern'],'k':k,'started_at_Asia_Seoul':call_start,
                  'finished_at_Asia_Seoul':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                  'elapsed_seconds':time.perf_counter()-call_clock,'success':False,'status':'exception',
                  'message':repr(exc),'objective_h':None,'solver_iterations':None,'model_sha256':model_sha256}
                with audit_path.open('a',encoding='utf-8') as log:
                    log.write(json.dumps(audit,ensure_ascii=False,allow_nan=False)+'\n');log.flush();os.fsync(log.fileno())
                raise
            with audit_path.open('a',encoding='utf-8') as log:
                log.write(json.dumps(audit,ensure_ascii=False,allow_nan=False)+'\n');log.flush();os.fsync(log.fileno())
            solver_calls.append(audit)
            if not res.success:raise RuntimeError(f'{sid}: {res.message}')
            a=res.x[:12].reshape((4,3)).copy();times=derived_times(a,q);T=float(res.fun)
            baselines=baseline_allocations(area,q);methods={**baselines,'optimal':a}
            for method,aa in methods.items():
                tt=derived_times(aa,q);mt=float(tt.sum(axis=1).max())
                ch=check_one(aa,tt,mt,area,q,T if method=='optimal' else None)
                if T>mt+1e-7:raise ValueError(f'{sid}: optimum slower than {method}')
                checks.append({'scenario':sid,'solver_call_id':call_id,'method':method,**ch,'passed':True})
            primary_solutions.append({'scenario':sid,'solver_call_id':call_id,'area_pattern':comp['area_pattern'],'k':k,
              'raw_solver_vector':res.x.tolist(),'objective_h':T,'status':int(res.status),'message':res.message,
              'solver_iterations':int(res.nit),'linear_equality_count':4,'independent_terrain_equalities':3,'time_inequality_count':4})
            totals={m:derived_times(aa,q).sum(axis=1) for m,aa in methods.items()}
            finishes={m:float(t.max()) for m,t in totals.items()}
            row={'scenario':sid,**comp,'k':k,'solver_call_id':call_id,
              'human_q1_m2_h':float(q[0,0]),'human_q2_m2_h':float(q[0,1]),'human_q3_m2_h':float(q[0,2]),
              'ugv_q1_m2_h':float(q[3,0]),'ugv_q2_m2_h':float(q[3,1]),'ugv_q3_m2_h':0.,
              'T_equal_h':finishes['equal'],'T_proportional_h':finishes['proportional'],'T_optimal_h':T,
              'saved_equal_h':finishes['equal']-T,'saved_proportional_h':finishes['proportional']-T,
              'improvement_equal_pct':(finishes['equal']-T)/finishes['equal']*100.,
              'improvement_proportional_pct':(finishes['proportional']-T)/finishes['proportional']*100.,
              'ugv_area1_m2':float(a[3,0]),'ugv_area2_m2':float(a[3,1]),'ugv_area3_m2':float(a[3,2]),'ugv_total_m2':float(a[3].sum()),
              'ugv_limited_share_pct':float(a[3,1]/area[1]*100.) if area[1]>0 else None,
              'ugv_structure_primary':structure(a,area),'ugv_time_h':float(times[3].sum()),'ugv_slack_h':float(T-times[3].sum()),
              'bottleneck_means':';'.join(MEANS[d] for d in range(4) if abs(float(times[d].sum())-T)<=1e-7)}
            for d,mean in enumerate(MEANS):
                row[f'{mean}_total_area_m2']=float(a[d].sum());row[f'{mean}_time_h']=float(times[d].sum())
            rows.append(row)
            for method,aa in methods.items():
                tt=derived_times(aa,q);total=tt.sum(axis=1);finish=finishes[method]
                for d,mean in enumerate(MEANS):
                    unitrows.append({'scenario':sid,'area_pattern':comp['area_pattern'],'k':k,'method':method,'means':mean,
                      'good_pct':comp['good_pct'],'restricted_pct':comp['restricted_pct'],'high_pct':comp['high_pct'],
                      'area_good_m2':float(aa[d,0]),'area_restricted_m2':float(aa[d,1]),'area_high_m2':float(aa[d,2]),
                      'total_area_m2':float(aa[d].sum()),'work_time_h':float(total[d]),'completion_h':finish,'slack_h':float(finish-total[d]),
                      'workload_ratio_pct':float(total[d]/finish*100.),'is_bottleneck':bool(abs(total[d]-finish)<=1e-7)})
                    for i,terrain in enumerate(TERRAINS):
                        record={'scenario':sid,'area_pattern':comp['area_pattern'],'k':k,'method':method,'means':mean,'terrain':terrain,
                          'terrain_required_m2':float(area[i]),'capacity_m2_h':float(q[d,i]),'area_m2':float(aa[d,i]),'time_h':float(tt[d,i]),
                          'mean_total_time_h':float(total[d]),'completion_time_h':finish,'terrain_share_pct':float(aa[d,i]/area[i]*100.) if area[i]>0 else None,
                          'terrain_present':bool(area[i]>0),'permitted':bool(q[d,i]>0),'solver_call_id':call_id}
                        alloc.append(record)
                        if method=='optimal':primary.append(record)
        print(f'{comp["area_pattern"]}: {comp["good_pct"]}/{comp["restricted_pct"]}/{comp["high_pct"]} complete',flush=True)
    if len(rows)!=594 or solve_count!=594 or len(solver_calls)!=594:raise ValueError('Scenario or solve count mismatch')
    if len({a['solver_call_id'] for a in solver_calls})!=594 or len({a['scenario'] for a in solver_calls})!=594:
        raise ValueError('Solver audit must have a distinct call and scenario for every solve')
    save_csv(HERE/'logs/solver_calls.csv',solver_calls)
    marginal=[];transitions=[];plateaus=[];endpoints=[]
    for comp in compositions:
        seq=sorted([r for r in rows if r['area_pattern']==comp['area_pattern']],key=lambda x:x['k'])
        for left,right in zip(seq,seq[1:]):
            saving=left['T_optimal_h']-right['T_optimal_h']
            if saving < -1e-7:raise ValueError('Optimal completion time increased with k')
            marginal.append({'area_pattern':comp['area_pattern'],'good_pct':comp['good_pct'],'restricted_pct':comp['restricted_pct'],'high_pct':comp['high_pct'],
              'k_from':left['k'],'k_to':right['k'],'T_from_h':left['T_optimal_h'],'T_to_h':right['T_optimal_h'],'time_saved_h':saving,
              'equal_improvement_change_pp':right['improvement_equal_pct']-left['improvement_equal_pct'],
              'ugv_limited_area_change_m2':right['ugv_area2_m2']-left['ugv_area2_m2'],
              'ugv_structure_before':left['ugv_structure_primary'],'ugv_structure_after':right['ugv_structure_primary']})
            if left['ugv_structure_primary']!=right['ugv_structure_primary']:
                transitions.append({'area_pattern':comp['area_pattern'],'good_pct':comp['good_pct'],'restricted_pct':comp['restricted_pct'],'high_pct':comp['high_pct'],
                  'k_left':left['k'],'k_right':right['k'],'from_primary_structure':left['ugv_structure_primary'],'to_primary_structure':right['ugv_structure_primary'],
                  'interpretation':'Observed change in stored primary solutions; grid interval, not unique or exact threshold.'})
        start=0
        for end in range(1,len(seq)+1):
            if end==len(seq) or abs(seq[end]['T_optimal_h']-seq[start]['T_optimal_h'])>1e-7:
                if end-start>=2:
                    plateaus.append({'area_pattern':comp['area_pattern'],'good_pct':comp['good_pct'],'restricted_pct':comp['restricted_pct'],'high_pct':comp['high_pct'],
                      'k_first':seq[start]['k'],'k_last':seq[end-1]['k'],'T_h':seq[start]['T_optimal_h'],'grid_points':end-start,
                      'restricted_terrain_absent':comp['restricted_pct']==0})
                start=end
        first,last=seq[0],seq[-1]
        endpoints.append({**comp,'k01_T_h':first['T_optimal_h'],'k09_T_h':last['T_optimal_h'],'time_saved_h':first['T_optimal_h']-last['T_optimal_h'],
          'time_saved_pct':(first['T_optimal_h']-last['T_optimal_h'])/first['T_optimal_h']*100.,'k01_equal_improvement_pct':first['improvement_equal_pct'],
          'k09_equal_improvement_pct':last['improvement_equal_pct'],'k01_ugv_limited_area_m2':first['ugv_area2_m2'],'k09_ugv_limited_area_m2':last['ugv_area2_m2']})
    def extremes(key,rr):
        lo=min(r[key] for r in rr);hi=max(r[key] for r in rr)
        take=lambda r:{'scenario':r['scenario'],'good_pct':r['good_pct'],'restricted_pct':r['restricted_pct'],'high_pct':r['high_pct'],'k':r['k'],key:r[key]}
        return {'minimum':lo,'maximum':hi,'minimum_scenarios':[take(r) for r in rr if abs(r[key]-lo)<=1e-7],'maximum_scenarios':[take(r) for r in rr if abs(r[key]-hi)<=1e-7]}
    summary={'scenario_count':len(rows),'area_composition_count':len(compositions),'primary_lp_count':solve_count,'individually_solved_scenario_count':len(solver_calls),
      'terrain_group_counts':{str(n):{'compositions':sum(c['terrain_count']==n for c in compositions),'scenarios':sum(r['terrain_count']==n for r in rows)} for n in (1,2,3)},
      'extrema':{key:extremes(key,rows) for key in ['T_optimal_h','improvement_equal_pct','improvement_proportional_pct','saved_equal_h','saved_proportional_h']},
      'by_terrain_count':{str(n):{key:extremes(key,[r for r in rows if r['terrain_count']==n]) for key in ['T_optimal_h','improvement_equal_pct','improvement_proportional_pct']} for n in (1,2,3)},
      'plateau_composition_count':len(set(p['area_pattern'] for p in plateaus)),'plateau_segments':len(plateaus),'primary_structure_transition_count':len(transitions),
      'proportional_slower_than_equal_scenarios':[r['scenario'] for r in rows if r['T_proportional_h']>r['T_equal_h']+1e-7],
      'negative_equal_improvement_steps':len([r for r in marginal if r['equal_improvement_change_pp']<-1e-7]),
      'all_checks_passed':True,'max_residuals':{key:max(c[key] for c in checks) for key in checks[0] if key not in ('scenario','solver_call_id','method','passed')},
      'interpretation_notes':['Each of the 594 deterministic scenarios is solved directly once. These are designed conditions, not independent empirical observations.',
       'No p-values or probability distributions are estimated.','All allocation patterns refer to stored primary LP solutions, not uniquely necessary individual assignments.',
       'A zero-area terrain is absent, not fully allocated to the UGV. Undefined terrain-share percentages are null.',
       'Total-area equality is included explicitly but is the sum of three terrain equalities.']}
    for name,records in [('scenario_results',rows),('allocations_all_methods',alloc),('allocations_primary',primary),
       ('unit_results',unitrows),('numerical_checks',checks),('marginal_changes',marginal),('primary_structure_transitions',transitions),('plateau_segments',plateaus),('endpoint_summary',endpoints)]:save_csv(OUT/(name+'.csv'),records)
    save_json(OUT/'scenario_results.json',rows);save_json(OUT/'primary_solutions.json',primary_solutions);save_json(OUT/'summary.json',summary)
    after={str(p.relative_to(PREVIOUS)):digest(p) for p in source_files}
    if source_before!=after:raise RuntimeError('Protected prior source changed')
    save_json(OUT/'run_manifest.json',{'start_time_Asia_Seoul':start_date,'elapsed_seconds':time.perf_counter()-started,'python':sys.version,'executable':sys.executable,
      'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,'existing_dependency_directory':str(DEPENDENCIES),
      'command':f'"{sys.executable}" -B "{HERE / "run_experiment.py"}"','solver_method':cfg['solver']['method'],'scenario_count':594,'primary_lp_count':594,
      'run_id':run_id,'individually_solved_scenario_count':len(solver_calls),'unique_solver_call_id_count':len({a['solver_call_id'] for a in solver_calls}),
      'successful_solver_call_count':sum(a['success'] for a in solver_calls),'audit_jsonl':str(audit_path),'audit_sha256':digest(audit_path),
      'input_config':str(HERE/'config_594.json'),'prior_source_directory':str(PREVIOUS),
      'comparison_methods':METHODS,'alternative_optimum_lp_count':0,'independent_revalidation_lp_count':0,'source_hashes_before':source_before,'source_hashes_after':after,
      'prior_files_unchanged':True,'code_sha256':digest(Path(__file__)),'config_sha256':digest(HERE/'config_594.json'),'all_checks_passed':True})
    save_json(HERE/'input_snapshot/config_594_executed.json',cfg)
    (HERE/'input_snapshot/run_experiment_executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'scenario_count':594,'primary_lp_count':594,'all_checks_passed':True,
      'equal_improvement_range':[summary['extrema']['improvement_equal_pct']['minimum'],summary['extrema']['improvement_equal_pct']['maximum']],
      'proportional_improvement_range':[summary['extrema']['improvement_proportional_pct']['minimum'],summary['extrema']['improvement_proportional_pct']['maximum']]},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
