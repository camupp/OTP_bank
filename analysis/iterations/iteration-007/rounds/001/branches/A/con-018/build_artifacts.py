#!/usr/bin/env python3
"""Build own branch artifacts only; read frozen inputs; never execute prior financial model."""
import csv,hashlib,json,copy,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BRANCH=HERE.parent
ROUND=HERE.parents[2]
RUN=ROUND.parents[1]
PARENT=RUN/'incumbent'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvsave(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
reward_keys=['N_eligible','scenario_parameters','guarantee','contests','special','stacking','calendar','dated_prefunding','finance_handoff','no_self_award_controls']
parent=json.loads((PARENT/'finance-spec.json').read_text())
reward={k:parent[k] for k in reward_keys}
reward_sha=hashlib.sha256(json.dumps(reward,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
core_paths=[PARENT/'finance-spec.json',PARENT/'first-launch.csv',PARENT/'employee-profiles.csv',PARENT/'concept.md',PARENT/'assumptions.csv',ROUND/'supporting/finance-basis/scenario-inputs.json',ROUND/'supporting/finance-basis/annual-three-year.csv',ROUND/'supporting/finance-basis/source-manifest.json']
core=[{'path':str(p.relative_to(RUN.parent.parent.parent)),'sha256':sha(p)} for p in core_paths]
# Path base for core is repository root (analysis/iterations/iteration-007 up three parents).
repo=RUN.parents[2]
core=[{'path':str(p.relative_to(repo)),'sha256':sha(p)} for p in core_paths]
for num,mode,title in [(18,'capacity','Принятый объём при независимой мощности'),(19,'obligations','Исполнение закреплённых обязательств')]:
 folder=BRANCH/f'con-{num:03d}'
 spec={'schema_version':'otp-metrics-007-1','candidate_key':f'CON-{num:03d}@v2','rule_version':f'A{num}-prospective-2','classification':'all thresholds are prospective design assumptions; all records synthetic',
  'mechanism':mode,'source_version':'OTP-SYN-007-v1','source_manifest_sha256':'2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc',
  'normal':1.0 if mode=='capacity' else .95,'stretch':1.10 if mode=='capacity' else 1.0,
  'min_active_days':20,'min_flow_roots':20,'project_min_usage':1,
  'stratum_normal_floor':.95,'backoffice_SLA_normal':.95,'guarantee_R':2500,'top_R_per_person':150,'top_shares':[.4,.3,.2,.1],
  'grain':{'support':'one person × due-assignment quarter; unique case-root','backoffice':'one person × due-assignment quarter; unique operation-root','project':'one team × assigned-quarter × root deliverable; personal exposure/one fixed annual window separately'},
  'required_fields':{
   'period_rules':['period_id','start','end','quality_close','standard_owner','approved_at','stratum_allocations','outcome_followup_days'],
   'work_events':['event_id','version','case_id','root_id','duplicate_of','reopen_of','correction_of','subject_id','family','period_id','type_id','assigned_at','assigned_by','assignment_history_status','due_at','accepted_at','accepted_by'],
   'roster_capacity':['scheduled_hours','leave_hours','training_hours','allocation_fraction','fte','active_days','capacity_owner','registered_at','assignment_history_status'],
   'classifier':['type_id','standard_units','unit','engineering_minutes_per_standard_unit','approved_at','complexity_owner','employee_editable'],
   'project_records':['deliverable_id','benefit_id','criteria_ref','criteria_agreed_at','acceptance_at','acceptance_ref','acceptance_owner','release_at','release_ref','usage_status','usage_units','usage_measure','usage_coverage','usage_observed_at','usage_ref','usage_owner','rollback'],
   'quality_acts':['inspection_id','case_id','subject_id','period_id','scope','coverage_object','criterion','scale','scale_version','score','minor','major','critical','checker_id','observation_start','observation_end','finalized_at','sample_method','evidence_status'],
   'approvals_audit':['beneficiary_id','period_id','action','input_editor_id','signer_id','operator_id','appeal_owner_id','signer_reporting_to','operator_reporting_to','signed_at','alternate_signer_id','alternate_operator_id'],
   'team_members':['employee_id','team_id','personal_active_days','contribution_share','approved_by','approved_at','window_id','cohort_id'],
   'source_manifest':['table','period_id','availability','expected_count','received_count','expected_before_start','generated_at'],
   'comparison_registry':['subject_id','period_id','home_pool_id','window_id','cohort_id']},
  'formula': ('accepted units=sum(class.standard_units once per accepted root); H=(scheduled_hours-leave_hours-training_hours-union(independently approved exceptions))*allocation_fraction; E=sum(H*stratum.capacity_share*stratum.standard_units_per_hour); value=accepted_units/E; normal value>=1 and each stratum ratio>=0.95; stretch value>=1.10 and each stratum>=1. No FTE second multiplier; no mix_weight second multiplication. Project requires root-specific standard absent from fixture.' if mode=='capacity' else 'cohort=all independently assigned unique roots due by end of quarter, including unresolved/reopened/late; support numerator=accepted resolved nonrepeat roots, backoffice numerator=accepted in-SLA nonreturned roots, project numerator=accepted released used matured root obligations. value=numerator/all_due_roots; normal>=0.95, stretch=1.00. No worklog or available-hours denominator; no complexity weights in outcome fraction.'),
  'project_contract':{'due_rule':'All root obligations assigned in quarter with pre-quarter criteria are due by quarter end; independent prospective programme contract, not task due_at. This assumption must be announced before effort; open root without project evidence stays in denominator pending.','use':'At least one observed real workflow run for declared one_internal_process; positive adoption evidence, not monetary benefit or impact_score. Repeated usage_units for parts counted once per deliverable.','maturity':'14 days from release to usage observation; observation no later than quality_close. Actual acceptance/release after period end is failed period, distinct from late export of timely proof.','capacity_standard':{'required_fields':['root_id','accepted_used_stage_class','standard_work_units_at_root','standard_units_per_hour_at_root','scope_version','approved_before_period','independent_engineering_owner'],'fixture_status':'absent; IT-DEL is task class, not a normative root result','if_absent':'not_computable, no substituted 480x weight','future_setup':'80 manager+40 IT hours preliminary commissioning included in launch; no fabricated normative values in runtime'}},
  'quality':{'compatible':'personal/team scope as applicable; defect_penalty,0..100,penalty-v1; independently finalized by quality_close, observation through quality_close, census_of_scenario_work_register. Whole root/case coverage required; same inspection_id is one check; projects must cover all source parts or same_deliverable_inspection.','pass':'root-wise worst observed score; average across unique roots>=95, critical=0 and major=0. This is a conservative observed QA gate, not an inference of population quality.','missing':'incompatible, other period, wrong scope, unobserved consequences or missing independent acts => pending, not zero; missing before start=>not_computable; lost partition=>source_incident/pending.','CSAT':'report eligible/invited/responded and scale separately; no CSAT rank/gate, no blending 97/100 and4/5.','reuse':'Only matching criterion+scope+period+inspection+independence reused. No routine new20-case QA of every person; unavailable trait requires separately costed check.'},
  'rank':{'order':'inside same registered role/source group, descending ROUND_HALF_UP(value,2); original unrounded value decides normal/stretch. No ranking across families.','ties':'All equal rounded values share scheduled slot fractions spanning ranks r..r+k-1 intersect1..4, including all tied units beyond4. No deterministic ID tiebreak payout.','small_n':'less than2 registered units => no top. Unqualified/absent slots remain unissued, no renormalization.','team':'pool=150R*unique registered people; allocate one team award after ties, multiply predeclared contribution_share, floor final personal R only; shares<=1; unallocated share remains unissued.','missing':'No stretch rank if source unconfirmed; hold contested money pending independent resolution; rerank group on restored version with preserved original rights.'},
  'windows':{'fixed':'one preassigned six-month/two-quarter window every12months, personal cohort unchanged on transfer; same G for eligible part-time person; no floating retry','failure':'low result/quality fail or insufficient exposure =>0G current window, next fixedannual window; no retrospective new cohort','incidents':'late restored proof of timely performance relates to original right/date; U and orders persist, no savings from delay','fixture_mapping':'P1/P2 are fixture-labelled quarters of W2026-A. Source quarterly dates are illustrative; G date maps to P2 quality-close28July2026. Deployment must use inherited Jan15..Jul14 cohort contract; do not extend effort to qualityclose.'},
  'missing_and_updates':{'statuses':['earned','not_earned','pending','not_computable'],'data_status':['sufficient','insufficient','source_incident'],'precedence':'known insufficient personal exposure=>not_earned; known prestart gap=>not_computable; lost source=>pending; unconfirmed evidence=>pending; norm absent=>not_computable; verified quality fail=>not_earned; below normal=>not_earned; else measured eligibility earned. Posting requires independent signoff.','updates':'source versions append/recompute same window; no subject/scenario ID conditionals. Prospective metric changes only for unopened periods; appeal independent5+5 workingdays assumption.'},
  'signing':{'recipient_excluded':'own source edits, own classifier change, own exception, acceptance, QA, appeal, signature and posting; team members/control chain excluded','alternate':'Named alternate is routing information, never a fabricated executed signature; self-edited records remain held until independent replacement verification.','missing_signature':'computed eligibility and calculated amount retained, payment held; U only after signed evidence; no signed_at invented for absent records.'},
  'refresh':{'source_import':'daily/versioned during window; final source completeness+quality close; quarterly eligibility and top then personal two-quarter ledger','owner':'independent data/quality/process owner; HR validates rights/fund, distinct nonrecipient operator posts; appeal owner separate'},
  'implementation':'evaluator.py evaluate(data,spec) is authoritative executable detail; only public reader materializes tables; JSON and docs publish assumptions before evaluation'}
 save(folder/'metrics-spec.json',spec)
 # Count every new operation, independent checks and generation separately.
 resource_rows=[]
 for readiness in ['base','export_fallback','source_absent']:
  for reuse in [0,.5,1]:
   for mult in [1,2]:
    for cash_share in [0,.25]:
     HR=96;manager=154.26666666666665+160+64+24+(40 if mode=='capacity' else 1760/60);employee=113.6;IT=15
     if readiness!='base':HR+=20;manager+=80
     if readiness=='source_absent':manager+=700;employee+=1300
     new_QA=(1600*30+160*4.5)*5/60*(1-reuse)
     manager+=new_QA
     hrs={'HR':HR*mult,'manager':manager*mult,'employee':employee*mult,'IT':IT*mult}
     rates={'HR':1000,'manager':1500,'employee':1000,'IT':2000}
     cost=sum(hrs[k]*rates[k] for k in hrs)*12
     resource_rows.append({'source_readiness':readiness,'QA_reuse':reuse,'labor_multiplier':mult,'paid_substitution_share':cash_share,
       **{k+'_new_hours_month':v for k,v in hrs.items()},'new_QA_hours_month':new_QA*mult,'existing_business_QA_hours_month_separate':2436,
       'resource_RUB_year':cost,'new_cash_outside_procurement_RUB_year':cost*cash_share,'source_validity':'not_proven_by_labor_estimate' if readiness=='source_absent' else 'hypothesis',
       'scope_N':7200,'flow_QA_units_month':1600,'project_team_QA_units_month':160,'personal_checks_month':2400,'groups':180})
 csvsave(folder/'resource-sensitivity.csv',resource_rows)
 base=next(x for x in resource_rows if x['source_readiness']=='base' and x['QA_reuse']==1 and x['labor_multiplier']==1 and x['paid_substitution_share']==0)
 finance=copy.deepcopy(parent);finance['candidate_key']=spec['candidate_key'];finance['metric_spec_ref']='metrics-spec.json'
 finance['operational_metrics_assumptions']=spec
 finance['workload']={'classification':'Prospective resource scenario; no bank capacity established','resource_table':'resource-sensitivity.csv','same_mix':{'support_people':2400,'backoffice_people':2400,'project_people':2400,'project_teams':480,'team_size':5,'groups':180,'group_n':40,'personal_quarter_checks_year':28800,'quality_units_month':1760},
  'stages':{'existing_business_data_generation':'unknown ordinary paid productive work; not zero, not automatically new; no extra per-task employee diary',
   'existing_business_QA':'(1600flow packages*30 root cases+160project packages*4.5 part inspections)*3min/60=2436h/month illustration separately; 30/4.5 prospective workload assumptions. Source source/base.json#resource_assumptions gives per-case3min. Existing work is not abolished at0% compatible reuse.',
   'reward_operations_HR':'88h/month: fixed6;200special*4min;48approval*5min;120appeals*6min;72corrections*5min;12recusals*5min;10rules*10min;180exports*10min;2400batch*.25min;2400annualledger*.1min',
   'reward_operations_manager':'154.2666667h/month:200special*10min;48approval*5min;120appeals*8min;72corrections*5min;12recusals*8min;10rules*20min;180exports*30min',
   'employee_reward_operations':'113.6h/month:2400statement*2min+200special*6min+120appeals*5min+72corrections*3min; voluntary card reading, not worklog production',
   'new_independent_personal_signature':'2400personal records*4min=160manager h/month; exposure/conflicts individually checked, project QA team reuse does not remove signature',
   'new_feature_validation':'1600flow*2min+160teamacceptance/use*4min=64manager h/month, even at100% old QA reuse; validates existing source features, does not manufacture missing evidence',
   'new_partition_completeness':'180groups*8min=24manager h/month',
   'new_denominator_audit':('2400personal*1min=40manager h/month; independent capacity allocations/union overlap' if mode=='capacity' else '1760units*1min=29.333333manager h/month; all assigned obligations including unfinished'),
   'new_missing_QA':'(1600flow packages*30 root cases+160project packages*4.5 part inspections)*5min*(1-reuse)/60; reuse0/50/100 =>4060/2030/0 newQA h/month. 30 flow cases and4.5 project parts are prospective volume assumptions; no fixed20-case replay. Exact census cost depends on actual source rows; do not price a whole employee census as one5min inspection. Missing traits not supplied by resource estimate remain pending.',
   'IT_recurring':'180h/year; includes calculations/import and fixed window ledger, not added twice'},
  'HR_hours_monthly':[base['HR_new_hours_month']]*12,'manager_hours_monthly':[base['manager_new_hours_month']]*12,
  'employee_process_hours_monthly':[base['employee_new_hours_month']]*12,'IT_initial_hours':640,'IT_recurring_hours_year':180,
  'launch_hours':{'HR':90,'manager':320 if mode=='capacity' else 240,'employee':1800,'IT':640},
  'launch_stage':'mapping/field test and import then independent rule+source audit; employee familiarization7200*15min; capacity branch includes80manager+40IT commissioning attempt for root standard, not a fake completed norm',
  'fallback':{'export_only':{'HR':20,'manager':80},'source_creation_additional':{'manager':700,'employee':1300},'warning':'same scenario for both; estimates do not prove source readiness; no unavailable feature is generated by evaluator'},
  'rates_RUB_hour':{'HR':1000,'manager':1500,'employee':1000,'IT':2000},'reuse_cases':[0,.5,1],
  'resource_costs_RUB':{'new_annual_at_reuse100':base['resource_RUB_year'],'existing_QA_separate_annual':2436*12*1500,'paid_substitution_25pct_at_reuse100':base['resource_RUB_year']*.25},
  'capacity':{'HR_shop_total_limit_h_month':220,'actual_bank_available_hours':None,'warning':'88 awardHR plus common shopHR may exceed220. See peak resource; no invented capacity. Manager/employee/IT independent capacity unknown.'},
  'own_award_recusals_included':True,'common_M05_basket_hours_excluded':True,'old_800_QA':'retain original parent quote only as provenance; not proof of savings vs88 existing aggregate QA at different grain/trait'}
 finance['reward_core']={'keys_unchanged':reward_keys,'canonical_sha256':reward_sha,'monetary_core_file_refs':core,'path_base':'OTP_bank repository root','verification':'reward sections exactly equal frozen parent; local qualification is metrics-spec, oldQ text in inherited fields is provenance, not runtime; no parent model executed'}
 finance['resource_assumptions']=finance['workload']
 finance.pop('version_provenance',None)
 finance['workload']['stages']['small_SKU_incremental_orders']='96HR h/year=8h/month steady full E24 redemption; 500rub2500C vs5000C baskets; outside procurement; firstlaunch timing separately'
 finance['workload']['capacity']['warning']='88 awardHR+8 smallSKUsteadyHR plus common shopHR may exceed220. See peak-resource.csv. Actual independent staffing unknown.'
 finance['output_paths']=['concept.md','cards.md','metrics-spec.json','evaluator.py','decisions.csv','traces.json','money-examples.csv','employee-card.md','source-to-award.md','finance-spec.json','assumptions.csv','changes.md','self-check.json','resource-sensitivity.csv','peak-resource.csv']
 # Preserve E24/E36 monetary calendar; compute resource peak using recorded cohort checks.
 launch=list(csv.DictReader((PARENT/'first-launch.csv').open()))
 annual=list(csv.DictReader((ROUND/'supporting/finance-basis/annual-three-year.csv').open()))
 peaks=[]
 for x in launch:
  if x['E_R_year']!='24000000':continue
  records=int(x['ordinary_cycle_records'])
  # HR88 comprises standing74h + quarterbatch10h+annualledger4h at2400.
  award_hr=74+records*.35/60
  for sc in ['EXPECTED','FULL_NEW','JAN_OLD50','REGION80']:
   z=next(z for z in annual if z['scenario']==sc and z['fixed_C_year']=='96000000' and z['envelope_R_year']=='24000000' and z['year']=='1')
   shop_peak=float(z['peak_common_HR_hours_month'])
   peaks.append({'month':x['month'],'scenario':sc,'source_calendar_ref':'incumbent/first-launch.csv',
    'personal_records':records,'guarantee_R_max':x['guarantee_post_all_success_R'],'total_R_post_max':x['R_post_all_success_max'],
    'award_HR_hours':award_hr,'M05_shop_HR_peak_upper_hours':shop_peak,'small_SKU_extra_HR_upper_hours':float(x['R_post_all_success_max'])/5000*.02,'combined_upper_HR_hours':award_hr+shop_peak+float(x['R_post_all_success_max'])/5000*.02,
    'common_HR_limit':220,'within_220_upper':award_hr+shop_peak+float(x['R_post_all_success_max'])/5000*.02<=220,'interpretation':'conservative shared shop peak added each month; not actual timed peak; staffing uncertain'})
 csvsave(folder/'peak-resource.csv',peaks)
 finance['inherited_reward_policy']=copy.deepcopy(reward)
 override={
 'guarantee.qualification':'Both fixed quarters satisfy local absolute normal, quality and personal exposure from metrics-spec.json; no quota. '+spec['formula'],
 'guarantee.part_time':'Same G if local normal/quality and personal exposure pass both fixed quarters; no second FTE factor or G haircut. Insufficient exposure => current window not qualified, next fixed annual window only.',
 'guarantee.nonqualification':'0 G on verified local below-normal/quality failure or insufficient exposure in either fixed quarter. Unknown source/verification is pending/not_computable, not result0. Proven recovered rights keep original window/date/U; no floating retry.',
 'guarantee.newcomer':'No imported prehire history. Both prospective fixed quarters need local minimum20active days and20flow roots or1project root, quality/normal. Missing quarter waits next unchanged annual window; no personal date extension.',
 'contests.ranking':'Local stretch from metrics-spec.json; descending ROUND_HALF_UP(value,2) within comparable group; unrounded thresholds. Unconfirmed competitor evidence holds pool; inherited four-slot ties and money unchanged.',
 'calendar.source':'../../../../../incumbent/first-launch.csv'}
 for path,value in override.items():
  section,key=path.split('.');finance[section][key]=value
 finance['metric_text_overrides']=override
 finance['reward_core']['verification']='Embedded inherited_reward_policy exactly equals frozen parent; root monetary sections change ONLY enumerated qualification/ranking wording and recoverable calendar.source. All other fields equal parent. No parent model executed.'
 save(folder/'finance-spec.json',finance)
 assumptions=[('A01','normal',spec['normal'],'ratio','prospective_assumption','Absolute; no performance quota'),('A02','stretch',spec['stretch'],'ratio','prospective_assumption','Attainable; no104.5percent'),('A03','min_exposure',20,'active_days/quarter','prospective_assumption','FTE not multiplied again'),('A04','min_flow_roots',20,'roots/quarter','prospective_assumption','assigned cohort, not completed only'),('A05','QA',95,'score/100','prospective_assumption','compatible census, critical0 major0'),('A06','project_usage_min',1,'observed_run/root','prospective_assumption','usage proves adoption only'),('A07','project_due','quarter_end','date','prospective_assumption','programme obligation declared before effort; not task due_at'),('A08','QA_missing_check',5,'min/quality_unit','prospective_assumption','verify scope; no fabricated result'),('A09','QA_reuse','0/50/100','percent','common_assumption','same readiness comparison'),('A10','N_mix','2400/2400/2400','people','common_assumption','project480teams5; not bank org'),('A11','resource','resource-sensitivity.csv','hours/year/RUB','calculation','ratesHR1000 manager1500 employee1000 IT2000'),('A12','project_capacity_norm','absent','root_standard','missing_source','018 not computable; 80manager+40IT commissioning cost does not create field'),('A13','systems_and_API','unknown','not applicable','unverified_for_bank','names are logical export classes'),('A14','effect','unmeasured','causal_effect','hypothesis','prospective trial required'),('A15','reward_policy','unchanged E24/E36','R/person/window','frozen_design','G2500 onefixedwindow/12mo; same9cohorts4top, no new budget'),('A16','fixture_dates','P1/P2 W2026-A','quarter','fixture_assumption','illustrative quarter calendar; cohort deployment dates inherited'),('A17','signature_missing','hold posting','status','design_assumption','named alternate not completed replacement'),('A18','source_generation_fallback','700manager+1300employee','hours/month','common_sensitivity','not baseline existing data generation and not bank evidence')]
 csvsave(folder/'assumptions.csv',[dict(zip(['id','parameter','value','unit','classification','limitation'],row)) for row in assumptions])
 title=('Принятый объём при независимой мощности' if mode=='capacity' else 'Исполнение закреплённых обязательств')
 mechanism=('Для потока признаётся принятый нормированный объём относительно заранее независимо доступной мощности. Это интенсивность инженерно сопоставимой работы, а не личная ценность и не полезность отработанных часов. Проектная карточка проверяет тот же принцип, но без root-нормы не вычисляется.' if mode=='capacity' else 'Признаётся исполнение всего закреплённого потока обязательств, включая незавершённое. Это надёжность принятого исхода в объявленной когорте; человек с большим числом лёгких закрытий не получает преимущество только от объёма. Проектная единица — один принятый, выпущенный и используемый root-результат.')
 calc=('Поддержка S01:18×2+18×4=108ст.ед.; H=(480−0−0)×0,225=108ч; E=108×(1/3×1+2/3×1)=108ст.ед.;108/108=1,00. Обе страты1,00, QA99/100, normal выполнен, stretchнет. S02:120/108=1,1111, обе страты1,1111, topпри n2=300×40%=120R; подпись S02 отсутствует, проводка удержана. Бэк B01:80/80=1,00 и SLA19/20=95%; B02:96/80=1,20, top120R с удержанием неподписанного. У S01 иB01 оба квартала normal и подписаны: по2500R27? **28.07.2026**, без top. ПроектT01:1принятый используемый root,480ч доступной мощности; требуемый root-норматив отсутствует, отношение не вычисляется и Gне считается заработанным. Подстановка1/480 либо8/480 по тикетам запрещена.' if mode=='capacity' else 'Поддержка S01:36/36=100%, S02:40/40=100%; оба stretch, равный ранг. Пул n2:150×2=300R; два участника делят(40%+30%)×300/2=105R каждый. S01 имеет независимые подписи:105R28.04,105R28.07 и2500R28.07. У S02 расчёт тот же, проводка удержана без подписи. Бэк B01:19/20=95% normal безtop; B02:24/24=100%, top120R, подпись отсутствует. ПроектыT01/T02: каждый1/1 принят, выпущен, используется120раз одним процессом, зрелость≥14дней;8частейT02 не8обязательств. Четыре человека дают600R пула, ничья команд по210R. T01 делится0,6/0,4:126/84R; T02 по0,5:105/105R. Только P01 имеет свою подпись, его126R можно включить вU; личная гарантия2500R за оба квартала не умножается на долю команды.')
 calc=calc.replace('по2500R27? **28.07.2026**','по2500R **28.07.2026**')
 normaltext=('Общий normal:неокруглённый объём/E≥1,00 и каждая заранее выделенная страта≥0,95; stretch:≥1,10 и каждая страта≥1,00. Eиз независимой мощности и норматива, не из результата коллег. Для проекта те же пороги применимы только после независимого root-норматива; сейчас not_computable.' if mode=='capacity' else 'Общий смысл normal:≥95% всех закреплённых созревших обязательств выполнены нужным исходом; stretch:100%. Это достижимо при потолке100%, без требования104,5%. Для одного проектного обязательства доля дискретна:normal иstretch требуют1/1; это честно раскрытая слабая различимость, а не притворная точность.')
 (folder/'concept.md').write_text(f'''# {title}

## 1. Проблема и проверяемая гипотеза

В отобранных ответах после покупки есть запрос на понятные критерии начисления: лист «старая-2026»,T1335. Это одна строка, не оценка несправедливости по всему штату. Замороженная диагностика:1913строк, не1913уникальных работников. Проблема проекта — дать человеку проверяемый путь от результата до признания при одинаковой цене награды. Гипотеза: заранее понятное правило и объяснимая выписка повысят понимание и доступ к заслуженному признанию без ухудшения качества/помощи. Причинный эффект пока не измерен.

{mechanism}

## 2. Механика признания и наград

{normaltext} Порог объявляется до усилия и не зависит от числа лучших/мест. Минимум20активных дней квартала и20уникальных flow-root для потока; в проекте1root и20личных дней. 0,5FTE не уменьшает2500R; scheduled_hours уже содержитFTE. Не хватает наблюдений — отдельный исход, не качество0. Done, длительность звонка, worklog, storypoints и число частей не доказывают пользу.

Сохраняются платформа/корпоративные события и фактические ставки:50Cдень рождения,50Cконкретный опрос,150Cпервый день назначенного курса,1000Cежегодный стаж — только при состоявшемся событии. ЛичныеC/R, переводы,1:1R→C, Uи заказы сохраняются; сроки личных средств не вводятся.

E24:7200сценарно подходящих, гарантия2500R за оба качественных квартала одного **фиксированного** полугодового окна раз в12месяцев. 9когорт по800, стартыm1…m9дня15, первыеGm7…m15дня28; следующий шанс ровно через12месяцев, провал не сдвигает окно. Нормальный результат не конкурс/квота. Гарантия18млнR/год, top4,32млн, special1,68млн. Topраз в квартал:150R×число уникальных допущенных людей группы, четыре фиксированных слота40/30/20/10%. На topдопускает stretch; сортировка внутри своей сопоставимой группы по отношению, округлённому HALF_UPдо0,01, пороги по неокруглённому. Равный ранг делит сумму занятых слотов, включая связанные места за4; отсутствующие/незанятые слоты не перенормируются, при одной зарегистрированной единицеtop0. Команда получает одну сумму; заранее назначенные доли≤1, округление вниз только личногоR, остаток не перераспределяется. Незавершённое доказательство потенциального конкурента удерживает topпула до разрешения, а не улучшает чужое место автоматически.

Specialежемесячно20×2500+12×7500R, тот же независимый уровень пользы; готовые подтверждения в хронологическом порядке, точная ничья делит соответствующие фиксированные слоты. Не более2особых наград/15000R на человека вгод; команда≤7500R за результат; общий личныйcap100000R/год. Обычное достижение+specialтолько другойbenefitID либо отдельно доказанная добавочная польза, исключённая из обычного измерения. Одинroot, одна домашняя группа, одна польза. E36лишь общая чувствительность:3750G,27/6,48/2,52млнR, прежние30/18specialмест, ставкиtop225R; условия не улучшаются ради прохода бюджета.

Никто не утверждает собственные входы/тип/исключение/приёмку/QA/апелляцию/ставку/проводку. Подписи и контрольная зависимость проверяются поимённо. Именованный заместитель — маршрут, пока нет выполненной независимой проверки. Исправление и апелляция5+5рабочих дней — проектныйSLA; банковская мощность неизвестна.

## 3. Три сценария и конкретный расчёт

Три полные карточки источника/полей/формулы/границ — [cards.md](cards.md); цепочка до права и проводки — [source-to-award.md](source-to-award.md). Все приведённые записи синтетические, не данные ОТП.

{calc}

Сотрудник до окна видит свою карточку и личную когорту, после квартала — числитель/знаменатель, охватQA, причину/дату и подпись. Не ведёт второй отчёт о каждой задаче. Руководитель закрепляет поток/ресурс до результата, восстанавливает общий источник, свои случаи передаёт независимому владельцу. HRпроверяет оба квартала именно личного фиксированного окна, фонд/сумму/дубль и другую подпись; иной неполучатель проводит. Проектный QAможет быть командным, личная экспозиция/подпись проверяются у каждого.

## 4. Экономика и ресурсы

Условное предложение→проверенное непроведённоеU→личныйR→конвертация1:1→C→заказ→получение. Fневыданного фонда отдельно. Перевод между людьми и конвертация не создают валюту; одно погашение теми жеR. Расчётное право и подтверждённоеUразличаются вCSV. Проводка при конфликте удержана, доказанное право сохраняется исходным окном.

Максимум обещаний резервируется до дня14 для начала15-го по всем7200, не по ожидаемым победителям. 18млнR гарантии — консервативный общий максимум, включает уже открытые условные окна, не дублируется сверх них. Topgrossперекрытие4×3×800×150=1,44млнR, special0,14млн; подтверждённыеU/заказы и fixed/старое добавляются однократно. Наm12E24:15,84млн проведено+7,08млн открытых условных+1,08млн будущего неоткрытого разрешения=24млн. Остановка новых оконm36 завершает объявленные кm39; заработанныеU/личные средства/заказы сохраняются дольше. Закрытый денежный календарь переиспользован поSHA в [finance-spec.json](finance-spec.json), старые генераторы не запускались.

При проектном ценнике5C/руб.2500R→2500C→сертификат500руб., закупка500руб.+неизвестный сервис. Номинал не наличные. Общая M05смешанная корзина0,194руб./C не цена сертификата0,20руб./C. Полная гарантия всем требует3,6млнруб.сертификатной закупки; конверт24млнR —4,8млнруб. вместо4,656млнсмеси, дельта144тыс. без комиссии. E24/fixed96/old20/FULL_NEW:31,540млнруб. с резервом/буфером M05,31,684млнпри новыхRсертификатами, условно внутри34млн. Fixed144,old35,цены+20%, старые/региональные пики остаются ограничениями; реальный банковскийpassне установлен. МалыйSKU500руб.9600заказов/год вместо4800корзин при той же сумме;+96HRч/год при прежних0,02ч/заказ до неизвестного сервиса, не повторное погашение.

Единый вымышленныйmix7200:2400поддержка+2400бэк+2400в480командах по5;180групп по40. 28800личных проверок/год,1760quality-единиц/месяц(1600flow+160командных) при доказанном охвате. [resource-sensitivity.csv](resource-sensitivity.csv) отделяет прежнюю бизнесгенерацию/QA от новой настройки/выгрузки/полноты/доппризнака/подписи/исключений/апелляции. Существующая QA 2436 ч/месяц при 3 мин на исходную проверку — допущение: 1600 flow-пакетов по 30 root-случаев и 160 проектных пакетов по 4,5 проверяемых частей. Это не реальная экономия против старых 800 ч на другом grain. Новая QA при reuse 0/50/100: 4060/2030/0 ч/месяц по 5 мин на исходную проверку; недостающий признак всегда оплачивается отдельно. Приreuse100новый регулярный ресурс {base['resource_RUB_year']:,.0f}руб./год, прежняя QA отдельно 43,848 млн руб./год;25%оплачиваемого замещения {base['resource_RUB_year']*.25:,.0f}руб./год вне закупок. Часы×2/25%замещение/неполные акты/нет источника — общие чувствительности, не новый фонд. Разово HR90,manager{320 if mode=='capacity' else 240},employee1800,IT640ч; нормы сценарные. Пики9когорт сопоставлены с замороженным календарём в [peak-resource.csv](peak-resource.csv); общиймагазин+HRнаград может превысить220ч. Требуется реальная мощность независимых людей, её нельзя считать известной или бесплатной.

## 5. Доступность, зависимости и защита от искажений

Названия систем — предполагаемые классы рабочих выгрузок, не установленная архитектура ОТП. Пилот возможен на подписанном экспорте, готовыйAPIне обещан. Требуются существующая приёмка/наблюдение исхода, независимыйQA, кадровыйграфик/назначения и аудит. Нет признака — явныйpending/not_computable с ценой отдельной проверки; бюджет труда не материализует доказательство.

Root/duplicate/reopen/correctionне дают повторную единицу; неизвестная root-связь удерживает вывод. Worklog/переработка/уменьшение записанных часов не влияют. Исключения мощности только другого владельца, объединение пересекающихся интервалов; если даты отпуска/обучения не позволяют проверить пересечение —pending. Самозаявленная помощь не улучшает знаменатель. У версии обязательств доказанная помощь не вычитает часы/поток сама по себе: объективный перевод обязательства возможен только независимой историей, иначе исход остаётся закреплённым и оспаривается отдельно. Классификация проспективна; самоисправленный тип блокирует выгоду до другой подписи.

НеполныйQA/неизвестныйисточник/PENDING, недостаточная экспозиция, доказанный результат нижеnormal/qualityfail и конфликт подписи — отдельные состояния. CSATимеет eligible/invited/responded, шкалу и период, используется диагностически;0ответов не0качества,3пятёрки не победа над большой выборкой. Региональный доступ требует пригодногоSKUи независимого заказа, не обещается по числу регионов сети. Рабочий терминал/сменное объяснение, непубличные личные KPI, публикация признания только по согласию. Новичок без первого полного квартала может ждать следующего фиксированного окна; переход/FTEне создаёт второйгарантии/пула.

## 6. Внедрение и проверка эффекта

До первого обещания:заморозить роли/сопоставимые группы/пороги/когорты/словарь и предел охвата, проверить источники и независимость/дубли, выгрузку/окна/ресурс/фонд/SKU. Затем8–12недель теневого расчёта на существующих данных: независимый пересчёт, сверка часов, объяснение карточки случайной выборке в том числе ненаграждённых. Первую гарантию и получение измерять послеm7–15, не объявлять итогом8недель; повтор черезm19–27. Нет пригодного признака/доступного ресурса — не открывать новое обещание безусловно, сохранять уже доказанные права.

Для причинной проверки — заранее зарегистрированная кластерная рандомизация сопоставимых групп/волн при одинаковой наградной политике, корпоративной основе/каталоге и готовности источников. Предварительные метрики:понимание карточки≥80% ответивших случайной выборки с опубликованными приглашёнными/ответившими; пригодный маршрут≥90%всехeligible и≥80%каждойсемьи;≥95%совпадения независимого пересчёта и подтверждения/проводки поSLA;critical/self-award0;≥90%заказовв срок. Числа — проспективные гипотезы, не результаты. Для этой ресурсной версии нынешняя проектная невычислимость учитывается в знаменателе охвата, а не скрывается. До запуска определить размер кластеров/мощность, границу неухудшениякачества/помощи/сложного потока, субъективную ценность500руб./ожидания. Показывать уникальныхполучателей, концентрациюtop, исключённых по данным, p50/p95первого полезногополучения, U/заказы/резерв/кассу и минутыкаждойроли. При маломчисле кластеров только описательное сравнение. CSI4,85/ER75% — целикейса, не предсказанный эффект этой формулы.

## 7. Источники и ограничения доказательств

База путей — кореньOTP_bank. Переиспользованы замороженные inputs/context.md,evidence.md,diagnosis.md,baseline.md и supporting/source-evidence-brief.md; оригинальныеPDF/XLSX/аудио повторно не исследовались. Факты:PDFфиз.10–12(валюты/корпоративные ставки),14–15(Q3),19(30/34млн/цели); diagnosisисходникXLSX «старая-2026»A5:T1917,T1335. Source-claims E01–05:Transcript39:18–39:55стр72–75,41:50стр79,43:03стр80,50:26стр112; письменные ответыстр112–116/138–142 — общаяплатформа/внутренняякоманда и допустимость допущений, не готовыеCRM/API. E07–15 — определения времени/приёмки/знаменателя и арифметика потолка, а не наблюдение банка; E16–18 —условноеQA/труд/неизмеренныйэффект.

Численные source-примеры:OTP-SYN-007-v1, supporting/fixtures/source/base.json#{{classifier,period_rules,roster_capacity,work_events,quality_acts,project_records,comparison_registry,approvals_audit}}, patches/F01..F12.json исловарь; manifestSHA256 `2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc`. Это синтетикаSF01–09. Внешние сертификаты — supporting/reward-basis.md, таблица официальныхстраниц/§правил; доступ31.10.2026, публикациянеустановлена, банковскиеусловия/личнаяценностьнеподтверждены. M05 — supporting/finance-basis/scenario-inputs.json и annual-three-year.csv; денежныйcore/SHAи его границы — finance-spec.json. Новые нормы — assumptions.csv. Никакие oracle/generator/privateданные не читались и готовыйimpact_scoreне создавался.

## 8. Границы и основания отказа

Проверяется изменение измерения при прежней денежнойполитике: понятная карточка сама по себе не доказывает улучшение. Ресурсная интенсивность применима лишь к воспроизводимомустандарту/мощности; исход обязательств — лишь к полному закреплённому портфелю и независимой приёмке/использованию. Уникальныепроектныеработы нельзя универсально упорядочить тикетами/часами. Сходнаядоляуспеха вразныхпрофессиях не единаяшкала способности.

Отвергнутьмасштабирование при неполныхназначениях/норме, систематическом отборелёгкого, скрытом незавершённом, невоспроизводимомroot, чрезмерномpending/неохватекрупнойроли, самоодобрении, недостижимомstretch, ухудшениикачества/помощи, необеспеченнойгарантии/ресурсе/каталоге или неприемлемойценности/ожидании. Технически завершённые файлы и собственныйself-check не независимыйдопуск. Содержательные изменения версионируются до новогоусилия; lineage/diff вынесены вchanges.md и индексветки.
''')
 cap_formula='V/E; V — сумма проспективных standard_units принятого root, E — независимо доступныечасы×стратадолямощности×standard_units/hour. Классы дают ст.ед., а не ценность; тип/сложность не взвешиваются второйраз.'
 obl_formula='Успешныеисходы/всезакреплённыеroot соспланированнымсрокомвквартале, включаяпросроченные/незавершённые. Незавершённое с доказанным исходомfalse остаётся в знаменателе; отсутствующая выгрузка/приёмка даётpending, а не исключение.'
 (folder/'cards.md').write_text(f'''# Три карточки источника и признания

Все продукты/схемы/пороги ниже — проектные допущения. Общие поля и машинные правила опубликованы вmetrics-spec.json; executableдетальвevaluator.py. Grainрешения — субъект×квартал; личныйгодовойреестр связывает ровно двафиксированныхквартала. Даты примеров:01.01–31.03/P1,01.04–30.06/P2,quality-close28.04/28.07.2026; это fixture-кварталы, при внедрении используется сохранённый календарькогорт с днём15/14/28.

## Поддержка

**Источник и владелец.** Предполагаемый регистр обращений/исходов, независимый руководитель процесса иQA-владелец; кадровыйграфик — другойroster-owner. source/base.json:work_events(event_id,case_id,root_id,version,subject_id,period_id,type_id,queue_id,channel,assigned_at/by,assignment_history_status,due_at,accepted_at/by,duplicate_of,reopen_of,correction_of,status), support_outcomes(outcome_id,case_id,resolved,transfer,repeat_of,observation_end),quality_acts,roster_capacity,period_rules,classifier,source_manifest,comparison_registry,approvals_audit. Исходныйgrain — статуссобытия/обращение, результат — одна исходнаяпричинаroot. Копииevent_idидемпотентны, reopen/новыйcaseсduplicate_of не новая польза. Непрослеженныйrootудерживает вывод.

**Период и достаточность.** Полнаяисториянезависимогоназначения иmanifest; всеroot, назначенные/подлежащиеисполнению кконцуквартала. Не толькоresolved. Минимум20root и20активныхдней. 14днейнаблюденияпоследствий, заполненный compatibleQAдля всехroot; transferred/repeat/reopenнеуспех. Отсутствующий ответCSATнепровал. Invited/responded/scale/topic/shiftпубликуются отдельно. Нет историйназначенияилиroot-связи —pending; известныйдостартовыйнепригодныйисточник—not_computable; потеряннаяпартиция—source_incident/pending.

**Формула.** {cap_formula if mode=='capacity' else obl_formula} Для мощности H=(scheduled−leave−training−union независимых blocker/help)×allocation; scheduledужеучитываетFTE. Для исходов числитель — принятые resolvedrootбезповтора/передачи, знаменатель — всякогортаназначения; работа/часы отсутствуютвзнаменателе. Normal{spec['normal']},stretch{spec['stretch']}; для интенсивности каждаястрата≥0,95/1,00 соответственно. Проспективные весаS-C1/2/4=1/2/4 и нормы источника используются лишь в версии мощности. Источникмощности не заменяетсяworklog; в версииобязательств инженерныйвес не нужен.

**Качество/ранг/деньги.** Совместимаярубрикаdefect_penalty/penalty-v1/0..100, личныйscope, независимыйinspectionID, наблюдение докачестваclose, весьroot-поток. Средний худшийscoreпоroot≥95,critical0,major0; несопоставимые97/100и4/5не складываются. normalдаёткварталкG, дваnormalличногоокна2500R; stretchдопускает кtop150R×n, четыре40/30/20/10слота. РангHALF_UP(отношение,0,01) поубыванию в своейгруппе; ничья делит занятыеслоты, n1—top0, пропускислотовнесгораютвпользучужихмест. Проводка по28.04/28.07впримере, G28.07послеобоих. S01вбазе{('108/108=1;G2500,top0' if mode=='capacity' else '36/36=1;G2500,top105закварталприничьесS02')}.

**Человек и контроль.** Работниквидитисход/страты/повтор/причину, подаётзапрос наисправлениебезповторноготабеля. Руководительневыбираетnormalполучателей, подтверждаетпоток/помощь только чужимслучаям. Администраторсверяетличноеокно, независимуюподпись/фонд/проводку; своивходы/тип/исключениенеутверждаетникто. Самозаявленнаяпомощь невычитается; при20наблюденияхминимумпройден, при10дняхновичканет. Поддержке0,5FTEтажеGприобщихусловиях.

## Операционный бэк-офис

**Источник и владелец.** Предполагаемаяпроцесснаяочередь, независимыйprocess-owner/QA, кадровыйroster-owner. work_eventsсrootназначениями/сроками;process_outcomes(outcome_id,case_id,operation_type,accepted,accepted_at,sla_due_at,returned,return_reason,correction_of,external_wait_reason,observation_end). Одинrootоперации ивсеегоисправления; корректировка не новаяоперация. Остальныетребуемыетаблицы — каквподдержке; engineeringклассыB-C1/3/5=1/3/5нужнытолькоинтенсивности.

**Формула/достаточность.** {cap_formula if mode=='capacity' else obl_formula} Интенсивностьучитываетпринятуюоперациюодинраз; дополнительноSLA≥95%отвсехdue-root. Исходыиспользуютчислительпринятыхвсрокбезвозврата; знаменательвсезакреплённыеdue-rootвключаянезакрытые. 20root,20активныхдней, совместимаяличнаяQAсполнымrootохватом,14днейпоследствий. Принятиепозжесрокадоказанонеуспех, неопределённаяприёмка/пропавшаяистория —pending. Внешнееожиданиенеавтоматическоевычитаниеопераций: нужнанезависимаяпроспективнаяисторияпереносасрока/назначения, иначе сохранениеисходнойкогорты/апелляция.

**Normal/stretch/ранг.** {('V/E≥1 и каждаястрата≥0,95;stretch≥1,10икаждая≥1,00;SLA≥0,95' if mode=='capacity' else 'доляпринятыхвсрок≥0,95;stretch=1,00')}. B01:20root/80ст.ед.,19всрок: {('80/80=1' if mode=='capacity' else '19/20=0,95')}, normalбезtop;F11.below18/20=90%—подтверждённыйпровалусловия,SLA100%достижим. Не требуется104,5%.QAи денежнаялестница каквподдержке, свойhome-pool; Gне зависитотB02. Однапользанеусиливаетсяspecialпослепеределки.

**Человек и контроль.** Сотрудникпроверяетисходсвоейоперации, руководительобеспечиваетполныйпоток/причинывозвратов, HRполучаетподписанныйитогиегоисточники. B01рольHRнеисключаетсяиздоступа, но свойinput-correction/signature/posting уходитвненезависимойкоманды. Отсутствующийзаместитель —held/escalation, несаморазрешение.

## Проектная IT/аналитика

**Источник и владелец.** Предполагаемыйтрекерсrootсвязями+существующийрелизный/процессныйотчёт, независимыйзаказчикacceptance_owner/usage_owner,QAвладелец. Work-eventsгранулярноститаскнеравенрезультату. project_records(record_id,case_id,deliverable_id,parent_id,benefit_id,criteria_ref,criteria_agreed_at,acceptance_ref/owner/at,release_ref/at,usage_status/ref/owner/observed_at/coverage/units/measure,rollback). Team_membersдаётличныеэкспозицию/долю/когорту; comparison_registry—одиндомашнийпул. Rootdeliverableсвязываетчасти,однаприёмка/одноиспользование120неумножаетсяна8.

**Когорта и исход.** Всезакреплённыеrootскритерием, согласованнымдоквартала, иполнойисториейназначения, включаянепринятое/незавершённое. Проектнообъявленныйсрокrootобязательства —конецквартала;due_atдочернейзадачинетрактуетсясрокомroot. Приёмкаирелиздоконцаквартала, независимоеиспользованиехотябыоднимреальнымworkflow-runпомереdistinct_workflow_runs_at_deliverable_grain, scopeone_internal_process,14днейотвыпускадонаблюдениядокачестваclose. Этоузкаясопоставимостьэтапапринятоговработу, неуниверсальнаяполезностьвсехпроектов/денежнаяэкономия. Нетusageилиприёмки—unconfirmed/pending; фактическаяпоздняяприёмка05.05вместоQ1—неуспехQ1. Поздняявыгрузкаужеимевшейсяприёмки—incidentсвосстановлениемисходногоправа.

**Алгоритм и граница.** {('Требуетсянезависимыйпроспективный root_scope standard_work_units и standard_units_per_hour длякласса принятогоиспользуемогорезультата;V—суммарнаяroot-нормапринятыхиспользуемыхэтапов,E—доступнаямощностьэтогожеscope×егоroot-нормативнаяскорость,normal≥1/stretch≥1,10. Вfixtureтакойпарысопоставимыхнормативовнет. IT-DEL=1стандартнаяединицачасовтаска/инженерногоучётанеобосновываетнорму1root=1или480ед. ПоэтомуT01/T02иихучастникиnot_computable,числитель1принятыйrootпоказан,знаменательnull. Полепроектаотсутствуетуобеихверсийодинаково,этаверсияеготребует,анеполучаетидеальныйAPI. Нужныйвладелец—независимаяинженерная/процесснаяфункция,доусилияклассповторяемогоэтапа/версияscope/пилотнаякалибровка. 80manager+40ITчразовозаложенывподготовке,результаткалибровкиневыдуман;нетсопоставимыхповторяемыхэтапов—отвергнутьэтуметрикудляданнойроли. Послеотдельногоподтверждениямощности/нормытеже20личныхднейиQA;доэтогонетбезусловногообещанияGдляпроектов.' if mode=='capacity' else 'Числитель—rootобязательстваспринятым/выпущенным/используемымсозревшимисходом;знаменатель—всерутызакреплённойкогортыпериода,втомчисленезавершённые. Normal≥0,95,stretch=1,00. Одинrootдаётдискретный1/1или0/1,приодномrootнетразличимогоповышенногоуровнямеждуnormalиstretch;при20root19/20normalи20/20stretch. Этоограничениеprecision/частыхничьих. Нужныполнотаобязательств/проспективныекритерии,независимыйownerинаблюдаемоеиспользование;ихисточниковаянеполнотаудерживаетрешение,анепополняетсяoracle. Worklog,elapsed,engineeringнормаIT-DELиstorypointsвформулеотсутствуют.')}

**QA, ранг и деньги.** КомандныйQAдействующегопризнакапереиспользуетсяодинразнаroot; всечастидолжныбытьпокрытылибоактявноsame_deliverable_inspection,копиятогожеinspectionIDнеувеличиваетнезависимость. Качество≥95/100,critical0major0;QAдругогопериода/личныйактодногоучастниканеподтверждаеткомандуполностью. Личнаяэкспозиция≥20днейиопубликованноевкладноечленствонужныкаждому;G2500каждомунезависимоотдоли,topтолькооднаteamсумма. Ранг/ничья/слотыобщие,нонесравниваетпроектысподдержкой. БазоваяпараT01/T02—{('невычислимыйрангбезroot-нормы;top0расчётноененазначение,неистинныйпровал' if mode=='capacity' else 'оба1/1stretch;пул600R,ничья2командделит420Rпо210;T01доли0,6/0,4дают126/84R,однаUподписанногоP01=126R')}. F12переводP02сохраняетC01/W2026-A,0,2доляT02неполучаетдополнительногопула/второйG, незаполненная0,4T01непередаётсядругим.

**Сценарий ролей.** Инженер/аналитиквидиткритерийroot,приёмку/использование/QA/своюдолю,запрашиваетисправлениеоднойссылкой. Руководительсогласуетэтап/портфельдонаблюдения, неусложняетегорадинаграды,неподписываетсвоюкоманднуювыгоду. АдминистраторсверяетодинbenefitID/домашнийпул/личныйгодовойреестр. P01руководительполучаетпризнаниетолькосдругимподписантомвнезависимойцепочки; именованныйalternateнеравенподписанномуакту.
''')
 (folder/'source-to-award.md').write_text(f'''# От источника до права и проводки

1. **До усилия.** Процессныйвладелецпубликуетроль/группу,метрикуA{num},словари/когорту/normal/stretch/срок;HRпроверяетфондисохраняетусловноеобещание. Это неU/F→R. Укаждогоиз7200одинличныйгодовойреестр;сменароли/командыего несбрасывает.
2. **Версия источника.** Manifestпроверяетналичие/полнотукаждойнужнойпартиции иreadiness. Runtimeнеиспользуетимясценария: `evaluate(data,spec)`. Ключи/версиидедуплицируются,конфликтодинаковогоключаостановитпересчёт. Материализациятолькопубличнымreader.expand_scenario;ниoracle,ниавторскийденежныйгенераторнужен. ИсточниковыеSHAиlocatorsвspec/finance;source_refвdecisions/traces. Результатнепроверяеткриптографическуюподписьбанка—такойсистемынетвдоступномпакете.
3. **Связь и когорта.** Одинroot/benefitсвязандоступнымиrootID/duplicate/reopen/correction,статусныеверсии/частинеединицы. Назначениеидатасрокасохраняютнезавершённоевзнаменателеобязательств;вмощностнойверсииотдельносохраняетсяполныйграфик/распределение. Пропусксвязи/историинеудаляетсяизоценкикакусиленакрасиваяметрика.
4. **Приёмка/использование/QA.** Принимаетдругойвладелец,применениепроекта1разнаroot,14днейдозревания. ТолькоQAснужнымscope/периодом/критерием/версией/независимымinspectionпокрываетпризнак. Старыеактынепроверяютсязановопо20случаямвсех. Совместимыйактпереиспользуется,недостающийпризнакотдельнаяпроверка/стоимость;безнегоpending. CSATотдельнымизнаменателями,неконвертируетсявQA.
5. **Число и решение.** Формулыspec;промежуточныеH/union/страты/root/QAвtraces,личныечислитель/знаменатель/статусывdecisions. normalабсолютен,stretchдостижим;внепригодномпроектномнормированиинетподставногознаменателя. `eligibility`—измеренныйквартальныйитогдооператорскойподписи,`reward_status`можетбытьpendingиз-заеёотсутствия. `data_status`неравеннизкойпроизводительности.
6. **Гарантия.** Только2normalвфиксированномличномокне,1G/12месяцев;впримереP1/P2→28.07.2026. Неуспех/малоличныхнаблюденийдаёт0Gэтогоокна;истинныйsourceincidentдаётpending. Восстановленная08.05партициясдоказательствомсвоевременнойработывосстанавливаетисходныйквартал/окно,недатуновогоконкурса. Нельзяобъявитьэкономиейрасходпоотложеннымправам.
7. **Конечный top.** Внутрисвоейгруппы,150R×uniquepeople;четыреслота,ничьи/малыеn/долибезперенормировки. Колонкаtop_R—расчётнаопубликованнойверсии;top_status=pending_group_evidenceудерживаетвесьпулпринеопределённомконкуренте,покаисход/рангнепроверены. Доликомандыприменяютсяодинразпосленичьей,получателюfloor. Specialотдельнопоможеттолькозаинойbenefit/независимуюдобавкувпрежнихлимитах.
8. **Подпись и U.** Beneficiaryнеутверждаетвходы,исключение,исправление,класс,апелляцию,подписьипроводку. `approvals_audit`проверяетeditor/signer/operator/appeal/dependency;namedalternate—ещёневыполненнаяпроверка. ПриконфликтеS01/B01естьмаршрутдругойпроверки,P01нетзаместителя—эскалация. Неодобренныеизмененияудерживаютвыгоду. `approved_G_U_R`толькоеслиподписаныобаэтапа;`approved_top_U_R`толькоподписаннаясуммабезнеопределённогопула. Приотсутствииаудит-записиS02/B02/P02–04проводканесфабрикована.
9. **Погашение.** НеполучающийHRоператорпереводитU→личныйR;корректнаяконвертацияR→C1:1иединыйзаказ.500руб.приценнике2500C/закупке500руб.+сервис;старыеC/Rилиреальнопроведённыеfixedмогутприблизитьзаказ,никогданесчитаютсядвойнымпогашением. НетSKU/ресурса—очередьссохранённымправом,неисчезновениеспроса.

Повторение: `python3 evaluator.py`пересчитаетbaseи22варианта,запишеттольколокальныеCSV/JSON. `--scenario F10.restored`или`--out-dir`доступны. Полныйизначальныйrawнеразмножается:traceхранитодинeventпример/юнитискалярныепромежуточныеполя;источникисохраняютсяобщими. Этоанализ,недействующийбанковскийAPI.
''')
 (folder/'employee-card.md').write_text(f'''# Личная карточка: как проверить признание

До начала окна я вижу своюроль,группу,когорту,двафиксированныхквартала,датыинаграду2500R. {('Мнепоказываютнезависимодоступнуюмощностьинорму,непросятбольшезаписанныхчасов.' if mode=='capacity' else 'Мнепоказываютвесьзакреплённыйпотокобязательствсо сроками,втомчисленезавершённые.')} Наnormalнетквотымест;topконеченинеобещанкаждому. 0,5ставкинеуменьшаетGпригодногорезультата.

{calc}

Вотстроки,которыеестьввыписке:период/окно,источник/версия/root,числитель,знаменатель/единица,QAохват/причина,normal/stretch/место/ничья,расчётнаясумма,исходнаядатаправа,независимыйподписантиготовностьпроводки. Онивdecisions.csv,money-examples.csv;traces.jsonобъясняетпромежуточныеполя. Дроблениерезультатанетчислителянезависимойпользы,нетавтоматическойнаградызаDoneилиworklog.

«Результатнижеусловия/qualityfail»—непройденныйквартал. «Недостаточнонаблюдений»—например10личныхднейновичка,а неоценкачеловека0. «PENDING/источникнеподтверждён»—нуженвладелецданных;потеряпартициипослеусилиянеаннулируетдоказуемоеправо. «Не вычисляется»—известнаянепригодностьисточника/нормы;необещаемGбезусловно. «Конфликт/нетподписи»—проверкадругомулицу,суммасохраняетсявреестре,именованныйзаместительеёпоканеподписал. Ямогусообщитьобошибке,нонесмогуодобритьсвоёисправление/исключение/проводку.

ПослеобоихnormalполучаюGвдатусвоейкогортыm7–15,следующееокночерез12месяцев;провалнепереноситтекущуюпопытку.2500R→2500C1:1позволитсертификат500руб.толькоприпроектномценнике/пригодномSKU. Регион/наличие/сервиснеобещаныкакпроверенные. Еслизаказждёт—средства/заказсохраняются. КорпоративныеCзаденьрождения/стаж/курс/опросприбавляютсятолькокогдареальносостоялисьсобытия,благодарностьнегарантируется.
''')
 if mode=='obligations':
  p=folder/'concept.md';s=p.read_text().replace('Для этой ресурсной версии нынешняя проектная невычислимость учитывается в знаменателе охвата, а не скрывается.','Для этой версии неподтверждённые назначения/использование учитываются в знаменателе охвата, а не скрываются.');p.write_text(s)
 p=folder/'concept.md';p.write_text(p.read_text().replace(' Содержательные изменения версионируются до новогоусилия; lineage/diff вынесены вchanges.md и индексветки.',' Содержательные изменения версионируются до нового усилия.'))
 (folder/'changes.md').write_text(f'''# Lineage/diff — не включать в слепое тело концепции

candidate_key:CON-{num:03d}@v2;parents:[CON-{num:03d}@v1];branch:A.

Замороженныйродитель:{PARENT.relative_to(repo)}/concept.md;SHA256:{sha(PARENT/'concept.md')}.
ДенежныйcoreканоническийSHA256:{reward_sha};секции{', '.join(reward_keys)}равныродителю. Денежныйкалендарь/SHAпроверяютсяотдельноfinance-spec.json. ФормулировкаQвнаследованномreward-разделеостаётсяпроисхождениемполитики;местноеопределениеквалификацииопубликовановmetrics-spec.json,цена/слоты/даты/лимитынеменялись.

Механизмизмерения:{mechanism}

Существенныйdiff: {('нормированныйflow-rootссогласованноймощностью,размерностьюистратамибездвойноговеса/FTE;проектнаянеприменимостьобнаруженаивынесенаnot_computableвместосчётчикатикетов/несуществующейroot-нормы.' if mode=='capacity' else 'знаменательвсехназначенныхdue-rootвместоworklog/мощности;своевременныйпринятыйисход,проектныйпринятыйиспользуемыйroot,normal95%/stretch100%висходнойшкале;полныйпортфельнепрячетнезавершённое.')}

QA:применимыесуществующиеcensus-актыпокритерию/scope/периоду/независимости;проектныекопииinspectionнеувеличиваютпроверку.НоваяQAпоостаткутолькоотсутствующегоохвата,нетавтоматических20накаждого. НовыеQAпакеты,дополнительныепризнаки,экспорт/полнота,личнаяподпись/отвод/апелляцияразделены. НеготовыйsourceнесталбесплатнымидеальнымAPI.

Источники:общийOTP-SYN-007-v1,manifestSHA2562a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc,base+22варианта. Oracle/generator/validation/private/веткаBнечитались. Никакойнезависимыйдопускилипобедаэтимdiffнеприсваиваются.
''')
