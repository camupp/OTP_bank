import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,math,itertools,collections
from pathlib import Path
P=Path(__file__).parent; R=P.parents[2]; INC=R.parents[1]/'incumbent'; S=R/'supporting'
def csvout(name,rows):
 with (P/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(name,x):(P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cal=[r for r in csv.DictReader((INC/'first-launch.csv').open()) if r['E_R_year']=='24000000']
shop=[r for r in csv.DictReader((P/'common-shop-inputs.csv').open()) if r['E_R_year']=='24000000' and r['scenario'] in ('EXPECTED','FULL_NEW','JAN_OLD50')]
lookup={(int(x['month']),x['scenario'],int(x['fixed_C_year'])):float(x['fixed_old_shop_HR_h']) for x in shop}
stages=[
 ('source_class_manifest_HR','HR',18,8,'18 class/partition controls replace 180 repeated group exports; IT handles canonical join/count/hash once'),
 ('award_batch_distinct_signer_and_operator','HR',60,8,'two independent HR roles4min each on immutable composition/decision/rule hash'),
 ('personal_exception_HR','HR',240,2,'10% of personal cases exceptions; full personal scope/identity/conflicts; not sample QA'),
 ('guarantee_ledger','HR',800,.1,'one idempotent entry/person/window; counts only actual guarantee month'),
 ('special_request','HR',200,4,'unchanged'),('special_award','HR',32,5,'unchanged independent award review'),
 ('appeal','HR',120,6,'unchanged'),('correction','HR',72,5,'unchanged'),('recusal','HR',12,10,'unchanged'),('monthly_control','HR',1,240,'four hour restore/reconciliation and access audit'),
 ('source_batch_owner','owner_QA',60,10,'one qualified owner checks scope/completeness/QA join per40people; replaces personal4min baseline'),
 ('personal_exception_owner','owner_QA',240,4,'10% exceptions retain4min personal owner review; scope/conflict and nonstandard records'),
 ('project_acceptance_use','owner_QA',160,2,'all project team roots retain2min acceptance/use recon; no expanded QA scope'),
 ('appeal_owner','owner_QA',120,12,'unchanged'),('recusal_owner','owner_QA',12,8,'unchanged'),
 ('special_request_owner','owner_QA',200,10,'unchanged'),('special_award_owner','owner_QA',32,5,'unchanged'),('correction_owner','owner_QA',72,5,'unchanged'),('rule_owner_control','owner_QA',1,480,'8h/month rule/version/QA checklist coverage supervision'),
 ('special_application','employee',200,6,'unchanged optional application, not ordinary second report'),('appeal_employee','employee',120,5,'unchanged'),('correction_employee','employee',72,3,'unchanged'),
 ('IT_integrity_join_export','IT',1,1920,'32h vs parent24: hash, identity graph, complete scope, exceptions, schema, receipt/rule/decision locks and recovery'),
 ('existing_QA','owner_QA',48720,3,'existing business QA2436h/month separately retained'),('missing_QA','owner_QA',48720,5,'only missing fraction; no whole-act invented:4060/2030/0h at readiness0/50/100')]
csvout('resource-stages.csv',[dict(stage=x,role=y,reference_units_month=n,minutes_per_unit=m,reference_h=n*m/60,operation=b,classification='design assumption, not observed bank work') for x,y,n,m,b in stages])
rows=[]
for redemption,fixed,qa,mult,sub in itertools.product(('EXPECTED','FULL_NEW','JAN_OLD50'),(96000000,144000000),(0,.5,1),(1,2),(0,.25)):
 for c in cal:
  mo=int(c['month']);checks=float(c['ordinary_cycle_records']);g=float(c['guarantee_post_all_success_R'])/2500;groups=checks/40;flow=checks*2/3;teams=checks/15
  # same immutable source benchmark38/22/4.5; not prototype120-person expansion
  inspections=(checks/3)*38+(checks/3)*22+teams*4.5
  existing=inspections*3/60; missing=inspections*5/60*(1-qa)
  hr=42.4+groups*8/60+.1*checks*2/60+g*.1/60
  owner=75.6+groups*10/60+.1*checks*4/60+teams*2/60 #75.6=24+1.6+36+6+8
  employee=33.6;it=32
  # Full published maximum flow; same common certificate500 SKU delta once.
  newshop=float(c['R_post_all_success_max'])/2500*.02
  fixed_old=lookup[mo,redemption,fixed]
  for role,demand0,base,booked,rate,new_activity,existing_h in [
   ('HR',fixed_old+newshop+hr,220,120,1000,hr,0),
   ('owner_QA',existing+missing+owner,2436,math.ceil(max(0,(existing+missing+owner)*mult-2436)/20)*20,1500,missing+owner,existing),
   ('employee',employee,0,math.ceil(employee*mult/20)*20,1000,employee,0),
   ('IT',it,0,math.ceil(it*mult/20)*20,2000,it,0)]:
    demand=demand0*mult;available=base+booked;used=min(booked,max(0,demand-base));idle=booked-used;over=max(0,demand-available)
    # Baseline cost plus booked cash; used purchased work already within demand.
    priced_work=demand*rate;full=priced_work+idle*rate
    base_used=min(base,demand);extra_sub_cash=base_used*rate*sub
    bookingcash=booked*rate
    rows.append(dict(redemption=redemption,fixed_C_year=fixed,QA_reuse=qa,labor_multiplier=mult,base_substitution=sub,month=mo,role=role,source_person_checks=checks,source_inspections=inspections if role=='owner_QA' else 0,existing_QA_h=existing_h*mult,new_activity_h=new_activity*mult,common_fixed_old_shop_h=fixed_old*mult if role=='HR' else 0,new_R_shop_h=newshop*mult if role=='HR' else 0,demand_h=demand,base_available_h=base,paid_blocks=booked/20,paid_booked_h=booked,paid_used_h=used,paid_idle_h=idle,available_h=available,base220_pass=(demand<=220) if role=='HR' else '',funded_capacity_pass=demand<=available,excess_h=over,queue_carry_h=over,deadline='day28' if over==0 else 'FAIL_due_day28_rights_and_original_reserve_preserved',completion='day28' if over==0 else 'not_guaranteed_external_recovery_required',rate_RUB_h=rate,priced_activity_RUB=priced_work,paid_idle_RUB=idle*rate,full_resource_RUB=full,paid_booking_cash_RUB=bookingcash,additional_base_substitution_cash_RUB=extra_sub_cash,new_cash_RUB=bookingcash+extra_sub_cash,unfunded_capacity_cost_RUB=over*rate,price_without_paid_idle_RUB=priced_work))
csvout('monthly-resource.csv',rows)
# Carry unmet work explicitly in failed scenarios; monthly spare capacity can clear it.
queues={}
for r in rows:
 key=tuple(r[k] for k in ('redemption','fixed_C_year','QA_reuse','labor_multiplier','base_substitution','role'))
 previous=queues.get(key,0);end=max(0,previous+r['demand_h']-r['available_h']);queues[key]=end
 r['queue_carry_h']=end
 if previous or end:
  r['deadline']='FAIL_due_day28_rights_and_original_reserve_preserved';r['completion']='not_guaranteed_external_recovery_required'
csvout('monthly-resource.csv',rows)
annual=[]
keyfields=('redemption','fixed_C_year','QA_reuse','labor_multiplier','base_substitution','role')
groups=collections.defaultdict(list)
for r in rows:groups[tuple(r[k] for k in keyfields)].append(r)
for k,v in groups.items():
 for label,lo,hi in [('Y1',1,12),('Y2',13,24),('Y3',25,36),('tail',37,39),('m1-39',1,39)]:
  vs=[r for r in v if lo<=r['month']<=hi];rr=dict(zip(keyfields,k));rr.update(period=label,months=len(vs),peak_h=max(r['demand_h'] for r in vs),peak_month=max(vs,key=lambda x:x['demand_h'])['month'],capacity_pass=all(r['funded_capacity_pass'] for r in vs),failed_months=','.join(str(r['month']) for r in vs if not r['funded_capacity_pass']))
  for col in ['demand_h','paid_booked_h','paid_used_h','paid_idle_h','existing_QA_h','new_activity_h','full_resource_RUB','paid_booking_cash_RUB','additional_base_substitution_cash_RUB','new_cash_RUB','excess_h']:rr[col]=sum(r[col] for r in vs)
  annual.append(rr)
csvout('annual-resource.csv',annual)
setup=[]
for month in (-3,-2,-1):
 for role,hours,rate in [('HR',40,1000),('owner_QA',120,1500),('IT',240,2000),('employee',20,1000)]:
  setup.append(dict(month=month,role=role,paid_blocks=hours/20,paid_hours=hours,used_hours=hours,idle_hours=0,rate_RUB_h=rate,cash_RUB=hours*rate,ready_by='month-1 day28',work={'HR':'authorities, alternates, training, ledger and restore rehearsals','owner_QA':'freeze role checklists; independence/QA scope and 136-specialist split roster qualification','IT':'existing export join, schema/hash/rule lock, boundary/receipt classifier, delta ledger and test','employee':'representative usability sessions; no recurring second report'}[role]))
csvout('setup-resource.csv',setup)
# Explicit finite paid supply. Every block in monthly rows must be accepted before offer day14.
dump('resource-supply.json',{'classification':'prospective conditional staffed operating-budget scenario, not bank staffing','HR':{'base_h':220,'paid_h':120,'people':['HR-independent-signer-1','HR-independent-signer-2','HR-posting-1','HR-posting-2','HR-recovery-1','HR-recovery-2'],'max_h_per_person_month':20,'all39months_paid_RUB':4680000,'separation':'paired signer/operator; rotate all personal/team/reporting conflicts; no person can use same20h twice'},'owner_QA':{'base_QA_h':2436,'paid_max_h_month':max(r['paid_booked_h'] for r in rows if r['role']=='owner_QA'),'pool':'136 qualified QA specialists, each max80h/month;6 independent business-role owners each max60h/month; assign QA blocks first and owner blocks separately, never QA own work; cap11240h','independence':'3 role-specialist owner pools plus three alternates; alternates outside recipient team/reporting; existing31QA×80h includes2436 supplied hours, not a claim of actual staff','qualification_ready':'month-1 day28; 360h setup; exact monthly bookings by scenario are finite scenario alternatives, not all scenario rows simultaneous'},'employee':{'paid_max_h_month':80,'people':'400 finite participant-slots up to0.2h/person/month; pool supports200special+120appeals+72corrections without assigning one application to somebody else; prepaid40/80h pooled into20h blocks; unused time paid','payment':'all booked hours priced at1000; no ordinary reporting'},'IT':{'paid_max_h_month':80,'people':'two independent export/ledger support specialists max40h each; neither signs own data','setup':'3specialists×80h/month for3prelaunchmonths'},'booking_conditions':'real launch only after signed staffing orders, qualified role assignments and separate operating cash; money alone does not create hours','calendar':{'before_day14':'book supply, prefund all conditional maxima; validate rules/access','day15':'fixed offers start; immutable criteria','days1_20':'continuous export QA and exceptions, full special200/32,appeals120,corrections72','days21_24':'source composition owner and digest; missing-only recovery','days25_26':'independent award signer exact frozen decisions/rules/hash; individual conflicts alternate','days27_28':'distinct posting operator, same immutable version; day28 right','correction':'new version voids prior permission; delta reapproval, same original right/window; idempotent ledger','tail37_39':'no new windows after36; same paid capacity through39; personal rights/stock/U/orders persist after39'},'queue_model':'monthly excess is measured unsatisfied demand, no declaration of timely completion in failed scenario. Baseline≤220 and funded≤340 separately. No funded capacity queues in x1; x2 HR fails require external recovery, not accepted launch scope.'})
fin=json.loads((P/'finance-spec.json').read_text());fin['candidate_key']='CON-022@v1';fin['metric_spec_ref']='metrics-spec.json';fin['guarantee']['qualification']='metrics-spec normal for both first contiguous fixed quarters of original annual window; no sliding retry. Full scope/signatures required. Source failure holds reserve, not earned0.';fin['contests']['ranking']='Quality-only robust clusters, meanQA>=99 plus sufficient exposure and all normal conditions. No added volume/business-effect claim; ranking described in metrics-spec.'
fin['workload']={'inputs':'resource-stages.csv,monthly-resource.csv,annual-resource.csv,setup-resource.csv,resource-supply.json','base_HR':220,'paid_HR_max':120,'existing_QA_reference':2436,'missing_QA_reference':[4060,2030,0],'mean_new_HR_h':42.4+8+8+800*.1/60,'mean_new_owner_h':75.6+10+16+160*2/60,'IT_h':32,'employee_h':33.6,'HR_exception_fraction':.1,'exception_boundary':'at fixed144 JAN peak HR below340 at10%; solve per-month residual/(checks*2/60) and owner bound from same rows; beyond funded capacity new offers blocked; existing conditional rights preserved','scope':'E24; x1 allQA ready with booked supply; x2 HR failures explicitly outside timely launch scope; finite owner_QA reserve pays missing QA at0/50/100; no unpriced whole-act replacement','new_cash':'separate conditional operating budget: all booked hours plus25% actually used unpurchased base work only; no used reserve double price','setup_cash_RUB':sum(r['cash_RUB'] for r in setup)}
fin['source_hashes']={str(p.relative_to(R.parents[4])):sha(p) for p in [S/'fixtures/manifest.json',S/'round002-stress/manifest.json',S/'round002-stress/business-config.json',S/'finance-basis/annual-three-year.csv',S/'finance-basis/scenario-inputs.json',S/'resource-menu.json',INC/'first-launch.csv']}
fin['readiness_boundary']='Scenario pass is capacity only, not M05 procurement or real availability. Preserve common E36/fixed144/fullnew/JAN/30m/price+20 failed or uncertain procurement gates; operating cash cannot repair reward backing.'
# clear inherited contradictory measurement/resource reports, preserve immutable cash/window core
for x in ['source_sha256_new','source_sha256','output_paths','inherited_core_locators','measurement_override','operational_metrics_assumptions']:fin.pop(x,None)
fin['calendar']['source']='project-root analysis/iterations/iteration-007/incumbent/first-launch.csv'
dump('finance-spec.json',fin)
ass=[('A01','role normal/top thresholds','metrics-spec.json','prospective design','not bank policy facts'),('A02','reusable QA','0/50/100 percent','shared assumption','existing2436h; missing4060/2030/0h reference'),('A03','exception rate','10 percent of personal checks','new assumption','not sample QA; exception rate boundary reported'),('A04','HR paid reserve','6 blocks×20h every month1..39','shared menu condition','4.68m RUB cash before additional roles'),('A05','new independent QA pool','136×80h plus6owners×60h max','new prospective staffing assumption','finite staffing orders and setup required, not observed people'),('A06','batch substitution','90 percent routine personal rows machine-joined; all exceptions reviewed','new assumption','three required roles and signed composition; controller cost in stages'),('A07','causal effect','unknown','hypothesis','pilot tests understanding and quality, no measured business uplift'),('A08','budget','separate operating budget for all bookings','project prerequisite','not paid byM05 or tokens'),('A09','run domain','x1 with funded bookings; x2 HR fails explicit','calculated boundary','no timely execution claimed outside domain'),('A10','fixed money','E24=18mG+4.32mTop+1.68mSpecial','frozen policy assumption','source reward-basis and incumbent first-launch')]
csvout('assumptions.csv',[dict(id=a,parameter=b,value=c,type=d,limitation=e) for a,b,c,d,e in ass])
print(json.dumps({'monthly_rows':len(rows),'setup_cash_RUB':sum(r['cash_RUB'] for r in setup),'max_owner_booked':max(r['paid_booked_h'] for r in rows if r['role']=='owner_QA')}))
