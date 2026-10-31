"""Owned branch B artifacts. Reads frozen M05, never writes common inputs/models."""
from pathlib import Path
import json,csv,importlib.util,hashlib,sys
sys.dont_write_bytecode=True
ROOT=Path.cwd()
OUT=ROOT/'analysis/iterations/iteration-005/rounds/001/branches/B'
FROZEN=ROOT/'analysis/iterations/iteration-005/rounds/001/inputs'
text=(FROZEN/'baseline.md').read_text()
p=json.loads(text.split('```json\n',1)[1].split('\n```',1)[0])
# The common model is a read-only import; parameters are ONLY the frozen JSON.
mp=ROOT/'analysis/preparation/iteration-005-finance-basis/model.py'
s=importlib.util.spec_from_file_location('M05_read_only',mp);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
rows=[]
for scenario in p['scenarios']:
 for fixed in p['fixed_C_cases_year']:
  for E in [12000000,24000000,36000000]:
   rows.extend(m.simulate(p,scenario,fixed,E))
with (OUT/'finance-m05.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def work(team=False,expected=False,worst_team=False):
 # One application per person/cycle, correction included, rejected applications retained.
 people=1920 if expected else 2400
 special=20 if expected else 40
 groups=40
 team_size=1 if worst_team else 6
 teams=people/team_size
 error=.1;appeal=.02;recusal=.01
 if not team:
  HR=12+groups*10/60+people*(.25+error*2+appeal*5+recusal*3)/60+special*5/60
  manager=groups*10/60+people*(4+.1*4+error*5+appeal*8+recusal*5)/60+special*12/60
  employee=people*(3+error*4+appeal*4)/60+special*6/60
 else:
  HR=12+groups*10/60+people*(.25+.1+appeal*5+recusal*3)/60+teams*error*3/60+special*5/60
  manager=groups*10/60+people*(1+error*2+appeal*8+recusal*5)/60+teams*(8+.1*6+error*10)/60+special*12/60
  employee=people*(2+1+error*3+appeal*4)/60+teams*(4+error*4)/60+special*6/60
 extra=(20,30,720) if not team else (24,60,960)
 return {'HR_hours_monthly':[round(HR+extra[0],6)]+[round(HR,6)]*11,
 'manager_hours_monthly':[round(manager+extra[1],6)]+[round(manager,6)]*11,
 'employee_process_hours_monthly':[round(employee+extra[2],6)]+[round(employee,6)]*11,
 'IT_initial_hours':520 if team else 400,'IT_recurring_hours_year':180 if team else 120,
 'employee_useful_work_hours_year':57600,
 'flow':{'application_people_month':people,'accepted_lower_people_month':1440 if expected else 2400,
 'ordinary_groups_month':groups,'team_size_for_workload':team_size if team else None,
 'ordinary_team_acts_month':teams if team else None,'special_applications_month':special,
 'special_accepted_month':12 if expected else 30,'correction_fraction':error,
 'appeal_fraction_of_people':appeal,'recusal_fraction_of_people':recusal,'quality_sample_fraction':.1},
 'minutes':{'HR':{'fixed_admin_hours_month':12,'packet_per_group':10,'reconcile_per_person':.25,'correction_personal':2 if not team else 0,'membership_per_person':.1 if team else 0,'team_rework':3 if team else 0,'appeal_per_person':5,'recusal_per_person':3,'special_per_application':5},
 'manager':{'packet_per_group':10,'ordinary_person_acceptance':4 if not team else 1,'quality_sample_person':4 if not team else 0,'team_acceptance':8 if team else 0,'quality_sample_team':6 if team else 0,'correction_person':5 if not team else 2,'correction_team':10 if team else 0,'appeal_per_person':8,'recusal_per_person':5,'special_per_application':12},
 'employee':{'ordinary_per_person':3 if not team else 2,'share_acknowledgement_per_person':1 if team else 0,'team_lead_per_team':4 if team else 0,'correction_per_person':4 if not team else 3,'correction_team_lead':4 if team else 0,'appeal_per_person':4,'special_per_application':6}},
 'month1_additional_hours':dict(zip(['HR','manager','employee'],extra)),
 'acceptance_units':{'max_atomic_items_per_bundle':3,'personal_bundles_year':people*12 if not team else None,'team_bundles_year':teams*12 if team else None,'max_atomic_milestone_checks_year':(teams if team else people)*12*3,'interpretation':'Personal owner4min=3 simple checklist items*1min+1min reconcile; team owner8min=3*2min+2min integration. Personal participation per person separate in team. Atomic checks are INSIDE costed bundle, not free extra acceptance. Complex factual verification requires re-estimate/2x stress.'},
 'units':'hours/year for scalar; arrays hours/month for Jan..Dec; flow counts/month; minutes/act. Useful work 7200*4*2h, ordinary productive work, separate from process and not assumed incremental.',
 'scope':'Incremental contest/special process only; common M05 basket handling excluded; all applicant failures and rework included. Upper bounds under stated rates, not pathological unlimited appeal storm.'}
def cost(w):
 rates=p['common']['rates_rub_hour']; hours={k:sum(w[v]) for k,v in [('HR','HR_hours_monthly'),('manager','manager_hours_monthly'),('employee','employee_process_hours_monthly')]}
 hours['IT']=w['IT_initial_hours']+w['IT_recurring_hours_year']
 annual=sum(hours[k]*rates[k] for k in hours)
 return {'hours_year':hours,'year1_process_resource_RUB':round(annual,2),
 'year2_3_process_resource_RUB_each':round(annual-w['IT_initial_hours']*rates['IT'],2),
 'all_labor_2x_resource_RUB':round(2*annual,2),'paid_replacement_25pct_RUB':round(.25*annual,2),
 'interpretation':'Resource outside procurement limit. 25% is separate replacement-cash sensitivity on process resource, not added as a second full resource cost. IT internal hours valued, not vendor invoice. Productive ordinary work 57.6m RUB/year separately, no assertion of incremental opportunity cost.'}
for number,team in [(13,False),(14,True)]:
 key=f'CON-{number:03d}@v1'; dest=OUT/f'CON-{number:03d}-v1'
 full=work(team);expected=work(team,True);stress=work(team,worst_team=True)
 spec={'schema_version':1,'candidate_key':key,'classification':'ALL design numbers are new scenario assumptions except referenced frozen M05. No bank feasibility approval.',
 'currency':'R; R_to_C=1; fixed in C unchanged','envelope_R_year':24000000,'selected_envelope_R':24000000,'N_eligible':7200,
 'eligibility_rule':'All employees in defined comparable role/exposure groups, including HR/managers. No application quota; no invite/rank requirement. 7200 reserve used until smaller objective population evidenced. One home group/card and one cohort per cycle.',
 'lower_tier':{'N':7200,'cycles_year':4,'award_R':500,'max_awards_person_year':4,
 'base_formula':'7200 persons * 4 cycles/year * 500 R/person/cycle','annual_max_R':14400000,
 'team_formula':'500 R per independently verified participating person on accepted milestone; team total=500*k eligible participants, NOT 500 to one team then multiplied again' if team else None},
 'base_formula':'N_eligible*cycles*lower_R=7200*4*500=14,400,000 R/year',
 'contests':{'groups':120,'scenario_group_size_people':60,'cycles_year':4,'unit':'team' if team else 'person',
 'top_tiers':[{'place':1,'places_per_group_cycle':1,'award_R':7500},{'place':2,'places_per_group_cycle':1,'award_R':5000},{'place':3,'places_per_group_cycle':1,'award_R':2500}],
 'formula':'120 groups*4 cycles*(7500+5000+2500) R=7,200,000 R/year',
 'annual_max_R':7200000,'tie_rule':'Pool only tied occupied slots and divide equally among tied eligible units; no extra slots/money. Decimal R posted to cents; residual <0.01 per share retained in F; no arbitrary winner.',
 'team_share_formula':'team top pool * precommitted share_i; share_i=verified accepted workpackages_i / all precommitted workpackages; sum<=1; missing shares stay F; no reassignment after result. Max personal top <=7500/cycle even at share=1.' if team else None,
 'group_size_cap_people':60,'group_scaling_rule':'Each group<=60 eligible; split large departments by role/opportunity then stable registry subgroups before effort, never exclude people. For different actual department sizes allocate total 1.8m R/cycle proportionally to frozen eligible headcount, then tiers 50/33.333/16.667 percent. Comparable tracks within department get headcount shares. Single entrant may win only first tier if top quality met. Never invent 120 real departments.'},
 'special':{'levels':[{'award_R':5000,'max_count_year':240},{'award_R':10000,'max_count_year':120}],
 'special_maximum':'240*5000+120*10000=2,400,000 R/year','annual_max_R':2400000,
 'monthly_caps':{'5000_R_count':20,'10000_R_count':10},
 'authorization':'Other benefit owner verifies, independent fund custodian authorizes fixed level, substitute if conflict. Receiver cannot alter rate/evidence/exception. Cap announced before effort; unexpected contributions above finite capacity receive factual recognition, no unfunded entitlement.'},
 'special_maximum':2400000,'stacking':{'base_plus_top':'Allowed; top is explicitly additional layer for same ordinary accepted result, reserved in full.',
 'special_same_benefit':'Prohibited for same root benefit ID in ordinary base/top or other department/salary result bonus. Distinct benefit ID can stack.',
 'max_person_R_year':72000,'formula':'4*500+4*7500+4*10000=72000; max one special/person/cycle. Team top <=personal ceiling. No reduction of total reserve due presumed different winners.'},
 'annual_total_R':24000000,'maximum_formula':'14.4m lower+7.2m top+2.4m special=24m R/year; E replaces all future additional F, never E+old F',
 'monthly_calendar_R':[2000000]*12,
 'calendar_components':{'lower_R':[1200000]*12,'top_R':[600000]*12,'special_R':[200000]*12},
 'calendar_rights':'Ordinary eligibility requires quality over the complete announced three-month window; early artifact acceptance is provisional, no earned right is held back. 120 scenario groups assigned before period to 3 balanced cohorts, 40 groups/2400 people each. Each has 3-month earning window ending in its cohort month; ongoing program Jan..Dec closes 1 cohort/month. First launch cohorts start 3 months before their first close; do not delay an already earned right. All staff 4 equal windows/year. Real headcounts need balancing and recalculation.',
 'posting_request_receipt':'Ordinary right at declared observation-window cutoff after quality check, special right at independent acceptance; posting <=2 workdays; request anytime immediately after posting; certificate target5 workdays, merch30 calendar days assuming preorders and one-month lead. These are design targets, not supplied SLA. Errors preserve effective right date. All new rights can be requested immediately; physical calendar modeled in full.',
 'envelope_policies':{'12000000':{'lower':'7200*2*500=7.2m','top':'120*2*(7500+5000+2500)=3.6m','special':'120*5000+60*10000=1.2m','total_R':12000000,'monthly_R':[1000000]*12,'personal_cap_R_year':36000,'window_months':6,'cycles':2,'cohorts':6,'people_per_month':1200,'time_to_5000C_lower_only_years':5},'24000000':{'lower':'7200*4*500=14.4m','top':'120*4*(7500+5000+2500)=7.2m','special':'240*5000+120*10000=2.4m','total_R':24000000,'monthly_R':[2000000]*12,'personal_cap_R_year':72000,'window_months':3,'cycles':4,'cohorts':3,'people_per_month':2400,'time_to_5000C_lower_only_years':2.5},'36000000':{'lower':'7200*4*1000=28.8m','top':'120*4*(5000+3000+2000)=4.8m','special':'240*5000+120*10000=2.4m','total_R':36000000,'monthly_R':[3000000]*12,'personal_cap_R_year':64000,'window_months':3,'cycles':4,'cohorts':3,'people_per_month':2400,'time_to_5000C_lower_only_years':1.25},'note':'These are prospective alternative policies, not reserve evasion or cuts to existing earned rights. E36 increases base and decreases top pool explicitly; no claim of monotone top value. Workload arrays in this spec apply selected E24; financial matrix compares identical E by common M05.'},
 'expected_design_award_flow_R_year':13920000,'expected_design_formula':'60% of lower14.4m + 60% of top7.2m +40% of special2.4m =13.92m. ONLY process planning; procurement stress still full24m, M05 expected still new R100%.',
 'workload':full,'workload_expected':expected,'workload_max_team_fragmentation':stress if team else None,
 'resource_costs':{'full_new':cost(full),'expected':cost(expected),'team_fragmentation':cost(stress) if team else None},
 'finance_checks':{'matrix_path':'branches/B/finance-m05.csv','source':'inputs/baseline.md embedded M05 JSON; common model read-only import',
 'rows':216,'scope':'12 common scenarios*2 fixed*3 envelopes*3 years. Rows identical for both candidates at same E/calendar, no altered M05. Use cash+signed reserve delta+500k buffer and monthly capacity, not cash alone.',
 'selected_scope_conditional':'E24 fixed96 old20 base price: 34m procurement+reserve buffer passes; 30m fails. Fixed144, old35 and price20 fail34; full old stress fails. All actual bank gates uncertain.',
 'overload_controls':'Stagger earning windows before effort, not redemption queues. Quarter synchronous stress, Jan old50, region80 retain all requests and fail if inadequate capacity. Do not claim smoothing covers unmodeled SKU or old-demand bursts.'},
 'data_requirements':['Frozen role/card/exposure, independent QA export, immutable root benefit ID','Versioned CSV with data owner signature; participant edit requires second verification','Team participant/accepted workpackage/share register' if team else 'Personal acceptance checklist and independent artifact use test','Separate conditional promise, confirmed unposted right, F, R,C,conversion,order,receipt ledger'],
 'no_self_award_controls':['Self nomination allowed; self approval, rate change and own exception prohibited','Bank manager award verified by next-level unrelated owner; HR award by nonbeneficiary HR substitute plus independent owner','All modified logs dual signed; data owner excluded as verifier of own entries','Mutual nominations trigger evidence audit, never proof by themselves'],
 'assumptions':{'group_count':120,'group_size':60,'monthly_cohort_people':2400,'lower_success_expected':.6,'top_utilization_expected':.6,'special_utilization_expected':.4,'team_size_scenario':6 if team else None,'team_size_allowed':[1,10] if team else None,'useful_work_hours_person_cycle':2},
 'references':['inputs/context.md, Ограничения и одинаковые проверки','inputs/evidence.md C01-C08/E01-E12','inputs/baseline.md, M05 tables and JSON','branches/B/CON-%03d-v1/assumptions.csv'%number]}
 (dest/'finance-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
 assumptions=[('B01','new_assumption','eligible_people',7200,'persons','year','Maximum reserve, frozen M05 N; true eligible count unknown'),('B02','new_assumption','groups',120,'groups','cycle','60 people/group scenario; all7200 covered'),('B03','new_assumption','cycles',4,'cycles/person','year','Four nonoverlapping three-month windows'),('B04','new_assumption','lower_award',500,'R/person','cycle','Guarantee if checklist independently accepted'),('B05','new_assumption','top_pool',15000,'R/group','cycle','7500+5000+2500; tied slots split'),('B06','new_assumption','special',2400000,'R','year','Finite360 awards; 240x5000+120x10000'),('B07','new_assumption','cohort_people',2400,'persons','month','Design balancing before effort; failure needs real capacity not queue'),('B08','new_assumption','expected_lower_rate',.6,'fraction','cycle','Not M05 redemption rate'),('B09','new_assumption','expected_top_rate',.6,'fraction','cycle','Not promised saving'),('B10','new_assumption','expected_special_rate',.4,'fraction','cycle','Not backing guarantee'),('B11','new_assumption','rework_rate',.1,'fraction of applicant people/team acts','month','Explicit procedure costing'),('B12','new_assumption','appeals',.02,'fraction of applicant people','month','Budgeted workload scenario'),('B13','new_assumption','recusal',.01,'fraction of applicant people','month','Independent substitute verification'),('B14','new_assumption','ordinary_useful_work',2,'hours/person','cycle','Separate ordinary productive work; not free or necessarily incremental'),('B15','new_assumption','region_delivery_targets','5/30','workdays certificate/calendar days merch','order','Requires SKU supplier verification; not fact'),('B16','new_assumption','IT_initial',520 if team else 400,'hours','once','Internal hours, no vendor'),('B17','new_assumption','IT_recurring',180 if team else 120,'hours','year','Internal team capacity unknown'),('B18','new_assumption','team_size',6 if team else 'NA','persons/team','cycle','014 allowed1-10; worst1 recomputed'),('B19','new_assumption','special_processing',40,'applications','month maximum workload','30 accepted plus10 rejected; expected20 applications/12 accepted'),('B20','new_assumption','metric_thresholds','see concept section2','role-specific rates/counts','cycle','Illustrations only; not actual bank metrics'),('B21','new_assumption','atomic_acceptance_checks_per_bundle',3,'checks/bundle','cycle','013 owner4min=3x1+1;014 owner8min=3x2+2. More complex evidence requires recosting'),('B22','new_assumption','group_size_cap',60,'eligible persons/group','cycle','All staff included via stable preperiod subgroups; actual packet/group counts unknown')]
 with (dest/'assumptions.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['id','type','parameter','value','unit','period','basis_and_limit']);w.writerows(assumptions)
# Add process workload to the common admin peak; it is never silently absorbed in 220h.
checks=[]
for number,team in [(13,False),(14,True)]:
 spec=json.loads((OUT/f'CON-{number:03d}-v1/finance-spec.json').read_text())
 assert spec['annual_total_R']==spec['lower_tier']['annual_max_R']+spec['contests']['annual_max_R']+spec['special']['annual_max_R']
 assert sum(spec['monthly_calendar_R'])==spec['annual_total_R']
 for wname in ['workload','workload_expected']+(['workload_max_team_fragmentation'] if team else []):
  w=spec[wname]
  assert all(len(w[k])==12 for k in ['HR_hours_monthly','manager_hours_monthly','employee_process_hours_monthly'])
  for scenario in ['FULL_NEW','EXPECTED','QUARTER_END_R','REGION80','JAN_OLD50']:
   for fixed in [96000000,144000000]:
    row=next(r for r in rows if r['year']==1 and r['scenario']==scenario and r['fixed_C_year']==fixed and r['envelope_R_year']==24000000)
    # conservative: use peak common load plus own peak even if months differ.
    peak=row['peak_common_HR_hours_month']+max(w['HR_hours_monthly'])
    checks.append({'candidate_key':spec['candidate_key'],'workload_case':wname,'M05_scenario':scenario,'fixed_C':fixed,'common_peak_HR_h':row['peak_common_HR_hours_month'],'own_peak_HR_h':max(w['HR_hours_monthly']),'conservative_combined_peak_HR_h':round(peak,4),'capacity_220h_pass':peak<=220,'2x_all_labor_capacity_pass':2*peak<=220,'physical_capacity_pass':row['capacity_pass']})
with (OUT/'workload-capacity.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
manifest={'frozen_input_sha256':{f:hashlib.sha256((FROZEN/f).read_bytes()).hexdigest() for f in ['context.md','evidence.md','diagnosis.md','baseline.md','rubric.json']},'model_read_only_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'checks':{'finance_rows':len(rows),'max_stock_error':max(abs(r['stock_error']) for r in rows),'max_inventory_cost_error':max(abs(r['inventory_cost_error']) for r in rows),'annual_envelopes_and_calendars':'pass','workload_arrays_length_12':'pass','bank_budget_approval':'not_asserted','interpretation':'Arithmetic self-check only; gates assessed externally. Common M05 values unchanged.'}}
(OUT/'self-check.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'rows':len(rows),'costs':{str(n):json.loads((OUT/f'CON-{n:03d}-v1/finance-spec.json').read_text())['resource_costs'] for n in [13,14]},'capacity_selected':[c for c in checks if c['M05_scenario']=='FULL_NEW' and c['fixed_C']==96000000]},ensure_ascii=False,indent=2))
