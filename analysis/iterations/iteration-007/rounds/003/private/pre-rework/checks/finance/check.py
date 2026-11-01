"""Round003 independent financial delta. Writes only this round's finance area.

Retains the independent002 tables after SHA checks; recalculates only changed
booking and category allocation. Never imports/runs any author or closed code.
Run with PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/check.py.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
import csv,hashlib,itertools,json,math,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; RD=HERE.parents[1]; PREV=RD.parent/'002'
ROOT=next(p for p in HERE.parents if (p/'project/brief.md').exists())
A=RD/'branches/A/con-024'; B=RD/'branches/B/con-025'; INC=RD/'supporting/previous-best'
OLD=PREV/'checks/finance'; RATES={'HR':1000,'owner_QA':1500,'employee':1000,'IT':2000}
KEY=['scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role']
CHECKS=[]; MANIFEST={}
def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def record(p):MANIFEST[str(p.relative_to(ROOT))]=sha(p)
def ck(name,ok,detail=None):CHECKS.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail is not None else {})})
def near(a,b):return abs(float(F(str(a)))-float(F(str(b))))<1e-5
def truth(v):return v is True or v=='True'
def table(name,rr):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rr for k in r)));w.writeheader();w.writerows(rr)
def dump(name,v):(HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def rid(r):return tuple(str(r[k]) for k in KEY)+(str(r['month']),)

# New round, same source. SHA establishes applicability of our earlier equations.
pins=read(RD/'private/versions-before-checks.json')['files'];record(RD/'private/versions-before-checks.json')
ck('current frozen files',all(sha(RD/p)==h for p,h in pins.items()))
for name in ['context.md','evidence.md','diagnosis.md','baseline.md','rubric.json']:
    p=RD/'inputs'/name;record(p);ck('unchanged input '+name,sha(p)==sha(PREV/'inputs'/name))
for rel in ['resource-menu.json','round002-common-assumptions.md','measurement-contract.md','finance-basis/scenario-inputs.json','finance-basis/annual-three-year.csv','fixtures/manifest.json','round002-stress/manifest.json','round002-stress/business-config.json']:
    p=RD/'supporting'/rel;record(p);ck('same common '+rel,sha(p)==sha(PREV/'supporting'/rel))
record(RD/'supporting/qa-neighborhood-recipe.json')
ck('prospective QA recipe',sha(RD/'supporting/qa-neighborhood-recipe.json')=='b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12')
ck('own inherited finance proof',read(OLD/'verification.json')['all_arithmetic_checks_pass'] and read(OLD/'delta-verification.json')['all_pass'])
for name in ['verification.json','delta-verification.json','monthly-resource.csv','annual-resource.csv','setup.csv','all-role-totals.csv','core-reconciliation.csv','calendar.csv','budget.csv','baseline-resource.csv','employee-paths.csv']:
    record(OLD/name)
for r in rows(OLD/'core-reconciliation.csv'):
    ck('original core verified file '+r['file'],sha(ROOT/r['file'])==r['sha256'])
for name in ['core-reconciliation.csv','calendar.csv','budget.csv','baseline-resource.csv','employee-paths.csv']:
    text=(OLD/name).read_text().replace('CON-022@v1','CON-024@v1')
    (HERE/name).write_text(text)
for p in INC.iterdir():
    old=PREV/'branches/B/con-023'/p.name
    if p.is_file() and old.exists():record(p);ck('unchanged CON-023@v2 '+p.name,sha(p)==sha(old))

# A has zero operational delta; no canceled U/qualifications reduce the ceiling.
for name,d in read(A/'resource-reference.json')['files'].items():
    p=ROOT/d['project_path'];record(p);ck('A resource identity '+name,sha(p)==d['sha256'])
for name in ['resource-stages.csv','setup-resource.csv','resource-supply.json']:
    if name.endswith('.csv'):
        norm=lambda pp:[{k:v for k,v in r.items() if k not in ('candidate_key','candidate')} for r in rows(pp)]
        ck('A local zero delta '+name,norm(A/name)==norm(PREV/'branches/A/con-022'/name))
    else:ck('A local zero delta '+name,(A/name).read_text()==(PREV/'branches/A/con-022'/name).read_text())
aspec=read(A/'finance-spec.json');apar=read(PREV/'branches/A/con-022/finance-spec.json')
for k in ['N_eligible','scenario_parameters','guarantee','special','stacking','calendar','dated_prefunding','no_self_award_controls','finance_handoff']:
    ck('A reward core '+k,aspec[k]==apar[k])
for k,v in apar['workload'].items():
    if k!='inputs':ck('A unchanged workload '+k,aspec['workload'].get(k)==v)

# B changes booking only. All actual work, norms, ceilings and setup stay fixed.
bs=read(B/'finance-spec.json');ips=read(INC/'finance-spec.json')
for k,v in ips.items():
    if k not in ['candidate_key','booking','calendar']:ck('B unchanged finance '+k,bs[k]==v)
ck('B unchanged menu', {k:v for k,v in bs['booking'].items() if k!='calendar_policy'}==ips['booking'])
for name in ['resource-stages.csv','setup-resource.csv']:
    ck('B unchanged '+name,(B/name).read_text().replace('CON-025@v1','CON-023@v2')==(INC/name).read_text())
for p in [A/'finance-spec.json',A/'metrics-spec.json',B/'finance-spec.json',B/'metrics-spec.json',A/'resource-reference.json']:record(p)

oldrows=rows(OLD/'monthly-resource.csv')
base=[{**r,'candidate_key':'CON-024@v1' if r['candidate_key']=='CON-022@v1' else r['candidate_key']} for r in oldrows if r['candidate_key'] in ('CON-022@v1','CON-023@v2')]
inc=[r for r in base if r['candidate_key']=='CON-023@v2']; groups=defaultdict(list)
for r in inc:groups[tuple(r[k] for k in KEY)].append(r)
new=[];delta=[];maxdelta=defaultdict(float)
author={rid(r):r for r in rows(B/'monthly-resource.csv')}; supply={rid(r):r for r in rows(B/'resource-supply.csv')}
for key,rr in groups.items():
    rr.sort(key=lambda r:int(r['month']));ck('complete forecast '+str(key),[int(r['month']) for r in rr]==list(range(1,40)))
    role=key[-1];rate=RATES[role];capblocks=max(int(float(r['booked_h']))//20 for r in rr);q=0
    for r in rr:
        m=int(r['month']);demand=float(r['demand_h']);baseh=float(r['base_h']);previous=q
        # Least whole blocks sufficient for the full predeclared calendar demand
        # and planned queue; bounded by the same original finite scenario pool.
        shortfall=max(0,demand+previous-baseh)
        blocks=min(capblocks,math.ceil(shortfall/20-1e-10));booked=blocks*20;cap=baseh+booked
        used=min(booked,max(0,demand-baseh));idle=booked-used;q=max(0,previous+demand-cap)
        v={**r,'candidate_key':'CON-025@v1','booked_h':booked,'reserve_used_h':used,'paid_idle_h':idle,'capacity_h':cap,'current_excess_h':max(0,demand-cap),'queue_start_h':previous,'queue_end_h':q,'paid_idle_RUB':idle*rate,'full_resource_RUB':float(r['actual_work_RUB'])+idle*rate,'booking_cash_RUB':booked*rate,'new_cash_RUB':booked*rate+float(r['substitution_cash_RUB']),'capacity_pass':demand<=cap+1e-8}
        a=author[rid(r)];s=supply[rid(r)]
        fields={'demand_h':'demand_h','existing_activity_h':'existing_activity_h','new_activity_h':'new_activity_h','actual_work_RUB':'activity_cost_RUB','substitution_cash_RUB':'base_replacement25_cash_RUB','booked_h':'booked_h','reserve_used_h':'reserve_used_h','paid_idle_h':'paid_idle_h','capacity_h':'total_capacity_h','queue_start_h':'queue_start_h','queue_end_h':'queue_end_h','full_resource_RUB':'full_cost_work_plus_idle_RUB','booking_cash_RUB':'reservation_cash_RUB','new_cash_RUB':'new_operating_cash_RUB'}
        ck('B monthly equations '+str(rid(r)),all(near(v[x],a[y]) for x,y in fields.items()))
        for x,y in fields.items():maxdelta[x]=max(maxdelta[x],abs(float(v[x])-float(a[y])))
        ck('B queue/actual-work invariance '+str(rid(r)),near(q,r['queue_end_h']) and near(v['actual_work_RUB'],r['actual_work_RUB']))
        ck('B no worsened pass or cost '+str(rid(r)), (not truth(r['capacity_pass']) or v['capacity_pass']) and v['new_cash_RUB']<=float(r['new_cash_RUB'])+1e-5 and v['full_resource_RUB']<=float(r['full_resource_RUB'])+1e-5)
        ck('B finite paid positions '+str(rid(r)),int(s['pool_position_max'])==capblocks and int(s['booked_position_count'])==blocks and near(s['booked_h'],booked) and s['hours_per_position_max']=='20' and s['committed_at']=='prelaunch_m-2_full_contingent39month_calendar')
        new.append(v);delta.append({k:r[k] for k in KEY}|{'month':m,'actual_work_delta_RUB':float(v['actual_work_RUB'])-float(r['actual_work_RUB']),'old_booked_h':float(r['booked_h']),'new_booked_h':booked,'old_idle_h':float(r['paid_idle_h']),'new_idle_h':idle,'old_queue_h':float(r['queue_end_h']),'new_queue_h':q,'saved_booking_cash_RUB':float(r['booking_cash_RUB'])-v['booking_cash_RUB'],'saved_full_resource_RUB':float(r['full_resource_RUB'])-v['full_resource_RUB'],'saved_new_cash_RUB':float(r['new_cash_RUB'])-v['new_cash_RUB']})
ck('all B resource keys',len(new)==11232 and len(author)==11232 and len(supply)==11232)
table('monthly-resource.csv',base+new);table('booking-delta.csv',delta)
dump('author-comparison.json',{'B_monthly_rows':len(new),'maximum_absolute_deltas':dict(maxdelta),'no_author_code_executed':True})

# Annual totals, peaks and tail are derived from exactly the same months.
allgroups=defaultdict(list);annual=[]
for r in base+new:allgroups[tuple(str(r[k]) for k in ['candidate_key']+KEY)].append(r)
sumcols=['demand_h','booked_h','reserve_used_h','paid_idle_h','actual_work_RUB','paid_idle_RUB','full_resource_RUB','booking_cash_RUB','substitution_cash_RUB','new_cash_RUB']
for key,rr in allgroups.items():
    rr.sort(key=lambda r:int(r['month']))
    for period,lo,hi in [('Y1',1,12),('Y2',13,24),('Y3',25,36),('tail',37,39),('all39',1,39)]:
        xs=[r for r in rr if lo<=int(r['month'])<=hi];peak=max(xs,key=lambda r:float(r['demand_h']))
        out=dict(zip(['candidate_key']+KEY,key));out.update(period=period,peak_h=float(peak['demand_h']),peak_month=int(peak['month']),capacity_at_peak_h=float(peak['capacity_h']),capacity_pass=all(truth(r['capacity_pass']) for r in xs),queue_end_h=float(xs[-1]['queue_end_h']))
        for c in sumcols:out[c]=sum(float(r[c]) for r in xs)
        annual.append(out)
table('annual-resource.csv',annual)
authorannual={(str(r['scenario']),str(r['fixed_C_year']),str(r['QA_reuse']),str(r['labor_multiplier']),str(r['substitution']),r['role'],{'year1':'Y1','year2':'Y2','year3':'Y3','tail':'tail','all39':'all39'}[r['period']]):r for r in rows(B/'annual-resource.csv')}
for r in annual:
    if r['candidate_key']!='CON-025@v1':continue
    a=authorannual[tuple(r[k] for k in KEY)+(r['period'],)]
    ck('B annual equations '+str(tuple(r[k] for k in KEY)+(r['period'],)),all(near(r[k],a[v]) for k,v in {'demand_h':'demand_h','booked_h':'booked_h','actual_work_RUB':'actual_work_RUB','paid_idle_RUB':'paid_idle_RUB','full_resource_RUB':'full_RUB','new_cash_RUB':'new_operating_cash_RUB','peak_h':'peak_h','peak_month':'peak_month','queue_end_h':'queue_end_h'}.items()))
totals=[];saving=[]
ix={(r['candidate_key'],)+tuple(r[k] for k in KEY)+(r['period'],):r for r in annual}
for cand,scenario,fixed,reuse,mult,sub,period in itertools.product(['CON-024@v1','CON-025@v1','CON-023@v2'],['EXPECTED','FULL_NEW','JAN_OLD50'],['96000000','144000000'],['0','0.5','1'],['1','2'],['0','0.25'],['Y1','Y2','Y3','tail','all39']):
    rs=[ix[cand,scenario,fixed,reuse,mult,sub,role,period] for role in RATES]
    t=dict(candidate_key=cand,scenario=scenario,fixed_C_year=fixed,QA_reuse=reuse,labor_multiplier=mult,substitution=sub,period=period,capacity_pass=all(r['capacity_pass'] for r in rs))
    for c in sumcols:t[c]=sum(r[c] for r in rs)
    totals.append(t)
    if cand=='CON-025@v1':
        old=[ix['CON-023@v2',scenario,fixed,reuse,mult,sub,role,period] for role in RATES]
        saving.append({k:t[k] for k in ['scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','period']}|{'old_booking_cash_RUB':sum(r['booking_cash_RUB'] for r in old),'new_booking_cash_RUB':t['booking_cash_RUB'],'saved_booking_cash_RUB':sum(r['booking_cash_RUB'] for r in old)-t['booking_cash_RUB'],'saved_full_resource_RUB':sum(r['full_resource_RUB'] for r in old)-t['full_resource_RUB'],'saved_new_cash_RUB':sum(r['new_cash_RUB'] for r in old)-t['new_cash_RUB'],'actual_work_delta_RUB':t['actual_work_RUB']-sum(r['actual_work_RUB'] for r in old)})
table('all-role-totals.csv',totals);table('savings.csv',saving)
table('HR-peaks.csv',[r for r in annual if r['role']=='HR' and r['QA_reuse']=='1' and r['substitution']=='0.25' and r['period']=='all39'])
setup=[{**r,'candidate_key':'CON-024@v1' if r['candidate_key']=='CON-022@v1' else r['candidate_key']} for r in rows(OLD/'setup.csv') if r['candidate_key'] in ['CON-022@v1','CON-023@v2']]
setup += [{**r,'candidate_key':'CON-025@v1'} for r in setup if r['candidate_key']=='CON-023@v2']
table('setup.csv',setup)

# A: derive categorical rank from exact published QA and unchanged eligibility,
# then independently allocate fixed slots, ties, shares and final personal floor.
units=rows(A/'unit-decisions.csv');people=rows(A/'decisions.csv');gg=defaultdict(list);alloc=[]
for r in units:gg[r['scenario'],r['period'],r['group']].append(r)
for (sc,period,group),rr in gg.items():
    pp=[r for r in people if (r['scenario'],r['period'],r['group'])==(sc,period,group)];pool=150*len({r['subject'] for r in pp});held=any(r['state'] in ['pending','not_computable'] or r['stretch_state']=='pending' for r in rr);rank={};want={};position=0
    for r in rr:
        qa=F(r['qa_mean']) if r['qa_mean'] else None
        score=2 if qa==100 else 1
        # Category is diagnostic even when independent normal/exposure fails;
        # only stretch-eligible units enter the paid ranking below.
        expected=[score] if qa is not None and qa>=99 and truth(r['top_exposure_sufficient']) else []
        ck('A observed category '+str((sc,period,r['subject'])),json.loads(r['rank_key'])==expected and (not truth(r['stretch']) or qa>=99))
        if truth(r['stretch']):rank[r['subject']]=score
    if len(rr)>=2 and not held:
        for score in sorted(set(rank.values()),reverse=True):
            tied=[s for s in rank if rank[s]==score];amount=F(pool)*sum([F(4,10),F(3,10),F(2,10),F(1,10)][position:position+len(tied)])/len(tied);want.update({s:amount for s in tied});position+=len(tied)
    for r in rr:ck('A category allocation '+str((sc,period,r['subject'])),near(want.get(r['subject'],0),r['unit_top_R']))
    total=0
    for r in pp:
        amount=math.floor(want.get(r['unit'],0)*F(r['share'])) if truth(r['calculated_normal']) else 0
        ck('A one share/floor '+str((sc,period,r['subject'])),near(amount,r['potential_top_R']) and float(r['top_U_R'])<=amount)
        total+=amount
    ck('A group ceiling '+str((sc,period,group)),total<=pool)
    alloc.append(dict(candidate_key='CON-024@v1',scenario=sc,period=period,group=group,pool_R=pool,group_held=held,calculated_personal_R=total))
table('allocation.csv',alloc)
qrows=rows(A/'qa-neighborhood.csv');qgroups=defaultdict(list);qout=[]
for r in qrows:qgroups[r['probe'],r['period'],r['group']].append(r)
for (probe,period,group),rr in qgroups.items():
    pp=[r for r in people if (r['scenario'],r['period'],r['group'])==('R2.quality',period,group)];pool=150*len({r['subject'] for r in pp});rank={r['subject']:2 if F(r['qa_exact'])==100 else 1 for r in rr if truth(r['stretch'])};want={};position=0
    for score in sorted(set(rank.values()),reverse=True):
        tied=[s for s in rank if rank[s]==score];amount=F(pool)*sum([F(4,10),F(3,10),F(2,10),F(1,10)][position:position+len(tied)])/len(tied);want.update({s:amount for s in tied});position+=len(tied)
    for r in rr:
        amount=want.get(r['subject'],0);members=[p for p in pp if p['unit']==r['subject']];personal=sum(math.floor(amount*F(p['share'])) for p in members if truth(p['calculated_normal']))
        ck('QA copy allocation '+str((probe,period,r['subject'])),near(amount,r['unit_calculated_R']) and near(personal,r['personal_calculated_R_sum']) and float(r['authorized_U_R'])==0)
        qout.append(dict(probe=probe,period=period,group=group,subject=r['subject'],qa_exact=r['qa_exact'],normal=r['normal'],stretch=r['stretch'],category=2 if F(r['qa_exact'])==100 else 1 if truth(r['stretch']) else 0,unit_R=str(amount),personal_R=personal,U_R=0))
for probe,person,qa in [('Q99_down','S11',F(3958,40)),('Q99_up','S11',F(3962,40)),('Q100_down','S21',F(4398,44))]:
    r=next(r for r in qrows if r['probe']==probe and r['period']=='P1' and r['subject']==person);ck('recipe exact QA '+probe,F(r['qa_exact'])==qa)
table('qa-allocation.csv',qout)
dump('source-manifest.json',MANIFEST)
dump('verification.json',{'method':'Independent003 category and booking equations; own prior002 core/resource tables reused with SHA and preserved equations. No author/closed model executed.','checks':len(CHECKS),'all_pass':all(r['pass'] for r in CHECKS),'failures':[r for r in CHECKS if not r['pass']],'checks_detail':CHECKS,'current_keys':['CON-024@v1','CON-025@v1','CON-023@v2','BASELINE'],'resource_rows':len(base)+len(new),'booking_delta_rows':len(delta),'QA_allocation_rows':len(qout),'authority_scope':'C3 source/permission integrity independently verified by evidence; this script checks calculated allocation and noU invention, not real ledger.'})
print(json.dumps({'checks':len(CHECKS),'all_pass':all(r['pass'] for r in CHECKS),'failures_first10':[r for r in CHECKS if not r['pass']][:10],'resource_rows':len(base)+len(new)},ensure_ascii=False))
