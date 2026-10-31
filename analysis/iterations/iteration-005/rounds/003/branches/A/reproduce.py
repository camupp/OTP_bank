"""Own-path-only desk calculation. Reads sealed money CSV/JSON; never imports a model.
Run: python3 analysis/iterations/iteration-005/rounds/003/branches/A/reproduce.py
The 8+2 minute decomposition is a falsifiable design assumption, not measured bank time.
"""
import csv, hashlib, json, math
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path

P=Path(__file__).resolve().parent
R=P.parent.parent
KEY='CON-011@v3'
def read(path): return json.loads(path.read_text())
def out(name,data): (P/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
    with (P/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
parent=read(R/'supporting/previous-best/finance-spec.json')
syn=read(R/'supporting/synthetic-examples.json')
plan=read(R/'plan.json')
hashes=[]
for base,manifest in [('inputs',read(R/'inputs/manifest.json')['files']),('supporting',read(R/'supporting/manifest.json'))]:
    for f,h in manifest.items():
        actual=sha(R/base/f);assert actual==h,(base,f)
        hashes.append({'path':base+'/'+f,'sha256':actual})
refs=[]
for ref in plan['money_core_reuse']['references']:
    assert sha(R/ref['path'])==ref['sha256']
    refs.append(ref)
frozen=['envelope_R_year','currency','N_eligible','eligibility','lower_tier','contests','special','stacking','annual_total_R','monthly_calendar_R','operational_metrics_assumptions','no_self_award_controls']

# Every component is rebuilt from acts, not inherited workload fields.
def ops(early=False,new=True,stress=False):
    rec=0 if early else 2400;groups=0 if early else 60
    appeal=0 if early else 120;corr=0 if early else 72
    special=7200 if stress else 200
    if stress: appeal=2400
    rows=[]
    def add(id,layer,role,n,oldmin,newmin,note):
        rows.append(dict(operation=id,layer=layer,role=role,frequency_month=n,old_minutes_each=oldmin,new_minutes_each=newmin,old_hours=n*oldmin/60,new_hours=n*newmin/60,removed_hours=n*(oldmin-newmin)/60,evidence_and_signers=note))
    add('fixed','award','HR',1,360,360,'Unchanged administration, nonrecipient HR')
    add('group_data_Q_QA_prepare','award','manager',groups,30,30,'Independent data owner signs same Q/QA/recipient/amount evidence, outside recipient control chain')
    add('duplicate_award_reassembly','award','HR',groups,8,0,'Removed second award-only transfer of already signed fields; common file union, no source capture removed; old8+2 is design decomposition')
    add('signed_batch_receipt','award','HR',groups,2,2,'Retain independent HR hash/count/sum/signature/ACL receipt; never recipient')
    add('posting_and_receipt','award','HR',rec,.25,.25,'Retain row posting and receipt reconciliation; no platform API/import assumption')
    add('secondary_award_sample','award','manager',rec*.1,3,3,'Independent second verifier, 10% of frozen award records, not primary QA')
    add('primary_case_QA','QA','manager',rec*20,1,1,'Independent primary QA, full critical registry; existing/new split unknown')
    add('special_intake_including_refusal','award','HR',special,4,4,'Nonrecipient HR documents eligibility/cap/reason; no discretionary own amount')
    add('special_fact_check_including_refusal','award','manager',special,10,10,'Other benefit owner verifies evidence; refusal signed with reason')
    add('special_independent_approval','award','manager',48,5,5,'48 approved awards; independent approver, then nonrecipient HR posting')
    add('special_report','award','employee',special,6,6,'Factual self-report allowed, amount not selected')
    for role,m in [('HR',6),('manager',8),('employee',5)]:add('appeal', 'award',role,appeal,m,m,'Reporter -> other appeals owner outside original decision/benefit -> other HR; preserve U')
    for role,m in [('HR',5),('manager',5),('employee',3)]:add('correction','award',role,corr,m,m,'Owner before/after -> other signer -> nonrecipient HR; same seed/rerun affected group, no self-correction approval')
    for role,m in [('HR',5),('manager',8)]:add('recusal','award',role,12,m,m,'Recipient removed from inputs/QA/approval/exception/posting; assigned outside-chain alternate signs')
    for role,m in [('HR',10),('manager',20)]:add('future_rules','award',role,10,m,m,'Independent future-only rule approval, no retrospective worsening')
    add('statement_read','award','employee',rec,2,2,'Employee explanation remains available, no new dossier')
    add('IT_maintenance','IT','IT',1,720,840,'12h existing+2h/month added file schema/hash/dedup/output checks, no API')
    return rows

opsrows=ops();csvout('workload-comparison.csv',opsrows)
def totals(rows,which):
    return {r:sum(x[which+'_hours'] for x in rows if x['role']==r and x['layer']!='QA') for r in ['HR','manager','employee','IT']}
old=totals(opsrows,'old');new=totals(opsrows,'new')
assert abs(old['HR']-60)<1e-8 and abs(new['HR']-52)<1e-8
assert abs(old['manager']-106.2666666667)<1e-7 and abs(old['employee']-113.6)<1e-8
rates={'HR':1000,'manager':1500,'employee':1000,'IT':2000}
def cost(t):return sum(t[r]*rates[r] for r in rates)
scenarios=[]
common=80+(40000000/12+96000000/12+2000000)/5000*(.02+.2/30)
for scenario in ['nominal','export_fallback','source_creation_fallback','all_eligible_peak']:
    for mul in [1,2]:
        oo=totals(ops(stress=scenario=='all_eligible_peak'),'old');nn=totals(ops(stress=scenario=='all_eligible_peak'),'new')
        source={'HR':0,'manager':0,'employee':0,'IT':0}
        if scenario in ['export_fallback','source_creation_fallback']:source.update(HR=20,manager=80)
        if scenario=='source_creation_fallback':source['manager']+=700;source['employee']+=1300
        o={r:mul*(oo[r]+source[r]) for r in rates};n={r:mul*(nn[r]+source[r]) for r in rates}
        scenarios.append(dict(scenario=scenario,labor_multiplier=mul,old_award_IT_hours=oo,new_award_IT_hours=nn,source_hours=source,primary_QA_total_hours=800*mul,primary_QA_incremental_hours=None,old_total_process_hours_excluding_common=sum(o.values())+800*mul,new_total_process_hours_excluding_common=sum(n.values())+800*mul,old_combined_HR_hours=common*mul+o['HR'],new_combined_HR_hours=common*mul+n['HR'],HR220_pass=common*mul+n['HR']<=220,separate_capacity240_pass=common*mul+n['HR']<=240,old_award_source_resource_RUB_month=cost(o),new_award_source_resource_RUB_month=cost(n),new_quality_plus_award_source_required_RUB_month=cost(n)+800*mul*1500,replacement25pct_cash_award_source_RUB_month=cost(n)*.25,replacement25pct_cash_quality_total_if_no_reusable_QA_RUB_month=(cost(n)+800*mul*1500)*.25,resource_plus25pct_replacement_RUB_month=cost(n)*1.25,actual_incremental_cash_RUB=None))
out('workload-scenarios.json',{'classification':'All minutes/flows design assumptions; calculated requirement; actual staffing/incrementality unknown','common_FULL_NEW_HR':common,'scenarios':scenarios})
display=deepcopy(opsrows)
for op,layer,role,n,om,nm,note in [
 ('export_fallback_addition','source','HR',1,1200,1200,'Full source exists, export unusable; additional20HR hours; ordinary QA/controls retained'),
 ('export_fallback_addition','source','manager',1,4800,4800,'Additional80manager hours; not source creation'),
 ('source_creation_addition','source','employee',144000,.5,.5,'Prospective case capture, additional to export fallback; not useful production'),
 ('source_creation_addition','source','manager',144000,.25,.25,'Independent case acceptance, additional to export fallback'),
 ('source_exposure_addition','source','employee',24000,.25,.25,'Exposure capture, additional100h'),
 ('source_exposure_addition','source','manager',24000,.25,.25,'Independent exposure acceptance, additional100h'),
 ('startup_total_HR','launch_once','HR',1,54*60,58*60,'Additional4HR includes1.6h shadow and2.4h training, m1'),
 ('startup_total_manager','launch_once','manager',1,180*60,184*60,'Additional4manager includes1.2h shadow and2.8h training, m1'),
 ('startup_total_employee','launch_once','employee',1,1800*60,1800*60,'No shift of file work to employees'),
 ('startup_total_IT','launch_once','IT',1,520*60,544*60,'Extra24h local template/union/schema/ACL/negative tests; no API')]:
    display.append(dict(operation=op,layer=layer,role=role,frequency_month=n,old_minutes_each=om,new_minutes_each=nm,old_hours=n*om/60,new_hours=n*nm/60,removed_hours=n*(om-nm)/60,evidence_and_signers=note))
csvout('workload-comparison.csv',display)
out('time-sensitivity.json',{'classification':'Design sensitivity, not bank observations','at60groups_saved_HR_h_month_equals_removed_min_group':True,'IT_extra_h_month':2,'net_hours_saved_formula':'d-2 where d is verified duplicate minutes/group at60groups','resource_saved_RUB_month_formula':'1000*d-4000','positive_hours_requires_d_gt':2,'positive_stationary_resource_requires_d_gt':4,'planned_d':8,'maximum_removable_from10min_if2min_receipt_retained':8,'fallback220_needs_d_at_least':common+60+20-220,'fallback220_unreachable_by_this8min_operation_alone':True,'startup_incremental_hours':32,'startup_incremental_resource_RUB':58000,'launch_year1_net_hours_saved':16,'launch_year1_incremental_resource_RUB':34000,'expected_resource_payback_approximately_month':21})

control=[]
for role in ['employee','manager_recipient','HR_recipient','data_owner_recipient','team_manager_recipient']:
    recipient=role+'-person';beneficiaries={recipient}
    if role=='team_manager_recipient':beneficiaries.add('team-member')
    for stage in ['input_approval','QA','award_approval','correction','exception_or_appeal','posting']:
        good=['outside-chain-owner','independent-verifier','alternate-HR']
        assert not beneficiaries.intersection(good)
        assert beneficiaries.intersection([recipient])
        control.append({'recipient_role':role,'stage':stage,'positive_signers':good,'own_signer_rejected':True,'inside_reporting_chain_rejected_for_manager_or_team':role in ['manager_recipient','team_manager_recipient'],'bank_ACL_verified':False})
out('control-checks.json',{'classification':'Designed authorization rules, synthetic negative cases; actual bank ACL not tested','checks':control,'missing_source_status':'pending_restoration; preserve proven U and conditional disputed reserve; cannot output Q0 from missing file','alternate_unavailable_status':'incident; preserve U; no recipient substitutes for independent signer'})

# Exact arithmetic from raw standard units and stratum hours, QA hashed on actual unique IDs.
details=[];money=[]
def assess(family,mult,prefix,days=None,controlled=None):
    f=deepcopy(syn['families'][family]);records=f['records'];mult=F(mult)
    if controlled is not None:records=controlled
    benefit=prefix+'::'+f['benefit_id']
    for x in records:x['case_id']=prefix+'::'+x['case_id']
    strata=[];q=F(0)
    for sid,s in f['strata'].items():
        units=sum(F(x['accepted_units']) for x in records if x['stratum']==sid)
        # Controlled quality-only tests explicitly create sufficient units & matching hours.
        hours=F(s['base_productive_hours'])/mult if controlled is None else units/F(s['benchmark_units_per_hour'])/mult
        term=F(s['mix_weight'])*units/hours/F(s['benchmark_units_per_hour']) if hours else F(0)
        q+=term;strata.append({'stratum':sid,'accepted_standard_units':str(units),'productive_hours':str(hours),'mix_weight':s['mix_weight'],'benchmark':s['benchmark_units_per_hour'],'Q_term':str(term)})
    def h(x):return hashlib.sha256(','.join([f['window_id'],benefit,x['case_id'],f['qa_seed']]).encode()).hexdigest()
    sample=records if len(records)<=20 else sorted(records,key=h)[:20]
    mean=sum(F(max(0,100-2*x['minor']-10*x['major'])) for x in sample)/len(sample)
    n=len(records);units=sum(F(x['accepted_units']) for x in records)
    critical=any(x['critical'] for x in records);ret=F(sum(x['reopened_or_returned'] for x in records),n);sla=F(sum(x['sla_met'] for x in records),n)
    it=family=='IT_team';minimum=8 if it else 20;qa=97 if family=='support' else 98;d=days if days is not None else f['exposure_days']
    reasons=[]
    for bad,reason in [(n<minimum,'insufficient_cases'),(not it and units<(100 if family=='support' else 80),'insufficient_units'),(d<10,'exposure_below10'),(mean<qa,'QA_below_threshold'),(critical,'full_registry_critical'),(ret>(F(2,100) if family=='backoffice' else F(5,100)),'return_reopen'),(it and sla<F(95,100),'SLA'),(q<1,'Q_below1')]:
        if bad:reasons.append(reason)
    a={'id':prefix,'family':family,'locator':f'supporting/synthetic-examples.json#/families/{family}/records + strata; profile hours / multiplier={mult}','benefit_id':benefit,'case_count':n,'accepted_units':str(units),'strata':strata,'Q_exact':str(q),'Q':float(q),'QA_mean':float(mean),'sample_case_ids':[x['case_id'] for x in sample],'sample_rule':'sha256(comma-joined windowID,benefitID,caseID,seed); independent published seed','critical_all_registry':critical,'return_fraction':float(ret),'SLA_fraction':float(sla),'days':d,'lower_R':500 if not reasons else 0,'top_eligible':not reasons and q>=F(11,10),'rank_Q_hundredths':math.floor(q*100+F(1,2)),'failure_reasons':reasons}
    details.append(a);return a
def row(scenario,who,a,top=0,place='',special=0,note='',shares='1'):
    lower=a['lower_R'] if a else 0
    money.append(dict(scenario=scenario,participant=who,family=a['family'] if a else 'special',benefit_id=a['benefit_id'] if a else who,Q_exact=a['Q_exact'] if a else '',QA=a['QA_mean'] if a else '',exposure_days=a['days'] if a else '',place=place,FTE_share=shares,parent_lower_R=lower,candidate_lower_R=lower,parent_top_R=top,candidate_top_R=top,parent_special_R=special,candidate_special_R=special,total_R=lower+top+special,parent_right_date='2027-04-28 18:00' if a else 'independent confirmation',candidate_right_date='2027-04-28 18:00' if a else 'independent confirmation',posting_date='2027-04-28 19:00' if a else 'immediate SLA after confirmation',signer='independent data/QA owner -> second verifier sample -> nonrecipient HR; recipient excluded',note=note))
def distribute(assessments,n,shares=None):
    # Parent two80/20 slots applied independently of HR file procedure.
    if len(assessments)==1:return [F(0)]
    result=[F(0)]*len(assessments);eligible=[i for i,a in enumerate(assessments) if a['top_eligible']]
    eligible.sort(key=lambda i:-assessments[i]['rank_Q_hundredths']);j=0;pool=250*n
    while j<len(eligible):
        k=j+1
        while k<len(eligible) and assessments[eligible[k]]['rank_Q_hundredths']==assessments[eligible[j]]['rank_Q_hundredths']:k+=1
        prize=sum([F(pool*4,5) if z==0 else F(pool,5) if z==1 else F(0) for z in range(j,k)])/(k-j)
        for i in eligible[j:k]:result[i]=prize
        j=k
    return result

for fam in syn['families']:
    for p in syn['Q_profiles']:
        a=assess(fam,p['productivity_multiplier'],fam+'-'+p['profile']);row('profiles',a['id'],a,note='Independent profile, single registered unit => top0; past baseline unused')
for fam in ['support','backoffice']:
    aa=[assess(fam,m,f'{fam}-person{i+1:02}') for i,m in enumerate(syn['individual_group_40']['multipliers'])]
    tt=distribute(aa,40)
    for i,(a,t) in enumerate(zip(aa,tt)):row('individual40-'+fam,a['id'],a,math.floor(t),1 if i==0 else 2 if i==1 else '',note='HR recipient person2 uses outside-chain data owner and alternate HR' if i==1 else '')
aa=[assess('IT_team',m,f'IT-team{i+1:02}') for i,m in enumerate(syn['team_group_40']['multipliers'])];tt=distribute(aa,40)
for i,(a,t) in enumerate(zip(aa,tt)):
    for j in range(5):row('8teams5',f'team{i+1}-member{j+1}',a,math.floor(t/5),i+1 if i<2 else '',shares='1/5',note='One shared team benefit, one QA act; team1 includes manager, verifier outside reporting chain')
for scenario,n,mults in [('tie40',40,['6/5']*40),('tie_last',40,['7/5']+['6/5']*3+['1']*36),('tie_first3',40,['6/5']*3+['1']*37),('group1',1,['6/5']),('group2',2,['6/5','11/10']),('group5',5,['6/5','11/10','1','1','1']),('group60',60,['7/5','13/10']+['1']*58),('only_one_qualifies',40,['6/5']+['1']*39)]:
    aa=[assess('support',m,f'{scenario}-person{i+1}') for i,m in enumerate(mults)];tt=distribute(aa,n)
    for a,t in zip(aa,tt):row(scenario,a['id'],a,math.floor(t),note='Residual/unoccupied slot remains F, never redistributed')
aa=[assess('IT_team','6/5',f'team-all-tie-{i+1}') for i in range(8)];tt=distribute(aa,40)
for i,(a,t) in enumerate(zip(aa,tt)):
    for j in range(5):row('team_all_tie',f'team{i+1}-member{j+1}',a,math.floor(t/5),shares='1/5',note='One benefit/QA per team, shared slot across8teams then FTE')
# Unequal teams / FTE, including one ineligible share.
for scenario,ss in [('teams3and7',[[F(1,3)]*3,[F(1,7)]*7]),('FTE25_75',[[F(1,4),F(3,4)],[F(1)]]),('ineligible_member_share',[[F(1,5)]*5,[F(1,5)]*5])]:
    n=10 if scenario!='FTE25_75' else 40
    aa=[assess('IT_team',m,scenario+'-team'+str(i)) for i,m in enumerate(['6/5','11/10'])];tt=distribute(aa,n)
    for i,(a,t) in enumerate(zip(aa,tt)):
        for j,s in enumerate(ss[i]):
            b=deepcopy(a)
            if scenario=='ineligible_member_share' and i==0 and j==4:b['lower_R']=0
            row(scenario,f'{scenario}-team{i}-member{j}',b,0 if b['lower_R']==0 else math.floor(t*s),shares=str(s),note='Ineligible personal share unissued; one source benefit, no other department award')

# Supplemental quality-only fixtures, explicitly constructed from shared templates.
for fam in syn['families']:
    for n in [10,20,60]:
        f=syn['families'][fam];recs=[]
        for i in range(n):
            x=deepcopy(f['records'][i%len(f['records'])]);x['case_id']=f'controlled-{i+1}';x['stratum']='s1' if i<n//2 else 's2';x['accepted_units']=max(10,x['accepted_units']);recs.append(x)
        # New controlled fixtures: units>=100, matching hours, two populated strata.
        a=assess(fam,'6/5',f'quality-{fam}-n{n}',controlled=recs);row('quality_n',a['id'],a,note='Supplemental constructed fixture, >=10 standard units/case; hours recomputed from units/benchmark/1.2; not original bank/raw observation')
for days in [9,10]:
    a=assess('support','6/5','exposure'+str(days),days=days);row('exposure',a['id'],a)
recs=deepcopy(syn['families']['backoffice']['records'])
for i,x in enumerate(recs):x['minor']=2 if i<10 else 1
a=assess('backoffice','6/5','QA97',controlled=recs);row('QA97_backoffice',a['id'],a,note='QA97 <98, lower0 despite Q1.2')
# Find a case outside SHA sample with the exact prefix used, then flag critical.
base=assess('support','6/5','critical-outside-sample')
recs=deepcopy(syn['families']['support']['records']);outside=next(x for x in recs if 'critical-outside-sample::'+x['case_id'] not in base['sample_case_ids']);outside['critical']=True
a=assess('support','6/5','critical-outside-sample',controlled=recs);assert not any('::'+outside['case_id']==x[-len(outside['case_id'])-2:] for x in a['sample_case_ids']);row('critical',a['id'],a,note='Critical outside sample still fails whole registry')
for case,amount,note in [('special_one_team',2500,'Unusual implemented benefit; different benefitID, other owner confirms'),('special_two_processes',7500,'Implemented in2 processes; independent evidence'),('special_same_benefit_rejected',0,'Same ordinary benefit without distinct incremental evidence => refusal'),('special_person_cap',0,'Already2 awards/year => no third; old earned rights retained'),('special_HR_recipient',2500,'Business owner+other HR; recipient cannot input-approve/correct/post'),('special_exact_tie',1250,'Two confirmations tied for final2500 slot; one slot shared')]:row('special',case,None,special=amount,note=note)
csvout('money-examples.csv',money);out('rawcase-calculations.json',{'classification':'Synthetic calculations, full standard units counted once, not bank data','hash_format':'windowID,benefitID,caseID,seed comma joined UTF8','calculations':details,'missing_source':'pending restoration/U retained, never fabricated Q0'})
assert all(x['parent_'+k+'_R']==x['candidate_'+k+'_R'] for x in money for k in ['lower','top','special'])
assert all(x['parent_right_date']==x['candidate_right_date'] for x in money)
# Golden amounts guard the shared frozen rule, not just equality of copied columns.
for scenario,expected in [('individual40-support',[8000,2000]),('8teams5',[1600]*5+[400]*5),('group60',[12000,3000]),('group1',[0]),('group2',[400,100]),('tie_first3',[3333]*3),('tie_last',[8000,666,666,666])]:
    rr=[x for x in money if x['scenario']==scenario]
    assert [x['candidate_top_R'] for x in rr[:len(expected)]]==expected,scenario
assert all(x['candidate_top_R']==250 for x in money if x['scenario'] in ['tie40','team_all_tie'])
assert sum(x['candidate_top_R'] for x in money if x['scenario']=='teams3and7')==2495
assert all(x['candidate_lower_R']==0 for x in money if x['scenario'] in ['QA97_backoffice','critical'])
assert 7200*4*500+7200*4*250+12*200000==24000000
# Different award file paths: parent copies/reassembles signed rows, candidate uses
# a lossless local-file union. The consumer and platform row posting are unchanged.
consumer_fields=['participant','benefit_id','Q_exact','QA','exposure_days','place','FTE_share','candidate_right_date']
canonical=[{k:x[k] for k in consumer_fields}|{'lower':x['candidate_lower_R'],'top':x['candidate_top_R'],'special':x['candidate_special_R']} for x in money]
old_reassembled=[dict(x) for x in canonical]
new_union=[]
for i in range(0,len(canonical),40):new_union.extend(deepcopy(canonical[i:i+40]))
assert old_reassembled==new_union
out('file-contract-check.json',{'classification':'Synthetic file contract test, not production-ready software or bank capability evidence','signed_row_fields':consumer_fields+['lower','top','special'],'parent_reassembly_sha256':hashlib.sha256(json.dumps(old_reassembled,sort_keys=True).encode()).hexdigest(),'candidate_lossless_union_sha256':hashlib.sha256(json.dumps(new_union,sort_keys=True).encode()).hexdigest(),'rows_equal':len(canonical),'signatures':'Owner signs group hash after source/QA freeze; HR verifies hash/count/sum and keeps posting receipts; signatures not simulated as actual bank signatures','prohibited':'Output cannot invent missing source or replace independent QA/control. Recipient ID is checked against signers at every stage; own record routed to alternate batch.'})

# Money core unchanged; own hours rebuilt for every first-launch row.
launch=read(R/'supporting/previous-best/first-launch.json');launch['candidate_key']=KEY
launch['money_provenance']='Money fields read unchanged from supporting/previous-best/first-launch.json, SHA in money-core-reuse.json; own hours recalculated by reproduce.py;36months/tails/dated14 by exact sealed core references'
launch['not_independent_admission']=True
allrows=[];money_unchanged=0
for scenario,v in launch['scenarios'].items():
    for x in v['rows']:
        m=x['month'];t=totals(ops(early=m<4),'new');x['candidate_key']=KEY
        for role,sched in [('HR',[42,8,8]),('manager',[124,30,30]),('employee',[600,600,600])]:
            field='employee' if role=='employee' else role
            x[field+'_recognition_hours']=t[role];x[field+'_launch_hours']=sched[m-1] if m<=3 else 0
            x[field+'_total_hours']=x[field+'_recognition_hours']+x[field+'_launch_hours']
        x['IT_initial_hours']=[144,200,200][m-1] if m<=3 else 0;x['IT_recurring_hours']=t['IT']
        x['primary_QA_total_hours']=0 if m<4 else 800
        x['primary_QA_verified_existing_hours']=None;x['primary_QA_actual_incremental_hours']=None
        x['primary_QA_if_no_reusable_source_incremental_hours']=x['primary_QA_total_hours']
        x['manager_quality_plus_award_required_hours']=x['manager_total_hours']+x['primary_QA_total_hours']
        # Rebuild the common M05 workload from NEW REQUESTS, including cold-shop queues.
        x['common_M05_HR_hours']=80+x['requested_C']/5000*(.02+.2/30)
        x['combined_HR_hours']=x['common_M05_HR_hours']+x['HR_total_hours'];x['combined_HR_capacity_220_pass']=x['combined_HR_hours']<=220
        # Parent reserves20h export fallback also during preparation: do not erase it.
        x['combined_HR_fallback_hours']=x['combined_HR_hours']+20
        x['money_provenance']='supporting/previous-best/first-launch.json#/scenarios/'+scenario+'/rows/'+str(m-1)
        allrows.append(x)
    for name,summary in v['budget_year_summaries'].items():
        rr=v['rows'][:12] if 'year1_' in name else v['rows'][12:15]
        summary['HR_combined_peak_hours']=max(x['combined_HR_hours'] for x in rr)
        summary['HR_export_fallback_peak_hours']=max(x['combined_HR_fallback_hours'] for x in rr)
        summary['recognition_hours_by_role']={role:sum(x[role+'_recognition_hours'] for x in rr) for role in ['HR','manager','employee']}
        summary['launch_hours_by_role']={role:sum(x[role+'_launch_hours'] for x in rr) for role in ['HR','manager','employee']}
        summary['IT_initial_hours']=sum(x['IT_initial_hours'] for x in rr);summary['IT_recurring_hours']=sum(x['IT_recurring_hours'] for x in rr)
        summary['primary_QA_required_total_hours_existing_new_split_unknown']=sum(x['primary_QA_total_hours'] for x in rr)
out('first-launch.json',launch);csvout('first-launch.csv',allrows)
oldlaunch=read(R/'supporting/previous-best/first-launch.json')
own_fields={k for k in allrows[0] if 'hours' in k or k in ['candidate_key','money_provenance','combined_HR_capacity_220_pass']}
for s,v in launch['scenarios'].items():
    for a,b in zip(v['rows'],oldlaunch['scenarios'][s]['rows']):
        for k in b:
            if k not in own_fields:assert a[k]==b[k],k;money_unchanged+=1

spec=deepcopy(parent);spec.update(candidate_key=KEY,parents=['CON-011@v2'])
spec['rights_calendar'].update(first_launch_json='branches/A/first-launch.json',first_launch_csv='branches/A/first-launch.csv',first_launch_months=15)
spec['dated_prefunding']['independent_dated_ledger']='../002/checks/finance/date-prefunding.csv';spec['dated_prefunding']['path_base']='rounds/003; inherited money locator CON-011@v2'
w=spec['workload'];w['HR_hours_monthly']=[new['HR']]*12;w['manager_hours_monthly']=[new['manager']]*12;w['employee_process_hours_monthly']=[new['employee']]*12
w['IT_initial_hours']=544;w['IT_recurring_hours_year']=168;w['launch_hours']={'HR':58,'manager':184,'employee':1800,'IT':544}
w['minutes_and_denominators']['export_HR_min_group']=2
w['new_procedure']={'removed':'HR repeated award-only reassembly8min/group; receipt2min retained, manager signed input30min and row posting.25min retained','classification':'8+2 split of parent10min is new design decomposition, needs time observation; not discovered bank fact','IT_extra_initial_hours':24,'IT_extra_recurring_hours_month':2,'HR_extra_launch_hours':4,'manager_extra_launch_hours':4,'ordinary_groups_month':60,'no_API':'Existing owner creates same award fields once in fixed local workbook/CSV, offline union+validation, signed file to HR. Current platform row posting retained. Schema unsupported => old path+fail, not assumed API.'}
w['IT_initial_schedule']='144/200/200h in m1/m2/m3 before corresponding cohort; extra24 in m1 Jan2-14; availability unknown'
w['capacity']=f'common220 unchanged; stationary FULL_NEW common{common}+own52={common+52}; exportfallback{common+72}>220 FAIL; no artificial norm adjustment'
w['resource_costs_RUB']={'stationary_recognition':cost(new)*12,'launch_one_off':58*1000+184*1500+1800*1000+544*2000,'primary_QA_component_stationary':14400000,'stationary_quality_plus_award_required_total':cost(new)*12+14400000,'stationary_actual_incremental_total':None,'stationary_2x_labor':cost(new)*24,'stationary_replacement25pct_additional_cash':cost(new)*12*.25,'stationary_2x_plus25pct_replacement_resource':cost(new)*24*1.25,'stationary_full_source_creation_fallback_excluding_unknown_incremental_QA':cost(new)*12+29880000,'stationary_full_source_creation_and_no_reusable_QA_scenario':cost(new)*12+29880000+14400000}
yr=launch['scenarios']['FULL_NEW']['budget_year_summaries']['year1_months1_12'];yr_cost=sum((yr['recognition_hours_by_role'][r]+yr['launch_hours_by_role'][r])*rates[r] for r in ['HR','manager','employee'])+(yr['IT_initial_hours']+yr['IT_recurring_hours'])*rates['IT']
w['resource_costs_RUB']['first_launch_year1_recognition_and_one_off']=yr_cost
w['resource_costs_RUB']['first_launch_year1_quality_plus_award_resource_required']=yr_cost+10800000
w['resource_costs_RUB']['stationary_export_fallback_excluding_unknown_incremental_QA']=cost(new)*12+1680000
w['resource_costs_RUB']['stationary_export_fallback_if_no_reusable_QA']=cost(new)*12+1680000+14400000
spec['data_requirements']+=['Award file schema/local union not current bank capability:24IT setup+2IT/month+4HR/4manager training; preserve source readiness and all fallback hours. Sender signs fixed data; control hashes/counts/totals archived. No change in person money/date.']
spec['assumptions']+= [{'id':'A20','parameter':'HR_export_decomposition_min_group','value':'8 duplicate reassembly+2 independent receipt'}, {'id':'A21','parameter':'IT_extra_recurring_h_month','value':2},{'id':'A22','parameter':'extra_launch_hours','value':{'HR':4,'manager':4,'IT':24}}]
out('finance-spec-011.json',spec)
assert all(parent[k]==spec[k] for k in frozen)
for k in parent['dated_prefunding']:
    if k not in ['independent_dated_ledger','path_base']:assert parent['dated_prefunding'][k]==spec['dated_prefunding'][k]
with (R/'supporting/previous-best/assumptions.csv').open() as f:assumptions=list(csv.DictReader(f))
for x in assumptions:
    if x['id']=='B10':x['value']='HR52/manager106.2667/employee113.6/IT14; primary QA800 separate';x['source_locator']='finance-spec-011.json workload; reproduce.py ops';x['type']='calculation_from_design'
    if x['id']=='B11':x['value']='HR58/manager184/employee1800/IT544';x['validation_limit']='IT144/200/200 m1/m2/m3; extra4HR+4manager includes bounded12group shadow/training; named capacity unknown'
    if x['id']=='B13':x['validation_limit']='Same additional source/export hours; HR223.111>220 stationary; source unknown, not new API'
for id,parameter,value,unit,typ,loc,limit in [
 ('A20','HR_duplicate_decomposition','8 duplicate+2 receipt of old10','minutes/group at60groups/month','new_design_hypothesis','reproduce.py ops; changes.md','Not separately observed in parent/bank; absence of duplicate rejects improvement'),
 ('A21','new_local_file_IT','24initial+2recurring','hours once + hours/month','new_design','finance-spec-011.json workload.new_procedure','Local table/CSV union, schema/signature controls; no new platformAPI; row posting retained'),
 ('A22','HR_manager_training_shadow','4HR+4manager','hours once m1','new_design','concept-011.md section6; first-launch.json','HR1.6shadow+2.4training; manager1.2shadow+2.8training;12synthetic groups, no claim observed bank duplicate'),
 ('A23','net_stationary_effect','HR-8/manager0/employee0/IT+2;total-6','hours/month at parent flow','calculation','workload-comparison.csv; workload-scenarios.json','First year34kRUB resource increase; not procurement cash savings'),
 ('A24','nominal_export_HR_stationary','203.111/223.111','common+award hours/month against220','calculation','workload-scenarios.json','Export fail retained; startup nominal205.511/export225.511 includes training, extra20capacity separate'),
 ('A25','bank_source_schema_ACL_IT_readiness','unknown','actual readiness/time/staffing','unknown','inputs/evidence.md C07; control-checks.json','Synthetic ACL rules and file hashes are not bank access-control validation'),
 ('A26','quality_only_extra_fixtures','n10/20/60; at least10 standardunits/case','constructed case and matching productive hours','supplemental_synthetic_design','reproduce.py controlled fixtures','Explicit additions to shared template, not original bank data or frozen case evidence')]:
    assumptions.append(dict(id=id,parameter=parameter,value=value,unit_period_denominator=unit,type=typ,source_locator=loc,validation_limit=limit))
csvout('assumptions-011.csv',assumptions)
reuse={'candidate_key':KEY,'parent':'CON-011@v2','path_base':'rounds/003','references':refs,'supporting_first_launch_sha256':sha(R/'supporting/previous-best/first-launch.json'),'inputs_and_supporting_hashes':hashes,'invariants':{k:parent[k] for k in frozen if k not in ['no_self_award_controls','operational_metrics_assumptions']},'invariant_checks':['Q/QA/source readiness and flow unchanged','lower/top80-20/special every personal amount and dates unchanged','annual24m, monthly2m, same starts and four rightsm13/14/15','same M05 prices/demand/regions/old rights/fixed/220h','same15/36month currency, cash, reserve, U/F, stock, requested/received queue, terminalm18/m39 and grossday14'],'inherited_fields':'All monetary/currency/calendar/inventory/request/received/reserve fields only; see own_fields_excluded. Aggregatefull36 and stress rows are referenced, not recomputed or relabelled as new independent checks.','own_fields_excluded':sorted(own_fields),'own_recalculated':['personal synthetic examples','all workload/minutes/peaks/costs','first-launch row and summary hours'],'first_launch_money_cells_equal':money_unchanged,'bank_readiness':'unknown; no independent financial admission inherited'}
out('money-core-reuse.json',reuse)
out('self-check.json',{'candidate_key':KEY,'status':'local_calculations_pass_not_independent_admission','hashes_verified':len(hashes)+len(refs),'money_invariants_equal':frozen,'first_launch_money_cells_equal':money_unchanged,'synthetic_assessments':len(details),'money_rows_identical_parent':len(money),'raw_to_Q_QA_payout_reproducible':True,'own_HR_old_new':[old['HR'],new['HR']],'award_IT_total_hours_old_new':[sum(old.values()),sum(new.values())],'net_stationary_hours_saved_month':sum(old.values())-sum(new.values()),'HR_peak_stationary_nominal':common+new['HR'],'HR_export_fallback_stationary':common+new['HR']+20,'HR_peak_launch_year1_nominal':yr['HR_combined_peak_hours'],'HR_peak_launch_year1_export_fallback':yr['HR_export_fallback_peak_hours'],'HR_export_fallback220_pass':False,'new_award_year_resource_RUB':cost(new)*12,'old_award_year_resource_RUB':cost(old)*12,'year1_resource_RUB':yr_cost,'unknown':['whether parent group10min actually includes8min duplicate assembly','actual minutes/schema/data/QA staffing/IT calendar/ACL','actual source-ready split existing versus new QA','low catalogue SKU/value','actual bank cash/stock/segregated reserve','employee understanding and business effect'],'fail_conditions':['duplicate absent or controller workload transferred beyond costed2IT hours','exportfallback220 remains fail','all-eligible peak, x2 labor, regional/quarter/cold/old stress fail preserved'],'independent_checks_required':['finance','evidence','blinded review']})
print(json.dumps({'candidate':KEY,'HR_old_new':[old['HR'],new['HR']],'HR_fallback':common+72,'net_hours_saved_month':sum(old.values())-sum(new.values()),'money_rows':len(money),'money_cells_preserved':money_unchanged,'resource_stationary_RUB':cost(new)*12,'year1_RUB':yr_cost},ensure_ascii=False))
