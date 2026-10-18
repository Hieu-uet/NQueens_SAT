"""Validate and summarize the main_v1 ZIP using Python's standard library.

Usage: python analyze_results.py INPUT.zip --output analysis_output
Raw observations are never modified. Warm-ups and license skips are excluded
from timings. Missing timings stay blank, including censored solve timeouts.
Quartiles use linear interpolation at (n-1)*p (Hyndman-Fan type 7).
"""

import argparse
import csv
import hashlib
import io
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile

METHODS = ('pairwise','seqcounter','bitwise','cp_sat','gurobi_mip','cplex_mip','cplex_cp')
SIZES = (8,16,24,31,32,64,128)
PHASES = ('build_s','init_s','solve_s','post_s')
TIMES = (*PHASES,'total_s','setup_watch_s','solve_watch_s','process_wall_s')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quantile(values, p):
    values=sorted(values)
    position=(len(values)-1)*p
    lo=math.floor(position)
    hi=math.ceil(position)
    return values[lo]+(values[hi]-values[lo])*(position-lo)


def valid_queens(n, queens):
    if not isinstance(queens,list) or len(queens)!=n:
        return False
    if any(not isinstance(q,list) or len(q)!=2 or
           any(type(x) is not int or not 0<=x<n for x in q) for q in queens):
        return False
    return all(len({key(r,c) for r,c in queens})==n for key in (
        lambda r,c:r,lambda r,c:c,lambda r,c:r-c,lambda r,c:r+c))


def load_and_validate(path):
    with ZipFile(path) as archive:
        require(archive.testzip() is None, 'ZIP CRC failure')
        require(len(archive.namelist())==len(set(archive.namelist())), 'Duplicate ZIP members')
        def member(name):
            matches=[x for x in archive.namelist() if x.endswith('/'+name)]
            require(len(matches)==1, f'Expected one {name}')
            return archive.read(matches[0])
        raw={name:member(name) for name in ('measurements.csv','warmup.csv','manifest.json')}
    manifest=json.loads(raw['manifest.json'])
    rows=list(csv.DictReader(io.StringIO(raw['measurements.csv'].decode('utf-8-sig'))))
    warm=list(csv.DictReader(io.StringIO(raw['warmup.csv'].decode('utf-8-sig'))))
    cfg=manifest['configuration']
    require(manifest['state']=='completed','Batch is incomplete')
    require(manifest['experiment_version']==1 and manifest['supervisor_version']==4,'Unexpected protocol')
    require(cfg['group']=='all' and cfg['repeats']==5,'Unexpected schedule')
    require(cfg['solve_limit_s']==30 and cfg['setup_limit_s']==120 and cfg['finalize_limit_s']==30,'Unexpected budgets')
    require(len(rows)==245 and len(warm)==7,'Unexpected number of rows')
    require(manifest['written_measurement_rows']==len(rows) and manifest['written_warmup_rows']==len(warm),'Manifest row mismatch')
    schedule=[]
    rng=random.Random(cfg['order_seed'])
    for n in SIZES:
        for repeat in range(1,6):
            order=list(METHODS)
            rng.shuffle(order)
            for method in order:
                schedule.append({'n':n,'method':method,'repeat':repeat,
                                 'group':'common' if n<32 else 'large',
                                 'run_order':len(schedule)+1})
    require(manifest['schedule']==schedule,'Manifest schedule differs from seeded order')
    for actual,expected in zip(rows,schedule):
        require(all(str(expected[k])==actual[k] for k in expected),'CSV schedule mismatch')
    warm_methods=list(METHODS)
    random.Random(cfg['order_seed']+1).shuffle(warm_methods)
    require([r['method'] for r in warm]==warm_methods,'Warm-up order mismatch')
    phase_residuals=[]
    checked=0
    groups=defaultdict(list)
    for row in rows+warm:
        n=int(row['n']);method=row['method'];status=row['status']
        where=f"{row['run_kind']} n={n} method={method} repeat={row['repeat']}"
        require(row['run_id']==manifest['run_id'],'Run ID mismatch')
        require(row['experiment_version']=='1' and row['benchmark_version']=='4','Row protocol mismatch')
        for key in ('solve_limit_s','setup_limit_s','finalize_limit_s'):
            require(float(row[key])==cfg[key],f'Budget mismatch: {where}')
        require(row['solver_workers']=='1','Worker count mismatch')
        require(row['solver_seed']==('' if method in METHODS[:3] else '0'),'Solver seed mismatch')
        require(row['order_seed']==str(cfg['order_seed']),'Order seed mismatch')
        require(row['warmup_runs_per_method']=='1' and row['warmup_n']=='16','Warm-up metadata mismatch')
        for key,value in manifest['environment'].items():
            require(row[key]==str(value),f'Environment mismatch: {key}')
        for key in TIMES:
            if row[key]!='':
                require(math.isfinite(float(row[key])) and float(row[key])>=0,f'Invalid time: {where} {key}')
        expected_skip=(method=='cplex_mip' and n*n>1000) or (method=='gurobi_mip' and n*n>2000)
        if expected_skip:
            require(status=='LICENSE_LIMIT' and row['attempted']=='False' and row['reason']=='license_limit_policy','Invalid policy skip')
            require(all(row[k]=='' for k in (*TIMES,'queens','model_vars','linear_constraints','valid','error')),'Skip contains measured result')
            require(int(row['expected_mip_vars'])==n*n,'Expected MIP variable mismatch')
        else:
            require(row['attempted']=='True','Attempt flag mismatch')
            require(row['timeout_mode']=='parent_process_tree' and row['process_scope']=='windows_job','Process containment mismatch')
            require(row['error']=='',f'Unexpected runtime error: {where}')
            require(float(row['setup_watch_s'])<=120,'Setup budget exceeded')
            if status=='SAT':
                require(row['valid']=='True' and valid_queens(n,json.loads(row['queens'])),f'Invalid witness: {where}')
                checked+=1
                require(row['reason']=='','SAT has unexpected reason')
                require(all(row[k]!='' for k in (*PHASES,'total_s')),'Missing completed time')
                residual=float(row['total_s'])-sum(float(row[k]) for k in PHASES)
                phase_residuals.append(abs(residual))
                require(abs(residual)<1e-8,'Phase-sum mismatch')
                require(float(row['process_wall_s'])>=float(row['total_s']),'Process wall below measured total')
                require(float(row['solve_watch_s'])>=float(row['solve_s']),'Solve watch below API time')
                require(float(row['solve_watch_s'])<=30,'Completed solve after budget')
            elif status=='UNKNOWN':
                require(row['reason']=='solve_timeout' and row['solver_status']=='PROCESS_TIMEOUT','Non-solve timeout')
                require(all(row[k]=='' for k in ('solve_s','post_s','total_s','queens','valid')),'Timeout contains invented result')
                require(float(row['solve_watch_s'])>=30,'Timeout before budget')
            else:
                raise ValueError(f'Unexpected status {status}: {where}')
            if method in ('cplex_mip','gurobi_mip'):
                require(int(row['model_vars'])==n*n and int(row['linear_constraints'])==6*n-6,'MIP counts mismatch')
                require(row['cnf_clauses']==row['global_constraints']=='','Mixed constraint units')
            elif method in ('cp_sat','cplex_cp'):
                require(int(row['model_vars'])==n and row['global_constraints']=='3','CP counts mismatch')
                require(row['cnf_clauses']==row['linear_constraints']=='','Mixed constraint units')
            else:
                require(int(row['model_vars'])>=n*n and int(row['cnf_clauses'])>0,'SAT counts invalid')
                if method=='pairwise':
                    require(int(row['model_vars'])==n*n and int(row['cnf_clauses'])==(5*n**3-6*n*n+7*n)//3,'Pairwise CNF counts mismatch')
        if row['run_kind']=='main':
            groups[n,method].append(row)
        else:
            require(row['run_kind']=='warmup' and row['group']=='warmup' and n==16 and row['repeat']=='0' and status=='SAT','Invalid warm-up')
    require(len(groups)==49 and all(len(v)==5 for v in groups.values()),'Incomplete groups')
    counts=dict(Counter(r['status'] for r in rows))
    require(counts==manifest['measurement_status_counts'],'Status totals mismatch')
    attempted=sum(r['attempted']=='True' for r in rows)
    require(attempted==manifest['attempted_measurement_rows']==manifest['planned_solver_calls'],'Attempt total mismatch')
    require(dict(Counter(r['status'] for r in warm))==manifest['warmup_status_counts'],'Warm-up totals mismatch')
    return manifest,rows,warm,groups,{
        'archive_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'member_sha256':{name:hashlib.sha256(value).hexdigest() for name,value in raw.items()},
        'measurement_rows':len(rows),'attempted_rows':attempted,'status_counts':counts,
        'warmup_rows':len(warm),'independently_valid_witnesses':checked,
        'max_phase_sum_residual_s':max(phase_residuals),
        'timeout_watch_range_s':[min(float(r['solve_watch_s']) for r in rows if r['status']=='UNKNOWN'),max(float(r['solve_watch_s']) for r in rows if r['status']=='UNKNOWN')],
    }


def summarize(groups):
    output=[]
    for n in SIZES:
        for method in METHODS:
            rows=groups[n,method]
            solved=[r for r in rows if r['status']=='SAT']
            stats={'n':n,'method':method,'planned':len(rows),
                   'attempted':sum(r['attempted']=='True' for r in rows),
                   'sat':len(solved),'solve_timeout':sum(r['reason']=='solve_timeout' for r in rows),
                   'license_limit':sum(r['status']=='LICENSE_LIMIT' for r in rows)}
            for key in ('model_vars','cnf_clauses','linear_constraints','global_constraints'):
                values={r[key] for r in rows if r[key]!=''}
                require(len(values)<=1,f'Model size varies across repeats: n={n}, method={method}')
                stats[key]=int(values.pop()) if values else None
            for key in TIMES:
                values=[float(r[key]) for r in solved if r[key]!='']
                for metric,value in (('median',median(values) if values else None),
                                     ('min',min(values) if values else None),
                                     ('max',max(values) if values else None),
                                     ('q1',quantile(values,.25) if values else None),
                                     ('q3',quantile(values,.75) if values else None),
                                     ('mean',mean(values) if values else None)):
                    stats[f'{key}_{metric}']=value
            overhead=[(float(r['build_s'])+float(r['init_s']))/float(r['total_s']) for r in solved]
            stats['build_plus_init_fraction_median']=median(overhead) if overhead else None
            output.append(stats)
    return output


def analyze(path,output):
    manifest,rows,warm,groups,validation=load_and_validate(path)
    summary=summarize(groups)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    package={'source_filename':Path(path).name,'manifest':manifest,
             'validation':validation,'summary':summary,
             'statistical_convention':'Five repetitions of the same N and seed; descriptive statistics, not independent puzzle instances. Quartiles: linear interpolation (type 7). Timings in seconds.'}
    (output/'analysis.json').write_text(json.dumps(package,ensure_ascii=False,indent=2),encoding='utf-8')
    with (output/'summary.csv').open('w',newline='',encoding='utf-8-sig') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    print(json.dumps(validation,ensure_ascii=False,indent=2))
    return package,rows,warm


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,default=Path('analysis_output'))
    args=parser.parse_args()
    analyze(args.archive,args.output)
