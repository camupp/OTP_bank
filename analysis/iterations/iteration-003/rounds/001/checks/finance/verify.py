"""Cross-check author claims and additional constraints; no candidate script runs."""
import csv,json,math,importlib.util,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROUND=OUT.parent.parent
spec=importlib.util.spec_from_file_location('fin003',OUT/'model.py');mod=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(mod)
def readcsv(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
ann=json.loads((OUT/'annual-results.json').read_text());idx={(r['candidate_key'],r['scenario'],r['year']):r for r in ann};comparisons=[]
def check(key,sc,y,metric,claim,loc,tol=1e-4):
 value=idx[(key,sc,y)][metric];comparisons.append(dict(candidate_key=key,scenario=sc,year=y,metric=metric,claimed=float(claim),calculated=value,difference=value-float(claim),tolerance=tol,match=abs(value-float(claim))<tol,locator=loc))
# Frozen original tables' numeric model outputs only, not their inferred real-world gates.
for r in readcsv(ROUND.parents[2]/'iteration-002/rounds/001/checks/finance/annual-results.csv'):
 if r['candidate_key'] not in ['BASELINE','CON-005@v1']:continue
 for metric in ['C_close','R_close','I_C','G_R','W_R','C_requested','R_requested','C_redeemed','R_redeemed','F_expired','procurement_required_rub','reward_cash_required_rub','peak_HR_hours']:
  check(r['candidate_key'],'M01_'+r['scenario'],int(r['year']),metric,r[metric],'iteration-002/checks/finance/annual-results.csv',tol=2e-5)
# New B author table, all matching named scopes, independently calculated.
for r in readcsv(ROUND/'branches/B/annual.csv'):
 mode=r['mode'];sc='M01_'+r['scenario'] if mode=='M01' else 'M02_'+r['scenario'] if mode=='M02_CORE' else 'M02_CORE_MERCH' if mode=='M02_MERCH' else 'M02_CORE_REGION' if mode=='M02_REGION' else None
 if (sc is None) or ('CON-006@v2',sc,int(r['year'])) not in idx:continue
 for metric,src in [('C_close','C_close'),('R_close','R_close'),('J_close','J_close'),('narrow_cost_required_rub','procurement_rub'),('reward_cash_required_rub','cash_rub'),('peak_HR_hours','peak_HR'),('HR_cash_rub','HR_cash_rub'),('R_cash_required_rub','R_cash_rub')]:
  check('CON-006@v2',sc,int(r['year']),metric,r[src],'branches/B/annual.csv')
a=json.loads((ROUND/'branches/A/author-preflight.json').read_text())
for metric,v in [('basket_units_required',a['core_full_demand']['physical_baskets_year1']),('procurement_required_rub',a['core_full_demand']['M01_procurement_rub_year1']),('reward_cash_required_rub',a['core_full_demand']['M01_cash_rub_year1']),('C_close',a['core_full_demand']['C_close_year1']),('R_close',a['core_full_demand']['R_close_year1']),('peak_HR_hours',a['workload_hours_month']['M01_total_HR_CORE'])]:check('CON-005@v2','M01_CORE',1,metric,v,'branches/A/author-preflight.json')
check('CON-005@v2','M02_CORE',1,'peak_HR_hours',a['workload_hours_month']['M02_total_HR_CORE_before_procurement_extra'],'branches/A/author-preflight.json')
for metric,v in [('basket_units_required',a['core_full_demand']['physical_baskets_year2']),('C_close',a['core_full_demand']['C_close_year2']),('R_close',a['core_full_demand']['R_close_year2'])]:check('CON-005@v2','M01_CORE',2,metric,v,'branches/A/author-preflight.json')
mod.csvout('author-comparisons.csv',comparisons)
# PO carry is not free: Dec commitments equal receipts next Jan at unchanged price.
months=readcsv(OUT/'monthly-results.csv');po=[]
for k in mod.KEYS:
 for y in range(1,5):
  a=idx[(k,'M02_CORE',y)];jan=next(r for r in months if r['candidate_key']==k and r['scenario']=='M02_CORE' and int(r['year'])==y+1 and int(r['month'])==1)
  receipts=float(jan['region1_receipt_actual'])+float(jan['region2_receipt_actual']);diff=receipts-a['closing_PO_next_January_units'];po.append({'candidate_key':k,'year':y,'December_PO_units':a['closing_PO_next_January_units'],'next_January_receipts_units':receipts,'difference':diff});assert abs(diff)<1e-4
# A's actual admission cap under regional skew, as distinct from full14400 stress.
rights=[];j=[0.,0.];totalcreated=0;totalserved=0
for m in range(1,13):
 op=sum(j);g=min(1200,max(0,2400-op));sums=0
 for s,share in enumerate([.3,.7]):
  j[s]+=g*share;available=[1800,1200][s]-1050*share;served=min(j[s],available);j[s]-=served;sums+=served
 totalcreated+=g;totalserved+=sums
 rights.append(dict(case='A_REGION_actual_cap',month=m,J_open=op,J_created=g,J_served=sums,J_close=sum(j),uncreated_vs1200=1200-g,rights_lost=0))
 assert op+g<=2400+1e-6
J=0
for m in range(1,13):
 op=J;g=min(1200,max(0,2400-op));J+=g;rights.append(dict(case='A_zero_use_actual_cap',month=m,J_open=op,J_created=g,J_served=0,J_close=J,uncreated_vs1200=1200-g,rights_lost=0))
for y in range(1,6):rights.append(dict(case='B_all_personally_defer_year',month=y,J_open=0 if y==1 else 7200,J_created=7200 if y==1 else 0,J_served=0,J_close=7200,uncreated_vs1200=0,rights_lost=0))
mod.csvout('rights-stresses.csv',rights)
# One delayed employer cycle: all first rights survive and next contractual dates remain.
extra={'A_REGION_actual_cap':{'J_created_year':totalcreated,'J_served_year':totalserved,'J_close':sum(j),'new_rights_not_created_vs14400':14400-totalcreated,'interpretation':'Reduced programme/admission refusals; does not rescue full14400 specification or erase acquired rights'},'A_zero_use':{'J_close':2400,'new_rights_not_created':12000,'full_current_execution_value_rub':2400*970,'interpretation':'Open rights and funding persist; reduced future issue is not efficiency'},'B_personal_deferral':{'J_close_each_year':7200,'full_current_execution_value_rub':7200*970,'interpretation':'No new cycle until voluntary receipt; lower prospective gift volume is disclosed'},'B_employer_delay':{'year1_rights_created':7200,'year1_served':0,'year1_close':7200,'year2_next_dates_rights_created':7200,'year2_rights_if_no_service':14400,'interpretation':'Both acquired cycles persist; normal one-active-right regime fails, no cancellation'},'A_concentrated_J':{'J_presented_month':2400,'old_CORE_units_month':1050,'total_requested':3450,'aggregate_capacity':3000,'minimum_unserved':450,'interpretation':'No unconditional instant exercise promise; if deadline breached, failure not saving'},'B_concentrated_J':{'J_presented_month':7200,'old_CORE_units_month':1050,'total_requested':8250,'aggregate_capacity':3000,'minimum_unserved':5250,'interpretation':'Concentration requires confirmed staggered dates; immediate fulfilment impossible; no expiring rights'},'A_optional_virtual':{'sessions_month':120,'expert_hours_month':60,'coordination_hours_month':4,'recipient_hours_month_omitted_from_spec':60,'total_added_resource_hours_month_at_least':124,'resource_rub_year_at_least':1488000,'incremental_cash_if_existing_paid_time':0,'status':'outside_CORE; unconfirmed owner/acceptance and recipient time omitted by author; do not fund CORE with assumed savings'},'equal_manager_capacity_sensitivity':{'hours_month':[100,300],'BASELINE':'unknown; no full workload supplied','CON-005@v1':'known86.667 plus unquantified full roster/reading;13.333h slack at100 not verified sufficient','CON-005@v2':'220: fails100, passes300 arithmetically','CON-006@v2':'124: fails100, passes300 arithmetically','interpretation':'100/300 are equally applied hypothetical capacity tests, not bank availability'},'supplier_full_prepayment_sensitivity':[]}
# Demand/price unchanged; prepay Dec next-Jan goods creates a different cash timeline.
for k in mod.KEYS:
 a=idx[(k,'M02_CORE',1)];cash=a['procurement_required_rub']-a['opening_PO_January_commitment_rub']+a['closing_PO_commitment_rub']+a['logistics_required_rub']+a['AP_open_rub']
 extra['supplier_full_prepayment_sensitivity'].append({'candidate_key':k,'year1_cash_rub':cash,'preyear_cash_January_PO_rub':a['opening_PO_January_commitment_rub'],'include_preyear_plus_year1_rub':cash+a['opening_PO_January_commitment_rub'],'status':'illustrative timing stress, transition preyear cash is additional disclosed funding; not free'})
mod.dump('additional-stresses.json',extra)
mod.dump('verification.json',{'author_numeric_checks':len(comparisons),'author_discrepancies':[x for x in comparisons if not x['match']],'PO_carry_checks':po,'additional_rights_rows':len(rights),'status':'pass' if all(x['match'] for x in comparisons) else 'author_differences','limitations':'Author comparisons target disclosed numeric outputs; no bank parameters validated'})
print(json.dumps({'author_checks':len(comparisons),'differences':sum(not x['match'] for x in comparisons),'PO_checks':len(po),'rights_rows':len(rights)}))
