#!/usr/bin/env python3.12
"""CSV-only independent verification; does not import model.py or author code."""
import csv,json,math,hashlib,argparse
from pathlib import Path
p=Path(__file__).resolve().parent;r=p.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--source-snapshot');args=parser.parse_args()
SNAPSHOT=(r/args.source_snapshot).resolve() if args.source_snapshot else None
def rows(name):return list(csv.DictReader((p/name).open()))
m=rows('monthly.csv');a=rows('annual.csv');tol=2e-5;checks=0
for x in m:
 f=lambda k:float(x[k])
 assert abs(f('closing_C')-f('opening_C')-f('fixed_C')-f('R_to_C')+f('physical_C'))<tol
 assert abs(f('closing_R')-f('opening_R')-f('posted_R')+f('R_to_C')+f('direct_R'))<tol
 assert abs(f('F_close')-f('F_open')-f('F_grant')+f('F_posted')+f('F_unissued_expired'))<tol
 assert abs(f('cash_total')-f('procurement_cash')-f('delivery_cash'))<tol
 assert f('target_new_cash_reserve')+f('paid_stock_RUB')+tol>=f('new_exposure_RUB')
 assert abs(f('new_rights_close')+f('initial_rights_close')-f('closing_C')-f('closing_R'))<tol
 checks+=6
for x in a:
 matching=[z for z in m if all(z[k]==x[k] for k in ['candidate_key','scenario','fixed_C_year','year'])]
 assert len(matching)==12
 for k in ['cash_total','procurement_cash','delivery_cash']:
  assert abs(sum(float(z[k]) for z in matching)-float(x[k]))<tol
 assert abs(float(x['funding_plus_buffer'])-float(x['cash_total'])-float(x['closing_new_reserve'])+float(x['opening_new_reserve'])-500000)<tol
 for b in [30,34]:assert (x[f'budget{b}_pass']=='True')==(float(x['funding_plus_buffer'])<=b*1000000+tol)
 checks+=6
# M05 published independent arithmetic anchors (basis.md procurement cash table).
anchors=[(144000000,12000000,'EXPECTED',26966000),(144000000,24000000,'EXPECTED',29294000),(144000000,36000000,'EXPECTED',31525000),(96000000,12000000,'EXPECTED',21340000),(96000000,24000000,'EXPECTED',23668000),(96000000,36000000,'EXPECTED',25996000),(144000000,12000000,'FULL_NEW',38121000),(144000000,24000000,'FULL_NEW',40449000),(144000000,36000000,'FULL_NEW',42680000),(96000000,12000000,'FULL_NEW',28809000),(96000000,24000000,'FULL_NEW',31040000),(96000000,36000000,'FULL_NEW',33465000)]
controls=rows('equal-scale.csv')
for fx,e,s,cash in anchors:
 x=next(z for z in controls if int(z['fixed_C_year'])==fx and int(z['annual_R'])==e and z['scenario']==s and z['year']=='1')
 assert abs(float(x['cash_total'])-cash)<.01;checks+=1
for x in json.loads((r/'private/versions-before-checks.json').read_text()).items():
 source=SNAPSHOT/x[0] if SNAPSHOT and x[0].startswith('branches/') else r/x[0]
 assert hashlib.sha256(source.read_bytes()).hexdigest()==x[1];checks+=1
extra_launch_checks=0
for x in rows('launch-monthly.csv'):
 f=lambda k:float(x[k])
 assert abs(f('closing_C')-f('opening_C')-f('fixed_C')-f('R_to_C')+f('received_C'))<tol
 assert abs(f('closing_R')-f('opening_R')-f('posted_R')+f('R_to_C'))<tol
 assert abs(f('conditional_close_R')-f('conditional_open_R')-f('new_conditional_R')+f('matured_conditional_R'))<tol
 assert abs(f('U_close_R')-f('U_open_R')-f('confirmed_R')+f('posted_R'))<tol
 assert abs(f('committed_authorization_F_close')-f('conditional_close_R')-f('U_close_R'))<tol
 # Two queue columns serialized to1e-7basket imply at most0.0005C aggregate roundoff.
 assert abs(f('orders_pending_C')-(f('S1_queue')+f('S2_queue'))*5000)<.0006
 unit=.2316 if x['scenario'] in ['EXPECTED_PRICE20','FULL_NEW_PRICE20'] else .194
 assert f('total_reserve_RUB')+f('paid_stock_RUB')+tol>=f('new_and_requested_exposure_RUB')+f('conditional_close_R')*unit
 extra_launch_checks+=7
for x in rows('date-prefunding.csv'):
 assert abs(float(x['net_reserve_before_effort_RUB'])-float(x['net_reserve_month_close_RUB']))<tol
 assert x['budget34_pass']=='True'
 extra_launch_checks+=2
for x in rows('date-prefunding-late.csv'):
 assert x['promise_prefunding_under_this_schedule_pass']=='False'
 extra_launch_checks+=1
out={'pass':True,'CSV_invariants_and_anchors_checked':checks+extra_launch_checks,'source_fields_do_not_all_match':bool(json.loads((p/'verification.json').read_text())['source_monthly_mismatches'] or json.loads((p/'verification.json').read_text())['source_annual_mismatches']),'source_mismatch_details':'source-comparison-findings.json','M05_published_cash_anchors':len(anchors),'monthly_rows':len(m),'annual_rows':len(a),'all_four_keys':sorted(set(z['candidate_key'] for z in a)),'precision_tolerance_RUB_or_currency':tol,'queue_basket_to_C_serialization_tolerance':.0006,'frozen_candidate_hashes_unchanged':True,'not_verified':'Actual bank inputs, intra-month dates and SKU availability, unknown productive work/data costs.'}
(p/'independent-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
