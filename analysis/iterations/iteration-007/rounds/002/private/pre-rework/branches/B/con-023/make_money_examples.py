import csv,json
from pathlib import Path
p=Path(__file__).resolve().parent
examples=[
 ('ordinary',2500,0,0,1250,7,'normal both fixed quarters; no top'),
 ('strong_unique_first_group40',2500,2400,9600,1250,7,'first slot6000*.40; win each quarter is illustration not promise'),
 ('strong_tie10_first_group40',2500,600,2400,1250,7,'tie spans4slots;6000/10; top not2400'),
 ('team5_unique_first_group40',2500,480,1920,1250,7,'unit2400*.2 once; ordinary team top0'),
 ('analytical_three_tied_strong_teams',2500,360,1440,1250,7,'6000*(.4+.3+.2)/3*.2; pre-read tie; all-quarters scenario'),
 ('newcomer_T0',2500,0,0,1050,7,'both quarters prospective exposure sufficient; first fixed window'),
 ('late_newcomer_m4_C1',2500,0,0,1050,19,'no Gm7 due missing first quarter; next fixed window m13-18;15months sincehire'),
 ('FTE0.5_sufficient',2500,0,0,1250,7,'sameG; scheduledhours alreadyFTE; no haircut'),
 ('help_confirmed_normal',2500,0,0,1250,7,'independent union capacity interval; no automatic special and no samebenefit stacking'),
 ('HR_beneficiary_signed',2500,0,0,1250,7,'independent outside editor signer operator actually performed; no self award'),
 ('HR_beneficiary_missing_actual_signature',2500,0,0,1250,None,'earned-held2500; authorizedU0 until action; appointed alternate insufficient'),
 ('regional_SKU_unavailable',2500,0,0,1250,None,'right datedm7 preserved; useful receipt unknown until suitableSKU available')]
rows=[]
for name,g,first,top,fixed,m,condition in examples:
 held='missing_actual_signature' in name
 rows.append(dict(profile=name,classification='prospective illustration not source bank fact',group_people=40,G_earned_R=g,G_authorized_U_R=0 if held else g,G_earned_held_R=g if held else 0,first_cycle_top_R=first,annual_top_R=top,annual_work_R=g+top,corporate_events_C_separate=fixed,annual_total_C_after_R_conversion_if_all_posted=g+top+fixed,certificate500_price_C=2500,certificate500_nominal_RUB=500,first_500_without_fixed_month_C1=m,other_cohorts='firstGm7..15; nextm19..27; latehire fixed dates not reset',first_500_with_fixed='strong unique first m4 if actual200C course/survey; others Gdate; no actualsignature/SKU=>unknown',remaining_C_after_one500_no_fixed=g+top-2500,R_to_C=1,actual_posting_observed=False,condition=condition))
with (p/'money-examples.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
