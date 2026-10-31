#!/usr/bin/env python3
"""Owned-path calculator. Reads frozen JSON/CSV, never imports/executes sealed models.
All observations are synthetic; money core reuse is maximum-exposure equivalence.
"""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import csv, hashlib, json, math
O=Path(__file__).resolve().parent
R=O.parent.parent
KEY='CON-015@v1'
SLOTS=[F(4,10),F(3,10),F(2,10),F(1,10)]
OLD=[F(8,10),F(2,10)]
def read(p): return json.loads(p.read_text())
def write(name,obj): (O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvout(name,rows):
    assert rows
    cols=list(dict.fromkeys(k for row in rows for k in row))
    with (O/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def val(x): return float(x) if isinstance(x,F) else x
def rnd(q): return (q*100+F(1,2)).numerator//(q*100+F(1,2)).denominator

def allocation(n,units,slots,registered=None):
    """Return personal floor only, rank interval, unit exact gross. n counts unique people.
    Unqualified personal share is never reallocated. Units include failed units.
    """
    registered=len(units) if registered is None else registered
    qualified=sorted([u for u in units if u['top']],key=lambda u:-u['rank_key'])
    result={u['id']:{'rank':'','unit_top_exact':F(0),'personal':[0]*len(u['shares'])} for u in units}
    pos=0
    while pos<len(qualified):
        end=pos+1
        while end<len(qualified) and qualified[end]['rank_key']==qualified[pos]['rank_key']: end+=1
        gross=(sum(slots[pos:end],F(0))*250*n/(end-pos)) if registered>=2 else F(0)
        for u in qualified[pos:end]:
            personal=[math.floor(gross*s) if passed else 0 for s,passed in zip(u['shares'],u['personal_pass'])]
            result[u['id']]={'rank':str(pos+1) if end-pos==1 else f'{pos+1}..{end}', 'unit_top_exact':gross,'personal':personal}
        pos=end
    assert sum(sum(x['personal']) for x in result.values())<=250*n
    return result

RAW=[]; STRATA=[]; QROWS=[]
fixtures=read(R/'supporting/synthetic-examples.json')
parent=read(R/'supporting/previous-best/finance-spec.json')

def evaluate(family,mult,prefix,records=None,days=None):
    src=fixtures['families'][family]; records=deepcopy(src['records'] if records is None else records)
    mult=F(mult); benefit=prefix+':'+src['benefit_id']; window=src['window_id']; seed=src['qa_seed']
    for row in records:
        row['source_case_id']=row.get('template_case_id',row['case_id']);row['case_id']=prefix+':'+row['case_id']
        row['qa_hash']=hashlib.sha256(f"{window}|{benefit}|{row['case_id']}|{seed}".encode()).hexdigest()
    sample=sorted(records,key=lambda x:x['qa_hash'])[:min(20,len(records))]
    sample_ids={x['case_id'] for x in sample}; qa=sum((F(max(0,100-2*x['minor']-10*x['major'])) for x in sample),F(0))/len(sample)
    q=F(0);total=F(0)
    for st,par in src['strata'].items():
        units=sum(F(x['accepted_units']) for x in records if x['stratum']==st)
        hours=F(par['base_productive_hours'])/mult
        component=F(par['mix_weight'])*(units/hours/F(par['benchmark_units_per_hour']))
        q+=component;total+=units
        STRATA.append({'scenario_id':prefix,'family':family,'stratum':st,'accepted_standard_units':str(units),'productive_hours_exact':str(hours),'benchmark_units_hour':par['benchmark_units_per_hour'],'mix_weight':par['mix_weight'],'Q_component_exact':str(component),'source_locator':f'supporting/synthetic-examples.json#/families/{family}/strata/{st}'})
    days=src['exposure_days'] if days is None else days
    failures=[];minimum=8 if family=='IT_team' else 20
    if len(records)<minimum: failures.append('case_minimum')
    if family=='support' and total<100: failures.append('unit_minimum')
    if family=='backoffice' and total<80: failures.append('unit_minimum')
    if days<10: failures.append('exposure')
    if qa<(97 if family=='support' else 98): failures.append('QA_mean')
    if any(x['critical'] for x in records): failures.append('critical_full_registry')
    rate=F(sum(x['reopened_or_returned'] for x in records),len(records))
    if rate>(F(2,100) if family=='backoffice' else F(5,100)): failures.append('returns_or_reopen')
    if family=='IT_team' and F(sum(x['sla_met'] for x in records),len(records))<F(95,100): failures.append('SLA')
    lower=not failures and q>=1; top=lower and q>=F(11,10)
    for row in records:
        RAW.append({'scenario_id':prefix,'family':family,'window_id':window,'benefit_id':benefit,**row,'selected_QA':row['case_id'] in sample_ids,'seed':seed,'score':max(0,100-2*row['minor']-10*row['major']),'source_locator':f'supporting/synthetic-examples.json#/families/{family}/records/'+str(next(i for i,z in enumerate(src['records']) if z['case_id']==row['source_case_id']))+'; expansion='+prefix})
    out={'scenario_id':prefix,'family':family,'n_cases':len(records),'units_exact':str(total),'exposure_days':days,'Q_exact':str(q),'Q':float(q),'rank_Q':rnd(q)/100,'QA_n':len(sample),'QA_exact':str(qa),'QA_mean':float(qa),'returned_fraction':str(rate),'QA_and_exposure_failures':';'.join(failures),'lower_R':500 if lower else 0,'top_eligible':bool(top),'benefit_id':benefit,'sample_IDs':';'.join(sorted(sample_ids)),'source_locator':f'supporting/synthetic-examples.json#/families/{family}'}
    QROWS.append(out)
    return dict(id=prefix,top=bool(top),rank_key=rnd(q),shares=[F(1)],personal_pass=[bool(lower)],evaluation=out)

for family in fixtures['families']:
    for prof in fixtures['Q_profiles']:
        evaluate(family,prof['productivity_multiplier'],family+':'+prof['profile'])
IND=[evaluate('support',m,f'I{i+1:02}') for i,m in enumerate(fixtures['individual_group_40']['multipliers'])]
TEAMS=[]
for i,m in enumerate(fixtures['team_group_40']['multipliers']):
    u=evaluate('IT_team',m,f'T{i+1:02}')
    u['shares']=[F(x) for x in fixtures['team_group_40']['fte_shares']];u['personal_pass']=[u['evaluation']['lower_R']>0]*5;TEAMS.append(u)
MONEY=[]; SUMMARY=[]
for label,units in [('individual40',IND),('teams8x5',TEAMS)]:
    a=allocation(40,units,OLD);b=allocation(40,units,SLOTS)
    for u in units:
        e=u['evaluation'];ident=u['id']
        for j,(old,new) in enumerate(zip(a[ident]['personal'],b[ident]['personal'])):
            lo=500 if u['personal_pass'][j] else 0
            MONEY.append({'group':label,'unit_id':ident,'person_id':ident if label=='individual40' else ident+f'-P{j+1}', 'benefit_id':e['benefit_id'],'Q_exact':e['Q_exact'],'QA_mean':e['QA_mean'],'qualified_top':e['top_eligible'],'rank':b[ident]['rank'],'FTE_share':str(u['shares'][j]),'lower_R':lo,'old_unit_top_exact':str(a[ident]['unit_top_exact']),'new_unit_top_exact':str(b[ident]['unit_top_exact']),'old_person_top_R':old,'new_person_top_R':new,'delta_top_R':new-old,'old_total_R':lo+old,'new_total_R':lo+new,'cycles_to_5000_if_repeated_new':math.ceil(5000/(lo+new)) if lo+new else None,'qualification_locator':'synthetic-results.csv scenario_id='+ident})
    SUMMARY.append({'group':label,'n_unique_people':40,'qualified_units':sum(u['top'] for u in units),'old_paid_units':sum(any(a[u['id']]['personal']) for u in units),'new_paid_units':sum(any(b[u['id']]['personal']) for u in units),'old_paid_people':sum(v>0 for x in a.values() for v in x['personal']),'new_paid_people':sum(v>0 for x in b.values() for v in x['personal']),'old_paid_top_R':sum(sum(x['personal']) for x in a.values()),'new_paid_top_R':sum(sum(x['personal']) for x in b.values()),'unit_position_scope':'positions per cycle; not unique people per year'})
# Exposure and quality barriers, all independently evaluated.
for fam in fixtures['families']:
    evaluate(fam,'6/5',fam+':days9',days=9)
    evaluate(fam,'6/5',fam+':days10',days=10)
    for n in [10,20,60]:
        src=fixtures['families'][fam];base=src['records'];rows=[]
        for k in range(n):
            row=deepcopy(base[k%len(base)]);row['template_case_id']=row['case_id'];row['case_id']=f'{fam}-n{n}-{k:03}';rows.append(row)
        # Retain all raw values; this tests count + actual units and strata, not fake eligibility.
        evaluate(fam,'6/5',fam+f':n{n}',records=rows)
# Exactly QA97 backoffice, all20 inspected.
rows=deepcopy(fixtures['families']['backoffice']['records'])
for i,x in enumerate(rows): x['minor']=2 if i<10 else 1
evaluate('backoffice','6/5','BO:QA97',records=rows)
# Critical outside deterministic sample: choose an unselected hash with the final prefixed IDs.
prefix='support:criticalOutside';src=fixtures['families']['support'];rows=deepcopy(src['records']);benefit=prefix+':'+src['benefit_id']
hashes=[hashlib.sha256(f"{src['window_id']}|{benefit}|{prefix}:{x['case_id']}|{src['qa_seed']}".encode()).hexdigest() for x in rows]
rows[max(range(len(rows)),key=lambda i:hashes[i])]['critical']=True
crit=evaluate('support','6/5',prefix,records=rows);assert 'critical_full_registry' in crit['evaluation']['QA_and_exposure_failures']
assert not next(x for x in RAW if x['scenario_id']==prefix and x['critical'])['selected_QA']
# QA97 at n60 for every family: set selected sample exactly10 score96/10 score98.
for fam in fixtures['families']:
    src=fixtures['families'][fam];rows=[];prefix=fam+':sample60_QA97'
    for k in range(60):
        row=deepcopy(src['records'][k%len(src['records'])]);row['template_case_id']=row['case_id'];row['case_id']=f'qa60-{k}';rows.append(row)
    bid=prefix+':'+src['benefit_id']
    ids=sorted(range(60),key=lambda i:hashlib.sha256(f"{src['window_id']}|{bid}|{prefix}:{rows[i]['case_id']}|{src['qa_seed']}".encode()).hexdigest())[:20]
    for i in ids[:10]: rows[i]['minor']=2
    evaluate(fam,'6/5',prefix,records=rows)

EDGES=[]
def edge(name,n,qs,shares=None,passes=None):
    us=[]
    for i,q in enumerate(qs):
        s=[F(1)] if shares is None else [F(x) for x in shares[i]]
        us.append(dict(id=f'U{i+1}',top=q is not None and F(q)>=F(11,10),rank_key=rnd(F(q)) if q else 0,shares=s,personal_pass=([True]*len(s) if passes is None else passes[i])))
    a=allocation(n,us,OLD);b=allocation(n,us,SLOTS)
    paid=0
    for u in us:
        for j,(x,y) in enumerate(zip(a[u['id']]['personal'],b[u['id']]['personal'])):
            paid+=y;EDGES.append({'scenario':name,'n_people':n,'registered_units':len(us),'unit_id':u['id'],'person_index':j+1,'Q':qs[int(u['id'][1:])-1],'rank':b[u['id']]['rank'],'share':str(u['shares'][j]),'personal_pass':u['personal_pass'][j],'old_top_R':x,'new_unit_top_exact':str(b[u['id']]['unit_top_exact']),'new_top_R':y,'group_pool_R':250*n,'source_locator':'build_artifacts.py#edge explicit synthetic extension'})
    for row in EDGES:
        if row['scenario']==name:row['new_group_unissued_R']=250*n-paid
for n in [1,2,5,10,60,100]: edge(f'n{n}_ranked',n,[str(F(3,2)-F(i,1000)) for i in range(n)])
edge('onlyOneQualifiedOf40',40,['6/5']+[None]*39)
edge('tieAll40',40,['6/5']*40)
edge('tieRanks4through6',40,['7/5','13/10','6/5','23/20','23/20','23/20']+[None]*34)
edge('teams3and7',10,['7/5','13/10'],[[F(1,3)]*3,[F(1,7)]*7])
edge('crossDepartmentOneBenefit',40,['7/5','13/10']+[None]*37,[['1/4','3/4']]+[['1']]*38)
edge('FTEfailedShare',40,['7/5','13/10'],[['1/2','1/3','1/6'],['1']],[[True,False,True],[True]])
edge('tinyFTE',2,['7/5','13/10'],[['1/1000','999/1000'],['1']])
edge('singleRegisteredTeam',40,['7/5'],[['1/5']*5])
edge('roundingBoundaryTop',2,['10999/10000','11/10'])
# Workload recalculated from frozen event counts, not copied totals.
OPS=[('export',60,10,30,0),('batch_all_records_including_rejected',2400,.25,0,0),('secondary_QA',240,0,3,0),('special_requests_including_refusal',200,4,10,6),('special_independent_approval',48,0,5,0),('appeal',120,6,8,5),('correction',72,5,5,3),('recusal',12,5,8,0),('fixed_administration',1,360,0,0),('rule_change',10,10,20,0),('employee_statement',2400,0,0,2)]
roles=['HR','manager','employee']; sums={role:sum(F(str(op[i+2]))*op[1]/60 for op in OPS) for i,role in enumerate(roles)}
assert all(abs(float(sums[k])-v)<1e-8 for k,v in [('HR',60),('manager',106.26666666666667),('employee',113.6)])
WORK=[]
for name,count,*mins in OPS:
    for role,minute in zip(roles,mins):
        WORK.append({'scope':'stationary_operation','operation':name,'role':role,'events_month':count,'minutes_event':minute,'old_hours':float(F(str(minute))*count/60),'new_hours':float(F(str(minute))*count/60),'delta_hours':0,'classification':'design minutes / calculated; procedure unchanged','source_locator':'supporting/previous-best/finance-spec.json#/workload/minutes_and_denominators'})
def wh(scope,role,old,new,note): WORK.append({'scope':scope,'operation':'total_or_resource','role':role,'old_hours':old,'new_hours':new,'delta_hours':new-old,'classification':note,'source_locator':'build_artifacts.py#workload'})
for role in roles: wh('stationary_award_total',role,float(sums[role]),float(sums[role]),'all requests, no transfer of work')
wh('primary_QA_required_existing_new_unknown','manager',800,800,'2400*20*1/60; actual incremental unknown; never free')
for role,x in [('HR',20),('manager',80),('employee',0)]: wh('export_fallback_additional',role,x,x,'source exists; QA unchanged')
for role,x in [('manager',700),('employee',1300)]: wh('source_creation_above_export_and_QA',role,x,x,'144000cases and24000exposure rows; full source absent')
for role,old,new in [('HR',54,58),('manager',180,184),('employee',1800,1800),('IT',520,544)]: wh('launch_initial_total',role,old,new,'added4HR+4manager+24IT: tier tables/tie/FTE fixtures, signed config and card; scenario')
wh('stationary_recurring_month','IT',12,13,'one new hour/month for configuration regression; internal capacity unknown')
common=80+F(160000000,12)/5000*F(2,100)+F(160000000,12)/5000*F(2,10)/30
# More explicit common = full-new requests(40m old+96mfixed+24mR)/12/5000 baskets.
common=80+F(160000000,12*5000)*(F(2,100)+F(2,10)*F(2,60))
assert abs(float(common)-151.1111111111)<1e-7
for scope,h in [('nominal_combined_HR',common+60),('export_combined_HR',common+80),('full_source_combined_HR',common+80),('2x_all_combined_HR',2*(common+60))]: wh(scope,'HR',float(h),float(h),'M05 capacity220; nominal pass, fallback and2x fail')
for role,mins in [('HR',4),('manager',10),('employee',6)]:
    special_extra=F((7200-200)*mins,60); appeal_extra=F((2400-120)*{'HR':6,'manager':8,'employee':5}[role],60)
    wh('all_eligible_special_and_appeal_extra',role,float(special_extra+appeal_extra),float(special_extra+appeal_extra),'above normal flow; no access cap, HR fails')
# Full-role labor sensitivity; replacement is a separate extra-cash scenario.
for role in roles+['IT']:
    old=float(sums[role]) if role in sums else 12
    new=float(sums[role]) if role in sums else 13
    wh('2x_stationary_award_by_role',role,old*2,new*2,'twice all labor, no claim of available capacity')
    rate={'HR':1000,'manager':1500,'employee':1000,'IT':2000}[role]
    WORK.append({'scope':'replacement25pct_extra_cash','operation':'resource sensitivity separately from hours','role':role,'old_RUB_month':old*rate/4,'new_RUB_month':new*rate/4,'delta_RUB_month':(new-old)*rate/4,'classification':'design replacement cash; not procurement budget; not observed hiring'})
# Hash inputs/supporting and money-core references. No write outside O.
checked=[]
for directory,manifest in [('inputs',read(R/'inputs/manifest.json')['files']),('supporting',read(R/'supporting/manifest.json'))]:
    for path,sha in manifest.items():
        actual=digest(R/directory/path);assert actual==sha,(path,actual,sha);checked.append({'path':directory+'/'+path,'sha256':actual})
reuse=deepcopy(read(R/'plan.json')['money_core_reuse'])
for ref in reuse['references']:
    actual=digest(R/ref['path']);assert actual==ref['sha256'],ref;ref['verified_sha256']=actual
reuse.update(candidate_key=KEY,path_base='analysis/iterations/iteration-005/rounds/003',independent_admission_inherited=False,
    invariant_parameters={'N':7200,'max_new_R_year':24000000,'lower':14400000,'top':7200000,'special':2400000,'M05':'unchanged frozen M05-2026-10-31','cohort_size':2400,'start_months':[1,2,3],'observation_months':3,'quality_days':14,'ordinary_promise_month':1800000,'fixed_prices_old_use_capacities':'unchanged','max_demand_not_predictive':'all new R100%; no payout-distribution use-response effect assumed'},
    inherited_fields=['C/R/F/U gross maximum calendars','fixed/old balances and demand','procurement/logistics/inventory/cash/reserve/dated14','15month money columns','36month full year2/3, terminal tails m18/m39','M05 stress cash/capacity conclusions'],
    recalculated_fields=['Q/QA from unique prefixed rawcases','new personal tiers/ties/FTE','own workload/HR peaks/IT','first-launch hours and new candidate key'],
    limitations=['Maximum core is conservative; tiny groups or vacant slots leave more unissued than maximum, never a source of new promises.','No inherited workload fields or pass status; no claim source/SKU/day-level stock actually ready.','Personal cap97000 unchanged and nonbinding; attainable no-tie n100 ordinary first total42500/year plus special15000=57000.'])
write('money-core-reuse.json',reuse)
# Own spec, frozen fields preserved; lineage only branch/changes.
spec=deepcopy(parent);spec['candidate_key']=KEY;spec.pop('parents',None)
spec['contests']['top_tiers']=[{'places':1,'rank':i+1,'share_group_pool':float(s),'award_R_n40':int(10000*s)} for i,s in enumerate(SLOTS)]
spec['contests']['team_rule']='One pool250*n_unique_people, four team slots40/30/20/10%; predeclared FTE shares. Personal failed share unissued; no team headcount cap and no duplicated benefit.'
spec['contests']['tie_rule']='Tie spanning ranks r..r+k-1 equally shares sum of scheduled slots1..4 intersecting ranks, including all units beyond rank4. Apply FTE after tie; floor final personal R only; no redistributed remainder.'
spec['contests']['small_groups']='One registered unit before results =>top0. Two+ registered units use fixed four-slot table; absent/unqualified slots remain unissued. Do not renormalize; no artificial team splitting.'
spec['contests']['n40_eight_teams_five_example']={'pool_R':10000,'team_top_R':[4000,3000,2000,1000],'member_top_R':[800,600,400,200],'team_member_cap_by_headcount':None}
w=spec['workload'];w['IT_initial_hours']=544;w['IT_recurring_hours_year']=156;w['launch_hours']={'HR':58,'manager':184,'employee':1800,'IT':544}
w['IT_initial_schedule']='144h m1 (120 common architecture+24 tier configuration/regression),200h m2,200h m3. New HR4+manager4 m1 before Jan14, existing launch HR38+8+8 and manager120+30+30 retained. All dates/resource readiness conditional.'
w['tier_configuration_delta']={'classification':'new design workload assumptions, not observed timing','initial_hours':{'HR':4,'manager':4,'IT':24,'employee':0},'recurring_IT_hours_month':1,'scope':'four-slot config/tie/FTE testing and revised statement; same ordinary batch and no new commission','no_hidden_savings':'all original operation minutes and sample rates unchanged'}
c=w['resource_costs_RUB']
for k in ['stationary_recognition','stationary_quality_plus_award_required_total','stationary_if_no_reusable_QA_source_incremental_total','stationary_full_source_creation_fallback_excluding_unknown_incremental_QA','stationary_full_source_creation_and_no_reusable_QA_scenario']: c[k]+=24000
c['launch_one_off']+=58000;c['first_launch_year1_recognition_and_one_off']+=82000;c['first_launch_year1_quality_plus_award_resource_required']+=82000
c['stationary_2x_labor']=2*c['stationary_recognition'];c['stationary_replacement25pct_additional_cash']=c['stationary_recognition']/4;c['stationary_2x_plus25pct_replacement_resource']=c['stationary_recognition']*2.5;c['stationary_full_source_fallback_replacement25pct_cash_excluding_unknown_incremental_QA']=c['stationary_full_source_creation_fallback_excluding_unknown_incremental_QA']/4
spec['assumptions'] += [{'id':'T01','parameter':'top_slot_shares','value':[.4,.3,.2,.1]},{'id':'T02','parameter':'new_configuration_initial_hours','value':{'HR':4,'manager':4,'IT':24}},{'id':'T03','parameter':'additional_IT_monthly_hours','value':1}]
spec['money_core_provenance']='money-core-reuse.json; exact hashes and unchanged maximum invariants, not inherited admission'
spec['finance_handoff']['no_admission']='Self-check only; independent finance/evidence required. All frozen stresses and source/QA unknowns retained; additional IT/launch hours newly costed.'
write('finance-spec-015.json',spec)
# Rebuild launch hours independently; money columns copied with SHA provenance only.
launch=deepcopy(read(R/'supporting/previous-best/first-launch.json'));launch['candidate_key']=KEY
launch['money_provenance']={'path':'supporting/previous-best/first-launch.json','sha256':digest(R/'supporting/previous-best/first-launch.json'),'scope':'unchanged full-maximum money columns only; money-core-reuse.json references36months/tails/dated14','hours':'independently recomputed from operation counts, plus explicit new configuration hours'}
FLAT=[]
for scenario,data in launch['scenarios'].items():
    for row in data['rows']:
        month=row['month'];ordinary=month>=4
        hr=22+(38 if ordinary else 0);mgr=F(200*10+48*5+12*8+10*20,60)+(64 if ordinary else 0);emp=20+(F(936,10) if ordinary else 0)
        # event decomposition: appeals/corrections/exports/secondary/rule changes begin with ordinary m4.
        assert abs(float(mgr)-(106.26666666666667 if ordinary else 42.266666666666666))<1e-7
        row['candidate_key']=KEY
        for role,amount,setup in [('HR',hr,[42,8,8]),('manager',mgr,[124,30,30]),('employee',emp,[600,600,600])]:
            row[role+'_recognition_hours']=float(amount);row[role+'_launch_hours']=setup[month-1] if month<=3 else 0;row[role+'_total_hours']=row[role+'_recognition_hours']+row[role+'_launch_hours']
        row['combined_HR_hours']=row['common_M05_HR_hours']+row['HR_total_hours'];row['combined_HR_capacity_220_pass']=row['combined_HR_hours']<=220;row['combined_HR_fallback_hours']=row['combined_HR_hours']+20
        row['IT_initial_hours']=[144,200,200][month-1] if month<=3 else 0;row['IT_recurring_hours']=13
        row['primary_QA_total_hours']=800 if ordinary else 0;row['primary_QA_if_no_reusable_source_incremental_hours']=800 if ordinary else 0
        row['manager_quality_plus_award_required_hours']=row['manager_total_hours']+row['primary_QA_total_hours']
        FLAT.append(row)
    # Refresh resource summary fields; inherit money summaries only.
    for title,summary in data['budget_year_summaries'].items():
        rows=[x for x in data['rows'] if (x['month']<=12)==('year1' in title)]
        summary['HR_combined_peak_hours']=max(x['combined_HR_hours'] for x in rows)
        summary['recognition_hours_by_role']={role:sum(x[role+'_recognition_hours'] for x in rows) for role in roles}
        summary['launch_hours_by_role']={role:sum(x[role+'_launch_hours'] for x in rows) for role in roles}
        summary['IT_initial_hours']=sum(x['IT_initial_hours'] for x in rows);summary['IT_recurring_hours']=sum(x['IT_recurring_hours'] for x in rows)
        summary['primary_QA_required_total_hours_existing_new_split_unknown']=sum(x['primary_QA_total_hours'] for x in rows)
write('first-launch.json',launch);csvout('first-launch.csv',FLAT)
csvout('rawcases-expanded.csv',RAW);csvout('strata-calculation.csv',STRATA);csvout('synthetic-results.csv',QROWS);csvout('money-examples.csv',MONEY);csvout('edge-cases.csv',EDGES);csvout('workload-comparison.csv',WORK)
write('payout-summary.json',{'candidate_key':KEY,'groups':SUMMARY,'nominal_no_tie_positions_per_cycle':{'groups':180,'old':360,'new':720,'old_fraction_people':.05,'new_fraction_people':.10,'not_unique_annual':True},'concentration':{'old_first_pool_share':.8,'new_first_pool_share':.4,'old_HHI':.68,'new_HHI':.30,'old_first_share_all_24m':.24,'new_first_share_all_24m':.12,'old_first_two_top_share':1,'new_first_two_top_share':.7},'min_value':'n40 individual1000R; equal5 member200R. Arbitrary ties/FTE no guaranteed positive minimum; fraction <1/slotR rounds0. No verified small SKU.'})
# Checks on owned artifacts and invariant fields; never financial self-admission.
assert sum(spec['monthly_calendar_R'])==24000000
for field in ['lower_tier','special','stacking','operational_metrics_assumptions','data_requirements','no_self_award_controls','dated_prefunding']:
    assert spec[field]==parent[field],field
for k in ['HR_hours_monthly','manager_hours_monthly','employee_process_hours_monthly','minutes_and_denominators','primary_QA_reconciliation','manual_fallback_additional_h_month','source_creation_fallback_additional_h_month']:
    assert spec['workload'][k]==parent['workload'][k],k
assert SUMMARY[0]['new_paid_people']==4 and SUMMARY[1]['new_paid_people']==20
assert all(s['new_paid_top_R']==10000 for s in SUMMARY)
assert [x for x in QROWS if x['scenario_id']=='BO:QA97'][0]['lower_R']==0
assert all(x['lower_R']==0 for x in QROWS if x['scenario_id'].endswith('days9'))
for scenario,data in launch['scenarios'].items():
    before=read(R/'supporting/previous-best/first-launch.json')['scenarios'][scenario]['rows']
    for old,new in zip(before,data['rows']):
        for key,value in old.items():
            if not ('hours' in key or 'capacity_220' in key): assert new[key]==value,(scenario,key)
    assert sum(x['posted_R'] for x in data['rows'] if x['month']<=12)==18600000
assert len([line for line in (O/'concept-015.md').read_text().splitlines() if line.startswith('## ')])==8
assert 'CON-011' not in (O/'concept-015.md').read_text()
assert len(MONEY)==80 and len(FLAT)==45
write('self-check.json',{'candidate_key':KEY,'status':'local_checks_pass_not_independent_admission','checks':{'five_inputs_and20_supporting_hashes':len(checked),'money_core_hashes_verified':len(reuse['references']),'invariant_Q_QA_quality_source_controls_lower_special_stacking':True,'independent_prefixed_raw_Q_QA_money':True,'one_team_one_benefit':len(set(x['benefit_id'] for x in QROWS if x['scenario_id'].startswith('T0')))==8,'same_top_qualifiers':True,'positions_not_unique_annual':True,'first_launch_45_rows_new_key_own_hours':len(FLAT),'all_money_columns_equal_maximum_core':True,'eight_sections_blinded_concept_no_lineage':True,'posting_year1_R':18600000,'conditional_tail_year1_R':5400000,'no_sealed_model_import_or_execution':True},'artifact_counts':{'rawcases':len(RAW),'strata':len(STRATA),'Q_scenarios':len(QROWS),'money_people_rows':len(MONEY),'edge_people_rows':len(EDGES)},'resource_RUB':c,'open_unknown':['bank source/readiness/API','QA existing versus new share','role engineering standard and actual FTE mix','HR/manager/internalIT availability including Jan setup','small regional SKU and employee perceived value','day14 paid appropriate inventory or segregated liquid replacement','actual effect and actual unique winner reach'],'not_done':['Independent finance/evidence/reviewer','Bank pilot or causal experiment','Real stock/catalogue/ACL verification']})
print(json.dumps({'candidate_key':KEY,'groups':SUMMARY,'counts':[len(RAW),len(QROWS),len(EDGES)],'resource':c},ensure_ascii=False))
