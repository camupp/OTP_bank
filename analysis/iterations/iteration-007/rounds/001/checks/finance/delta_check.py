"""Independent current-version financial check; no candidate/sealed model execution.

Reuses hash-verified cash/cohort controls because money policy is unchanged.
Rechecks changed authority/reserves, small allocation tables and all new resources.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
from datetime import datetime
import csv, json, hashlib, importlib.util, math, sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RD = HERE.parents[1]
RUN = RD.parents[1]
ROOT = RUN.parents[2]
ARCH = RD / 'private/pre-rework'
FIX = RD / 'supporting/fixtures'
PATHS = {f'CON-{n:03d}@v2': RD / f'branches/{"A" if n < 20 else "B"}/con-{n:03d}' for n in range(18,22)}
checks=[]

def read(p): return json.loads(p.read_text())
def rows(p): return list(csv.DictReader(p.open()))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def truth(v): return v is True or v == 'True'
def ck(name, value, detail=None):
    r={'name':name,'pass':bool(value)}
    if detail is not None:r['detail']=detail
    checks.append(r)
def near(a,b): return abs(float(a)-float(b))<1e-6
def save(name,v): (HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def table(name,rr):
    fields=list(dict.fromkeys(k for r in rr for k in r))
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rr)
def policy(d):
    x={k:json.loads(json.dumps(d[k])) for k in ['N_eligible','scenario_parameters','guarantee','contests','special','stacking','calendar','dated_prefunding','no_self_award_controls']}
    for k in ['qualification','part_time','nonqualification','newcomer']:x['guarantee'].pop(k)
    x['contests'].pop('ranking');x['calendar'].pop('source')
    return x

pins=read(RD/'private/versions-before-checks.json')['files']
bad=[p for p,s in pins.items() if sha(RD/p)!=s]
ck('current finished-version pins',not bad,bad)
archive=read(ARCH/'archive.json')['files']
reused_names=['verification.json','core-reconciliation.csv','calendar-reconciliation.csv','base-source-controls.csv','budget-comparable.csv']
for name in reused_names:
    rel='checks/finance/'+name
    ck('unchanged archived proof '+name,sha(ARCH/rel)==archive[rel])
prior=read(ARCH/'checks/finance/verification.json')
ck('cash/core proof complete',prior['all_arithmetic_checks_pass'] and prior['checks']==2904)
parent=read(RUN/'incumbent/finance-spec.json')
for key,p in PATHS.items():ck(key+' unchanged numeric reward policy',policy(read(p/'finance-spec.json'))==policy(parent))
ck('A repaired authority and unchanged arithmetic proved',read(HERE/'delta-A.json')['all_pass'])

# Source-only expansion is data access; no author scoring function imported.
sp=importlib.util.spec_from_file_location('public_source_only_reader',FIX/'source/reader.py')
reader=importlib.util.module_from_spec(sp);sp.loader.exec_module(reader)
names=['base']+[x['scenario_id']+'.'+v for x in read(FIX/'source/scenario_index.json') for v in x['variants']]
source={n:reader.expand_scenario(n) for n in names}

def authority(data,r,is_A):
    period=r.get('period',r.get('period_id'));person=r.get('subject',r.get('subject_id'));unit=r.get('unit',r.get('unit_id'))
    members={m['employee_id'] for m in data['team_members'] if m['period_id']==period and m['team_id']==unit}
    forbidden=members|{person,unit}
    aa=[a for a in data['approvals_audit'] if a['period_id']==period and a['beneficiary_id']==person and a.get('action')=='input_correction_and_posting_review']
    if not aa:return False
    a=max(aa,key=lambda z:(z.get('version',0),z.get('signed_at') or '',z['approval_id']))
    fields=['input_editor_id','signer_id','operator_id']+(['appeal_owner_id'] if is_A else [])
    if any(not isinstance(a.get(k),str) or not a[k].strip() or a[k] in forbidden for k in fields):return False
    if any(v in forbidden for k,v in a.items() if k.endswith('_reporting_to') and isinstance(v,str)):return False
    if any(t in forbidden for k,v in a.items() if k.endswith('_reporting_to') and isinstance(v,list) for t in v):return False
    if not isinstance(a.get('signed_at'),str) or not a['signed_at'].strip():return False
    if a['signer_id']==a['operator_id']:return False
    if not is_A:
        try:datetime.fromisoformat(a['signed_at'])
        except (TypeError,ValueError):return False
        if len({a[k] for k in fields})!=3:return False
        if a.get('source_ref')!=period+':'+person:return False
        if members and a.get('beneficiary_team') not in (None,unit):return False
    return True

allocation=[];auth_rows=[]
for key,p in PATHS.items():
    ds=rows(p/'decisions.csv');is_A=key.startswith(('CON-018','CON-019'))
    ck(key+' 23 source sets',len({r['scenario'] for r in ds})==23 and len(ds)==368)
    if is_A:
        old=ARCH/p.relative_to(RD)
        norm=lambda rr:[{k:v for k,v in r.items() if k not in ('candidate_key','rule_version')} for r in rr]
        ck(key+' allocation payload unchanged',norm(ds)==norm(rows(old/'decisions.csv')))
        ck(key+' money payload unchanged',norm(rows(p/'money-examples.csv'))==norm(rows(old/'money-examples.csv')))
        mm={(r['scenario'],r['period_id'],r['subject_id']):r for r in rows(p/'money-examples.csv')}
        for r in ds:
            good=authority(source[r['scenario']],r,True)
            ck(key+'/'+r['scenario']+'/'+r['period_id']+'/'+r['subject_id']+' actual authority',good==(r['signoff_status']=='signed'))
            m=mm[r['scenario'],r['period_id'],r['subject_id']]
            want=float(r['top_R']) if good and truth(r['normal']) and not truth(r['top_pending']) else 0
            ck(key+' top sanctioned U',near(m['approved_top_U_R'],want))
        initial=rows(ARCH/'checks/finance/allocation-controls.csv')
        for r in initial:
            if r['candidate_key']==key.replace('@v2','@v1'):
                allocation.append({**r,'candidate_key':key,'calculated_vs_authorized':'calculated; U separately independently verified'})
        continue
    us=rows(p/'unit-decisions.csv');groups=defaultdict(list)
    for r in us:groups[r['scenario'],r['period'],r['group']].append(r)
    for (scenario,period,group),units in groups.items():
        people=[r for r in ds if (r['scenario'],r['period'],r['group'])==(scenario,period,group)]
        pool=150*len({r['subject'] for r in people})
        held=any(r['state'] in ('pending','not_computable') or r['stretch_state']=='pending' for r in units)
        qualified=[r for r in units if truth(r['stretch'])]
        kval={r['subject']:tuple(F(x) for x in json.loads(r['rank_key'])) for r in qualified}
        expected={};pos=0
        if len(units)>=2:
            for val in sorted(set(kval.values()),reverse=True):
                tied=[u for u in kval if kval[u]==val]
                amount=F(pool)*sum([F(4,10),F(3,10),F(2,10),F(1,10)][pos:pos+len(tied)])/len(tied)
                expected.update({u:amount for u in tied});pos+=len(tied)
        for r in people:
            good=authority(source[scenario],r,False)
            ck(key+'/'+scenario+'/'+period+'/'+r['subject']+' actual authority',good==(r['authorization']=='authorized'))
            potential=math.floor(expected.get(r['unit'],0)*F(r['share'])) if not held and truth(r['calculated_normal']) else 0
            approved=potential if good and r['calculated_qualification_state']=='earned' else 0
            ck(key+' computed and sanctioned top',near(potential,r['potential_top_R']) and near(approved,r['top_U_R']) and near(approved,r['top_R']))
            ck(key+' held share conserved',near(r['top_reserved_R'],potential-approved))
            auth_rows.append({'candidate_key':key,'scenario':scenario,'period':period,'subject':r['subject'],
                              'source_authorized':good,'potential_top_R':potential,'sanctioned_U_R':approved,'held_personal_R':potential-approved})
        paid=sum(float(r['top_U_R']) for r in people)
        reserved=pool if held else sum(float(r['top_reserved_R']) for r in people)
        ck(key+' group fund conservation',paid+reserved<=pool+1e-6)
        allocation.append(dict(candidate_key=key,scenario=scenario,period=period,group=group,unique_people=len({r['subject'] for r in people}),
                               pool_R=pool,declared_calculated_R=sum(float(r['potential_top_R']) for r in people),
                               group_held=held,calculated_vs_authorized='potential and sanctioned U distinct',authorized_U_R=paid,held_group_R=reserved))
    for r in rows(p/'window-guarantee.csv'):
        ps=[x for x in ds if (x['scenario'],x['subject'],x['window_id'])==(r['scenario'],r['subject'],r['window_id'])]
        calc=2500 if len(ps)==2 and all(truth(x['calculated_normal']) for x in ps) else 0
        earned=2500 if len(ps)==2 and all(x['state']=='earned' and authority(source[r['scenario']],x,False) for x in ps) else 0
        ck(key+' one computed and sanctioned G/window',near(r['calculated_G_R'],calc) and near(r['authorized_U_R'],earned) and near(r['guarantee_R'],earned))
        ck(key+' guarantee pending preserved',near(r['reserved_max_R'],2500 if r['state'] in ('pending','not_computable') else 0))
table('allocation-controls.csv',allocation);table('authorization-controls.csv',auth_rows)

# Keep raw task-class units diagnostic for projects: no root norm was supplied.
# Do not display task/hour arithmetic as a computable project reward Q.
base_rows=rows(ARCH/'checks/finance/base-source-controls.csv')
for r in base_rows:
    if r['subject'].startswith('T'):
        r['diagnostic_task_class_units']=r['accepted_standard_units']
        r['accepted_standard_units']=''
        r['capacity_ratio']=''
        r['metric_interpretation']='Project root norm absent; task-class units are diagnostic only'
    else:
        r['diagnostic_task_class_units']=''
        r['metric_interpretation']='Flow accepted standard units / independently allocated hours'
table('base-source-controls.csv',base_rows)

# Revised resource algebra, with same case/part QA and shared SKU delta explicit.
rate={'HR':1000,'manager':1500,'employee':1000,'IT':2000}
existing=48720*3/60;gap=48720*5/60
profiles={
 'CON-018@v2':{'HR':88,'manager':442.26666666666665,'employee':113.6,'IT':15},
 'CON-019@v2':{'HR':88,'manager':431.6,'employee':113.6,'IT':15},
 'CON-020@v2':{'HR':72+16+6,'manager':244.26666666666668+36+6,'employee':20+10+3.6,'IT':24},
 'CON-021@v2':{'HR':72+16+6,'manager':244.26666666666668+36+6+160,'employee':20+10+3.6,'IT':24},
 'CON-016@v2':{'HR':64+20,'manager':106.26666666666665+60,'employee':113.6,'IT':15}}
resource=[]
for key,role in profiles.items():
    for reuse in (0,.5,1):
        for mult in (1,2):
            required=gap if key!='CON-016@v2' else (800*20+800*20+160*4.5)*5/60
            missing=required*(1-reuse)
            recognition=sum(role[k]*rate[k] for k in role)*12
            new=(recognition+missing*1500*12)*mult
            resource.append(dict(candidate_key=key,QA_compatible_reuse=reuse,labor_multiplier=mult,
                HR_recognition_h_month=role['HR']*mult,manager_recognition_h_month=role['manager']*mult,
                employee_process_h_month=role['employee']*mult,IT_h_month=role['IT']*mult,
                new_QA_h_month=missing*mult,existing_QA_h_month_separate=existing*mult,
                existing_QA_resource_RUB_year=existing*1500*12*mult,
                new_recognition_plus_QA_RUB_year=new,shared_extra_SKU500_HR_h_year=96*mult,
                shared_extra_SKU500_resource_RUB_year=96000*mult,
                full_comparable_new_including_SKU_RUB_year=new+96000*mult,
                substitution25pct_cash_RUB_year=(new+96000*mult)*.25,
                full_existing_plus_new_including_SKU_RUB_year=existing*1500*12*mult+new+96000*mult,
                scope_note='All resource assumptions; no actual staffing/admission. Common M05 old/fixed shop and useful production separate.'))
for key in ('CON-020@v2','CON-021@v2'):
    p=PATHS[key]
    for r in rows(p/'resource.csv'):
        reuse=float(r['QA_reuse_share']);rr=next(x for x in resource if x['candidate_key']==key and x['QA_compatible_reuse']==reuse and x['labor_multiplier']==1)
        ck(key+' QA required case-inspection count',near(r['new_missing_QA_h_month'],gap*(1-reuse)) and near(r['existing_business_QA_h_month'],existing))
        ck(key+' revised regular resource',near(r['new_resource_RUB_year'],rr['new_recognition_plus_QA_RUB_year']))
        ck(key+' corrected labor x2 and25pct cash',near(r['new_resource_x2_RUB_year'],float(r['new_resource_RUB_year'])*2) and near(r['replacement25pct_new_cash_RUB_year'],float(r['new_resource_RUB_year'])*.25))
    s=read(p/'finance-spec.json')['workload']['special_and_appeal_counters']
    ck(key+' special explicit hours',near((200*4+32*5)/60,16) and near((200*10+32*5)/60,36) and near(200*6/60,20) and s['special_resource_RUB_year']==1080000)
    ck(key+' appeal and correction no duplicate',near(120*5/60,10) and s['appeal_HR12h_owner24h_already_in_base_exceptions'] and
       near(72*5/60,6) and near(72*3/60,3.6))
table('resources-comparable.csv',resource)

# Reuse cash/source calendar rows; change recognition hours only, month by month.
old_timed=rows(ARCH/'checks/finance/time-correct-HR.csv');timed=[]
cal={(int(r['E_R_year']),int(r['month'])):r for r in rows(HERE/'calendar-reconciliation.csv')}
for r in old_timed:
    key=r['candidate_key'].replace('@v1','@v2');E=int(r['E_R_year']);m=int(r['month']);c=cal[E,m]
    if key in ('CON-020@v2','CON-021@v2'):
        recognition=62+float(c['ordinary_records'])*.15/60+float(c['guarantee_persons'])*.1/60+16+6+(16*5/60 if E==36000000 else 0)
    elif key=='CON-016@v2': recognition=64+20 # consistent180-group source mix
    else: recognition=float(r['recognition_HR_h'])
    total=float(r['fixed_old_shop_HR_h'])+float(r['new_R_certificate500_HR_h'])+recognition
    timed.append({**r,'candidate_key':key,'recognition_HR_h':recognition,'total_HR_h':total,'capacity220_pass':total<=220,
                  'boundary':'Current declared complete recognition; common180groups; same month; newR mixed handling replaced once by certificate500 orders; no actual bank capacity claim'})
table('time-correct-HR.csv',timed)
peaks=[]
for key in profiles:
    for scenario in ('EXPECTED','FULL_NEW','JAN_OLD50','REGION80'):
        rr=[r for r in timed if r['candidate_key']==key and r['E_R_year']=='24000000' and r['fixed_C_year']=='96000000' and r['scenario']==scenario]
        if not rr:continue
        peak=max(rr,key=lambda r:float(r['total_HR_h']))
        peaks.append({k:peak[k] for k in ['candidate_key','E_R_year','scenario','fixed_C_year','month','total_HR_h','capacity220_pass']})
table('HR-peaks.csv',peaks)
for key in ('CON-020@v2','CON-021@v2'):
    for scenario,want,month in [('EXPECTED',234.7111111111111,'10'),('FULL_NEW',251.77777777777777,'10'),('JAN_OLD50',322.74666666666667,'13')]:
        r=next(x for x in peaks if x['candidate_key']==key and x['scenario']==scenario)
        ck(key+' exact peak '+scenario,near(r['total_HR_h'],want) and r['month']==month and not r['capacity220_pass'])

# Current key labels for unchanged cash budgets; no big model recomputation.
budget=[{**r,'candidate_key':r['candidate_key'].replace('@v1','@v2')} for r in rows(ARCH/'checks/finance/budget-comparable.csv')]
table('budget-comparable.csv',budget)
verification={'current_candidate_keys':list(PATHS)+['CON-016@v2','BASELINE'],'method':'Independent read-only source/CSV arithmetic. No candidate or sealed models executed. Cash/core/cohort proofs reused only after unchanged numeric policy and hashes. Current authorization/reserves, allocation and resource/capacity recomputed.',
 'checks':len(checks),'failures':[r for r in checks if not r['pass']],'all_arithmetic_checks_pass':all(r['pass'] for r in checks),
 'cash_core_controls_reused':{'balance_rows':13392,'cohort_rows':78,'all_pass':True},'checks_detail':checks,
 'scope':'Scenario procurement admission only; no real-bank capacity/catalog/data admission; declared metric levels outside source base require separate evidence check.'}
save('verification.json',verification)
save('delta-verification.json',{'all_pass':verification['all_arithmetic_checks_pass'],'current_pin_mismatches':bad,'scope':'Current repair only; prior proofs retained by hashes; final resource and authorizations now current-version data','checks':checks})
save('source-manifest.json',{'current_pins_sha256':sha(RD/'private/versions-before-checks.json'),'archived_initial_verification_sha256':sha(ARCH/'checks/finance/verification.json'),
 'source_base_sha256':sha(FIX/'source/base.json'),'candidate_specs':{key:sha(p/'finance-spec.json') for key,p in PATHS.items()},
 'current_artifact_hashes':{n:sha(HERE/n) for n in ['allocation-controls.csv','authorization-controls.csv','resources-comparable.csv','time-correct-HR.csv','HR-peaks.csv','budget-comparable.csv','verification.json']}})
print(json.dumps({'checks':len(checks),'failures':verification['failures'][:20],'all_pass':verification['all_arithmetic_checks_pass']},ensure_ascii=False))
