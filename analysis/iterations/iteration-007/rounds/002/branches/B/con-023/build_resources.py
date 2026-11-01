#!/usr/bin/env python3
"""Finite m1..39 resource and separate operating cash; no monetary grid regeneration."""
import sys
sys.dont_write_bytecode=True
import csv,json,math,hashlib
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[7]
PARENT=HERE.parents[3]/'001/branches/B/con-021'
# resolve explicitly from project root, not current working directory
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists() and (p/'project').exists())
PARENT=ROOT/'analysis/iterations/iteration-007/rounds/001/branches/B/con-021'
INC=ROOT/'analysis/iterations/iteration-007/incumbent'
ROUND=HERE.parents[2]
def csvrows(p):return list(csv.DictReader(p.open()))
def write(name,rows):
 with (HERE/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
stages=[
 ('personal_eligibility_conflict_and_signatures','owner_QA','ordinary_cycle_records',4,'new','no batch shortcut; named independent signer'),
 ('result_QA_scope_reconciliation','owner_QA','ordinary_cycle_records*1760/2400',2,'new','parts checked; no invented whole act'),
 ('prospective_local_goal_and_pool_review','owner_QA','180/3',10,'new','pre-effort requirements, not beneficiary choice'),
 ('appeal_owner','owner_QA','120',12,'new','different independent appeal owner'),
 ('recusal_owner','owner_QA','12',8,'new','existing 12 planned recusals'),
 ('special_owner_requests','owner_QA','200',10,'new','benefit registry prevents same-benefit stacking'),
 ('special_award_independent','owner_QA','32',5,'new','separate performed award authorization'),
 ('correction_owner','owner_QA','72',5,'new','new version needs renewed signed decision'),
 ('source_incident_owner','owner_QA','12',12,'new','finite12 incidents/month assumed, overflow not free'),
 ('personal_HR_register','HR','ordinary_cycle_records',.15,'new','same parent operation'),
 ('G_ledger_reserve','HR','guarantee_persons',.1,'new','same parent operation'),
 ('export_partition_completeness','HR','180',8,'new','24h no reduction'),
 ('group_HR','HR','180',4,'new','12h no reduction'),
 ('appeal_HR','HR','120',6,'new','12h'),
 ('recusal_HR','HR','12',10,'new','2h'),
 ('monthly_HR_control','HR','1',720,'new','12h'),
 ('special_HR_request','HR','200',4,'new','13.333h'),
 ('special_HR_post_review','HR','32',5,'new','2.667h'),
 ('correction_HR','HR','72',5,'new','6h'),
 ('source_recovery_and_completeness','HR','12',38,'new','30min operator+8min completeness'),
 ('special_employee','employee','200',6,'new','20h'),
 ('appeal_employee','employee','120',5,'new','10h'),
 ('correction_employee','employee','72',3,'new','3.6h'),
 ('IT_integrity_rules_export','IT','1',1440,'new','24h'),
 ('IT_source_restoration','IT','12',30,'new','6h additional bounded incident envelope'),
 ('existing_business_QA','owner_QA','ordinary_cycle_records/3*38+ordinary_cycle_records/3*22+ordinary_cycle_records/15*4.5',3,'existing','48720 inspections/month at steady state'),
 ('missing_usable_QA','owner_QA','same_original_inspection_count*(1-reuse)',5,'new','4060/2030/0h steady state'),
 ('fixed_old_shop','HR','common_fixed_old_shop_HR_h',60,'existing_plus_shop','exact inherited same month includes fixed80 and handling'),
 ('new_R_certificate500','HR','R_post_all_success_max/2500',1.2,'new_shop','full new R, paid fixed/old not duplicated')]
write('resource-stages.csv',[dict(candidate='CON-023@v2',stage=a,role=b,counter=c,minutes_per_unit=d,classification=e,operation=f) for a,b,c,d,e,f in stages])
cal=[r for r in csvrows(INC/'first-launch.csv') if int(r['E_R_year'])==24000000]
shop=[r for r in csvrows(PARENT/'common-shop-inputs.csv') if int(r['E_R_year'])==24000000 and r['scenario'] in ('EXPECTED','FULL_NEW','JAN_OLD50')]
rates={'HR':1000,'owner_QA':1500,'employee':1000,'IT':2000}
# Base supplies are shared scenario assumptions, not actual available OTP people.
base={'HR':220,'owner_QA':2436,'employee':0,'IT':0}
maxblocks={'HR':6,'owner_QA':240,'employee':4,'IT':3}
allrows=[]
for sc in ('EXPECTED','FULL_NEW','JAN_OLD50'):
 for fixed in (96000000,144000000):
  common={int(r['month']):float(r['fixed_old_shop_HR_h']) for r in shop if r['scenario']==sc and int(r['fixed_C_year'])==fixed}
  assert set(common)==set(range(1,40))
  for reuse in (0,.5,1):
   for mult in (1,2):
    for subst in (0,.25):
     demands=[]
     for c in cal:
      m=int(c['month']);n=float(c['ordinary_cycle_records']);g=float(c['guarantee_post_all_success_R'])/2500
      inspections=n/3*38+n/3*22+n/15*4.5
      existing={'HR':common[m],'owner_QA':inspections*3/60,'employee':0,'IT':0}
      new={'HR':84+n*.15/60+g*.1/60+7.6+float(c['R_post_all_success_max'])/2500*.02,
           'owner_QA':n*4/60+(n*1760/2400)*2/60+10+24+1.6+36+6+2.4+inspections*5/60*(1-reuse),
           'employee':33.6,'IT':30}
      demands.append((m,existing,new))
     # Maximum booking fixed before launch per named scenario; capped at finite menu.
     blocks={role:min(maxblocks[role],math.ceil(max(max(0,(e[role]+n[role])*mult-base[role]) for _,e,n in demands)/20-1e-10)) for role in rates}
     for role in rates:
      q=0
      for m,e,n in demands:
       demand=(e[role]+n[role])*mult;reserved=blocks[role]*20;cap=base[role]+reserved
       used=min(reserved,max(0,demand-base[role]));idle=reserved-used;unserved=max(0,demand-cap)
       prev=q;q=max(0,q+demand-cap)
       # Annual resource values are demand costs even in fails; delivered+idle separately.
       activity=demand*rates[role];cost=activity+idle*rates[role]
       booking_cash=reserved*rates[role]
       base_actual=min(demand,base[role]);replacement_cash=subst*base_actual*rates[role]
       allrows.append(dict(candidate='CON-023@v2',scenario=sc,fixed_C_year=fixed,QA_reuse=reuse,labor_multiplier=mult,substitution=subst,month=m,role=role,existing_activity_h=e[role]*mult,new_activity_h=n[role]*mult,demand_h=demand,base_available_h=base[role],booked_blocks=blocks[role],booked_h=reserved,person_month_max_h=20,unique_additional_people=blocks[role],total_capacity_h=cap,reserve_used_h=used,paid_idle_h=idle,unserved_current_h=unserved,queue_start_h=prev,queue_end_h=q,deadline='close+5workingdays; exceptions+10; shop same month SLA',deadline_state='fail_current_month' if q>1e-8 else 'capacity_conditional_ready',earliest_finish_month=m+math.ceil(q/cap) if q else m,activity_cost_RUB=activity,full_cost_work_plus_idle_RUB=cost,reservation_cash_RUB=booking_cash,base_replacement25_cash_RUB=replacement_cash,new_operating_cash_RUB=booking_cash+replacement_cash,HR220_only_state='pass' if role=='HR' and demand<=220 else 'fail' if role=='HR' else 'not_applicable',availability='conditional_signed_booking_due_prelaunch; not actual OTP availability',ready_date='preparation_m0_day14',qualification='trained independent payroll/ledger controls' if role=='HR' else 'domain QA/acceptance and conflict training' if role=='owner_QA' else 'voluntary requests/appeals or training in paid time' if role=='employee' else 'export/hash/ledger recovery operator',recusal='no same person across conflicting roles or beneficiary chain; 2 cross-region pools and designated alternate; action still required'))
write('monthly-resource.csv',allrows)
annual=[]
keys=list(dict.fromkeys((r['scenario'],r['fixed_C_year'],r['QA_reuse'],r['labor_multiplier'],r['substitution'],r['role']) for r in allrows))
for key in keys:
 rs=[r for r in allrows if (r['scenario'],r['fixed_C_year'],r['QA_reuse'],r['labor_multiplier'],r['substitution'],r['role'])==key]
 for label,lo,hi in [('year1',1,12),('year2',13,24),('year3',25,36),('tail',37,39),('all39',1,39)]:
  xs=[r for r in rs if lo<=r['month']<=hi];peak=max(xs,key=lambda r:r['demand_h'])
  annual.append(dict(zip(['scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role'],key))|dict(period=label,demand_h=sum(r['demand_h'] for r in xs),booked_h=sum(r['booked_h'] for r in xs),reserve_cash_RUB=sum(r['reservation_cash_RUB'] for r in xs),actual_work_RUB=sum(r['activity_cost_RUB'] for r in xs),paid_idle_RUB=sum(r['paid_idle_h']*rates[r['role']] for r in xs),full_RUB=sum(r['full_cost_work_plus_idle_RUB'] for r in xs),new_operating_cash_RUB=sum(r['new_operating_cash_RUB'] for r in xs),peak_h=peak['demand_h'],peak_month=peak['month'],peak_capacity_h=peak['total_capacity_h'],queue_end_h=xs[-1]['queue_end_h'],state='fail' if any(r['queue_end_h']>1e-8 for r in xs) else 'conditional_capacity_only'))
write('annual-resource.csv',annual)
setup=[]
for month in (-2,-1,0):
 for role,total in {'HR':120,'owner_QA':420,'IT':720,'employee':1800}.items():
  hours=total/3;blocks=math.ceil(hours/20);setup.append(dict(month=month,role=role,demand_h=hours,booked_blocks=blocks,booked_h=blocks*20,unique_people=blocks,person_max_h=20,paid_idle_h=blocks*20-hours,cash_RUB=blocks*20*rates[role],ready='m0_day14; before promise',deliverable='m-2 recruit/check independence; m-1 train/configure; m0 shadow/timed rehearsal/mandates' ))
write('setup-resource.csv',setup)
finance={
 'candidate_key':'CON-023@v2','classification':'design/scenario; no confirmed bank budget or staff','money_core_reused_no_reexecution':{},
 'unchanged':{'N':7200,'cohorts':9,'cohort_size':800,'G_R':2500,'G_frequency':'once/12months; both first quarters same fixed window','E_R_year':24000000,'G_ceiling_R_year':18000000,'top_R_year':4320000,'special_R_year':1680000,'top_pool_R_per_person_quarter':150,'top_shares':[.4,.3,.2,.1],'R_to_C':1,'certificate500_price_C':2500,'corporate_fixed':'unchanged real event rates, not guaranteed1250 average'},
 'booking':{'blocks_max':maxblocks,'rates_RUB_h':rates,'HR_base_h':220,'existing_QA_baseline_h_month':2436,'person_max_additional_h_month':20,'paid_idle':True,'finite_launch_months':[-2,-1,0],'finite_operating_months':[1,39],'payment':'additional independent capacity booked and paid in full; actual reserve work never charged twice','funding':'separate operational appropriation prerequisite, not M05 or tokens','availability':'conditional contracted booking+qualified roster+cross-region recusal+timed rehearsal; no actual staff claimed'},
 'calendar':'monthly-resource.csv and annual-resource.csv, sourced same-month fixed_old_shop and original first-launch; fixed96/144, EXPECTED/FULL_NEW/JAN_OLD50, QA0/50/100 x1/x2, substitution0/25',
 'scope':'no unconditional resource pass; x2 HR and lowest readiness may fail finite supply; no offer in failed scenario. Existing earned/conditional rights remain funded and original dated, queue disclosed, not a saving',
 'C_R_F_U':'source calculation does not create currency; authorization creates U only when actual matching independent act performed; posting moves U to personalR once; R->C1:1 conserves combined balance; redemption debits once, inventory/cash matched; F expires only unissued, personal balances do not',
 'M05_limit':'resource changes do not cure30m/fixed144/E36/old35/price20/stock/region/old-order failures; certificate500 all-newR procurement delta144000RUB/year vs0.194, handling newR order count accounted once in resource',
 'prefund':'reserve G for every eligible before fixed window, top all registered unique people, special140000/month; conditional maxima not duplicated with earned U/orders; preserve old/fixed backing separately; no signed funding/SKU => no new offer',
 'unknowns':['bank cost and staff','supplier regional500SKU/commission/service availability','existing balances/backing','causal effect','production source readiness'],
 'source_unit_benchmark':'7200/2400+2400+480teams*5; original 38/22/4.5 inspections; 120 panel people are not financial population'
}
for p in [INC/'finance-spec.json',INC/'first-launch.csv',ROUND/'supporting/finance-basis/scenario-inputs.json',ROUND/'supporting/finance-basis/annual-three-year.csv',ROUND/'supporting/finance-basis/model.py',PARENT/'common-shop-inputs.csv']:
 finance['money_core_reused_no_reexecution'][str(p.relative_to(ROOT))]=sha(p)
(HERE/'finance-spec.json').write_text(json.dumps(finance,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'monthly_rows':len(allrows),'annual_rows':len(annual),'setup_cash_RUB':sum(x['cash_RUB'] for x in setup),'HR120_cash39':120*1000*39,'scopes':len(keys)}))
