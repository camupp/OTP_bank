#!/usr/bin/env python3
"""Build only owned branch B artifacts. Does not execute any inherited generator."""
import sys
sys.dont_write_bytecode=True
import copy,csv,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
B=HERE.parent
R=B.parents[1]
INC=R.parents[1]/'incumbent'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows):
 if p.parent.name in ('con-020','con-021'):
  rows=[dict(candidate_key='CON-'+p.parent.name[-3:]+'@v2',**r) for r in rows]
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
parent=json.loads((INC/'finance-spec.json').read_text())
reward_keys=['N_eligible','scenario_parameters','guarantee','contests','special','stacking','calendar','dated_prefunding','no_self_award_controls','finance_handoff']
source_paths=[INC/'concept.md',INC/'finance-spec.json',INC/'assumptions.csv',INC/'first-launch.csv',INC/'employee-profiles.csv',R/'supporting/fixtures/manifest.json',R/'supporting/fixtures/source/base.json',R/'supporting/measurement-contract.md',R/'supporting/finance-basis/scenario-inputs.json',R/'supporting/finance-basis/annual-three-year.csv',R/'supporting/reward-basis.md',R/'supporting/source-claims.json']
source_manifest={str(p.relative_to(R.parents[4])) if p.is_relative_to(R.parents[4]) else str(p):sha(p) for p in source_paths}
common={
 'schema_version':1,'source_version':'OTP-SYN-007-v1','source_manifest_sha256':'2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc',
 'epistemic_type':'prospective design assumptions; source outcomes synthetic; no bank measured effect',
 'exposure_days':10,'followup_days':14,'guarantee_R':2500,'top_R_per_person':150,'top_shares':[0.4,0.3,0.2,0.1],
 'input_contract':{
  'grain':'comparison_registry subject/quarter; project deliverable root once; personal memberships separate',
  'source_fields':{
   'period_rules':'rule_id,period_id,family,start,end,quality_close,approved_at,standard_owner,comparison_group_id',
   'work_events':'event_id,version,case_id,root_id,parent_id,duplicate_of,reopen_of,correction_of,assigned_at/by,assignment_history_status,due_at,status,accepted_at/by,type_id',
   'roster_capacity':'capacity_id,subject_id,period_id,active_days,scheduled_hours,fte,leave_hours,training_hours,allocation_fraction,assignment_history_status',
   'quality_acts':'act_id,inspection_id,case_id,subject_id,period_id,scope,criterion,scale,scale_version,sample_method,checker_id,evidence_status,finalized_at,observation_end,minor,major,critical,existing_minutes',
   'support_outcomes':'outcome_id,case_id,resolved,repeat_of,observation_end,invited,responded,csat_scale,csat_score,topic,queue_id,shift',
   'process_outcomes':'outcome_id,case_id,accepted,accepted_at,sla_due_at,returned,correction_of,observation_end',
   'project_records':'record_id,case_id,deliverable_id,benefit_id,parent_id,criteria_ref/agreed_at,acceptance_ref/owner/at,release_ref/at,usage_status/ref/owner/observed_at/coverage/units,rollback',
   'team_members':'membership_id,team_id,employee_id,period_id,contribution_share,personal_active_days,window_id,cohort_id',
   'approvals_audit':'approval_id,beneficiary_id,period_id,action,input_editor_id,signer_id,operator_id,signer_reporting_to,operator_reporting_to,alternate_signer_id,alternate_operator_id,signed_at',
   'source_manifest':'partition_id,table,period_id,expected_count,received_count,received_sha256,availability,readiness_at'},
  'units':'hours are h; QA 0..100 penalty-v1; ratios 0..1; usage distinct workflow runs per deliverable; money R',
  'worklog':'diagnostic hours only; changing recorded hours cannot change gates/rank/money',
  'elapsed':'status-time interval, not available capacity; never reward denominator',
  'capacity':'(scheduled_hours-leave_hours-training_hours)*allocation_fraction shown diagnostically; scheduled already includes FTE; intervals never increase level',
  'prospective':'rules and criteria approved before period; independently assigned complete scope; no outcome-dependent roster',
  'dedup':'exact event copies once; all versions retain original root; repeat/correction not new benefit; missing root pending; project acceptance/use at deliverable grain once'},
 'quality':{'reuse':'only existing compatible mature census acts; no new sample of20; accept correct subject/scope/period, penalty-v1 0..100, independent checker, finalized<=quality_close and observation_end>=quality_close',
   'coverage':'every original project case/part must have compatible one_distinct_case QA, OR an actually existing explicit same_deliverable_inspection act linked to its deliverable/root through source case_id/deliverable_id. Benefit dedup never broadens case QA scope. Flow cases/root links retained; same inspection_id counted once using worst penalty score',
   'score':'max(0,100-2*minor-10*major); mean over independent inspection_id, no rounding',
   'critical':'any compatible verified critical fail; missing/incomplete whole-register coverage pending, never infer absence from a small incompatible sample',
   'csat':'diagnostic only; report n contacts, invitations, responses, 1..5 mean and topic/queue/shift source context; no responses=null; cannot substitute QA'},
 'missing':{'real_fail':'not_earned only independently observed violation of absolute condition; never move qualification to another quarter',
   'own_exposure':'insufficient/not_earned; current fixed window0, next fixed annual window only',
   'missing_evidence':'pending; hold conditional maximum; no imputed success, fail or quality0',
   'lost_source':'source_incident/pending; restored proof earns original window/date, no expiry; known gap before start not_computable/uncovered route',
   'late':'actual acceptance/use after quality_close is true late result, not delayed source delivery; unavailable evidence pending until known',
   'rank_unknown':'hold group top at maximum rather than award an easier rank; normal guarantee independent of rank'},
 'signature':{'factual':'source result and QA owner independent of ALL members of awarded team and team ID/control chain',
   'posting_action':'input_correction_and_posting_review',
   'distinct_pairs':[['input_editor_id','signer_id'],['input_editor_id','operator_id'],['signer_id','operator_id']],
   'posting':'Only actual required action with valid signed_at, source_ref=period:beneficiary, nonempty independent editor/signer/operator and specified distinct role pairs authorizes U. All awarded team members and every explicitly provided reporting_to dependency are excluded; no signature or type_correction alone=>pending conditional reserve, never sanctioned U or actual ledger posting.',
   'conflict':'missing/invalid posting review => authorization pending, calculated qualification separately retained; valid independent review=>authorized U, actual ledger posting still absent. Alternate names never performed signature; held share not redistributed',
   'package':'employee/window/cohort; source version/hash/record refs; role rule version; exposure; QA scope/inspection IDs; normal/stretch/rank/tie; benefit/root ID; R; independent verifier and nonrecipient HR posting signature'},
 'rank':{'scope':'within frozen comparable family/group only; no interprofessional Q/impact score',
   'money':'150*n_unique_persons; registered group<2 units top0; only stretch eligible; four slots40/30/20/10; absent slots unissued',
   'tie':'equal rank keys tie; positions r..r+k-1 pool all intersecting fixed slots1..4 / k, even ties beyond4; apply predeclared contribution shares; floor only final personal R; unallocated share/remainder unissued',
   'uncertain':'any unresolved ordinary result/stage stretch evidence => group top pending, personal normal independent; personal signature conflict reserves that share only'},
 'roles':{
  'support':{'minimum_roots':20,'quality_min':97,'accepted_min':0.95,'adverse_max':0.05,'stretch_quality':99},
  'backoffice':{'minimum_roots':20,'quality_min':98,'accepted_min':0.95,'sla_min':0.95,'adverse_max':0.02,'stretch_quality':99},
  'project':{'minimum_roots':1,'quality_min':98,'stretch_quality':99,'stretch_usage':100}},
 'evaluation':'evaluator.py evaluate(data,spec) uses only public expanded tables; IDs label output, never choose rules; run() writes own CSVs; no source mutation'}

for number,mode,title in [(20,'role_conditions','Ролевые условия качества и результата'),(21,'ordinary_commitment','Принятый и используемый обычный результат')]:
 d=B/f'con-{number:03d}';d.mkdir(exist_ok=True)
 if number==21:(d/'evaluator.py').write_bytes((HERE/'evaluator.py').read_bytes())
 key=f'CON-{number:03d}@v2';spec=copy.deepcopy(common);spec.update(candidate_key=key,mode=mode)
 # Preserve the common cash/shop vector actually read during rework, so later
 # independent checks can replace their reports without changing these inputs.
 extract=d/'common-shop-inputs.csv'
 if not extract.exists():
  original=R/'checks/finance/time-correct-HR.csv'
  selected=[{k:row[k] for k in ('E_R_year','scenario','fixed_C_year','month','fixed_old_shop_HR_h')}
            for row in csv.DictReader(original.open()) if row['candidate_key']=='CON-020@v1']
  assert selected
  csvout(extract,selected)
  dump(d/'common-shop-inputs-meta.json',{'candidate_key':key,'source_path':'checks/finance/time-correct-HR.csv',
    'source_sha256_at_capture':sha(original),'source_locator':'B control row common fixed_old_shop_HR_h only; key E/scenario/fixed/month',
    'owned_extract_sha256':sha(extract),'scope':'no source scores, ranks or outputs of parallel branch; exact preserved common calendar vector'})
 if number==20:
  spec['normal']='All role-specific absolute conditions and common evidence/exposure/quality gates. Support accepted roots/all assigned roots>=.95 and repeat<=.05. Back accepted>=.95, SLA timely/all assigned due roots>=.95, returns<=.02. Project all observed prospective deliverable roots accepted+used by quality_close, usage>=1 and no rollback. At least1 project root, never8tickets.'
  spec['stretch']='Support accepted1/repeat0/QA>=99; back accepted1/SLA1/return0/QA>=99; project min usage>=100 distinct runs/root and QA>=99. Normal must pass first. No 1.10 multiplier on percentages.'
  spec['rank']['keys']={'support':['acceptance_rate DESC','repeat_rate ASC','QA_mean DESC'],'backoffice':['SLA_share DESC','acceptance_rate DESC','return_share ASC','QA_mean DESC'],'project':['min(usage_per_root,100) DESC','QA_mean DESC']}
 else:
  spec['stretch_early_days']=14
  spec['normal']='Complete concrete ordinary work-plan result with independent acceptance+actual use, not nomination. Project existing criteria_ref agreed before period and all deliverable roots accepted+used by close, QA/exposure. Flow assigned scope is real source; missing result-bundle acceptance/use confirmation is new, not assumed present. All assigned roots accepted and no adverse root for complete ordinary commitment.'
  spec['stretch']='Flow: the accepted used complete ordinary service bundle also has every obligation accepted by its existing due date, no repeat/return. Project: ordinary stage accepted >=14calendar days before its prospective stage due_at, used by close. Missing stage due_at leaves normal intact and top pending, never infer from child due_at.'
  spec['rank']['keys']={'support':[],'backoffice':[],'project':[]}
  spec['rank']['interpretation']='No numerical comparison of unlike commitments; every verified stretch result in same group ties. Fixed slots shared exactly; this is deliberate limited discrimination.'
  spec['new_missing_fields']={'ordinary_commitments':'one ordinary result bundle/subject/quarter: plan_ref,agreed_at,scope_ref,root_ids (all source assigned roots),owner,accepted,acceptance_ref/at,used,usage_ref/at. Only when no existing working act covers result-bundle acceptance/use; project use/acceptance already exists and is reused.',
    'project_records.commitment_due_at':'only for stretch: independently prospective deliverable-stage deadline from existing plan. Absent in fixture; child deadlines not stage deadlines.',
    'cost':'flow owner6min per quarter result bundle for genuinely missing acceptance/use scope; not employee dossier; use existing signed act if identical coverage, marginal check then0'}
 dump(d/'metrics-spec.json',spec)
 finance=copy.deepcopy(parent)
 finance.update(candidate_key=key,metric_spec_ref='metrics-spec.json')
 finance['operational_metrics_assumptions']={'superseded_for_measurement_only':True,'definition':'metrics-spec.json replaces inherited Q/exposure/quality/rank conditions; reward amounts/windows/shares/caps unchanged'}
 finance['guarantee']['qualification']='metrics-spec.json normal plus personal exposure and independent evidence; both fixed quarters must earn normal; absolute role condition, never rank/quota. See window-guarantee.csv; fixture P1/P2 qualification examples only, not production personal day15 calendar.'
 finance['guarantee']['part_time']='Same G without FTE haircut if metrics-spec.json personal exposure and normal pass both fixed quarters; insufficient own exposure means0G this fixed window, next annual window only.'
 finance['guarantee']['nonqualification']='metrics-spec.json missing: true fail or own insufficient exposure=>0G fixed window; lost source=>pending/recovery with maximum reserved; proven late-delivered timely facts retain original window/date, not a future retry.'
 finance['guarantee']['newcomer']='No past baseline; prospective work in both personal fixed quarters with metrics-spec.json exposure/normal required. Missing first quarter means next fixed annual window; no individual date extension.'
 finance['contests']['ranking']='metrics-spec.json stretch and rank.keys: '+('role-specific lexicographic exact ratios, no universal Q; equal keys tie' if number==20 else 'all independently verified stretch commitments tie; missing stage deadline affects top only, normal retained')+'. Only frozen comparable home group; missing competitor evidence reserves top maximum.'
 finance['calendar']['source']='../../../../../incumbent/first-launch.csv'
 finance['measurement_override']={'source_only':True,'scope':'measurement definitions replaced in guarantee qualification/part_time/nonqualification/newcomer and contests.ranking; money/windows unchanged. Calendar source points to unchanged imported file.'}
 resource=[]
 # Shared mix: 800support+800back checks/month;160team checks;2400 personal checks.
 for reuse in (0,0.5,1):
  qa_existing= (800*38+800*22+160*4.5)*3/60 # all existing work, even if unusable
  needed_acts=800*38+800*22+160*4.5
  new_qa=needed_acts*(1-reuse)*5/60
  new={'HR':72.0+16+6,'manager':((2400*4)+(1760*2)+(120*12)+(12*8))/60+36+6+(1600*6/60 if number==21 else 0),'employee':20+120*5/60+72*3/60,'IT':24.0}
  existing_cost=qa_existing*1500*12
  new_cost=sum(new[k]*{'HR':1000,'manager':1500,'employee':1000,'IT':2000}[k] for k in new)*12+new_qa*1500*12
  resource.append({'QA_reuse_share':reuse,'existing_business_QA_h_month':qa_existing,'existing_business_QA_resource_RUB_year':existing_cost,'new_missing_QA_h_month':new_qa,
   'new_recognition_hours_month_by_role':new,'new_resource_RUB_year':new_cost,'full_existing_plus_new_RUB_year':existing_cost+new_cost,
   'new_resource_x2_RUB_year':new_cost*2,'full_existing_plus_new_x2_RUB_year':(existing_cost+new_cost)*2,'replacement25pct_new_cash_RUB_year':new_cost*.25,
   'new_flow_bundle_accept_use_h_month':1600*6/60 if number==21 else 0,
   'special_HR_h_month':16,'special_manager_h_month':36,'special_employee_h_month':20,
   'appeal_employee_h_month':10,'correction_HR_h_month':6,'correction_manager_h_month':6,'correction_employee_h_month':3.6})
 finance['workload']={'classification':'all norms/scaling assumed, not actual bank staffing; ordinary useful business labor unknown beyond scenario QA',
   'mix':{'N':7200,'support':2400,'backoffice':2400,'project_people':2400,'project_teams':480,'team_size':5,'groups':180,'quarter_person_checks_year':28800},
   'existing':'actual synthetic existing QA3min/inspection; annualized common mix needs 800*38support+800*22back+160*4.5project existing acts/month,2436h/month; existing business production is not free and remains unpriced/unknown',
   'new_QA':'only missing usable coverage;48720 original case/part inspections/month at5min:4060/2030/0h for QA reuse0/50/100. Project benefit deduplicated but case QA not expanded unless an actual explicit whole-deliverable act exists. No synthetic whole-root act; source absence=>pending, not fabricated QA.',
   'new_recognition':'personal independent source/exposure/signature4min*2400;2min*1760 quality-result reconciliations;120appeals*12min owner;12recusals*8min/month. HR72h base includes personal batch6h, guarantee ledger4h, exports24h, groups12h,120appeals*6min=12h, recusal2h, monthly control12h. Then special HR16h/manager36h/employee20h and72corrections HR6h/manager6h/employee3.6h plus120appeals employee10h added. No second ordinary reward report, voluntary application/appeal labor not zero.',
   'special_and_appeal_counters':{
     'special_requests_month':200,'special_awards_E24_month':32,
     'special_HR_request_minutes':4,'special_HR_award_post_review_minutes':5,
     'special_owner_request_minutes':10,'special_independent_owner_award_minutes':5,'special_employee_request_minutes':6,
     'special_hours_month':{'HR':16,'manager':36,'employee':20},'special_resource_RUB_year':1080000,
     'appeals_month':120,'appeal_HR_minutes':6,'appeal_owner_minutes':12,'appeal_employee_minutes':5,
     'appeal_HR12h_owner24h_already_in_base_exceptions':True,'appeal_employee10h_new':True,
     'corrections_month':72,'correction_HR_minutes':5,'correction_owner_minutes':5,'correction_employee_minutes':3,
     'correction_new_hours_month':{'HR':6,'manager':6,'employee':3.6},
     'counts_classification':'all scenario assumptions, not source facts. 120 exceptions assigned entirely to120appeals;72corrections separate; source incidents exceeding these counts add30min/operator+8min/completeness+12min/owner each, never assumed free.',
     'E36':'48awards instead of32 at same200requests => additional HR=manager=16*5/60h per month; employee requests unchanged; resource and monthly cash sensitivity separate, reward unchanged'},
   'E36_new_resource_delta_RUB_year':40000,
   'E36_special_hours_month':{'HR':(200*4+48*5)/60,'manager':(200*10+48*5)/60,'employee':20},
   'new_IT':'24h/month: export/integrity/rule/ledger support; setup initial IT640h+HR80h+manager240h; bundle contract con021 additional IT40h+manager32h',
   'launch_hours':{'HR':80,'manager':240+(32 if number==21 else 0),'employee':0,'IT':640+(40 if number==21 else 0)},
   'launch_resource_RUB':80*1000+(240+(32 if number==21 else 0))*1500+(640+(40 if number==21 else 0))*2000,
   'source_recovery':'30min/data-operator/lost partition;12min owner/exception plus8min completeness/partition. Rates HR1000/manager1500/employee1000/IT2000. Full source creation not covered by recovery; unavailable until prospective independent evidence exists.',
   'readiness_scenarios':resource,
   'stages':['prospective rules/scope before offer','existing working export and QA','new integrity/coverage check','missing evidence only','independent per-person entitlement/signature','HR posting and appeals','shop redemption unchanged'],
   'cash':'new external vendor0 scenario; extra procurement delta0 due to measurement; incremental labor cash =25%new resource sensitivity, not all resource; source creation not assumed ready',
   'capacity':'no capacity pass claimed: common shop+HR94h/month conservative reserve; exact cohort trace includes special/corrections and request/appeal peaks. Independent manager/QA capacity unknown; E36 adds16award reviews at5min forHR/owner and inherited reward fails retained'}
 finance['source_sha256_new']=dict(source_manifest,**{str((d/'common-shop-inputs.csv').relative_to(R.parents[4])):sha(extract),str((d/'common-shop-inputs-meta.json').relative_to(R.parents[4])):sha(d/'common-shop-inputs-meta.json')})
 finance['inherited_core_locators']={'base':'project-root analysis/iterations/iteration-007/incumbent (unchanged copies from006)','hashes':{x.name:sha(x) for x in source_paths[:5]},'first_launch':'E_R_year=24000000/36000000 ×months1..39; first G7..15; max800G/month; original calendar copied read-only', 'reward_sections':reward_keys}
 finance['output_paths']=['metrics-spec.json','decisions.csv','unit-decisions.csv','window-guarantee.csv','top.csv','group-top-reserve.csv','money-examples.csv','traces.json','approval-traces.json','resource.csv','resource-stages.csv','calendar-resource.csv','monthly-HR-combined.csv','HR-peaks.csv']
 finance.pop('version_provenance',None)
 dump(d/'finance-spec.json',finance)
 flat=[]
 for r in resource:
  rr=dict(r);new=rr.pop('new_recognition_hours_month_by_role');rr.update({k+'_new_h_month':v for k,v in new.items()});flat.append(rr)
 csvout(d/'resource.csv',flat)
 launch=list(csv.DictReader((INC/'first-launch.csv').open()))
 cal=[]
 for row in launch:
  # Recognition processing follows real cohorts: quarter0..2400, G0..800/month.
  checks=float(row['ordinary_cycle_records']);g=float(row['guarantee_post_all_success_R'])/(2500 if int(row['E_R_year'])==24000000 else 3750)
  special_awards=32 if int(row['E_R_year'])==24000000 else 48
  special_hr=(200*4+special_awards*5)/60
  hr=62+checks*.15/60+g*.1/60+special_hr+72*5/60
  newshop=float(row['R_post_all_success_max'])/2500*.02
  cal.append({'E_R_year':row['E_R_year'],'month':row['month'],'source_cycle_records':checks,'guarantee_persons':g,
     'special_requests':200,'special_awards':special_awards,'appeals':120,'corrections':72,'special_HR_h':special_hr,'correction_HR_h':6,'recognition_HR_h':hr,
     'new_R_certificate500_order_HR_h':newshop,'recognition_plus_new_R_shop_HR_h':hr+newshop,'common_fixed_old_shop_HR_h':'add M05 same month; not zero','capacity220_status':'uncertain/add fixed+old; no annual-average pass'})
 csvout(d/'calendar-resource.csv',cal)
 # Reuse only checked B common fixed/old-shop inputs; no other branch results read.
 common_month=[];cal_by={(x['E_R_year'],x['month']):x for x in cal}
 for row in csv.DictReader(extract.open()):
  c=cal_by[(row['E_R_year'],row['month'])]
  fixed_old=float(row['fixed_old_shop_HR_h']);newshop=c['new_R_certificate500_order_HR_h']
  total=fixed_old+newshop+c['recognition_HR_h']
  common_month.append({'E_R_year':row['E_R_year'],'scenario':row['scenario'],'fixed_C_year':row['fixed_C_year'],'month':row['month'],
   'fixed_old_shop_HR_h':fixed_old,'new_R_certificate500_HR_h':newshop,'recognition_HR_h':c['recognition_HR_h'],
   'total_HR_h':total,'capacity220_pass':total<=220,
   'total_HR_all_labor_x2':total*2,'total_HR_recognition_only_x2':fixed_old+newshop+2*c['recognition_HR_h'],
   'boundary':'same-month imported common fixed/old shop only; own complete recognition and500certificate R flow; no capacity uplift'})
 csvout(d/'monthly-HR-combined.csv',common_month)
 peaks=[]
 for e,scenario,fixed in sorted({(x['E_R_year'],x['scenario'],x['fixed_C_year']) for x in common_month}):
  rows_m=[x for x in common_month if (x['E_R_year'],x['scenario'],x['fixed_C_year'])==(e,scenario,fixed)]
  peak=max(rows_m,key=lambda x:x['total_HR_h']);peaks.append(dict(peak))
 csvout(d/'HR-peaks.csv',peaks)
 # Every recurring role-minute has a named stage/denominator, no hidden special.
 stages=[
  {'stage':'personal_exposure_and_review','owner':'manager','units_month':2400,'minutes_unit':4,'hours_month':160,'existing':False},
  {'stage':'result_QA_reconciliation','owner':'manager','units_month':1760,'minutes_unit':2,'hours_month':1760*2/60,'existing':False},
  {'stage':'appeal_owner','owner':'manager','units_month':120,'minutes_unit':12,'hours_month':24,'existing':False},
  {'stage':'recusal_owner','owner':'manager','units_month':12,'minutes_unit':8,'hours_month':1.6,'existing':False},
  {'stage':'HR_person_batch','owner':'HR','units_month':2400,'minutes_unit':.15,'hours_month':6,'existing':False},
  {'stage':'HR_guarantee_ledger_reserve','owner':'HR','units_month':2400,'minutes_unit':.1,'hours_month':4,'existing':False},
  {'stage':'HR_export','owner':'HR','units_month':180,'minutes_unit':8,'hours_month':24,'existing':False},
  {'stage':'HR_group_review','owner':'HR','units_month':180,'minutes_unit':4,'hours_month':12,'existing':False},
  {'stage':'appeal_HR','owner':'HR','units_month':120,'minutes_unit':6,'hours_month':12,'existing':False},
  {'stage':'HR_recusal','owner':'HR','units_month':12,'minutes_unit':10,'hours_month':2,'existing':False},
  {'stage':'HR_monthly_control','owner':'HR','units_month':1,'minutes_unit':720,'hours_month':12,'existing':False},
  {'stage':'special_request_HR','owner':'HR','units_month':200,'minutes_unit':4,'hours_month':200*4/60,'existing':False},
  {'stage':'special_award_HR','owner':'HR','units_month':32,'minutes_unit':5,'hours_month':32*5/60,'existing':False},
  {'stage':'special_request_owner','owner':'manager','units_month':200,'minutes_unit':10,'hours_month':200*10/60,'existing':False},
  {'stage':'special_award_independent_owner','owner':'manager','units_month':32,'minutes_unit':5,'hours_month':32*5/60,'existing':False},
  {'stage':'special_request_employee','owner':'employee','units_month':200,'minutes_unit':6,'hours_month':20,'existing':False},
  {'stage':'appeal_employee','owner':'employee','units_month':120,'minutes_unit':5,'hours_month':10,'existing':False},
  {'stage':'correction_HR','owner':'HR','units_month':72,'minutes_unit':5,'hours_month':6,'existing':False},
  {'stage':'correction_owner','owner':'manager','units_month':72,'minutes_unit':5,'hours_month':6,'existing':False},
  {'stage':'correction_employee','owner':'employee','units_month':72,'minutes_unit':3,'hours_month':3.6,'existing':False},
  {'stage':'IT_export_integrity_rules','owner':'IT','units_month':1,'minutes_unit':1440,'hours_month':24,'existing':False},
  {'stage':'ordinary_bundle_missing_use_only','owner':'manager','units_month':1600 if number==21 else 0,'minutes_unit':6,'hours_month':160 if number==21 else 0,'existing':False},
  {'stage':'existing_business_QA','owner':'manager','units_month':48720,'minutes_unit':3,'hours_month':2436,'existing':True}]
 csvout(d/'resource-stages.csv',stages)
 # Money/calendar boundary excludes explicitly replaced measurement text and path.
 def invariant_core(x):
  out={k:copy.deepcopy(x[k]) for k in reward_keys}
  for k in ('qualification','part_time','nonqualification','newcomer'):out['guarantee'].pop(k)
  out['contests'].pop('ranking');out['calendar'].pop('source')
  return out
 assert invariant_core(finance)==invariant_core(parent)
 (d/'assumptions.csv').write_text((INC/'assumptions.csv').read_text()+
  '\nB01,role_thresholds,metrics-spec.json,per quarter,design assumption,Prospective published before effort; not OTP standard\n'+
  'B02,QA_readiness,0/50/100,percent,shared assumption,Same source readiness all candidates; missing checks not fabricated\n'+
  'B03,mix,2400/2400/2400,persons,shared assumption,480 project teams5;180groups;28800checks/year\n'+
  'B04,existing_QA,2436,hours/month,calculation,Synthetic mean38/22/4.5 acts and3minutes; not bank workload\n'+
  'B05,new_missing_QA,5,min/missing independent inspection,design assumption,Only gap to needed coverage; not new20per person\n'+
  'B06,independent_decision,4,min/person-quarter,design assumption,Exposure and signature; no second employee report\n'+
  'B07,exceptions,120,cases/month,design assumption,12min owner;12 own recusals8min\n'+
  'B08,flow_bundle_new_check,'+('6' if number==21 else '0')+',min/flow-person-quarter,design assumption,Only missing concrete acceptance/use scope; no duplicate existing act\n'+
  'B09,causal_effect,unknown,n/a,hypothesis,No measured bank uplift; controlled pilot required\n'+
  'B10,new_case_QA_coverage,48720,inspections/month,calculation,Every project case or actual whole-deliverable act;4060/2030/0newhours forreuse0/50/100\n'+
  'B11,special,200requests/32awards,per month,design assumption,HR16/manager36/employee20h;E36awards48addsHR1.3333/manager1.3333h\n'+
  'B12,appeals,120,cases/month,design assumption,HR6min+owner12min included base exceptions;employee5min separately10h\n'+
  'B13,corrections,72,cases/month,design assumption,HR5/owner5/employee3min separately6/6/3.6h\n'+
  'B14,authorization,actual signed correct action,per personal period,design assumption,All recipient team and explicit reporting excluded;3distinct actors;no signature=>conditionalreserve notU\n')
 (d/'source-manifest.json').write_text(json.dumps({'candidate_key':key,'files_sha256':finance['source_sha256_new']},ensure_ascii=False,indent=2)+'\n')
 # Candidate version on every assumptions row, without modifying frozen source assumptions.
 assumption_rows=list(csv.DictReader((d/'assumptions.csv').open()))
 assumption_rows=[row for row in assumption_rows if row.get('id')]
 csvout(d/'assumptions.csv',assumption_rows)
 subprocess.run([sys.executable,str(d/'evaluator.py')],check=True)

 # Fully specified normal/stretch employee profiles preserve inherited calendars.
 profiles=[
  ('ordinary_good_no_top',2500,0,1250,'both quarters normal; all missing proof/signature actually obtained; no top'),
  ('strong_first_each4',2500,9600,1250,'group40; stretch proven; four first places2400 each; not promised rank'),
  ('strong_stops_winning',2500,2400,1250,'one first place only; later no top'),
  ('tie_two_first_each4',2500,8400,1250,'(2400+1800)/2=2100 per quarter;4quarters'),
  ('team_first_equal5',2500,1920,1250,'one pool6000; first2400 split.2=480;4quarters'),
  ('team_normal_no_top',2500,0,1250,'guarantee personal; no duplicate team G'),
  ('half_FTE_sufficient',2500,0,1250,'20independent flow roots and10days; no FTE haircut'),
  ('newcomer_from_start',2500,0,1050,'both fixed quarters sufficient; G at cohort m7..15'),
  ('hire_m4_missed_firstquarter',0,0,1050,'current fixed window0; next m13..18; potential rightm19; no shift'),
  ('insufficient_exposure',0,0,1250,'not personal quality failure; next fixed annual window only'),
  ('regional_catalog',2500,0,1250,'500rub certificate only if region/vendor/channel actually usable; address availability unverified'),
  ('no_corporate_events',2500,0,0,'ordinary normal, no assumed corporate activity;2500C from2500R buys500rub scenarioSKU')]
 rows=[]
 for name,g,t,c,cond in profiles:
  rows.append({'profile':name,'G_R_year':g,'top_R_year':t,'R_year':g+t,'fixed_C_year':c,'C_if_all_R_converted':g+t+c,
    'guarantee_first_right':'cohort m7..15 unless miss; next same fixed date12months later','posting':'independent signed; U retained if delayed',
    'first_useful_reward':'at most first G post for2500C500rub if SKU available; actual receipt date unknown','condition':cond})
 csvout(d/'employee-profiles.csv',rows)
 # Trace source-only and reward checks, not an independent admission.
 dec=list(csv.DictReader((d/'decisions.csv').open()));units=list(csv.DictReader((d/'unit-decisions.csv').open()))
 baseline=[r for r in units if r['scenario']=='base']
 checks={'candidate':key,'type':'author self-check, not independent gate admission','scenarios':len({r['scenario'] for r in dec}),
  'personal_decision_rows':len(dec),'unit_decision_rows':len(units),'monetary_invariants_equal':invariant_core(finance)==invariant_core(parent),
  'source_manifest_sha_match':sha(R/'supporting/fixtures/manifest.json')==common['source_manifest_sha256'],
  'base_units':[{k:r[k] for k in ['period','subject','state','normal','stretch','roots','accepted_roots','qa_inspections','qa_mean','unit_top_R','top_state','reason']} for r in baseline],
  'limitations':['ordinary_commitment flow acceptance/use absent => pending, not worker failure' if number==21 else 'QA coverage/census may be expensive if existing evidence unavailable',
                 'no real bank API/workforce/capacity/cost or causal effect established','independent finance/evidence/review still required']}
 dump(d/'self-check.json',checks)
 print(key,'complete data files',len(dec),'decisions')
