#!/usr/bin/env python3
"""Independent targeted finance check. Reads sources only; writes only this directory.
No author code or sealed-round code is imported or executed. No new scenario grid.
Run: python3 analysis/iterations/iteration-005/rounds/003/checks/finance/model.py
"""
import csv, json, hashlib, math
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict

P = Path(__file__).resolve().parent
R = P.parent.parent
CORE = R.parent / '002/checks/finance'
errors, checks, sources = [], defaultdict(int), {}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    p = Path(p); sources[str(p.relative_to(R)) if p.is_relative_to(R) else str(p)] = sha(p)
    return p.read_text()
def js(p): return json.loads(read(p))
def rows(p): return list(csv.DictReader(read(p).splitlines()))
def out(name, value): (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
def table(name, data):
    if not data: return
    fields = list(dict.fromkeys(k for row in data for k in row))
    with (P/name).open('w') as h:
        w = csv.DictWriter(h, fields); w.writeheader(); w.writerows(data)
def ck(ok, label, detail=''):
    checks[label] += 1
    if not ok: errors.append({'check': label, 'detail': str(detail)})
def eq(a, b, label, detail='', tol=0.00003): ck(abs(float(F(a))-float(F(b))) <= tol, label, (str(detail),str(a),str(b)))
def num(d,k): return float(d[k] or 0)
def truth(v): return str(v).lower()=='true'
def grouped(data, field):
    g=defaultdict(list)
    for x in data: g[x[field]].append(x)
    return g

# Freeze provenance, policy, and source hashes are checked before arithmetic.
pins=js(R/'private/versions-before-checks.json')
for path,h in pins.items(): ck(sha(R/path)==h,'candidate freeze SHA256',path)
for folder in ['inputs','supporting']:
    manifest=js(R/folder/'manifest.json'); manifest=manifest.get('files',manifest)
    for path,h in manifest.items():
        if isinstance(h,str): ck(sha(R/folder/path)==h,'frozen input SHA256',path)
for name in ['context.md','evidence.md','diagnosis.md','baseline.md','rubric.json']:
    ck((R/'inputs'/name).read_bytes()==(R.parent/'002/inputs'/name).read_bytes(),'same five inputs as money core',name)
ck((R/'supporting/finance-basis/scenario-inputs.json').read_bytes()==(R.parent/'002/supporting/finance-basis/scenario-inputs.json').read_bytes(),'same M05 as money core')
plan=js(R/'plan.json'); assignment=js(R/'candidate-inputs.json')
ck({x['candidate_key'] for x in assignment['candidates']}=={'CON-011@v3','CON-015@v1'},'candidate keys')
for branch in ['A','B']:
    ck(js(R/f'branches/{branch}/branch.json')['status']=='complete','complete branch',branch)
refs=plan['money_core_reuse']['references']
for ref in refs: ck(sha(R/ref['path'])==ref['sha256'],'sealed money core SHA256',ref['path'])
for branch in ['A','B']:
    reuse=js(R/f'branches/{branch}/money-core-reuse.json')
    for ref in reuse['references']: ck(sha(R/ref['path'])==ref['sha256'],'branch reuse SHA256',ref['path'])
M=js(R/'supporting/finance-basis/scenario-inputs.json'); rates=M['common']['rates_rub_hour']
parent=js(R/'supporting/previous-best/finance-spec.json')
specs={'CON-011@v2':parent,'CON-011@v3':js(R/'branches/A/finance-spec-011.json'),'CON-015@v1':js(R/'branches/B/finance-spec-015.json')}
for key,s in specs.items():
    for field in ['N_eligible','currency','eligibility','lower_tier','special','annual_total_R','monthly_calendar_R']:
        ck(s[field]==parent[field],'money policy invariant',key+'/'+field)
    eq(s['annual_total_R'],7200*4*500+250*7200*4+12*(32*2500+16*7500),'all promises maximum',key)
    eq(sum(s['monthly_calendar_R']),24000000,'calendar sum',key)
    eq(s['workload']['primary_QA_reconciliation']['required_total_hours_month'],800,'primary QA retained',key)
    eq(s['workload']['primary_QA_reconciliation']['secondary_award_verification_hours_month'],12,'secondary QA retained',key)
ck(specs['CON-011@v3']['contests']==parent['contests'],'A payout policy unchanged')
ck(specs['CON-011@v3']['stacking']==parent['stacking'],'A caps unchanged')
ck(specs['CON-015@v1']['workload']['minutes_and_denominators']==parent['workload']['minutes_and_denominators'],'B procedure unchanged')
for k,s in specs.items():
    eq(sum(x['share_group_pool'] for x in s['contests']['top_tiers']),1,'top shares sum',k)
    eq(s['contests']['annual_max_R'],7200000,'one top pool',k)
    eq(s['stacking']['personal_all_channels_R_year_cap'],97000,'preserved cap',k)

# Read-only reuse of existing CSV grid; verify balances and reserve formulas in
# relevant rows, rather than regenerate or expand that grid.
annual=[x for x in rows(CORE/'annual.csv') if x['candidate_key'] in ['BASELINE','CON-011@v2']]
monthly=[x for x in rows(CORE/'monthly.csv') if x['candidate_key'] in ['BASELINE','CON-011@v2']]
for x in monthly:
    eq(num(x,'closing_C'),num(x,'opening_C')+num(x,'fixed_C')+num(x,'R_to_C')-num(x,'physical_C'),'core C stock-flow')
    eq(num(x,'closing_R'),num(x,'opening_R')+num(x,'posted_R')-num(x,'R_to_C')-num(x,'direct_R'),'core R stock-flow')
    eq(num(x,'F_close'),num(x,'F_open')+num(x,'F_grant')-num(x,'F_posted')-num(x,'F_unissued_expired'),'core F stock-flow')
    eq(num(x,'target_new_cash_reserve'),max(0,num(x,'new_exposure_RUB')-num(x,'paid_stock_RUB')),'core reserve single stock credit')
    eq(num(x,'closing_C')+num(x,'closing_R'),num(x,'initial_rights_close')+num(x,'new_rights_close'),'core remaining obligations')
for x in annual:
    eq(num(x,'funding_plus_buffer'),num(x,'cash_total')+num(x,'closing_new_reserve')-num(x,'opening_new_reserve')+500000,'annual signed reserve funding')
table('reused-annual.csv',annual)
launch=[x for x in rows(CORE/'launch-monthly.csv') if x['candidate_key']=='CON-011@v2']
for x in launch:
    unit=.2316 if 'PRICE20' in x['scenario'] else .194
    eq(num(x,'closing_C'),num(x,'opening_C')+num(x,'fixed_C')+num(x,'R_to_C')-num(x,'received_C'),'launch C redeemed on receipt')
    eq(num(x,'closing_R'),num(x,'opening_R')+num(x,'posted_R')-num(x,'R_to_C'),'launch R stock-flow')
    eq(num(x,'conditional_close_R'),num(x,'conditional_open_R')+num(x,'new_conditional_R')-num(x,'matured_conditional_R'),'launch conditional rights')
    eq(num(x,'U_close_R'),num(x,'U_open_R')+num(x,'confirmed_R')-num(x,'posted_R'),'launch U retained')
    eq(num(x,'committed_authorization_F_close'),num(x,'conditional_close_R')+num(x,'U_close_R'),'U within encumbered F once')
    eq(num(x,'orders_pending_C'),5000*(num(x,'S1_queue')+num(x,'S2_queue')),'queued request retained',tol=.0006)
    exposure=unit*(num(x,'unrequested_new_C')+num(x,'unrequested_new_R')+num(x,'orders_pending_C')+num(x,'U_close_R'))
    eq(num(x,'new_and_requested_exposure_RUB'),exposure,'queue incl requested legacy exposure',tol=.0007)
    eq(num(x,'total_reserve_RUB'),max(0,exposure+unit*num(x,'conditional_close_R')-num(x,'paid_stock_RUB')),'launch one stock credit',tol=.0007)
    eq(num(x,'funding_without_buffer'),num(x,'cash_total')+num(x,'reserve_delta_RUB'),'launch signed funding')
launchannual=[x for x in rows(CORE/'launch-annual.csv') if x['candidate_key']=='CON-011@v2']
table('reused-launch-annual.csv',[{k:v for k,v in x.items() if k not in ['HR220_pass','HR_peak','own_HR_hours','manager_including_QA_hours','employee_submission_hours','employee_evidence_hours','QA_required_hours','IT_hours','existing_business_RUB','incremental_program_RUB','own_all_process_RUB','ordinary_useful_hours']} for x in launchannual])
tail=[x for x in rows(CORE/'terminal-tail.csv') if x['candidate_key']=='CON-011@v2']
table('reused-terminal-tail.csv',tail)
for stop in ['15','36']:
    t=[x for x in tail if x['stop_new_promise_after_month']==stop]
    ck(any(int(x['month'])==int(stop)+3 and num(x,'conditional_close_R')==0 for x in t),'tail closes m18/m39',stop)
dated=[x for x in rows(CORE/'date-prefunding.csv') if x['candidate_key']=='CON-011@v2']
late=[x for x in rows(CORE/'date-prefunding-late.csv') if x['candidate_key']=='CON-011@v2']
for x in dated:
    eq(num(x,'ordinary_conditional_peak_R'),min(int(x['month']),4)*1800000,'day14 gross before quality')
    eq(num(x,'net_reserve_before_effort_RUB'),num(x,'net_reserve_month_close_RUB'),'day14 stock credit once')
for x in late:
    ck(not truth(x['promise_prefunding_under_this_schedule_pass']),'late no substitute fails')
table('reused-dated-examples.csv',[x for x in dated if int(x['month']) in [1,4,12,24,36]])

# Independent exact rational ranking, slot intersection for ties, and FTE.
def payout(units,n,shares):
    result={u: F(0) for u in units}
    if len(units)<2: return result
    eligible={u:q for u,q in units.items() if q>=F(11,10)}
    rank=0
    for q in sorted(set(eligible.values()),reverse=True):
        tied=[u for u,v in eligible.items() if v==q]
        prize=250*n*sum(shares[rank:rank+len(tied)],F(0))/len(tied)
        for u in tied: result[u]=prize
        rank+=len(tied)
    return result
old=[F(4,5),F(1,5)]; new=[F(4,10),F(3,10),F(2,10),F(1,10)]
def rankq(q): return F(math.floor(q*100+F(1,2)),100)
syn=js(R/'supporting/synthetic-examples.json')
def from_fixture(family,mult,prefix):
    f=syn['families'][family]; rec=f['records']; q=F(0)
    for st,par in f['strata'].items():
        units=sum(F(x['accepted_units']) for x in rec if x['stratum']==st)
        q+=F(par['mix_weight'])*units/(F(par['base_productive_hours'])/F(mult)*F(par['benchmark_units_per_hour']))
    pref=lambda x:prefix+x
    pick=sorted(rec,key=lambda x:hashlib.sha256(','.join([f['window_id'],pref(f['benefit_id']),pref(x['case_id']),f['qa_seed']]).encode()).hexdigest())[:20]
    qa=sum(max(0,100-2*x['minor']-10*x['major']) for x in pick)/len(pick)
    return q,qa

# Reconstruct frozen rawcase->Q->QA->personal money for the 2 frozen groups.
personal=[]
for group,family,mults,members in [('individual40','support',syn['individual_group_40']['multipliers'],1),('teams8x5','IT_team',syn['team_group_40']['multipliers'],5)]:
    qs={}; qa={}
    for i,m in enumerate(mults,1):
        ident=f'I{i:02}' if members==1 else f'T{i:02}'
        q,qual=from_fixture(family,m,ident+':'); qs[ident]=rankq(q) if q>=F(11,10) else q;qa[ident]=qual
        eq(q,F(m),'frozen raw Q equals derived multiplier',ident)
    po,pn=payout(qs,40,old),payout(qs,40,new)
    for ident,q in qs.items():
        lower=500 if q>=1 and qa[ident]>=97 else 0
        for j in range(1,members+1):
            a=math.floor(po[ident]/members); b=math.floor(pn[ident]/members)
            personal.append({'group':group,'unit_id':ident,'person_id':ident if members==1 else ident+f'-P{j}','Q_exact':str(q),'QA_mean':qa[ident],'lower_R':lower,'old_top_R':a,'A_top_R':a,'B_top_R':b,'old_total_R':lower+a,'B_total_R':lower+b,'cycles_to5000_B':math.ceil(F(5000,lower+b)) if lower+b else None,'source_locator':f'supporting/synthetic-examples.json#/{"individual_group_40" if members==1 else "team_group_40"}'})
bexamples=rows(R/'branches/B/money-examples.csv')
idx={(x['group'],x['person_id']):x for x in bexamples}
for x in personal:
    y=idx[x['group'],x['person_id']]
    for k,j in [('old_top_R','old_person_top_R'),('B_top_R','new_person_top_R'),('lower_R','lower_R')]: eq(x[k],y[j],'B frozen personal recomputation',(x['person_id'],j))
table('personal-comparison.csv',personal)

# A: all 445 money/date rows unchanged, plus independent slot/FTE arithmetic.
amoney=rows(R/'branches/A/money-examples.csv')
ck(len(amoney)==445,'A 445 examples')
for x in amoney:
    for k in ['lower_R','top_R','special_R']: eq(x['parent_'+k],x['candidate_'+k],'A all money unchanged',(x['scenario'],x['participant'],k))
    ck(x['parent_right_date']==x['candidate_right_date'],'A right dates unchanged')
    eq(x['total_R'],sum(int(x['candidate_'+k]) for k in ['lower_R','top_R','special_R']),'A personal total')
skip={'profiles','quality_n','exposure','QA97_backoffice','critical','special'}
for scenario,data in grouped(amoney,'scenario').items():
    if scenario in skip: continue
    # Registered population for partial FTE fixture is explicitly 40.
    n=40 if scenario=='FTE25_75' else len(data)
    units={x['benefit_id']:rankq(F(x['Q_exact'])) for x in data}
    paid=payout(units,n,old)
    for x in data:
        expected=math.floor(paid[x['benefit_id']]*F(x['FTE_share'])) if int(x['candidate_lower_R']) else 0
        eq(x['candidate_top_R'],expected,'A independent slots FTE',(scenario,x['participant']))
acalcs=js(R/'branches/A/rawcase-calculations.json')['calculations']
for x in acalcs:
    eq(F(x['Q_exact']),sum(F(a['mix_weight'])*F(a['accepted_standard_units'])/(F(a['productive_hours'])*F(a['benchmark'])) for a in x['strata']),'A all Q stratum arithmetic',x['id'])
for family in syn['families']:
    for prof in syn['Q_profiles']:
        ident=family+'-'+prof['profile']; q,qa=from_fixture(family,prof['productivity_multiplier'],ident+'::')
        x=next(x for x in acalcs if x['id']==ident)
        eq(x['Q'],q,'A raw frozen profiles Q',ident);eq(x['QA_mean'],qa,'A raw frozen profiles QA',ident)

# B: raw expanded cases checked independently, including sample hash and all Q.
braw=rows(R/'branches/B/rawcases-expanded.csv'); bstrata=rows(R/'branches/B/strata-calculation.csv'); bresult=rows(R/'branches/B/synthetic-results.csv')
br=grouped(braw,'scenario_id');bs=grouped(bstrata,'scenario_id')
for x in bresult:
    ident=x['scenario_id']; raw=br[ident]; strata=bs[ident]; q=F(0)
    # B exports use pipe-delimited serialization; A declares comma-delimited.
    # Each is verified against its actual raw hash, with independent recomputation.
    ordered=sorted(raw,key=lambda y:hashlib.sha256('|'.join([y['window_id'],y['benefit_id'],y['case_id'],y['seed']]).encode()).hexdigest())[:20]
    for y in raw:
        h=hashlib.sha256('|'.join([y['window_id'],y['benefit_id'],y['case_id'],y['seed']]).encode()).hexdigest()
        ck(y['qa_hash']==h,'B raw QA hash',ident)
        ck(truth(y['selected_QA'])==(y in ordered),'B selected independent sample',ident)
    qa=sum(max(0,100-2*int(y['minor'])-10*int(y['major'])) for y in ordered)/len(ordered)
    for st in strata:
        units=sum(F(y['accepted_units']) for y in raw if y['stratum']==st['stratum'])
        eq(st['accepted_standard_units'],units,'B raw stratum units',ident)
        term=F(st['mix_weight'])*units/(F(st['productive_hours_exact'])*F(st['benchmark_units_hour']))
        eq(st['Q_component_exact'],term,'B Q component',ident);q+=term
    eq(x['Q_exact'],q,'B all Q from raw',ident);eq(x['QA_mean'],qa,'B all QA from sample',ident)
    ck(not any(truth(y['critical']) for y in raw) or int(x['lower_R'])==0,'critical outside sample blocks money',ident)
    family=x['family']; total_units=sum(F(y['accepted_units']) for y in raw)
    repeat=F(sum(truth(y['reopened_or_returned']) for y in raw),len(raw))
    sla=F(sum(truth(y['sla_met']) for y in raw),len(raw))
    passed=(int(x['exposure_days'])>=10 and not any(truth(y['critical']) for y in raw))
    if family=='support': passed=passed and len(raw)>=20 and total_units>=100 and qa>=97 and repeat<=F(5,100)
    elif family=='backoffice': passed=passed and len(raw)>=20 and total_units>=80 and qa>=98 and repeat<=F(2,100)
    else: passed=passed and len(raw)>=8 and qa>=98 and repeat<=F(5,100) and sla>=F(95,100)
    eq(x['lower_R'],500 if passed and q>=1 else 0,'B all eligibility barriers lower',ident)
    ck(truth(x['top_eligible'])==bool(passed and q>=F(11,10)),'B all eligibility barriers top',ident)
edges=rows(R/'branches/B/edge-cases.csv'); edge_summary=[]
for scenario,data in grouped(edges,'scenario').items():
    # Empty Q explicitly denotes nonqualified unit in these synthetic edges,
    # not a missing bank source (the latter preserves pending rights).
    units={x['unit_id']:rankq(F(x['Q'])) if F(x['Q'] or 0)>=F(11,10) else F(x['Q'] or 0) for x in data}
    n=int(data[0]['n_people']); po,pn=payout(units,n,old),payout(units,n,new)
    total=0
    for x in data:
        a=math.floor(po[x['unit_id']]*F(x['share'])) if truth(x['personal_pass']) else 0
        b=math.floor(pn[x['unit_id']]*F(x['share'])) if truth(x['personal_pass']) else 0
        eq(x['old_top_R'],a,'B edge old payout',(scenario,x['unit_id']))
        eq(x['new_top_R'],b,'B edge new payout',(scenario,x['unit_id']))
        eq(x['new_unit_top_exact'],pn[x['unit_id']],'B edge tie slots',(scenario,x['unit_id']))
        total+=b
    eq(data[0]['new_group_unissued_R'],250*n-total,'B residual unissued',scenario)
    edge_summary.append({'scenario':scenario,'people':n,'registered_units':len(units),'old_paid_R':sum(int(x['old_top_R']) for x in data),'B_paid_R':total,'B_unissued_R':250*n-total,'pool_R':250*n})
table('edge-cases.csv',edge_summary)

# Compact slot bounds independent of authored edge definitions.
slotbounds=[]
for n in [1,2,5,10,60,100]:
    slots=[0] if n==1 else [math.floor(250*n*x) for x in new[:n]]
    slotbounds.append({'eligible_people':n,'registered_units':n,'no_rounded_ties_B_slots_R':str(slots),'paid_R':sum(slots),'unissued_R':250*n-sum(slots)})
table('finite-slot-bounds.csv',slotbounds)
two=payout({'a':F(14,10),'b':F(13,10)},40,new)
eq(sum(two.values()),7000,'B two qualify uses70pct')
mass=payout({str(i):F(12,10) for i in range(40)},40,new)
eq(sum(mass.values()),10000,'B mass tie same total')
ck(all(v==250 for v in mass.values()),'B mass tie250 same personal')
teamtie=payout({str(i):F(12,10) for i in range(8)},40,new)
ck(all(v/5==250 for v in teamtie.values()),'B team mass tie250 same personal')
eq(4*(500+250*100*F(4,10)),42000,'B attained ordinary max42000')
eq(4*(500+250*100*F(4,10))+15000,57000,'B attained all channels57000')
summary=[]
for group in ['individual40','teams8x5']:
    data=[x for x in personal if x['group']==group]
    summary.append({'group':group,'old_paid_people_per_cycle':sum(x['old_top_R']>0 for x in data),'B_paid_people_per_cycle':sum(x['B_top_R']>0 for x in data),'old_paid_units_per_cycle':2,'B_paid_units_per_cycle':4,'first_old_total_person_R':max(x['old_total_R'] for x in data),'first_B_total_person_R':max(x['B_total_R'] for x in data),'first_top_to_lower_old':max(x['old_top_R'] for x in data)/500,'first_top_to_lower_B':max(x['B_top_R'] for x in data)/500,'scope':'positions/persons in this cycle, not unique annual recipients'})
table('positions-per-cycle.csv',summary)
out('concentration.json',{'classification':'calculation, full nominal distinct rounded ranks','group_pool_R_n40':10000,'old_shares':[.8,.2],'B_shares':[.4,.3,.2,.1],'HHI_old':.8**2+.2**2,'HHI_B':sum(x*x for x in [.4,.3,.2,.1]),'first_positions_share_all24m_old':.8*7200000/24000000,'first_positions_share_all24m_B':.4*7200000/24000000,'positions_per_cycle_180groups_old':360,'positions_per_cycle_180groups_B':720,'not_unique_annual':True,'personal_cap_preserved_R':97000,'B_attainable_ordinary_R_year':42000,'B_attainable_all_channels_R_year':57000,'B_text_typo':{'path':'branches/B/concept-015.md','line':45,'written_ordinary_R':42500,'calculated_ordinary_R':42000,'effect':'isolated prose arithmetic inconsistency; no change to cap97000, calendar or envelope24m'}})

# Own resource model: operation denominators, M05 rates, unchanged primary QA,
# existing/new uncertainty, replacement cash distinct from resource cost.
d=parent['workload']['minutes_and_denominators']
hr=6+60*10/60+2400*.25/60+200*4/60+120*6/60+72*5/60+12*5/60+10*10/60
manager=60*30/60+240*3/60+200*10/60+48*5/60+120*8/60+72*5/60+12*8/60+10*20/60
employee=2400*2/60+200*6/60+120*5/60+72*3/60
eq(hr,60,'independent operation HR');eq(manager,106.26666666666667,'independent operation manager');eq(employee,113.6,'independent operation employee')
resources=[]; launchresources=[]; launchcompare=[]
eq(2400*60*.5/60+2400*10*.25/60,1300,'source creation employee formula')
eq(2400*60*.25/60+2400*10*.25/60,700,'source creation manager formula')
for key,s in specs.items():
    saving=8 if key=='CON-011@v3' else 0; it=14 if key=='CON-011@v3' else 13 if key=='CON-015@v1' else 12
    h={'HR':hr-saving,'manager':manager,'employee':employee,'IT':it}
    for role,field in [('HR','HR_hours_monthly'),('manager','manager_hours_monthly'),('employee','employee_process_hours_monthly')]:
        for value in s['workload'][field]: eq(value,h[role],'own role hours',key+role)
    award=sum(h[role]*rates[role] for role in rates)*12
    eq(s['workload']['resource_costs_RUB']['stationary_recognition'],award,'stationary resource own',key)
    peak={'HR':(7200-200)*4/60+(2400-120)*6/60,'manager':(7200-200)*10/60+(2400-120)*8/60,'employee':(7200-200)*6/60+(2400-120)*5/60}
    for fallback,extra in [('nominal',{'HR':0,'manager':0,'employee':0}),('export_fallback',{'HR':20,'manager':80,'employee':0}),('full_source_creation',{'HR':20,'manager':780,'employee':1300}),('all_eligible_requests_appeals_peak',peak)]:
        for mult in [1,2]:
            work=(award+12*sum(v*rates[role] for role,v in extra.items()))*mult
            qa=800*12*1500*mult
            resources.append({'candidate_key':key,'scenario':fallback,'labor_multiplier':mult,'own_award_and_source_RUB_year':work,'primary_QA_required_RUB_year':qa,'quality_plus_award_RUB_year':work+qa,'verified_existing_QA_hours':None,'actual_incremental_QA_hours':None,'new_procedure_resource_RUB_year':award,'replacement25_cash_on_award_source_RUB_year':work*.25,'replacement25_if_all_QA_new_RUB_year':(work+qa)*.25,'resource_plus25_cash_RUB_year':work*1.25,'common_plus_own_HR_month':(151.11111111111111+h['HR']+extra['HR'])*mult,'HR220_pass':(151.11111111111111+h['HR']+extra['HR'])*mult<=220,'actual_incremental_cash_RUB':None})
    for month in range(1,37):
        active=month>=4
        hh={'HR':h['HR'] if active else 22,'manager':manager if active else 42.26666666666667,'employee':employee if active else 20,'IT':it}
        initial={'HR':(38+(4 if key!='CON-011@v2' else 0)) if month==1 else 8 if month in [2,3] else 0,'manager':(120+(4 if key!='CON-011@v2' else 0)) if month==1 else 30 if month in [2,3] else 0,'employee':600 if month<=3 else 0,'IT':(120+(24 if key!='CON-011@v2' else 0)) if month==1 else 200 if month in [2,3] else 0}
        own=sum((hh[role]+initial[role])*rates[role] for role in rates)
        launchresources.append({'candidate_key':key,'month':month,'year':(month-1)//12+1,'HR_award_h':hh['HR'],'HR_launch_h':initial['HR'],'manager_award_h':hh['manager'],'manager_launch_h':initial['manager'],'employee_award_h':hh['employee'],'employee_launch_h':initial['employee'],'IT_recurring_h':it,'IT_initial_h':initial['IT'],'QA_required_h':800 if active else 0,'own_award_plus_launch_RUB':own,'QA_required_RUB':1200000 if active else 0,'existing_QA_split':None,'incremental_cash_actual':None})
    if key!='CON-011@v2':
        branch='A' if key=='CON-011@v3' else 'B'
        author=rows(R/f'branches/{branch}/first-launch.csv'); prior=rows(R/'supporting/previous-best/first-launch.csv')
        pi={(x['scenario'],x['month']):x for x in prior}
        hours_keywords=('HR','manager','employee','IT','QA')
        monetary_fields=[k for k in prior[0] if k not in ['candidate_key','money_provenance'] and not any(w in k for w in hours_keywords)]
        for x in author:
            y=pi[x['scenario'],x['month']]; z=next(z for z in launchresources if z['candidate_key']==key and z['month']==int(x['month']))
            for field in monetary_fields: ck(x[field]==y[field],'first15 invariant cells',(key,x['month'],field))
            for field,col in [('HR_recognition_hours','HR_award_h'),('HR_launch_hours','HR_launch_h'),('manager_recognition_hours','manager_award_h'),('employee_recognition_hours','employee_award_h'),('IT_initial_hours','IT_initial_h'),('IT_recurring_hours','IT_recurring_h'),('primary_QA_total_hours','QA_required_h')]:
                eq(x[field],z[col],'first15 independent hours',(key,x['month'],field))
            eq(x['combined_HR_hours'],num(x,'common_M05_HR_hours')+z['HR_award_h']+z['HR_launch_h'],'launch total HR',key)
            launchcompare.append({'candidate_key':key,'scenario':x['scenario'],'month':x['month'],'money_cells_equal':len(monetary_fields),'own_award_plus_launch_RUB':z['own_award_plus_launch_RUB'],'combined_HR_hours':x['combined_HR_hours'],'fallback_HR_hours':x['combined_HR_fallback_hours'],'source_locator':f'branches/{branch}/first-launch.csv month={x["month"]}'})
table('resources.csv',resources);table('launch-resources-monthly.csv',launchresources);table('first15-verification.csv',launchcompare)
la=[]
for key in specs:
    for year in [1,2,3]:
        data=[x for x in launchresources if x['candidate_key']==key and x['year']==year]
        la.append({'candidate_key':key,'year':year,'own_award_and_launch_RUB':sum(x['own_award_plus_launch_RUB'] for x in data),'QA_required_RUB':sum(x['QA_required_RUB'] for x in data),'quality_plus_award_required_RUB':sum(x['own_award_plus_launch_RUB']+x['QA_required_RUB'] for x in data),'incremental_QA_actual':None,'incremental_cash_actual':None})
table('launch-resources-annual.csv',la)
eq(next(x['own_award_and_launch_RUB'] for x in la if x['candidate_key']=='CON-011@v3' and x['year']==1)-6765200,34000,'A launch extra34000')
eq(4284000-specs['CON-011@v3']['workload']['resource_costs_RUB']['stationary_recognition'],48000,'A steady savings48000')
eq(next(x['own_award_and_launch_RUB'] for x in la if x['candidate_key']=='CON-015@v1' and x['year']==1)-6765200,82000,'B launch extra82000')
snap=js(R.parent/'002/snapshot.json')['files']
for path,h in list(sources.items()):
    q=Path(path)
    if q.is_absolute() and q.is_relative_to(R.parent/'002'):
        relative=str(q.relative_to(R.parent/'002'))
        if relative!='snapshot.json': ck(snap.get(relative)==h,'sealed snapshot pins actual reused file',relative)
out('source-manifest.json',{'path_base':'rounds/003; absolute paths identify read-only sealed core','sha256':sources,'sealed_references':refs,'executed_author_code':False,'executed_sealed_code':False})
out('verification.json',{'status':'pass' if not errors else 'fail','checks':dict(checks),'total_checks':sum(checks.values()),'errors':errors,'money_core_reuse':'lawful only at same maximum/calendar/M05, not copied gates or labor','monthly_rows_checked':len(monthly),'launch_rows_checked':len(launch),'A_examples':len(amoney),'B_personal_examples':len(bexamples),'B_raw_rows':len(braw),'B_synthetic_scenarios':len(bresult),'A_raw_calculations':len(acalcs),'not_verified':['Actual bank inputs/readiness/source/ACL/QA split; timing/minutes; regional small SKU and value; causality.']})
print(json.dumps({'status':'pass' if not errors else 'fail','checks':sum(checks.values()),'errors':errors[:15]},ensure_ascii=False))
