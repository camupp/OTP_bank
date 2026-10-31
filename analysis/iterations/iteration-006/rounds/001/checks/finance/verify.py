"""CSV-only independent invariants. Does not import the audit calculator."""
from pathlib import Path
import csv,json,math

H=Path(__file__).resolve().parent;R=H.parent.parent
def rows(n):return list(csv.DictReader((H/n).open()))
errors=[];checks=0
for name in ['structural-monthly.csv','calendar-monthly.csv']:
    for r in rows(name):
        n=lambda k:float(r[k])
        residuals=[n('C_open')+n('fixed_C_issued')+n('R_to_C')-n('required_redemption_C')-n('C_close'),n('R_open')+n('R_posted')-n('R_to_C')-n('R_close'),n('required_cash_RUB')-n('required_redemption_C')*((940 if 'PRICE20' not in r['scenario'] else 1128)+30)/5000-n('inventory_close_RUB')+n('inventory_open_RUB')]
        for x in residuals:errors.append(abs(x));checks+=1;assert abs(x)<1e-5
        assert min(n('C_close'),n('R_close'),n('inventory_close_RUB'),n('reserve_close_RUB'))>=-1e-5;checks+=1
        assert abs(n('reserve_close_RUB')-max(0,n('new_personal_exposure_RUB')-n('inventory_close_RUB')))<1e-5;checks+=1
for r in rows('baseline-F-controls.csv'):
    e=float(r['F_open'])+float(r['F_granted'])-float(r['R_posted'])-float(r['F_free_expired'])-float(r['F_close']);assert abs(e)<1e-6;checks+=1
A=json.loads((R/'branches/A/finance-spec.json').read_text());B=json.loads((R/'branches/B/finance-spec.json').read_text())
for e,s in A['scenario_parameters'].items():
    assert s['guarantee_R_person']*7200==s['guarantee_max_R_year'];assert s['contest_R_eligible_cycle']*7200*4==s['contest_R_year'];assert s['guarantee_max_R_year']+s['contest_R_year']+s['special_R_year']==int(e);checks+=3
for e,s in B['scenarios'].items():
    assert 7200*4*s['contests']['unit_R_per_person_cycle']==s['contests']['annual_max_R'];assert sum(x['slots']*x['award_R'] for x in s['special']['monthly_levels'])*12==s['special']['annual_max_R'];checks+=2
for r in rows('employee-paths-comparable.csv'):
    key=r['candidate_key'];E=int(r['available_E_R_year']);p=r['profile'];corp=r['corporate_case']=='specified_events'
    isA=key.startswith('CON-016@');isB=key=='CON-017@v1'
    rate=(A['scenario_parameters'][str(E)]['contest_R_eligible_cycle'] if isA else B['scenarios'][str(E)]['contests']['unit_R_per_person_cycle'] if isB else 250)
    G=A['scenario_parameters'][str(E)]['guarantee_R_person'] if isA else 0
    top=40*rate*.4/(5 if p=='team_member' else 1) if p in ['strong_repeat_winner','team_member'] else 0
    def balance(m):
        quarter=max(0,1+(m-4)//3);annual=max(0,1+(m-7)//12)
        value=quarter*(top+(500 if not isA and not isB else 0))+annual*G
        if corp:
            for t in range(1,m+1):
                yr=(t-1)//12;mo=(t-1)%12+1
                value+=({1:350,2:50,3:600,6:50} if p=='novice' and yr==0 else{1:150,2:50,6:50,12:1000}).get(mo,0)
        return value
    for target,col in [(1500,'first_1500C_300RUB_month'),(2500,'first_2500C_500RUB_month'),(5000,'first_5000C_1000RUB_month')]:
        first=next((m for m in range(1,73) if balance(m)>=target),None);given=int(r[col]) if r[col] else None;assert given==first;checks+=1
    expected=4*top+(G if isA else 0 if isB else 2000);assert abs(float(r['R_per_completed_12_observation_months'])-expected)<1e-6;checks+=1
for r in rows('resources.csv'):
    key=r['candidate_key'];E=int(r['E_R_year']);isA=key.startswith('CON-016@');isB=key=='CON-017@v1'
    HR=60+(4 if isA else 0);awards=(75 if E==24000000 else 125) if isB else 48
    manager=30+12+200*10/60+awards*5/60+120*8/60+72*5/60+12*8/60+10*20/60
    employee=2400*2/60+200*6/60+120*5/60+72*3/60
    it=15 if isA else 13
    annual=12*(HR*1000+manager*1500+employee*1000+it*2000)
    assert abs(annual-float(r['annual_recognition_resource_RUB']))<1e-6;assert float(r['annual_primary_QA_required_RUB'])==2400*20/60*12*1500;checks+=2
sourceA={(x['E_R_year'],x['month']):x for x in list(csv.DictReader((R/'branches/A/first-launch.csv').open()))}
for x in rows('fixed-window-conditional-ledger.csv'):
    y=sourceA[(x['E_R_year'],x['month'])]
    for a,b in [('guarantee_conditional_end_R','guarantee_conditional_open_endmonth_R'),('guarantee_gross_R','guarantee_gross_open_before_quality_close_R'),('top_conditional_end_R','top_conditional_open_endmonth_R')]:assert float(x[a])==float(y[b]);checks+=1
out={'independence':'CSV-only balance, reserve, F and closed-form profile check; calculator not imported','checks':checks,'max_balance_or_stock_residual':max(errors),'status':'pass'}
(H/'independent-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out))
