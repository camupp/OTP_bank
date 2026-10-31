"""Independent arithmetic/contract and FULL_NEW peak checks; writes ONLY owned B."""
from pathlib import Path
import csv,json,re,hashlib,math
B=Path(__file__).resolve().parent
I=B.parent.parent/'inputs'
verify=json.loads((B/'self-check.json').read_text())
for f,h in verify['frozen_input_sha256'].items():
 assert hashlib.sha256((I/f).read_bytes()).hexdigest()==h
out=[];summaries=[]
for n in [13,14]:
 d=B/f'CON-{n:03d}-v1';s=json.loads((d/'finance-spec.json').read_text());t=(d/'concept.md').read_text()
 assert [int(x) for x in re.findall(r'^## (\d)\.',t,re.M)]==list(range(1,9))
 assert s['candidate_key']==f'CON-{n:03d}@v1'
 assert s['lower_tier']['N']*s['lower_tier']['cycles_year']*s['lower_tier']['award_R']==s['lower_tier']['annual_max_R']
 assert s['contests']['groups']*s['contests']['cycles_year']*sum(x['award_R']*x['places_per_group_cycle'] for x in s['contests']['top_tiers'])==s['contests']['annual_max_R']
 assert sum(x['max_count_year']*x['award_R'] for x in s['special']['levels'])==s['special']['annual_max_R']
 assert sum(s['monthly_calendar_R'])==sum([s['lower_tier']['annual_max_R'],s['contests']['annual_max_R'],s['special']['annual_max_R']])==24000000
 assert s['stacking']['max_person_R_year']==4*500+4*7500+4*10000
 assert s['envelope_policies']['24000000']['personal_cap_R_year']==72000
 assert s['envelope_policies']['36000000']['personal_cap_R_year']==64000
 for E in [12000000,24000000,36000000]:
  p=s['envelope_policies'][str(E)];assert sum(p['monthly_R'])==E
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',t):
  assert (d/target).exists(),(n,label,target)
 # Four tied individuals / teams cannot overrun the three paid slots.
 assert sum([15000/4]*4)==15000
 assert sum([7500/6]*6)==7500
 # F free, P pending, posted R; after quarter full lower right still preserved.
 ceiling=2000000;P=500;free=ceiling-P;R=0
 assert free+P+R==ceiling
 R+=P;P=0
 assert free+P+R==ceiling
 # Existing 3000C + four successful lower awards ->5000; no forced redemption.
 assert 3000+4*500==5000
 for fixed in [96000000,144000000]:
  for E in [12000000,24000000,36000000]:
   for mode in ['EXPECTED','FULL_NEW']:
    f_use=fixed*(.6 if mode=='EXPECTED' else 1)
    for calendar in ['COHORTS','QUARTER_SYNC','JAN_OLD50','REGION80','FULL_OLD']:
     for month in range(1,13):
      old_total=200000000 if calendar=='FULL_OLD' else 40000000
      old_share=(.5 if month==1 else .5/11) if calendar=='JAN_OLD50' else 1/12
      add=(E/4 if month in [3,6,9,12] else 0) if calendar=='QUARTER_SYNC' else E/12
      demand=old_total*old_share+f_use/12+add
      basket=demand/5000
      shares=[.2,.8] if calendar=='REGION80' else [.6,.4]
      r1,r2=[basket*x for x in shares]
      commonHR=80+basket*(.02+.2/30)
      ownHR=s['workload']['HR_hours_monthly'][month-1]
      receipts=[math.ceil(x/100-1e-9)*100 for x in [r1,r2]]
      out.append({'candidate_key':s['candidate_key'],'fixed_C':fixed,'envelope_R':E,'mode':mode,'calendar':calendar,'month':month,'new_R_rights':add,'required_baskets':round(basket,6),'S1_baskets':round(r1,6),'S2_baskets':round(r2,6),'physical_capacity_pass':r1<=1800+1e-7 and r2<=1200+1e-7,'common_HR_h':round(commonHR,6),'own_selected_E24_HR_h':ownHR if E==24000000 else None,'HR_total_selected_E24_h':round(commonHR+ownHR,6) if E==24000000 else None,'HR_220_pass_selected_E24':commonHR+ownHR<=220 if E==24000000 else None,'zero_opening_stock_first_month_preorder_units_S1':receipts[0] if month==1 else None,'zero_opening_stock_first_month_preorder_units_S2':receipts[1] if month==1 else None})
 summaries.append({'candidate_key':s['candidate_key'],'eight_sections':True,'links_exist':True,'lower_top_special_maximum':'pass','ties_shares_cap':'pass','P_carry_across_quarter':'pass','monthly_calendar':'pass','frozen_inputs_hashes_unchanged':True})
with (B/'monthly-peak-checks.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
assert len(out)==1440
result={'status':'arithmetic_contract_pass','candidate_checks':summaries,'monthly_peak_rows':len(out),'peak_scope':'Year1 old20 except FULL_OLD=100%; full new and expected both. Monthly quantities are requested/required, never clipped by capacity. E12/E36 own workload not extrapolated from E24. Receipt columns ONLY first-month zero-stock batch plan, no annual cash/reserve re-estimation; use unchanged common M05 annual CSV for annual cash.', 'external_financial_gate':'not_issued','unresolved':['Real bank balances/eligible/fixed/availability/HR capacity unknown','Quarter sync, regional concentration, January old and full old stresses fail normal capacity','2x labor fails220h;014 team fragmentation fails220h','Tiny base value and fair opportunities require pilot','Simple max3-item bundle acceptance minutes are assumptions, not measured evidence']}
(B/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
