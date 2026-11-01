#!/usr/bin/env python3
"""CON-025: ex-ante monthly booking of the SAME full parent labor forecast.
Reads closed CSV/JSON as data only. No scorer, award, price or minute changes.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,math,hashlib
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists() and (p/'project').exists())
PARENT=ROOT/'analysis/iterations/iteration-007/rounds/002/branches/B/con-023'
KEY=('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role')
def read(p):return list(csv.DictReader(p.open()))
def write(name,rows):
 with (HERE/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=read(PARENT/'monthly-resource.csv');finance=json.loads((PARENT/'finance-spec.json').read_text());rates=finance['booking']['rates_RUB_h'];forecast_sha=sha(PARENT/'monthly-resource.csv')
 groups=defaultdict(list)
 for row in source:groups[tuple(row[k] for k in KEY)].append(row)
 monthly=[];delta=[];supply=[]
 for key,rows in groups.items():
  rows.sort(key=lambda r:int(r['month']));assert [int(r['month']) for r in rows]==list(range(1,40))
  # This entire39-month contingent schedule is signed before any offer. It is
  # the parent's full promised-rights/QA/shop forecast, not observed winners/U.
  role=key[-1];maximum=max(int(r['booked_blocks']) for r in rows);q=0
  for old in rows:
   row=dict(old);demand=float(old['demand_h']);base=float(old['base_available_h']);rate=rates[role]
   blocks=min(maximum,max(0,math.ceil((demand+q-base)/20-1e-10)))
   booked=20*blocks;capacity=base+booked;used=min(booked,max(0,demand-base));idle=booked-used
   prev=q;q=max(0,prev+demand-capacity)
   assert abs(q-float(old['queue_end_h']))<1e-7 # no queue saving/delay
   booking_cash=booked*rate;full=float(old['activity_cost_RUB'])+idle*rate
   row.update(candidate='CON-025@v1',booked_blocks=blocks,booked_h=booked,unique_additional_people=blocks,total_capacity_h=capacity,reserve_used_h=used,paid_idle_h=idle,queue_start_h=prev,queue_end_h=q,unserved_current_h=max(0,demand-capacity),reservation_cash_RUB=booking_cash,full_cost_work_plus_idle_RUB=full,new_operating_cash_RUB=booking_cash+float(old['base_replacement25_cash_RUB']),earliest_finish_month=int(old['month'])+math.ceil(q/capacity) if q else int(old['month']))
   monthly.append(row)
   delta.append({k:old[k] for k in KEY}|dict(month=old['month'],old_booked_h=old['booked_h'],new_booked_h=booked,old_paid_idle_h=old['paid_idle_h'],new_paid_idle_h=idle,old_capacity_h=old['total_capacity_h'],new_capacity_h=capacity,old_queue_end_h=old['queue_end_h'],new_queue_end_h=q,old_reservation_cash_RUB=old['reservation_cash_RUB'],new_reservation_cash_RUB=booking_cash,operating_cash_saved_RUB=float(old['new_operating_cash_RUB'])-row['new_operating_cash_RUB'],full_cost_saved_RUB=float(old['full_cost_work_plus_idle_RUB'])-full))
   supply.append({k:old[k] for k in KEY}|dict(month=old['month'],pool_position_max=maximum,booked_position_count=blocks,booked_position_ids=';'.join(f'{role}-'+('A' if i%2 else 'B')+f'-{i:03}' for i in range(1,blocks+1)) if role!='employee' else 'actual_applicants_paid_time_budget_not_proxy_claimants',hours_per_position_max=20,booked_h=booked,base_h=base,forecast_source_sha256=forecast_sha,committed_at='prelaunch_m-2_full_contingent39month_calendar',ready_date=old['ready_date'],qualification=old['qualification'],recusal=old['recusal'],payment='all listed monthly hours paid even if unused; no standby duty in unbooked months; full future dated commitments signed in advance',employee_note='actual200requests/120appeals/72corrections in actual people paid time; blocks are aggregate protected time, not4 substitutes' if role=='employee' else 'disjoint qualified role positions; beneficiary cases transferred across independent pools; performed action still required'))
 write('monthly-resource.csv',monthly);write('booking-delta.csv',delta);write('resource-supply.csv',supply)
 annual=[];savings=[]
 for key,oldrows in groups.items():
  rows=[r for r in monthly if tuple(str(r[k]) for k in KEY)==key]
  for label,lo,hi in [('year1',1,12),('year2',13,24),('year3',25,36),('tail',37,39),('all39',1,39)]:
   xs=[r for r in rows if lo<=int(r['month'])<=hi];os=[r for r in oldrows if lo<=int(r['month'])<=hi];peak=max(xs,key=lambda r:float(r['demand_h']))
   annual.append(dict(zip(KEY,key))|dict(period=label,demand_h=sum(float(r['demand_h']) for r in xs),booked_h=sum(float(r['booked_h']) for r in xs),reserve_cash_RUB=sum(float(r['reservation_cash_RUB']) for r in xs),actual_work_RUB=sum(float(r['activity_cost_RUB']) for r in xs),paid_idle_RUB=sum(float(r['paid_idle_h'])*rates[key[-1]] for r in xs),full_RUB=sum(float(r['full_cost_work_plus_idle_RUB']) for r in xs),new_operating_cash_RUB=sum(float(r['new_operating_cash_RUB']) for r in xs),peak_h=peak['demand_h'],peak_month=peak['month'],peak_capacity_h=peak['total_capacity_h'],queue_end_h=xs[-1]['queue_end_h'],state='fail' if any(float(r['queue_end_h'])>1e-7 for r in xs) else 'conditional_capacity_only'))
   savings.append(dict(zip(KEY,key))|dict(period=label,old_booked_h=sum(float(r['booked_h']) for r in os),new_booked_h=sum(float(r['booked_h']) for r in xs),old_operating_cash_RUB=sum(float(r['new_operating_cash_RUB']) for r in os),new_operating_cash_RUB=sum(float(r['new_operating_cash_RUB']) for r in xs),saved_operating_cash_RUB=sum(float(r['new_operating_cash_RUB']) for r in os)-sum(float(r['new_operating_cash_RUB']) for r in xs),saved_full_cost_RUB=sum(float(r['full_cost_work_plus_idle_RUB']) for r in os)-sum(float(r['full_cost_work_plus_idle_RUB']) for r in xs),actual_work_delta_RUB=sum(float(r['activity_cost_RUB']) for r in xs)-sum(float(r['activity_cost_RUB']) for r in os)))
 write('annual-resource.csv',annual);write('resource-savings.csv',savings)
 finance.update(candidate_key='CON-025@v1',parents=['CON-023@v2'],calendar='monthly-resource.csv: fixed ex-ante monthly20h bookings from pinned full7200/E24 parent forecast+planned queue; booking-delta.csv covers all11232keys; no observed award/U input',resource_parent={'path':str(PARENT.relative_to(ROOT)),'monthly_SHA256':sha(PARENT/'monthly-resource.csv'),'setup_SHA256':sha(PARENT/'setup-resource.csv'),'stages_SHA256':sha(PARENT/'resource-stages.csv')})
 finance['booking']['calendar_policy']='before offers sign all39months and scenario contingencies; b[m]=min(parent_max,ceil(max(0,full_demand[m]+planned_queue[m-1]-base)/20)); same finite qualified pools; no retrospective hiring or unpaid standby. Employee budgets apply to actual applicants.'
 (HERE/'finance-spec.json').write_text(json.dumps(finance,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'monthly_rows':len(monthly),'annual_rows':len(annual),'delta_rows':len(delta),'supply_rows':len(supply)}))
if __name__=='__main__':main()
