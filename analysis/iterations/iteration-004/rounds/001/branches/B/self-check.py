"""Reproduce B maxima, demand, cash, labor and capacity from frozen M04 copy.
Only writes in this script's own directory. All modeled failed fulfillment is counterfactual.
"""
import json,math,csv,pathlib
P=pathlib.Path(__file__).resolve().parent
S=json.loads((P/'finance-spec.json').read_text()); B=S['frozen_m04']['common']; RP=S['resource_parameters']

def workload(role):
 items=RP[role+'_additional_recurring_quarter']; months=[0.0]*12
 for q in range(4):
  for item in items.values(): months[q*3+item['month_in_quarter']-1]+=item['count']*item['h_each']
 return months

LAB={role:workload(role) for role in ['HR','manager','employee']}
LAB['IT']=[RP['IT_recurring_hours_month']]*12
PILOT=S['pilot']['evaluation_extra_hours_year1']
PILOT_ALLOC=S['pilot']['evaluation_allocation']

def run(scenario):
 p=B|scenario['overrides']; share=p.get('region_demand_shares',[.6,.4]); old=p['old_annual_use']*(p['initial_C']+p['initial_personal_R'])
 old_m=[old/12]*12
 if 'old_january_share' in p: old_m=[old*p['old_january_share']]+[old*(1-p['old_january_share'])/11]*11
 r_m=S['calendar']['new_R_award_and_scenario_receipt_by_month']
 if 'receipt_override' in p:r_m=p['receipt_override']
 r_m=[r*p['new_R_use'] for r in r_m]
 inv=[0.0,0.0]; cash=0; purchase=0; logi=0; admin=0; rows=[]; caps=[]
 for m in range(12):
  demand_C=old_m[m]+p['annual_fixed_C']*p['new_fixed_C_use']/12+r_m[m]; baskets=demand_C/p['basket_C']; admin_m=p['admin_fixed_hours_month']+p['admin_hours_per_basket']*baskets+p['manual_merch_hours_per_unit']*.2*baskets
  md=[];ar=[];end=[]
  for i,reg in enumerate(p['regions']):
   d=baskets*share[i]; arrivals=math.ceil(max(0,d-inv[i]-1e-8)/100)*100; inv[i]+=arrivals-d
   md.append(d); ar.append(arrivals);end.append(inv[i]);caps.append(d<=reg['capacity_units_month']+1e-8)
  costp=sum(ar)*940*p['price_multiplier']; costl=sum(ar)*30
  cash+=costp+costl;purchase+=costp;logi+=costl;admin+=admin_m
  hr=admin_m+LAB['HR'][m]+PILOT_ALLOC['HR'].get(str(m+1),0)
  rows.append({'scenario':scenario['id'],'month':m+1,'old_rights_demand_C_R':old_m[m],'fixed_demand_C':p['annual_fixed_C']*p['new_fixed_C_use']/12,'new_R_demand':r_m[m],'baskets':baskets,'S1_demand':md[0],'S2_demand':md[1],'S1_arrivals_ordered_previous_month':ar[0],'S2_arrivals_ordered_previous_month':ar[1],'S1_closing_inventory':end[0],'S2_closing_inventory':end[1],'purchase_rub':costp,'logistics_rub':costl,'total_cash_rub':costp+costl,'existing_HR_h':admin_m,'branch_HR_h':LAB['HR'][m],'pilot_HR_h':PILOT_ALLOC['HR'].get(str(m+1),0),'all_HR_h':hr,'manager_h':LAB['manager'][m]+PILOT_ALLOC['manager'].get(str(m+1),0),'employee_h':LAB['employee'][m]+PILOT_ALLOC['employee'].get(str(m+1),0),'IT_h':LAB['IT'][m]+PILOT_ALLOC['IT'].get(str(m+1),0),'physical_capacity_pass':all(md[i]<=p['regions'][i]['capacity_units_month']+1e-8 for i in range(2)),'HR_capacity_pass':hr<=220+1e-8})
 rates=RP['rates_rub_hour'];hours={k:sum(v)+RP['one_off_hours_before_start'][k]+PILOT[k] for k,v in LAB.items()};hours['HR']+=admin
 costs={k:hours[k]*rates[k] for k in hours}; total_resource=cash+sum(costs.values()); unredeemed_R=8000000*(1-p['new_R_use']); reserve=unredeemed_R*(940*p['price_multiplier']+30)/5000
 fulfilled=old+p['annual_fixed_C']*p['new_fixed_C_use']+sum(r_m)
 result={'id':scenario['id'],'cash_rub':cash,'strict_purchase_rub':purchase,'logistics_rub':logi,'new_R_reserve_rub':reserve,'cash_plus_new_R_reserve_rub':cash+reserve,'budget_30_pass':cash+reserve<=30000000,'budget_34_pass':cash+reserve<=34000000,'physical_capacity_pass':all(caps),'max_baskets_month':max(x['baskets'] for x in rows),'max_S1':max(x['S1_demand'] for x in rows),'max_S2':max(x['S2_demand'] for x in rows),'existing_HR_hours':admin,'branch_HR_recurring_hours':sum(LAB['HR']),'HR_hours_including_initial':hours['HR'],'max_HR_hours_month':max(x['all_HR_h'] for x in rows),'HR_capacity_pass':all(x['HR_capacity_pass'] for x in rows),'all_role_hours_year1':hours,'all_role_resource_costs_rub':costs,'year1_total_known_resource_rub':total_resource,'pilot_evaluation_resource_rub':200000,'year1_before_pilot_evaluation_resource_rub':total_resource-200000,'useful_work_hours':2400,'useful_work_resource_rub':2400000,'procedure_and_fulfillment_including_cash_resource_rub':total_resource-2400000,'year1_known_cash_including_HR20_rub':cash+costs['HR']*.2,'replacement25_incremental_cash_rub':.25*sum(costs[k] for k in ['manager','employee','IT']),'double_effort_max_HR_h':max(x['all_HR_h'] for x in rows)*2,'double_effort_total_known_resource_rub':cash+2*sum(costs.values()),'closing_total_C_R_if_full_fulfillment':200000000+p['annual_fixed_C']+8000000-fulfilled,'unfulfilled_new_fixed_C':p['annual_fixed_C']*(1-p['new_fixed_C_use']),'failed_scenarios_balance_warning':'if capacity/cash fails, no actual debit or fulfillment claimed; closing is counterfactual'}
 return result,rows

scenarios=list(S['frozen_m04']['scenarios'])
for x in S['additional_stresses']:
 ref=next(v for v in scenarios if v['id']==x['other_inputs'])
 scenarios.append({'id':x['id'],'overrides':ref['overrides']|{'receipt_override':x['new_R_receipt_by_month']}})
results=[];monthly=[]
for sc in scenarios:
 r,rows=run(sc);results.append(r);monthly.extend(rows)
assert 300*5000+10*50000==2000000
assert sum(S['calendar']['base_R_award_by_month'])==6000000
assert sum(S['calendar']['contest_R_award_by_month'])==2000000
assert len(results)==20
rr={r['id']:r for r in results}
assert abs(rr['CORE_60']['cash_rub']-26190000)<1e-4
assert abs(rr['LOW_FIXED96_FULL_NEW']['cash_rub']-28033000)<1e-4
assert abs(rr['ALL_RIGHTS_100']['cash_rub']-68385000)<1e-4
assert all(rr[s]['physical_capacity_pass'] for s in ['CORE_60','LOW_FIXED96_FULL_NEW'])
assert not rr['NEW_R_DECEMBER_ALL']['physical_capacity_pass']
assert not rr['LOW_FIXED96_NEW_R_DECEMBER_ALL']['physical_capacity_pass']
assert sum(LAB['HR'])==456
assert abs(sum(LAB['manager'])-1824)<1e-8
assert abs(sum(LAB['employee'])-3972)<1e-8
report={'status':'self_checked_not_independent_finance','candidate_key':S['candidate_key'],'scenario_results':results,'labor_recurring_by_month':LAB,'assertions':['quarter<=2m R and year=8m R at all-person maximum','base guarantees6000000 R + finite contest2000000 R','common M04 cash anchors reproduced','quarter-end CORE/LOW96 physical capacities pass; December accumulation explicitly fails','all-appeal and all-application maxima counted','initial hours charged to year1; double labor and25% replacement separated'],'limits':['No real bank parameters verified','No claim of full old or central new-fixed backing','Existing platform running cost unknown','Unbounded errors or future clustered claims not guaranteed by this model']}
(P/'self-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
with (P/'self-check-monthly.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=monthly[0]);w.writeheader();w.writerows(monthly)
for r in results:
 print(r['id'], round(r['cash_rub']/1e6,6), '30/34',r['budget_30_pass'],r['budget_34_pass'],'capacity',r['physical_capacity_pass'],'peak',round(r['max_baskets_month'],3),'HR',round(r['max_HR_hours_month'],3))
print('CORE resource',rr['CORE_60']['year1_total_known_resource_rub'], 'LOW resource',rr['LOW_FIXED96_FULL_NEW']['year1_total_known_resource_rub'])
print('hours',rr['CORE_60']['all_role_hours_year1'])
print('CORE cash+',rr['CORE_60']['year1_known_cash_including_HR20_rub'],'replacement',rr['CORE_60']['replacement25_incremental_cash_rub'])
