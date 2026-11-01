"""Independent arithmetic, stock-flow and finite-resource reconstruction.

Run with PYTHONDONTWRITEBYTECODE=1 python3 -B <this file>.
Only reads published sources/CSVs; never imports or executes author models.
All writes are confined to this finance directory.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
import csv, hashlib, itertools, json, math, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RD = HERE.parents[1]
ROOT = next(p for p in HERE.parents if (p/'project/brief.md').exists())
INC = RD.parents[1]/'incumbent'
OLD = ROOT/'analysis/iterations/iteration-006/rounds/001/checks/finance'
PATHS = {'CON-022@v1': RD/'branches/A/con-022', 'CON-023@v1': RD/'branches/B/con-023', 'CON-016@v2': INC}
RATES = {'HR':1000, 'owner_QA':1500, 'employee':1000, 'IT':2000}
CHECKS=[]
def read(p): return json.loads(p.read_text())
def rows(p):
    with p.open() as f: return list(csv.DictReader(f))
def num(r,k): return float(r[k])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(name, ok, detail=None):
    CHECKS.append({'name':name,'pass':bool(ok), **({'detail':detail} if detail is not None else {})})
def near(a,b): return abs(float(a)-float(b)) < 1e-5
def dump(name,obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def table(name,rr):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rr for k in r))); w.writeheader(); w.writerows(rr)
def truth(s): return s is True or s=='True'

# Freeze and common source hashes are evidence of identity, not of economics.
pins=read(RD/'private/versions-before-checks.json')['files']
bad=[p for p,h in pins.items() if sha(RD/p)!=h]
ck('all frozen files unchanged',not bad,bad)
manifest={str(p.relative_to(ROOT)):sha(p) for p in [RD/'private/versions-before-checks.json',RD/'supporting/resource-menu.json',RD/'supporting/round002-common-assumptions.md',RD/'supporting/fixtures/manifest.json',RD/'supporting/round002-stress/manifest.json',RD/'supporting/finance-basis/scenario-inputs.json',RD/'supporting/finance-basis/annual-three-year.csv',INC/'finance-spec.json',INC/'first-launch.csv']}
for key,p in PATHS.items(): manifest[str((p/'finance-spec.json').relative_to(ROOT))]=sha(p/'finance-spec.json')
A=read(PATHS['CON-022@v1']/'finance-spec.json'); B=read(PATHS['CON-023@v1']/'finance-spec.json'); P=read(INC/'finance-spec.json')
ck('A unchanged numeric reward parameters',A['scenario_parameters']==P['scenario_parameters'])
ck('A unchanged fixed window and cohort dates',all(A['guarantee'][k]==P['guarantee'][k] for k in ['fixed_window_rule','initial_cohorts','cohort_size','cohort_starts_months','first_all_good_post_months','subsequent_all_good_post_months']))
ck('B E24 numeric invariant',all(B['unchanged'][k]==v for k,v in {'N':7200,'cohorts':9,'cohort_size':800,'G_R':2500,'E_R_year':24000000,'G_ceiling_R_year':18000000,'top_R_year':4320000,'special_R_year':1680000,'top_pool_R_per_person_quarter':150,'top_shares':[.4,.3,.2,.1],'R_to_C':1,'certificate500_price_C':2500}.items()))
ck('E24 channel sum',7200*2500+7200*4*150+12*(20*2500+12*7500)==24000000)
for path,h in B['money_core_reused_no_reexecution'].items(): ck('B declared core SHA '+path,sha(ROOT/path)==h)
for path,h in A['source_hashes'].items(): ck('A declared core SHA '+path,sha(ROOT/path)==h)

# Independent month calendar: fixed dates, no sliding retries, no opening after36.
calendar=[]
for E in (24000000,36000000):
    factor=E/24000000; G=2500*factor; top=150*factor
    gw=[(c+12*k,c+12*k+6) for c in range(1,10) for k in range(3)]
    tw=[(s,s+3) for c in range(1,10) for s in range(c,37,3)]
    for m in range(1,40):
        n=800*sum(end==m for _,end in tw); ng=800*sum(end==m for _,end in gw)
        gr=ng*G; tr=n*top; sr=140000*factor if m<=36 else 0
        calendar.append(dict(E_R_year=E,month=m,ordinary_records=n,guarantee_persons=ng,guarantee_R=gr,top_R=tr,special_R=sr,total_R=gr+tr+sr,G_open_R=800*G*sum(s<=m<e for s,e in gw),G_gross_R=800*G*sum(s<=m<=e for s,e in gw),top_open_R=800*top*sum(s<=m<e for s,e in tw)))
actual={(int(r['E_R_year']),int(r['month'])):r for r in rows(INC/'first-launch.csv')}
for c in calendar:
    r=actual[c['E_R_year'],c['month']]
    mapping={'ordinary_records':'ordinary_cycle_records','guarantee_R':'guarantee_post_all_success_R','top_R':'top_full_all_success_R','special_R':'special_full_R','total_R':'R_post_all_success_max','G_open_R':'guarantee_conditional_open_endmonth_R','G_gross_R':'guarantee_gross_open_before_quality_close_R','top_open_R':'top_conditional_open_endmonth_R'}
    ck('independent calendar '+str((c['E_R_year'],c['month'])),all(near(c[k],r[v]) for k,v in mapping.items()))
table('calendar.csv',calendar)
CAL={r['month']:r for r in calendar if r['E_R_year']==24000000}

# Recheck retained monthly balances directly, not the former verification flag.
core=[]
for name in ('structural-monthly.csv','calendar-monthly.csv'):
    raw=rows(OLD/name); residual=defaultdict(float); prevF=defaultdict(float)
    for r in raw:
        v=lambda k:num(r,k)
        key=tuple(r[k] for k in ['candidate_key','available_R_year','scenario','calendar','fixed_C_year'])
        errs={
          'C':v('C_close')-v('C_open')-v('fixed_C_issued')-v('R_to_C')+v('required_redemption_C'),
          'R':v('R_close')-v('R_open')-v('R_posted')+v('R_to_C'),
          'F':v('F_close')-prevF[key]-v('F_granted')+v('F_posted')+v('F_unissued_expired'),
          'stock':v('C_close')+v('R_close')-v('legacy_close_C_R')-v('new_personal_close_C_R'),
          'cash_stock':v('required_cash_RUB')-v('required_redemption_C')*.194-v('inventory_close_RUB')+v('inventory_open_RUB'),
          'reserve':v('reserve_close_RUB')-max(0,v('new_personal_exposure_RUB')-v('inventory_close_RUB')),
          'funding':v('net_funding_RUB')-v('required_cash_RUB')-v('reserve_close_RUB')+v('reserve_open_RUB')}
        # Heavy-price rows require their stated alternative landed unit.
        if 'PRICE20' in r['scenario']:
            errs['cash_stock']=v('required_cash_RUB')-v('required_redemption_C')*.2316-v('inventory_close_RUB')+v('inventory_open_RUB')
        for k,x in errs.items(): residual[k]=max(residual[k],abs(x))
        prevF[key]=v('F_close')
    core.append({'file':str((OLD/name).relative_to(ROOT)),'sha256':sha(OLD/name),'rows':len(raw),**{k+'_max_residual':v for k,v in residual.items()}})
    ck('independent stock-flow '+name,max(residual.values())<1e-5,dict(residual))
table('core-reconciliation.csv',core)

# Structural procurement ceiling. Full retained annual series keeps old demand,
# new saved stock, paid inventory and signed reserve delta in their own columns.
budget=[]
for r in rows(RD/'supporting/finance-basis/annual-three-year.csv'):
    if r['scenario'] not in ('EXPECTED','FULL_NEW','FULL_NEW_PRICE20','FULL_NEW_OLD35'): continue
    if int(r['envelope_R_year']) not in (24000000,36000000): continue
    base=num(r,'cash_plus_reserve_delta_plus_buffer_rub'); E=int(r['envelope_R_year'])
    certificate=base+E*((.24-.2316) if 'PRICE20' in r['scenario'] else (.2-.194))
    budget.append(dict(scenario=r['scenario'],fixed_C_year=int(r['fixed_C_year']),E_R_year=E,year=int(r['year']),cash_RUB=num(r,'total_cash_required_rub'),signed_reserve_delta_RUB=num(r,'reserve_target_delta_rub'),buffer_RUB=500000,M05_funding_RUB=base,certificate500_funding_RUB=certificate,pass30=certificate<=30000000,pass34=certificate<=34000000,personal_close_C_R=num(r,'C_close')+num(r,'R_close'),new_personal_close_C_R=num(r,'post_start_rights_close_C_R')))
table('budget.csv',budget)

# Fixed/old shop reconstructed from common retained redemption, removing the
# new R basket handling before adding certificate500 orders exactly once.
shop={}
for r in rows(OLD/'calendar-monthly.csv'):
    if r['candidate_key']!='CON-016@v2' or r['available_R_year']!='24000000' or r['calendar']!='all_good' or r['scenario'] not in ('EXPECTED','FULL_NEW','JAN_OLD50'): continue
    m=int(r['month']); amount=num(r,'required_redemption_C')-num(r,'R_posted')
    shop[r['scenario'],int(r['fixed_C_year']),m]=80+amount/5000*(.02+.2*2/60)
ck('same-month shop source complete',len(shop)==234,len(shop))

# Every operating norm below is taken from published stages, re-entered as
# independent equations. No author build function or CSV is used as oracle.
resource=[]; deltas=[]
for key in PATHS:
    for scenario,fixed,reuse,mult,sub in itertools.product(('EXPECTED','FULL_NEW','JAN_OLD50'),(96000000,144000000),(0,.5,1),(1,2),(0,.25)):
        demands=[]
        for m,c in CAL.items():
            n=c['ordinary_records']; g=c['guarantee_persons']; ins=n/3*38+n/3*22+n/15*4.5
            ex={'HR':shop[scenario,fixed,m], 'owner_QA':ins*3/60,'employee':0,'IT':0}
            if key=='CON-022@v1':
                new={'HR':42.4+n/40*8/60+n*.1*2/60+g*.1/60,
                     'owner_QA':75.6+n/40*10/60+n*.1*4/60+n/15*2/60+ins*5/60*(1-reuse),'employee':33.6,'IT':32}
            elif key=='CON-023@v1':
                new={'HR':(180*8+180*4+120*6+12*10+720+200*4+32*5+72*5+12*38+n*.15+g*.1)/60,
                     'owner_QA':(n*4+n*1760/2400*2+60*10+120*12+12*8+200*10+32*5+72*5+12*12)/60+ins*5/60*(1-reuse),'employee':(200*6+120*5+72*3)/60,'IT':(1440+12*30)/60}
            else:
                # Unchanged control, common180 groups, original48 special review
                # approvals retained. No paid resource plan silently invented.
                sampled=n/3*20+n/3*20+n/15*4.5
                new={'HR':70+n*.35/60,'owner_QA':(200*10+48*5+120*8+72*5+12*8+10*20+180*30)/60+n*.1*3/60+sampled*5/60*(1-reuse),'employee':33.6+n*2/60,'IT':15}
            new['HR']+=c['total_R']/2500*.02
            demands.append((m,ex,new))
        base={'HR':220,'owner_QA':2436,'employee':0,'IT':0}
        if key=='CON-023@v1':
            limits={'HR':6,'owner_QA':240,'employee':4,'IT':3}
            blocks={role:min(limits[role],math.ceil(max(max(0,(e[role]+n[role])*mult-base[role]) for _,e,n in demands)/20-1e-10)) for role in RATES}
        for role,rate in RATES.items():
            queue=0
            for m,ex,new in demands:
                demand=(ex[role]+new[role])*mult
                if key=='CON-022@v1': booked=120 if role=='HR' else math.ceil(max(0,demand-base[role])/20)*20
                elif key=='CON-023@v1': booked=blocks[role]*20
                else: booked=0
                used=min(booked,max(0,demand-base[role])); idle=booked-used; cap=base[role]+booked
                previous=queue; queue=max(0,queue+demand-cap); actual=demand*rate
                cash=booked*rate+sub*min(base[role],demand)*rate
                resource.append(dict(candidate_key=key,scenario=scenario,fixed_C_year=fixed,QA_reuse=reuse,labor_multiplier=mult,substitution=sub,month=m,role=role,existing_activity_h=ex[role]*mult,new_activity_h=new[role]*mult,demand_h=demand,base_h=base[role],booked_h=booked,reserve_used_h=used,paid_idle_h=idle,capacity_h=cap,current_excess_h=max(0,demand-cap),queue_start_h=previous,queue_end_h=queue,actual_work_RUB=actual,paid_idle_RUB=idle*rate,full_resource_RUB=actual+idle*rate,booking_cash_RUB=booked*rate,substitution_cash_RUB=sub*min(base[role],demand)*rate,new_cash_RUB=cash,capacity_pass=demand<=cap+1e-8,base220_pass=demand<=220+1e-8 if role=='HR' else 'not_applicable'))
    if key=='CON-016@v2': continue
    author=rows(PATHS[key]/'monthly-resource.csv')
    index={(r.get('scenario',r.get('redemption')),int(r['fixed_C_year']),float(r['QA_reuse']),float(r['labor_multiplier']),float(r.get('substitution',r.get('base_substitution'))),int(r['month']),r['role']):r for r in author}
    amap={'demand_h':'demand_h','booked_h':'paid_booked_h' if key=='CON-022@v1' else 'booked_h','reserve_used_h':'paid_used_h' if key=='CON-022@v1' else 'reserve_used_h','paid_idle_h':'paid_idle_h','queue_end_h':'queue_carry_h' if key=='CON-022@v1' else 'queue_end_h','full_resource_RUB':'full_resource_RUB' if key=='CON-022@v1' else 'full_cost_work_plus_idle_RUB','new_cash_RUB':'new_cash_RUB' if key=='CON-022@v1' else 'new_operating_cash_RUB'}
    maxdelta=defaultdict(float); failures=[]
    for r in (r for r in resource if r['candidate_key']==key):
        rid=tuple(r[k] for k in ['scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','month','role']); a=index[rid]
        for x,y in amap.items():
            d=abs(r[x]-float(a[y])); maxdelta[x]=max(maxdelta[x],d)
            if d>1e-5: failures.append({'row':rid,'column':x,'independent':r[x],'author':a[y]})
    ck(key+' independent monthly comparison',not failures,{'rows':len(author),'max_deltas':dict(maxdelta),'failures_first20':failures[:20]})
    deltas.append({'candidate_key':key,'rows':len(author),'max_deltas':dict(maxdelta),'failures':failures[:50]})
table('monthly-resource.csv',resource)
dump('author-comparison.json',deltas)

# Annual sums and peaks use exactly those rows, never sums of unrelated maxima.
groups=defaultdict(list)
fields=['candidate_key','scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role']
for r in resource: groups[tuple(r[k] for k in fields)].append(r)
annual=[]
for key,rs in groups.items():
    for label,lo,hi in [('Y1',1,12),('Y2',13,24),('Y3',25,36),('tail',37,39),('all39',1,39)]:
        rr=[r for r in rs if lo<=r['month']<=hi]; peak=max(rr,key=lambda r:r['demand_h'])
        out=dict(zip(fields,key)); out.update(period=label,peak_h=peak['demand_h'],peak_month=peak['month'],capacity_at_peak_h=peak['capacity_h'],capacity_pass=all(r['capacity_pass'] for r in rr),queue_end_h=rr[-1]['queue_end_h'])
        for col in ['demand_h','booked_h','reserve_used_h','paid_idle_h','actual_work_RUB','paid_idle_RUB','full_resource_RUB','booking_cash_RUB','substitution_cash_RUB','new_cash_RUB']:out[col]=sum(r[col] for r in rr)
        annual.append(out)
table('annual-resource.csv',annual)
peaks=[r for r in annual if r['role']=='HR' and r['QA_reuse']==1 and r['substitution']==.25 and r['period']=='all39']
table('HR-peaks.csv',peaks)

# Setup source schedules are independently costed; paid blocks and idle included.
setup=[]
for key,sch in [('CON-022@v1',{-3:{'HR':40,'owner_QA':120,'IT':240,'employee':20},-2:{'HR':40,'owner_QA':120,'IT':240,'employee':20},-1:{'HR':40,'owner_QA':120,'IT':240,'employee':20}}),('CON-023@v1',{-2:{'HR':40,'owner_QA':140,'IT':240,'employee':600},-1:{'HR':40,'owner_QA':140,'IT':240,'employee':600},0:{'HR':40,'owner_QA':140,'IT':240,'employee':600}})]:
    ar={(int(r['month']),r['role']):r for r in rows(PATHS[key]/'setup-resource.csv')}
    for m,roles in sch.items():
        for role,h in roles.items():
            paid=math.ceil(h/20)*20; cash=paid*RATES[role]; a=ar[m,role]
            ck(key+' setup '+str((m,role)),near(cash,a['cash_RUB']))
            setup.append(dict(candidate_key=key,month=m,role=role,actual_h=h,paid_h=paid,idle_h=paid-h,full_resource_RUB=cash,new_cash_RUB=cash))
for role,h in P['workload']['launch_hours'].items():
    role='owner_QA' if role=='manager' else role
    setup.append(dict(candidate_key='CON-016@v2',month='prelaunch_unscheduled',role=role,actual_h=h,paid_h='unconfirmed',idle_h='unknown',full_resource_RUB=h*RATES[role],new_cash_RUB='unknown'))
table('setup.csv',setup)

# Allocation arithmetic is independently reconstructed from published rank keys.
# Metric/authority validity remains a separate evidence check on source primitives.
allocation=[]
for key in ('CON-022@v1','CON-023@v1'):
    units=rows(PATHS[key]/'unit-decisions.csv'); people=rows(PATHS[key]/'decisions.csv'); gg=defaultdict(list)
    for r in units:gg[r['scenario'],r['period'],r['group']].append(r)
    for (sc,period,group),rr in gg.items():
        pp=[r for r in people if (r['scenario'],r['period'],r['group'])==(sc,period,group)]
        pool=150*len({r['subject'] for r in pp}); strong='stretch' if key=='CON-022@v1' else 'strong'
        eligible=[r for r in rr if truth(r[strong])]; expected={}; pos=0
        ranks={r['subject']:tuple(Fraction(str(x)) for x in json.loads(r['rank_key'])) for r in eligible}
        if len(rr)>=2:
            for score in sorted(set(ranks.values()),reverse=True):
                ids=[s for s in ranks if ranks[s]==score]; amount=Fraction(pool)*sum([Fraction(4,10),Fraction(3,10),Fraction(2,10),Fraction(1,10)][pos:pos+len(ids)])/len(ids)
                expected.update({s:amount for s in ids}); pos+=len(ids)
        unitcol='unit_top_R' if key=='CON-022@v1' else 'top_R'
        # Pending group data may reserve the entire pool, so zero declared is
        # allowed only with explicitly pending group state.
        held=any(r.get('top_state','').startswith('pending') or r['state'] in ('pending','not_computable') for r in rr)
        # B explicitly suspends observed group allocation on incomplete source
        # review. A keeps a calculated amount and holds its authorization later.
        if key=='CON-023@v1': held=held or any(json.loads(r.get('source_review_errors') or '[]') for r in pp)
        for r in rr:
            want=float(expected.get(r['subject'],0)) if not held else 0
            ck(key+' allocation '+str((sc,period,group,r['subject'])),near(want,r[unitcol]))
        per_person=0
        for r in pp:
            amount=math.floor(expected.get(r['unit'],0)*Fraction(r['share'])) if not held and truth(r['calculated_normal']) else 0
            col='potential_top_R' if key=='CON-022@v1' else 'top_earned_R'
            ck(key+' personal single share '+str((sc,period,r['subject'])),near(amount,r[col]))
            per_person+=amount
        ck(key+' pool ceiling '+str((sc,period,group)),per_person<=pool)
        allocation.append(dict(candidate_key=key,scenario=sc,period=period,group=group,unique_people=len(pp),pool_R=pool,group_held=held,calculated_personal_R=per_person))
table('allocation.csv',allocation)

# Small n / tie / final-floor checks independent of source labels.
small=[]
for n,rank_sizes in [(1,[1]),(2,[1,1]),(3,[3]),(5,[5]),(40,[1,1,1,1]),(40,[3,2])]:
    pool=150*n; position=0; paid=0
    for tied in rank_sizes:
        amount=Fraction(0) if n==1 else Fraction(pool)*sum([Fraction(4,10),Fraction(3,10),Fraction(2,10),Fraction(1,10)][position:position+tied])/tied
        paid+=math.floor(amount)*tied;position+=tied
    ck('small group pool '+str((n,rank_sizes)),paid<=pool and (n!=1 or paid==0))
    small.append(dict(unique_people=n,tie_blocks=str(rank_sizes),pool_R=pool,total_floor_R=paid,unissued_R=pool-paid))
table('small-groups.csv',small)
dump('source-manifest.json',manifest)
summary={'method':'Own stock-flow and stage equations, read-only CSV comparison; no author imports, models or exporters executed. All volumes, rates, resources and readiness synthetic assumptions.','checks':len(CHECKS),'failures':[r for r in CHECKS if not r['pass']],'all_arithmetic_checks_pass':all(r['pass'] for r in CHECKS),'checks_detail':CHECKS,'core_rows':sum(x['rows'] for x in core),'monthly_resource_rows':len(resource),'authority_scope':'Allocation compares calculated amounts; separate independent evidence report decides source authority/U validity.'}
dump('verification.json',summary)
print(json.dumps({k:summary[k] for k in ['checks','core_rows','monthly_resource_rows','all_arithmetic_checks_pass','failures']},ensure_ascii=False))
