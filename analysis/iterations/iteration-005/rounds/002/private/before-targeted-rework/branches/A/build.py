"""CON-013v2: reproducible design arithmetic. Writes only this branch.
M05 imported read-only; all new calendars/labour are explicit assumptions.
"""
from pathlib import Path
import csv, json, math, hashlib, importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
ROUND=HERE.parents[1]
inputs=json.loads((ROUND/'inputs/baseline.md').read_text().split('```json\n')[-1].split('\n```')[0])
loader=importlib.util.spec_from_file_location('m05',ROOT/'analysis/preparation/iteration-005-finance-basis/model.py')
m05=importlib.util.module_from_spec(loader); loader.loader.exec_module(m05)

def dump(name, obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# 2400 ordinary bundles/month. All primary QA is valued, including ready acts.
N=2400;metric=1440;artifact=960;ready=.7;avg_n=42.5
qa_metric=metric*avg_n*.5/60
qa_artifact=artifact*3*12/60
qa=qa_metric+qa_artifact
evidence_metric=metric*avg_n*.25/60
evidence_artifact=artifact*3*20/60
hr=12+40*10/60+N*.25/60+N*.1*2/60+N*.02*5/60+N*.01*3/60+40*5/60
manager=qa+40*10/60+N*ready*1/60+N*(1-ready)*3/60+N*ready*.1*2/60+N*.1*5/60+N*.02*8/60+N*.01*5/60+40*12/60
employee_process=N*3/60+N*.1*4/60+N*.02*4/60+40*6/60
employee_evidence=evidence_metric+evidence_artifact
employee=employee_process+employee_evidence
rates=inputs['common']['rates_rub_hour']

spec={
 'schema_version':1,'candidate_key':'CON-013@v2','parents':['CON-013@v1'],
 'classification':'Frozen M05 numbers are scenario assumptions, not bank observations. All changed quality, timing and workload parameters are new design assumptions; outputs are calculations.',
 'envelope_R_year':24000000,'currency':'R; fixed C preserved; R_to_C=1, no reverse conversion',
 'N_eligible':7200,'eligibility_rule':'All objectively comparable role/exposure groups, including HR/managers. One home card/cohort per cycle; no application quota; fallback artifact route available before effort.',
 'lower_tier':{'N':7200,'cycles_year':4,'award_R':500,'max_awards_person_year':4,'formula':'7200*4*500','annual_max_R':14400000},
 'contests':{'groups':120,'scenario_group_size_people':60,'group_size_cap_people':60,'cycles_year':4,
   'group_pool_formula':'250 R*eligible headcount per cycle; all groups together 1,800,000 R/cycle',
   'top_tiers':[{'place':1,'places':1,'award_R':7500,'pool_fraction':'1/2'},{'place':2,'places':1,'award_R':5000,'pool_fraction':'1/3'},{'place':3,'places':1,'award_R':2500,'pool_fraction':'1/6'}],
   'annual_max_R':7200000,'formula':'120*4*(7500+5000+2500)',
   'group_scaling':'For headcount h<=60: pool=250*h; rank1=floor(pool*100/2)/100, rank2=floor(pool*100/3)/100, rank3=pool-rank1-rank2. Fixed role/card tracks funded by headcount before effort; no cross-metric raw ranking.',
   'tie_rule':'For tied units occupying r..r+k-1 pool ONLY funded rank slots in intersection with 1..3; equal floor-to-0.01R shares; remainder stays unissued F. No extra places. Tie spanning rank3 includes all tied units.',
   'team_share_formula':'A personal unit must have independent acceptance. Shared indivisible benefit is ONE top unit; its predeclared weights sum1 and home-group budget is counted once. Shares floor to0.01R, remainder F. Each person separately earns lower only on accepted personal contribution. 8 teams of5 in a40-person group share at most10,000R top, not8 times the pool.',
   'minimum_level':'L2; single entrant may receive only slot1. Vacant slots stay F, not automatically reassigned.'},
 'special':{'levels':[{'award_R':5000,'max_count_year':240},{'award_R':10000,'max_count_year':120}],
   'monthly_caps':{'5000_R_count':20,'10000_R_count':10},'annual_max_R':2400000,
   'confirmation':'Independent benefit owner verifies one useful adopted result outside ordinary card (5000R), two independent departments/processes adopting same result (10000R). Fund custodian different from receiver posts authorized amount. Finite contest: excess tied qualified cases split funded slots, not guaranteed level amount.',
   'ordering':'10000 and5000 tracks separate; order by number of independent adopting processes then earliest finalized evidence timestamp. Exact ties split occupied slots; no winner chosen by sympathy.'},
 'stacking':{'base_plus_top':'Explicitly allowed for same root benefit and fully reserved',
   'special_same_root':'Forbidden with ordinary or salary result bonus for same root benefit; different verified root may stack.',
   'max_special_person_cycle':1,'max_person_R_year':72000,'formula':'4*500 +4*7500 +4*10000; rolling4 ordinary cycles and rolling12 months for special, no fiscal-boundary reset'},
 'annual_total_R':24000000,'monthly_calendar_R':[2000000]*12,
 'calendar_components':{'lower_R':[1200000]*12,'top_R':[600000]*12,'special_R':[200000]*12},
 'calendar_scope':'STATIONARY only: 3 cohorts balanced at2400 people, one ordinary closure/month;4 windows/person/year. Full maximum, not forecast success. Startup first-launch.csv separate; no earnings before announcement.',
 'workload':{'HR_hours_monthly':[hr]*12,'manager_hours_monthly':[manager]*12,'employee_process_hours_monthly':[employee]*12,
   'employee_submission_hours_monthly':[employee_process]*12,
   'employee_evidence_creation_hours_monthly':[employee_evidence]*12,'employee_total_nonuseful_hours_monthly':[employee]*12,
   'IT_initial_hours':400,'IT_recurring_hours_year':120,'employee_useful_work_hours_year':103680,
   'flow':{'ordinary_people_month':2400,'groups_month':40,'metric_people_month':1440,'artifact_people_month':960,'max_units_artifact_person':3,'ready_independent_act_share':.7,'new_act_share':.3,'special_applications_month':40,'special_accepted_month':30,'correction_fraction':.1,'appeal_fraction':.02,'recusal_fraction':.01,'ready_act_audit_fraction':.1},
   'primary_QA':{'metric_observations_mean':42.5,'basis':'Equal scenario shares of n10/20/60/80 in metric population','metric_independent_minutes_per_observation':.5,'metric_hours_month':qa_metric,'artifact_minutes_unit':12,'artifact_minutes_breakdown':'10 expected-output cases*0.6min +2 independent reproductions*2min +2 actual-use records*1min. 30day surveillance from logs; timestamp included, not30days continuous labour.','artifact_hours_month':qa_artifact,'total_hours_month':qa,'existing_function_hours_month':qa*.7,'new_function_hours_month':qa*.3,'classification':'70% already necessary independent quality acts reused,30% acts newly commissioned; ALL included in manager_hours, none free. Ready existence scenario, not bank fact.'},
   'evidence_creation':{'metric_minutes_observation':.25,'metric_hours_month':evidence_metric,'artifact_minutes_unit':20,'artifact_hours_month':evidence_artifact,
      'existing_business_hours_month':evidence_metric+evidence_artifact*.7,'required_incremental_hours_month':evidence_artifact*.3,
      'classification':'Scenario only: metric data255h and70%artifact test packages672h already required for business,30%test packaging288h newly commissioned for program. All1215h valued once; not all incremental. Actual overlap unknown. Artifact construction/useful work separate.'},
   'verification_minutes':{'HR':{'fixed_hours':12,'group_packet':10,'person_reconcile':.25,'correction':2,'appeal':5,'recusal':3,'special_application':5},'manager':{'group_packet':10,'ready_act_scope_signature':1,'new_act_ledger_check_after_QA':3,'ready_act_risk_audit':2,'correction':5,'appeal':8,'recusal':5,'special_application':12},'employee':{'submission':3,'correction':4,'appeal':4,'special_application':6}},
   'initial_preparation_hours':{'HR':50,'manager':480,'employee_training':720,'IT':400},
   'useful_work':'metric1440*2h +artifact960*3units*2h=8640h/month. Productive ordinary work distinct; not claimed incremental or free. Scope may require more hours; 2x stress applies.',
   'scope':'employee_process_hours_monthly INCLUDES evidence creation; submission and evidence arrays are breakdowns, not additive again. Own process/evidence/QA only; common basket handling M05 added separately. Primary QA included once; ready-act recheck not a second full acceptance.'},
 'fallback':{'scenario':'All ordinary people artifact route, no ready acts; before effort choose this if data unusable',
   'HR_hours_month':hr,'manager_hours_month':manager-qa-64-5.6+1440+120,'employee_evidence_hours_month':2400,'employee_process_hours_month':employee_process,
   'condition':'Requires separately named independent owners and360? no:2400*3=7200 unit acts/month. Cannot silently use nominal resources.'},
 'data_requirements':['Versioned preannounced card, assignment/exposure/benchmark list, salary-bonus root mapping','Full denominator assigned cohort records, final timestamps and independent QA per record; missing data remains pending','Act with root ID, case IDs, numerator/denominator, all tests, usage timestamps, scope, window, signer/conflict flag and hash','Distinct conditional maximum, earned U, F, R, C, conversion, request, receipt, queue, paid inventory and cash reserve ledgers'],
 'no_self_award_controls':['Self report allowed; no receiver sets own rate, approves own data, exception, right or posting','HR recipient: other HR operator plus independent process owner; manager recipient: next-level authorized verifier without benefit, and separate operator','Data-owner recipient replaced by independent source verifier; all own fields frozen and access removed for decision','Corrections log before/after, reason, timestamp, other signer; formula changes only future cycles. Missing bank data does not cancel effective earned date'],
 'first_launch_ref':'first-launch.json; first-launch.csv (14months; full36month projection in launch-years.csv)',
 'assumptions_ref':'assumptions-013.csv','references':['inputs/context.md, constraints','inputs/evidence.md C01-C08 E08-E12','inputs/diagnosis.md T1335,T918,T25','inputs/baseline.md M05 embeddedJSON']
}
spec['fallback']['condition']='Requires 2400*3=7200 independent unit acts/month; appoint substitute owners and allocate their hours before effort.'
spec['resource_costs']={
 'stationary_nonuseful_resource_RUB_year':12*(hr*1000+manager*1500+employee*1000+10*2000),
 'initial_preparation_resource_RUB':50*1000+480*1500+720*1000+400*2000,
 'useful_work_resource_RUB_year':103680000,
 'classification':'All process resources valued; procurement separate. Existing QA and metric data creation included, not necessarily new cash. 25% replacement sensitivity applies all resources, not a bank spending observation.'}
spec['workload']['classification_monthly']={
 'existing_business':{'manager_primary_QA_hours':qa*.7,'employee_metric_data_hours':evidence_metric,'employee_artifact_test_hours':evidence_artifact*.7,'resource_RUB':qa*.7*1500+(evidence_metric+evidence_artifact*.7)*1000},
 'required_incremental_program':{'HR_hours':hr,'manager_hours':manager-qa*.7,'employee_hours':employee_process+evidence_artifact*.3,'IT_hours':10,'resource_RUB':hr*1000+(manager-qa*.7)*1500+(employee_process+evidence_artifact*.3)*1000+20000},
 'unknown_incrementality':{'employee_useful_hours':8640,'valued_resource_RUB':8640000,'scope':'Ordinary productive metric/artifact work; no claim all newly caused by recognition. Also actual existing/new split of QA/test packaging unknown;70/30 is explicit scenario, not observation.'},
 'cash':'Existing valued business resource is not a new invoice or hiring request. Required incremental resource needs time allocation; extra cash depends on replacement.25% paid replacement sensitivity on incremental program resource separate from broad25% all-resource stress.'}
spec['workload']['manager_incremental_program_hours_monthly']=[manager-qa*.7]*12
spec['workload']['employee_incremental_program_hours_monthly']=[employee_process+evidence_artifact*.3]*12
spec['workload']['manager_existing_business_hours_monthly']=[qa*.7]*12
spec['workload']['employee_existing_business_hours_monthly']=[evidence_metric+evidence_artifact*.7]*12
spec['finance_interpretation']='Canonical manager/employee arrays value the full process including existing business work. Incremental arrays and classification are subsets, never add them again. M05 common basket HR separate. Classify before comparing alternatives or estimating new cash.'
spec['resource_costs']['existing_business_resource_RUB_year']=12*spec['workload']['classification_monthly']['existing_business']['resource_RUB']
spec['resource_costs']['required_incremental_program_resource_RUB_year']=12*spec['workload']['classification_monthly']['required_incremental_program']['resource_RUB']
spec['resource_costs']['incremental_program_replacement25_RUB_year']=.25*spec['resource_costs']['required_incremental_program_resource_RUB_year']
spec['resource_costs']['all_valued_process_2x_RUB_year']=2*spec['resource_costs']['stationary_nonuseful_resource_RUB_year']
spec['resource_costs']['incremental_program_2x_RUB_year']=2*spec['resource_costs']['required_incremental_program_resource_RUB_year']
spec['resource_costs']['useful_work_2x_hours_year']=207360
spec['resource_costs']['useful_work_2x_resource_RUB_year']=207360000
spec['workload']['special_surge']={'applications_month':7200,'additional_HR_hours_vs40':(7200-40)*5/60,'additional_manager_hours_vs40':(7200-40)*12/60,'additional_employee_hours_vs40':(7200-40)*6/60,'scope':'40 special applications/month is planning scenario, not a hard maximum of eligible applications. Guarantee of5day service fails this surge without separately allocated capacity; preserve receipt and finite-fund rules.'}
spec['quality_dictionary']={
 'metric':'n all assigned finalized comparable cases; s first-pass successes after7/10day recurrence tail; q cases satisfying mandatory quality controls; critical separately0. Missing source pending, not success or0earned entitlement.',
 'thresholds':{'IT':{'min_n':10,'success_fraction':.90},'backoffice':{'min_n':60,'success_fraction':.97},'support':{'min_n':80,'success_fraction':.90},'quality_fraction':.98,'critical_max':0},
 'r':'Upper median of all n elapsed_ms/reference_ms fractions sorted exactly, index floor(n/2)+1 one-based, includes rework; exclude only independently signed system downtime. Reference frozen before effort by role/complexity/shift.',
 'level':'After success and QA gate: r<=.90 L3; else r<=.95 L2; else L1. Failed gate L0; missing bank data pending with preserved claim.',
 'artifact':'1/2/3 independently useful units=L1/L2/L3; each10expected-output tests all correct,2other-person reproductions,2real uses,30days without critical defects and98%control quality. Max3units; preannounced subbenefits only.',
 'ranking':'Metrics level descending,r ascending,s/n descending,q/n descending,exact ties split slots. Artifact level descending,independent real uses per unit capped2 descending,then exact tie. Separate funded cards, no raw cross-card comparison.'}
dump('finance-spec-013.json',spec)

# Standard stationary M05, no writes to original shared model.
stationary=[]
extra_stress=[{'id':'FULL_NEW_REGION80','overrides':{'new_fixed_C_use':1.0,'region_demand_shares':[.2,.8]}},{'id':'FULL_NEW_JAN_OLD50','overrides':{'new_fixed_C_use':1.0,'old_january_share':.5}},{'id':'FULL_NEW_QUARTER','overrides':{'new_fixed_C_use':1.0,'R_calendar':'quarter_end'}}]
for sc in inputs['scenarios']+extra_stress:
 for f in inputs['fixed_C_cases_year']:
  for E in (inputs['envelopes_R_year'] if sc not in extra_stress else [24000000]):
   for r in m05.simulate(inputs,sc,f,E):
    # R12/R36 here are common comparison envelopes, not alternate CON013v2 policies.
    r['own_HR_hours_peak']=hr if E==24000000 else ''
    r['all_HR_hours_peak']=r['peak_common_HR_hours_month']+hr if E==24000000 else ''
    r['all_HR_capacity_pass']=r['peak_common_HR_hours_month']+hr<=220 if E==24000000 else ''
    stationary.append(r)
csvout('stationary-m05.csv',stationary)

windows=[]
for cohort,start in [('A',1),('B',2),('C',3)]:
 for k in range(1,5):
  s=start+(k-1)*3
  windows.append({'cohort':cohort,'cycle':k,'N':2400,'start_month':s,'start_day':15,'observation_end_month':s+3,'observation_end_day':14,'quality_final_month':s+3,'quality_final_day':24,'effective_earned_month':s+3,'posting_day_target':26,'lower_max_R':1200000,'top_max_R':600000,'conditional_max_R':1800000,'financial_year':(s+2)//12+1})

def launch(fixed,scenario,months=36):
 p=inputs['common']|scenario['overrides'];proc,freight,unit=m05.unit_cost(p)
 inv=[0.,0.];back=[0.,0.]
 initial_demand=((p['initial_C']+p['initial_personal_R'])*p['old_annual_use']*(p.get('old_january_share',1/12))+fixed/12*p['new_fixed_C_use']+200000*p['new_R_use'])/5000
 initial_shares=p.get('region_demand_shares',[.6,.4])
 due=[math.ceil(initial_demand*s/100)*100 for s in initial_shares]
 if scenario['id']=='EMPTY_SHOP':due=[0.,0.]
 legacyC=p['initial_C'];legacyR=p['initial_personal_R'];newC=newR=0.;reserve=0.;U=0.;cond=0.;conditional_reserve_previous=0.
 rows=[];y_oldC=y_oldR=y_newC=y_newR=0
 for month in range(1,months+1):
  mo=(month-1)%12+1;fy=(month-1)//12+1
  if mo==1:
   y_oldC=legacyC*p['old_annual_use'];y_oldR=legacyR*p['old_annual_use'];y_newC=newC*p['old_annual_use'];y_newR=newR*p['old_annual_use']
  oldshare=p.get('old_january_share',1/12) if mo==1 else ((1-p['old_january_share'])/11 if 'old_january_share'in p else 1/12)
  oldCuse=y_oldC*oldshare;oldRuse=y_oldR*oldshare;carryCuse=y_newC*oldshare;carryRuse=y_newR*oldshare
  Copen=legacyC+newC;Ropen=legacyR+newR;Uopen=U;condopen=cond
  ordinary=1800000 if month>=4 else 0
  if p.get('R_calendar')=='quarter_end':
   # Stress: same forward starts/observation; simultaneous closings. No early earnings.
   ordinary=5400000 if month>=6 and mo in [3,6,9,12] else 0
  conditional_added=1800000
  if p.get('R_calendar')=='quarter_end':conditional_added=5400000 if mo in [1,4,7,10] else 0
  cond+=conditional_added-ordinary
  assert cond>=-1e-6
  confirmed=ordinary+200000
  U+=confirmed
  delayed=180000 if scenario['id']=='DELAYED_POST' and month==4 else 0
  posted=U-delayed;U-=posted
  fixedissue=fixed/12
  new_fixed_req=fixedissue*p['new_fixed_C_use'];new_R_req=posted*p['new_R_use']
  legacyC-=oldCuse;legacyR-=oldRuse
  newC+=fixedissue-new_fixed_req-carryCuse
  newR+=posted-new_R_req-carryRuse
  convert=oldRuse+carryRuse+new_R_req
  requested=oldCuse+oldRuse+carryCuse+carryRuse+new_fixed_req+new_R_req
  shares=p.get('region_demand_shares',[.6,.4]);demand=requested/5000
  received=[];supplier_receipt=sum(due);purchase=supplier_receipt*proc;logistics=supplier_receipt*freight;inventoryopen=sum(inv)
  for i in range(2):
   inv[i]+=due[i];back[i]+=demand*shares[i]
   actual=min(back[i],inv[i],p['regions'][i]['capacity_units_month'])
   inv[i]-=actual;back[i]-=actual;received.append(actual)
  receiptC=sum(received)*5000
  # Future procurement is forecast, placed AFTER announcement only; one-month lead.
  nextposted=200000+(1800000 if month+1>=4 else 0)
  if p.get('R_calendar')=='quarter_end':
   nm=mo%12+1;nextposted=200000+(5400000 if month+1>=6 and nm in [3,6,9,12] else 0)
  nextposted+=U
  nextmo=mo%12+1
  nextshare=p.get('old_january_share',1/12) if nextmo==1 else ((1-p['old_january_share'])/11 if 'old_january_share'in p else 1/12)
  annual_old_and_carry=(legacyC+legacyR+newC+newR)*p['old_annual_use'] if mo==12 else y_oldC+y_oldR+y_newC+y_newR
  forecast=(annual_old_and_carry*nextshare+new_fixed_req+nextposted*p['new_R_use'])/5000
  orders=[]
  for i in range(2):
   orders.append(math.ceil(max(0,back[i]+forecast*shares[i]-inv[i]-1e-8)/100)*100)
  due=orders
  invval=sum(inv)*(proc+freight)
  # Requests stay in personal C until receipt. Queue is a held claim, not redemption.
  personalC=legacyC+newC+sum(back)*5000
  personalR=legacyR+newR
  # Conservatively all pending orders are backed; legacy+new split not fabricated.
  new_exposure=(newC+newR+U)*unit
  queue_exposure=sum(back)*5000*unit
  reserveclose=max(0,new_exposure+queue_exposure-invval)
  earnedreserve=reserveclose
  # Paid stock backs earned exposure first, then conditional promises; credit once.
  stock_remaining_for_conditional=max(0,invval-new_exposure-queue_exposure)
  conditionalreserve=max(0,cond*unit-stock_remaining_for_conditional)
  commonHR=80+(demand+0)*(.02+.2/30) # requests, even failed delivery, not hidden
  # Own hours follow real starts/closings, not stationary arrays inserted before launch.
  close_factor=ordinary/1800000
  H=12+40*5/60+(hr-12-40*5/60)*close_factor
  M=8+(manager-8)*close_factor
  EP=4+(employee_process-4)*close_factor
  EE=employee_evidence # one new cohort window starts every month
  if month<=3:
   H+=[30,10,10][month-1];M+=160;EP+=240
  IT=10+([200,100,100][month-1] if month<=3 else 0)
  useful=2880*min(month,3)
  Cclose=personalC;Rclose=personalR
  # opening C includes preceding queue; separate queued C in both sides.
  prev_queue=rows[-1]['orders_pending_C_close'] if rows else 0
  err=Copen+prev_queue+fixedissue+convert-receiptC-Cclose
  rerr=Ropen+posted-convert-Rclose
  assert abs(err)<1e-5 and abs(rerr)<1e-5,(month,err,rerr)
  # full promise coverage reserve funded before effort: conditional ceiling separate.
  row={'scenario':scenario['id'],'fixed_C_year':fixed,'month':month,'financial_year':fy,'month_in_year':mo,
   'cohort_start':'ABC'[(month-1)%3],'window_index':(month-1)//3+1,'observation':'start day15; full3calendar months; quality final day24 of month start+3',
   'ordinary_confirmed_cohort':('ABC'[(month-4)%3] if month>=4 else ''),'ordinary_confirmed_cycle':((month-4)//3+1 if month>=4 else 0),
   'conditional_open_R':condopen,'conditional_new_R':conditional_added,'conditional_released_R':ordinary,'conditional_close_R':cond,
   'special_finite_offer_R':200000,'confirmed_R':confirmed,'U_open_R':Uopen,'U_peak_R':Uopen+confirmed,'posted_R':posted,'U_close_R':U,
   'F_open_R':Uopen,'F_granted_R':confirmed,'F_posted_R':posted,'F_unissued_expired_R':0,'F_close_R':U,
   'fixed_posted_C':fixedissue,'C_open_including_queue':Copen+prev_queue,'R_open':Ropen,'R_to_C':convert,'C_close_including_queue':Cclose,'R_close':Rclose,
   'new_personal_unrequested_C':newC,'new_personal_unrequested_R':newR,'new_rights_exposure_RUB':new_exposure,
   'requested_C':requested,'received_C':receiptC,'orders_pending_C_close':sum(back)*5000,'queue_S1_baskets':back[0],'queue_S2_baskets':back[1],
   'received_S1_baskets':received[0],'received_S2_baskets':received[1],'no_queue':sum(back)<1e-7,
   'new_requested_S1_baskets':demand*shares[0],'new_requested_S2_baskets':demand*shares[1],
   'paid_inventory_open_baskets':inventoryopen,'paid_inventory_close_baskets':sum(inv),'paid_inventory_close_RUB':invval,
   'supplier_received_baskets':supplier_receipt,
   'procurement_order_baskets_for_next_month':sum(orders),'procurement_cash_RUB':purchase,'logistics_cash_RUB':logistics,'cash_RUB':purchase+logistics,
   'reserve_open_RUB':reserve,'reserve_close_RUB':earnedreserve,'reserve_delta_RUB':earnedreserve-reserve,
   'conditional_exposure_RUB':cond*unit,'conditional_prefunding_RUB':conditionalreserve,'conditional_prefunding_delta_RUB':conditionalreserve-conditional_reserve_previous,
   'funding_cash_plus_earned_reserve_delta_RUB':purchase+logistics+earnedreserve-reserve,
   'funding_including_conditional_delta_RUB':purchase+logistics+earnedreserve-reserve+conditionalreserve-conditional_reserve_previous,
   'common_HR_hours':commonHR,'own_HR_hours':H,'total_HR_hours':commonHR+H,'HR_220_pass':commonHR+H<=220,
   'HR_added_capacity_hours_required':max(0,commonHR+H-220),'HR_2x_added_capacity_hours_required':max(0,2*(commonHR+H)-220),
   'manager_hours_including_primary_QA':M,'employee_process_hours':EP,'employee_evidence_hours':EE,'employee_useful_work_hours':useful,'IT_hours':IT,
   'existing_business_resource_RUB':qa*.7*close_factor*1500+(evidence_metric+evidence_artifact*.7)*1000,
   'required_incremental_program_resource_RUB':H*1000+(M-qa*.7*close_factor)*1500+(EP+evidence_artifact*.3)*1000+IT*2000,
   'unknown_incrementality_useful_resource_RUB':useful*1000,
   'nonuseful_resource_RUB':(commonHR+H)*1000+M*1500+(EP+EE)*1000+IT*2000,
   'replacement25_RUB':.25*((commonHR+H)*1000+M*1500+(EP+EE)*1000+IT*2000),
   'C_balance_error':err,'R_balance_error':rerr,'interpretation':'required orders retained; actual receipt capped by paid stock and regional capacity; conditional promises are not earned currency; all figures assumptions/calculations'}
  assert abs(inventoryopen+supplier_receipt-sum(received)-sum(inv))<1e-7
  assert abs(Uopen+confirmed-posted-U)<1e-7
  assert abs(condopen+conditional_added-ordinary-cond)<1e-7
  assert abs(row['existing_business_resource_RUB']+row['required_incremental_program_resource_RUB']+commonHR*1000-row['nonuseful_resource_RUB'])<1e-5
  rows.append(row);reserve=reserveclose;conditional_reserve_previous=conditionalreserve
 return rows

launch_rows=[];annual=[]
scenarios=[s for s in inputs['scenarios'] if s['id']!='QUARTER_END_R']+[{'id':'DELAYED_POST','overrides':{}},{'id':'EMPTY_SHOP','overrides':{}}]+extra_stress[:2]
for sc in scenarios:
 for f in inputs['fixed_C_cases_year']:
  rr=launch(f,sc)
  launch_rows.extend(rr[:15])
  for year in range(1,4):
   rs=[r for r in rr if r['financial_year']==year]
   sums=['posted_R','confirmed_R','requested_C','received_C','cash_RUB','reserve_delta_RUB','conditional_prefunding_delta_RUB','funding_cash_plus_earned_reserve_delta_RUB','funding_including_conditional_delta_RUB','common_HR_hours','own_HR_hours','manager_hours_including_primary_QA','employee_process_hours','employee_evidence_hours','employee_useful_work_hours','IT_hours','existing_business_resource_RUB','required_incremental_program_resource_RUB','unknown_incrementality_useful_resource_RUB','nonuseful_resource_RUB','replacement25_RUB']
   a={'scenario':sc['id'],'fixed_C_year':f,'year':year}|{k:sum(r[k] for r in rs) for k in sums}
   a|={k:rs[-1][k] for k in ['conditional_close_R','U_close_R','C_close_including_queue','R_close','orders_pending_C_close','paid_inventory_close_RUB','reserve_close_RUB','conditional_prefunding_RUB']}
   a|={'peak_total_HR_hours':max(r['total_HR_hours'] for r in rs),'no_queue_all_months':all(r['no_queue'] for r in rs),'funding_plus_buffer_RUB':a['funding_including_conditional_delta_RUB']+500000}
   a['funding_pass30']=a['funding_plus_buffer_RUB']<=30000000;a['funding_pass34']=a['funding_plus_buffer_RUB']<=34000000
   annual.append(a)
csvout('first-launch.csv',launch_rows);csvout('launch-years.csv',annual)
fiscal_slices=[]
for sc in ['EXPECTED','FULL_NEW']:
 for a,b in [(1,12),(13,14),(15,15)]:
  rs=[r for r in launch_rows if r['scenario']==sc and r['fixed_C_year']==96000000 and a<=r['month']<=b]
  fiscal_slices.append({'scenario':sc,'fixed_C_year':96000000,'months':[a,b],'financial_year':rs[0]['financial_year'],
   'posted_R':sum(r['posted_R'] for r in rs),'cash_RUB':sum(r['cash_RUB'] for r in rs),'reserve_open_RUB':rs[0]['reserve_open_RUB'],'reserve_close_RUB':rs[-1]['reserve_close_RUB'],
   'conditional_close_R':rs[-1]['conditional_close_R'],'conditional_prefunding_close_RUB':rs[-1]['conditional_prefunding_RUB'],'U_close_R':rs[-1]['U_close_R'],'orders_pending_C':rs[-1]['orders_pending_C_close'],
   'scope':'Partial year2 slices have no annual pass claim; full year2 in launch-years.csv.'})
dump('first-launch.json',{'candidate_key':'CON-013@v2','classification':'Prospective scenario beginning2027-01-01, not bank schedule','months':15,
 'announcement':'2027-01-01; no rewarded ordinary work before this date. Existing shop procurement continues: m0 order received/paid m1 is explicit readiness assumption, not an observed bank stock.',
 'preparation':'m1 days1-14 shared card/benchmark/owner setup; cohortA startsJan15, BFeb15,CMar15. B/C preparation charged m2/m3 before day15. No baseline history required: bench tests constructed in costed preparation.',
 'windows_first_four':windows,'quality':'Full three calendar months; last cases settle7/10days after window; quality finalized day24 next calendar month, then posting target2workdays. Artifact30day use surveillance must finish by observation cutoff; final late-data reconciliation still day24.',
 'monthly_summary_max_R':[200000]*3+[2000000]*12,
 'stationary_ref':'finance-spec-013.json monthly_calendar_R[12]','csv':'first-launch.csv','csv_rows':len(launch_rows),'csv_dimensions':'15 scenarios including posting-delay, empty-shop and full-new regional/January overlays;2fixed,15months; quarter synchronous demand separately in stationary-m05.csv. No rows embedded inJSON',
 'year_projection':'launch-years.csv: full36months, same date-based orders and promises; m13-14 only is not year2 pass',
 'fiscal_slices_fixed96':fiscal_slices,
 'fourth_late_cohort':'C cycle4 startsm12, full observation tom15day14, qualitym15day24, postingm15day26. 1.8mR is within conditional_close at m14, not expired; A/B fifth windows also conditional. C4 is not counted in year1 or omitted.',
 'state_definitions':{'conditional':'promised maximum BEFORE effort; no earned personal currency yet','U':'independently confirmed earned claim not yet posted; survives F rollover','F':'operating authorization; full maximum scenario Fgranted=confirmed; no unissued expiry. U shown also in Fclose as earmarked authorization, not second liability','request':'C held in personal account/order escrow until actual receipt; not redeemed at request','receipt':'actual fulfillment reduces C; failed fulfillment remains order queue','reserve':'all post-start unspent rights + U +ALL queued orders conservatively, minus paid stock once; original unrequested legacy exposure separately persists','conditional_prefunding':'conditional ordinary maxima funded separately before effort, added to M05 earned-right reserve; not counted twice after earning','special':'200k finite contest/month; funding forecast available before independent acceptance; full scenario all slots earned, no invented pre-announcement result'},
 'launch_gate':'Readiness assumption: existing-shop m0 order received/paid m1. EMPTY_SHOP stress removes incoming supply and creates retained queue; not base case. Quarter synchronous stress in stationary matrix is a separate announced calendar, not withholding already earned cohort rights.',
 'checks':'self-check.json; candidate self-check only, independent finance/evidence by coordinator required'})

# Exhaustive relevant integer outcomes and continuous ratio boundary fixtures.
quality=[]
for family,n,threshold in [('IT',10,.9),('IT',20,.9),('backoffice',60,.97),('support',80,.9)]:
 minimum_s=math.ceil(threshold*n-1e-9);minimum_q=math.ceil(.98*n-1e-9)
 for s in range(n+1):
  for q in range(n+1):
   for ratio in [.9000,.9001,.9500,.9501,1.0]:
    passed=s>=minimum_s and q>=minimum_q
    level=(3 if ratio<=.9 else 2 if ratio<=.95 else 1) if passed else 0
    quality.append({'family':family,'n':n,'s':s,'q':q,'critical':0,'normalized_upper_median_ratio':ratio,'minimum_s':minimum_s,'minimum_q':minimum_q,'level':level,'lower_R':500 if level else 0})
csvout('quality-boundaries.csv',quality)

assumptions=[
 ('A01','cohort_people',2400,'people/cohort','three cohorts all7200'),('A02','metric_share',.6,'fraction of ordinary bundles','new scenario, not bank mix'),('A03','artifact_share',.4,'fraction','max3 useful units each'),('A04','ready_act_share',.7,'fraction','all original primary QA still valued'),('A05','metric_average_n',42.5,'records/person/cycle','equal n10/20/60/80 mix'),('A06','QA_minutes_metric_case',.5,'manager min/case','independent full denominator control review'),('A07','QA_minutes_artifact_unit',12,'manager min/unit','test/reproduction/use breakdown in finance-spec'),('A08','evidence_minutes_metric_case',.25,'employee min/case','existing-function data production priced'),('A09','evidence_minutes_artifact_unit',20,'employee min/unit','test construction separate from useful work'),('A10','metric_ratio_L2_L3','.95/.90','ratio to preannounced same-complexity reference','upper median; all records, including rework'),('A11','QA_floor',.98,'q/n','not same numerator as business success; critical zero'),('A12','business_success_floor','IT/support .90;backoffice .97','s/n','exact integer thresholds not rounded rates'),('A13','cohort_starts','m1/m2/m3 day15','date','all preparation after announcement m1day1'),('A14','quality_final','start_month+3 day24','date','full3months endday14;10day tail'),('A15','initial_preparation','HR50;manager480;employee720;IT400','hours/once','costed m1..3'),('A16','ordinary_monthly_acts',2400,'people/month','maximum case all apply and qualify; rejected special10 extra'),('A17','special_monthly','20*5000+10*10000','R/month','finite200k;40applications incl10rejected'),('A18','HR_capacity',220,'hours/month','FROZEN M05; no silent increase'),('A19','useful_work','metric2h;artifact3*2h','hours/person/cycle','not declared wholly incremental'),('A20','service_value_examples','500C certificate/50C credit','illustrative catalog value','new proposed regional small balance products, priced .194RUB/C equivalence scenario, not existing bank SKU'),('A21','correction/appeal/recusal','.10/.02/.01','fraction of ordinary applications','all costed;2x sensitivity'),('A22','scale','120groups*60;4cycles;500base','people/cycle/R','max24mR stationary,14.4/7.2/2.4'),('A23','cash_replacement',.25,'fraction of valued process resource','separate sensitivity; not actual paid bank invoices')]
assumptions.append(('A24','existing_artifact_test_pack_share',.7,'fraction of evidence creation','Scenario business overlap tied to ready-act share; actual incremental fraction unknown'))
csvout('assumptions-013.csv',[{'id':i,'type':'new_design_assumption' if i!='A18' else 'frozen_M05_assumption','parameter':p,'value':v,'unit':u,'basis_and_limit':b} for i,p,v,u,b in assumptions])

# Compact audit output with base date-based fiscal summaries and input hashes.
base=[a for a in annual if a['scenario'] in ['EXPECTED','FULL_NEW'] and a['fixed_C_year']==96000000]
checks={'candidate_key':'CON-013@v2','status':'arithmetic_pass_operational_limits_disclosed','frozen_SHA256':{p:hashlib.sha256((ROUND/'inputs'/p).read_bytes()).hexdigest() for p in ['context.md','evidence.md','diagnosis.md','baseline.md','rubric.json']},
 'annual_policy_R':spec['annual_total_R'],'monthly_sum_R':sum(spec['monthly_calendar_R']),'stationary_rows':len(stationary),'first_launch_rows':len(launch_rows),'launch_year_rows':len(annual),'quality_rows':len(quality),
 'max_C_error':max(abs(r['C_balance_error']) for r in launch_rows),'max_R_error':max(abs(r['R_balance_error']) for r in launch_rows),'primary_QA_hours_month':qa,'manager_hours_month':manager,'employee_evidence_hours_month':employee_evidence,'employee_process_hours_month':employee_process,'HR_hours_month':hr,
 'repeat_verification_comparison':{'parent_4min_all_hours_month':160,'v2_ready_new_and_risk_audit_hours_month':64+5.6,'hours_difference':90.4,'scope':'Only repeated act checks, not all QA; v1 omitted primary proof creation so no total cost superiority claim'},
 'base_fiscal_summaries':base,'independent_checks':'Not self-certified independent. Coordinator must run finance/evidence review including unchanged parent and baseline.'}
dump('self-check.json',checks)

# Money examples use the same rounding rule as the written policy.
from decimal import Decimal, ROUND_DOWN
def floorcent(x):return Decimal(x).quantize(Decimal('.01'),rounding=ROUND_DOWN)
def slots(h):
 pool=Decimal(h)*250
 a=floorcent(pool/2);b=floorcent(pool/3)
 return a,b,pool-a-b
def share(amount,n):return floorcent(Decimal(amount)/n)
fixtures=[]
def addcase(name,actual,expected):
 assert actual==Decimal(expected),(name,actual,expected)
 fixtures.append({'case':name,'computed_R':str(actual),'expected_R':expected,'status':'pass'})
addcase('40_people_8_tied_teams_5_each_person',500+share(share(sum(slots(40)),8),5),'750.00')
addcase('40_tied_persons',500+share(sum(slots(40)),40),'750.00')
addcase('40_people_team_rank1_each',500+share(slots(40)[0],5),'1500.00')
addcase('40_people_team_rank2_each',500+share(slots(40)[1],5),'1166.66')
addcase('40_people_team_rank3_each',500+share(slots(40)[2],5),'833.33')
addcase('8_separate_groups_of5_sole_eligible_team_each_person',500+share(slots(5)[0],5),'625.00')
addcase('small_group5_one_top_person',500+slots(5)[0],'1125.00')
addcase('singleton_L2',500+slots(1)[0],'625.00')
addcase('60_group_rank2_through6_tie5',500+share(sum(slots(60)[1:]),5),'2000.00')
addcase('60_group_third_tied3',500+share(slots(60)[2],3),'1333.33')
addcase('rolling4cycles_person_max',Decimal(4)*(500+7500+10000),'72000')
csvout('money-examples.csv',fixtures)
for n in [10,20,60]:
 assert {r['level'] for r in quality if r['n']==n and r['s']==n and r['q']==n}=={1,2,3}
 assert all(r['level']==0 for r in quality if r['n']==n and (r['q']<r['minimum_q'] or r['s']<r['minimum_s']))
assert sum(spec['monthly_calendar_R'])==spec['lower_tier']['annual_max_R']+spec['contests']['annual_max_R']+spec['special']['annual_max_R']==24000000
delayed=[r for r in launch_rows if r['scenario']=='DELAYED_POST' and r['fixed_C_year']==96000000]
assert delayed[3]['U_close_R']==180000 and delayed[4]['posted_R']==2180000
assert any(w['cohort']=='C' and w['cycle']==4 and w['quality_final_month']==15 for w in windows)
checks['money_fixtures_pass']=len(fixtures)
checks['quality_all_levels_reachable_n10_20_60']=True
checks['delayed_U_and_C4_preserved']=True
checks['inventory_U_conditional_resource_balances']='pass across all36months and15 scenarios, bothfixed'
checks['calculation_paths']=['build.py','finance-spec-013.json','first-launch.json','first-launch.csv','launch-years.csv','stationary-m05.csv','quality-boundaries.csv','money-examples.csv','assumptions-013.csv']
dump('self-check.json',checks)
print(json.dumps({'wrote':str(HERE),'monthly_hours':{'HR':hr,'manager':manager,'employee':employee},'rows':len(launch_rows),'base_fiscal':[(a['scenario'],a['year'],a['funding_plus_buffer_RUB'],a['peak_total_HR_hours']) for a in base]},ensure_ascii=False))
