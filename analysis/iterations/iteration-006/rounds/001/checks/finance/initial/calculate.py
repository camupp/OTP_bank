"""Independent financial audit. Author files are data, never executed/imported.
All outputs stay under checks/finance. M05 is a scenario, not bank accounting.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
INPUTS = json.loads((R/'supporting/finance-basis/scenario-inputs.json').read_text())
A = json.loads((R/'branches/A/finance-spec.json').read_text())
B = json.loads((R/'branches/B/finance-spec.json').read_text())
OLD = json.loads((R/'../../incumbent/finance-spec.json').read_text())
N = INPUTS['common']['N']
KEYS = ['CON-016@v1','CON-017@v1','CON-015@v1','BASELINE']

def save_csv(name, rows):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def save_json(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def price(p):
    procurement=p['basket_nominal_rub']*(p['certificate_share']*p['certificate_cost_fraction']+p['merch_share']*p['merch_cost_fraction'])*p['price_multiplier']
    freight=p['merch_share']*p['logistics_rub_per_merch']
    return procurement,freight,(procurement+freight)/p['basket_C']

def simulate(p,fixed,posts,tag,scenario,key,available,recognition_hr=0):
    """Monthly prospective balances; forecast receipts assume one-month preordering.
    Annual old demand applies to opening legacy/carried stocks, like M05.
    Fulfilment in failed rows is required/counterfactual, never actual execution.
    """
    procurement,freight,unit=price(p)
    legacyC=p['initial_C'];legacyR=p['initial_personal_R'];futureC=futureR=0.
    stock=[0.,0.];reserve=0.;rows=[]
    yearopens=None
    for m,posted in enumerate(posts,1):
        year=(m-1)//12+1;mo=(m-1)%12+1
        if mo==1:
            yearopens=(legacyC,legacyR,futureC,futureR)
        oldshare=p.get('old_january_share',1/12) if mo==1 else ((1-p['old_january_share'])/11 if 'old_january_share' in p else 1/12)
        lc_use,lr_use,fc_use,fr_use=[x*p['old_annual_use']*oldshare for x in yearopens]
        fixed_issue=fixed/12;fixed_use=fixed_issue*p['new_fixed_C_use'];newR_use=posted*p['new_R_use']
        Copen=legacyC+futureC;Ropen=legacyR+futureR
        conversion=lr_use+fr_use+newR_use
        demand=lc_use+lr_use+fc_use+fr_use+fixed_use+newR_use
        legacyC-=lc_use;legacyR-=lr_use
        futureC+=fixed_issue-fixed_use-fc_use;futureR+=posted-newR_use-fr_use
        Cclose=legacyC+futureC;Rclose=legacyR+futureR
        baskets=demand/p['basket_C'];cash=0.;invopen=sum(stock)*(procurement+freight)
        capacities=[];regionshares=p.get('region_demand_shares',[x['demand_share'] for x in p['regions']])
        for i,reg in enumerate(p['regions']):
            need=baskets*regionshares[i]
            receipt=math.ceil(max(0,need-stock[i]-1e-8)/p['procurement_batch_per_region'])*p['procurement_batch_per_region']
            stock[i]+=receipt-need;cash+=receipt*(procurement+freight)
            capacities.append(need<=reg['capacity_units_month']+1e-6)
        invclose=sum(stock)*(procurement+freight)
        exposure=(futureC+futureR)*unit
        reserve_close=max(0,exposure-invclose)
        common_hr=p['admin_fixed_hours_month']+baskets*(p['admin_hours_per_basket']+p['merch_share']*p['manual_merch_hours_per_unit'])
        row=dict(candidate_key=key,available_R_year=available,actual_R_annual_scale=sum(posts[:12]) if tag=='structural' else 'calendar_postings',scenario=scenario,calendar=tag,fixed_C_year=fixed,month=m,year=year,C_open=Copen,R_open=Ropen,fixed_C_issued=fixed_issue,F_granted=posted,F_posted=posted,F_unissued_expired=0,F_close=0,R_posted=posted,R_to_C=conversion,C_to_R=0,required_redemption_C=demand,C_close=Cclose,R_close=Rclose,legacy_close_C_R=legacyC+legacyR,new_personal_close_C_R=futureC+futureR,required_cash_RUB=cash,inventory_open_RUB=invopen,inventory_close_RUB=invclose,new_personal_exposure_RUB=exposure,reserve_open_RUB=reserve,reserve_close_RUB=reserve_close,net_funding_RUB=cash+reserve_close-reserve,baskets_required=baskets,S1_baskets=baskets*regionshares[0],S2_baskets=baskets*regionshares[1],M05_basket_capacity_pass=all(capacities),common_HR_h=common_hr,recognition_HR_h=recognition_hr,combined_HR_h=common_hr+recognition_hr,combined_HR_capacity_pass=common_hr+recognition_hr<=p['admin_capacity_hours_month']+1e-6,C_residual=Copen+fixed_issue+conversion-demand-Cclose,R_residual=Ropen+posted-conversion-Rclose,cash_stock_residual=cash-demand*unit-invclose+invopen)
        assert max(abs(row[k]) for k in ['C_residual','R_residual','cash_stock_residual'])<1e-5
        assert min(legacyC,legacyR,futureC,futureR,*stock)>-1e-5
        rows.append(row);reserve=reserve_close
    return rows

def annualize(rows):
    out=[]
    for year in sorted({r['year'] for r in rows}):
        rr=[r for r in rows if r['year']==year];a=rr[0];z=rr[-1]
        cash=sum(r['required_cash_RUB'] for r in rr);funding=cash+z['reserve_close_RUB']-a['reserve_open_RUB'];unit=price(INPUTS['common']|next(s['overrides'] for s in INPUTS['scenarios'] if s['id']==a['scenario']))[2]
        d={k:a[k] for k in ['candidate_key','available_R_year','actual_R_annual_scale','scenario','calendar','fixed_C_year','year']}
        d.update(months=len(rr),R_posted=sum(r['R_posted'] for r in rr),fixed_C_issued=sum(r['fixed_C_issued'] for r in rr),required_cash_RUB=cash,reserve_open_RUB=a['reserve_open_RUB'],reserve_close_RUB=z['reserve_close_RUB'],cash_reserve_buffer_RUB=funding+INPUTS['common']['annual_buffer_rub'],C_close=z['C_close'],R_close=z['R_close'],new_personal_close_C_R=z['new_personal_close_C_R'],new_personal_exposure_RUB=z['new_personal_exposure_RUB'],all_personal_exposure_RUB=(z['C_close']+z['R_close'])*unit,peak_baskets=max(r['baskets_required'] for r in rr),peak_combined_HR_h=max(r['combined_HR_h'] for r in rr),basket_capacity_pass=all(r['M05_basket_capacity_pass'] for r in rr),HR_capacity_pass=all(r['combined_HR_capacity_pass'] for r in rr),funding_pass_30=funding+500000<=30000000+1e-6,funding_pass_34=funding+500000<=34000000+1e-6)
        out.append(d)
    return out

def params(key,E):
    if key=='CON-016@v1':
        s=A['scenario_parameters'][str(E)];return s['guarantee_R_person'],s['contest_R_eligible_cycle'],s['special_R_month']
    if key=='CON-017@v1':
        s=B['scenarios'][str(E)];return 0,s['contests']['unit_R_per_person_cycle'],s['special']['monthly_max_R']
    return 500,250,200000

def calendar(key,E,kind='all_good'):
    G,rate,special=params(key,E);horizon=42 if key=='CON-016@v1' else 39
    rows=[]
    for m in range(1,horizon+1):
        guarantee=top=lower=records=0.
        starts=A['guarantee']['cohort_starts_months'] if key=='CON-016@v1' else [1,2,3]
        size=A['guarantee']['cohort_size'] if key=='CON-016@v1' else 2400
        for c in starts:
            if m>=c+3 and (m-c-3)%3==0 and m-3<=36:
                top+=size*rate;records+=size
                if key=='CON-015@v1':lower+=size*500
            if key=='CON-016@v1':
                # Every cohort can qualify initially on any quarter after its first pair.
                # Stress fixture aligns same-phase cohorts at m13/14/15, then +12.
                first=c+6 if kind=='all_good' else 13+(c-1)%3
                if m>=first and (m-first)%12==0 and m-6<=36:
                    guarantee+=size*G
        special_post=special if m<=36 else 0
        if key=='CON-017@v1':special_post=special if 2<=m<=37 else 0
        rows.append(dict(candidate_key=key,E_R_year=E,calendar=kind,month=m,ordinary_records=records,guarantee_R=guarantee,lower_R=lower,top_R=top,special_R=special_post,posted_total_R=guarantee+lower+top+special_post))
    return rows

def profile_events(key,E,profile,corporate,months=72):
    G,rate,special=params(key,E);event=[0.]*(months+1);corporate_events=[0.]*(months+1)
    ranked=profile in ['strong_repeat_winner','team_member']
    top=40*rate*.4/(5 if profile=='team_member' else 1) if ranked else 0
    for m in range(4,months+1,3):
        event[m]+=top
        if key=='CON-015@v1':event[m]+=500
    if key=='CON-016@v1':
        for m in range(7,months+1,12):event[m]+=G
    if corporate:
        for m in range(1,months+1):
            y=(m-1)//12;mo=(m-1)%12+1
            if profile=='novice' and y==0:
                corporate_events[m]+={1:350,2:50,3:600,6:50}.get(mo,0)
            else:corporate_events[m]+={1:150,2:50,6:50,12:1000}.get(mo,0)
    balance=0.;first={1500:None,2500:None,5000:None}
    for m in range(1,months+1):
        balance+=event[m]+corporate_events[m]
        for threshold in first:
            if first[threshold] is None and balance>=threshold:first[threshold]=m
    annual=4*top+(2000 if key=='CON-015@v1' else G if key=='CON-016@v1' else 0)
    return dict(candidate_key=key,available_E_R_year=E,profile=profile,corporate_case='specified_events' if corporate else 'none',R_per_completed_12_observation_months=annual,R_posted_calendar_m1_12=sum(event[1:13]),C_corporate_m1_12=sum(corporate_events[1:13]),R_top_cycle=top,first_1500C_300RUB_month=first[1500],first_2500C_500RUB_month=first[2500],first_5000C_1000RUB_month=first[5000],start_basis='C1 starts m1; zero old balance; each threshold is separate save-only path, no prior spending',receipt_boundary='Currency threshold, not assured receipt; usable stocked SKU/address and independent posting required',dependence='Independent Q/QA and posting; top only for ranked fixture, no automatic special. Regional profile may have no usable SKU.')

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    structural=[];structural_month=[];cert=[]
    specs=[('CON-016@v1',24_000_000,24_000_000),('CON-016@v1',36_000_000,36_000_000),('CON-017@v1',24_000_000,24_000_000),('CON-017@v1',36_000_000,36_000_000),('CON-015@v1',24_000_000,24_000_000),('CON-015@v1',36_000_000,24_000_000),('BASELINE',24_000_000,24_000_000),('BASELINE',36_000_000,36_000_000),('BASELINE',77_710_364,77_710_364)]
    for key,available,actual in specs:
        for s in INPUTS['scenarios']:
            p=INPUTS['common']|s['overrides']
            for fixed in INPUTS['fixed_C_cases_year']:
                posts=[actual/12]*36
                if p.get('R_calendar')=='quarter_end':posts=[actual/4 if (i+1)%3==0 else 0 for i in range(36)]
                rows=simulate(p,fixed,posts,'structural',s['id'],key,available)
                ar=annualize(rows);structural.extend(ar)
                structural_month.extend(rows)
                if s['id'] in ['EXPECTED','FULL_NEW','EXPECTED_PRICE20','FULL_NEW_PRICE20']:
                    for a in ar:
                        delta=.2*p['price_multiplier']-price(p)[2]
                        for fee in [0,.05,.1]:
                            premium=actual*(delta+.2*p['price_multiplier']*fee)
                            total=a['cash_reserve_buffer_RUB']+premium
                            cert.append(dict(candidate_key=key,available_R_year=available,actual_R_scale=actual,scenario=s['id'],fixed_C_year=fixed,year=a['year'],certificate_fee_fraction=fee,mixed_cash_reserve_buffer_RUB=a['cash_reserve_buffer_RUB'],new_R_certificate_substitution_uplift_RUB=premium,certificate_total_RUB=total,pass_30=total<=30e6+1e-6,pass_34=total<=34e6+1e-6,scope='New R replaced by nominal certificate at5C/RUB; fixed/legacy stay M05 mix. No bank quote; stock-lot convention held fixed, service fee sensitivity separate.'))
    save_csv('structural-annual.csv',structural);save_csv('structural-monthly.csv',structural_month);save_csv('certificate-sensitivity.csv',cert)
    cal=[];monthly=[];calannual=[];peaks=[]
    for key in KEYS[:3]:
        for available in [24_000_000,36_000_000]:
            E=24_000_000 if key=='CON-015@v1' else available
            for kind in ['all_good']+(['retry_alignment'] if key=='CON-016@v1' else []):
                cc=calendar(key,E,kind);cal.extend(cc)
                hr=64 if key=='CON-016@v1' else 60
                for s in INPUTS['scenarios']:
                    # Quarterly/R-use stresses remain common; actual concept dates override uniform R_calendar.
                    p=INPUTS['common']|s['overrides'];p.pop('R_calendar',None)
                    for fixed in INPUTS['fixed_C_cases_year']:
                        rr=simulate(p,fixed,[c['posted_total_R'] for c in cc],kind,s['id'],key,available,hr)
                        monthly.extend(rr);calannual.extend(annualize(rr))
                        if s['id']=='FULL_NEW' and fixed==96e6:
                            r=max(rr,key=lambda z:z['baskets_required'])
                            peaks.append({k:r[k] for k in ['candidate_key','available_R_year','calendar','month','R_posted','baskets_required','S1_baskets','S2_baskets','common_HR_h','recognition_HR_h','combined_HR_h','M05_basket_capacity_pass','combined_HR_capacity_pass']})
    save_csv('calendars-independent.csv',cal);save_csv('calendar-monthly.csv',monthly);save_csv('calendar-annual.csv',calannual);save_csv('calendar-peaks.csv',peaks)
    profiles=[]
    for key in KEYS[:3]:
        for available in [24_000_000,36_000_000]:
            E=24_000_000 if key=='CON-015@v1' else available
            for profile in ['ordinary_no_top','strong_repeat_winner','novice','team_member','part_time','restricted_region']:
                for corporate in [False,True]:
                    d=profile_events(key,E,profile,corporate);d['available_E_R_year']=available;profiles.append(d)
    save_csv('employee-paths-comparable.csv',profiles)
    frontier=[]
    for award,cycles in [(500,4),(1500,2),(2500,1),(2500,2),(5000,1)]:
        G=N*award*cycles
        for preserve in [0,6_000_000,9_600_000]:
            required=G+preserve
            for budget in [30_000_000,34_000_000]:
                total=(96e6+40e6+required)*.194+500000
                frontier.append(dict(award_R=award,cycles_year=cycles,guarantee_all7200_R_year=G,guarantee_certificate_nominal_RUB_person_year=award*cycles/5,bank_certificate_guarantee_RUB=G/5,preserve_other_channels_R=preserve,required_fund_R=required,remainder_E24_R=24e6-G,remainder_E36_R=36e6-G,budget_RUB=budget,analytical_full_new_fixed96_old20_total_RUB=total,analytical_compatible_before_lots=total<=budget,scope='Full N; fixed/old unchanged. Analytical boundary before lots; certificates cost nominal, hypotheses only.'))
    save_csv('guarantee-frontier.csv',frontier)
    dated=[];orders=[];resources=[]
    for key in KEYS[:3]:
        for E in ([24_000_000,36_000_000] if key!='CON-015@v1' else [24_000_000]):
            G,rate,special=params(key,E)
            promise=N*G+4*2400*rate+special if key=='CON-016@v1' else (4*2400*rate+special if key=='CON-017@v1' else 4*2400*(500+rate)+special)
            dated.append(dict(candidate_key=key,E_R_year=E,conditional_R_ceiling_before_effort=promise,mixed_exposure_RUB=promise*.194,certificate_exposure_RUB=promise*.2,additional_existing_earned_U_orders='Add separately; not0, not part of unissuedfreeF',backing='Suitable paid inventory once + segregated cash; real backing/availability unknown',date='Before day14/effort15; B special also before day1'))
            for nominal in [300,500,1000]:
                orders.append(dict(candidate_key=key,E_R_year=E,certificate_nominal_RUB=nominal,certificate_price_C=nominal*5,new_R_full_redemption_certificate_orders_year=E/(nominal*5),new_R_M05_basket_equivalent_year=E/5000,extra_order_count_vs_M05=E/(nominal*5)-E/5000,extra_order_HR_h_at_M05_0_02=0.02*(E/(nominal*5)-E/5000),capacity_boundary='Basket-equivalent capacity and certificate transaction count are different units. Holding same transaction capacity is sensitivity, not bank fact.'))
            if key=='CON-016@v1':h=A['workload'];base=h['resource_costs_RUB']['stationary_recognition'];setup=h['resource_costs_RUB']['initial_setup'];HR=64
            elif key=='CON-017@v1':h=B['scenarios'][str(E)]['workload'];base=h['annual_award_resource_RUB'];setup=h['launch_one_off_resource_RUB'];HR=60
            else:h=OLD['workload'];base=4308000;setup=3222000;HR=60
            resources.append(dict(candidate_key=key,E_R_year=E,annual_recognition_resource_RUB=base,annual_primary_QA_required_RUB=14400000,total_recognition_plus_QA_RUB=base+14400000,setup_resource_RUB=setup,recognition_2x_RUB=2*base,QA_plus_recognition_2x_RUB=2*(base+14400000),recognition_25pct_replacement_cash_RUB=.25*base,full_QA_plus_recognition_25pct_replacement_cash_if_all_new_RUB=.25*(base+14400000),HR_recognition_month=HR,actual_existing_vs_added_split='unknown; QA counted once; common shop labor additional',fallback_additional_resource_RUB_year=12*(20*1000+80*1500),full_source_creation_additional_RUB_year=12*(1300*1000+700*1500),useful_work_evidence_creation='unknown, not zero and not hidden inside verification minutes'))
    save_csv('dated-prefunding.csv',dated);save_csv('small-sku-orders.csv',orders);save_csv('resources.csv',resources)
    # Independent comparison to already checked M05 table, not executing it.
    source=list(csv.DictReader((R/'supporting/finance-basis/annual-three-year.csv').open()))
    sourceindex={(x['scenario'],int(x['fixed_C_year']),int(x['envelope_R_year']),int(x['year'])):x for x in source}
    errors=[]
    for a in structural:
        E=round(a['actual_R_annual_scale']);src=sourceindex[(a['scenario'],a['fixed_C_year'],E,a['year'])]
        errors.append(abs(a['cash_reserve_buffer_RUB']-float(src['cash_plus_reserve_delta_plus_buffer_rub'])))
    checkedpaths=[R/'branches/A/finance-spec.json',R/'branches/B/finance-spec.json',R/'../../incumbent/finance-spec.json',R/'supporting/finance-basis/scenario-inputs.json']
    save_json('verification.json',dict(independence='Own formulas from data; no author or M05 calculator executed/imported',source_sha256={str(p.relative_to(R)) if p.is_relative_to(R) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkedpaths},structural_annual_rows=len(structural),calendar_month_rows=len(monthly),profile_rows=len(profiles),max_error_vs_verified_M05_annual_RUB=max(errors),max_C_residual=max(abs(r['C_residual']) for r in structural_month+monthly),max_R_residual=max(abs(r['R_residual']) for r in structural_month+monthly),max_cash_inventory_residual=max(abs(r['cash_stock_residual']) for r in structural_month+monthly),all_nonnegative=True,actual_bank_readiness='unknown'))
    print(json.dumps(dict(structural_rows=len(structural),calendar_rows=len(monthly),profile_rows=len(profiles),max_M05_error=max(errors))))

if __name__=='__main__':main()
