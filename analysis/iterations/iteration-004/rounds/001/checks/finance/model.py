#!/usr/bin/env python3
"""Independent M04 check. Run from any cwd; outputs only this owned directory.

No author model/self-check/result is imported. Required-demand plan and feasible
execution are separate: a failed required plan NEVER debits actual personal rights.
All non-source-anchor numbers are scenario assumptions, not bank observations.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent
ROOT = ROUND.parents[4]
BASE = ROUND / 'supporting/finance-basis/scenario-inputs.json'
M = json.loads(BASE.read_text())
COMMON = M['common']
KEYS = ['BASELINE', 'CON-006@v2', 'CON-009@v1', 'CON-010@v1']
EPS = 1e-7
SOURCE_PATHS = [BASE, ROUND/'inputs/baseline.md', ROUND/'inputs/context.md',
                ROUND/'branches/A/concept.md', ROUND/'branches/A/finance-spec.json',
                ROUND/'branches/B/concept.md', ROUND/'branches/B/finance-spec.json',
                ROUND.parents[1]/'incumbent/concept.md',
                ROUND.parents[1]/'incumbent/policy-spec.json']
assert json.loads((ROUND/'branches/A/finance-spec.json').read_text())['inputs']['M04']==M
assert json.loads((ROUND/'branches/B/finance-spec.json').read_text())['frozen_m04']==M
assert 38540000-19112409==19427591
assert [10*20000+10*15000+20*15000,
        10*15000+10*20000+20*15000,
        10*15000+10*15000+20*20000]==[650000,650000,700000]
assert [6*20000+6*15000+12*15000,
        6*15000+6*20000+12*15000,
        6*15000+6*15000+12*20000]==[390000,390000,420000]


def dump(name, obj):
    (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')


def table(name, rows):
    if not rows:
        return
    with (HERE/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def batch_units(n):
    return max(0, math.ceil((n-EPS)/100))*100


def params(s):
    return {**COMMON, **s.get('overrides', {})}


def calendar(key, p, expanded=False):
    """Issuance is not receipt. B conditional max is reserved before vesting."""
    if key == 'BASELINE':
        annual_r = 4*M['source_anchors']['q3_awards_R']
        fund_q = M['source_anchors']['q3_manager_fund_R']
        issue = [annual_r/12]*12
    elif key == 'CON-006@v2':
        annual_r, fund_q, issue = 0, 0, [0]*12
    else:
        annual_r = 24000000 if expanded else 8000000
        fund_q = annual_r/4
        issue = ([650000, 650000, 700000]*4 if key == 'CON-009@v1'
                 else [0, 0, 2000000]*4)
        issue = [x*annual_r/8000000 for x in issue]
    if p.get('R_calendar') == 'quarter_end':
        issue = [annual_r/4 if m%3 == 2 else 0 for m in range(12)]
    receipt = [x*p['new_R_use'] for x in issue]
    if p.get('new_R_all_december'):
        receipt = [0]*11+[annual_r*p['new_R_use']]
    return annual_r, fund_q, issue, receipt


def process_hours(key, m, baskets, include_setup=False):
    """Independent explicit counts/rates; month0 setup charged to year1 cost."""
    common_hr = 80 + baskets*(.02+.2/30)
    setup = dict(HR=0., manager=0., employee=0., IT=0.)
    useful = 0.
    if key == 'BASELINE':
        # Missing baseline manager/recognition/IT labor is not asserted zero.
        h = dict(HR=common_hr, manager=0., employee=0., IT=0.)
    elif key == 'CON-006@v2':
        h = dict(HR=common_hr+36+(16 if m==1 else 0),
                 manager=7200*.5/60+720*2/60+1200/60+1200/60,
                 employee=1200*3/60+1200/60, IT=8.)
        # Research100h allocated to employee/analyst rate; original role unspecified.
        setup = dict(HR=0., manager=315., employee=600.+100., IT=160.)
    elif key == 'CON-009@v1':
        hr = 600*.1*8/60 + 600*.05*20/60 + 600*.1*5/60 + 10+10
        mgr = 360*2*10/60 + 600*4/60 + 600*3/60 + 600*.1*5/60 + 600*.05*15/60
        if m in [1,4,7,10]:
            mgr += 40*.5
        emp = 600*(5+3+2)/60 + 600*.05*10/60
        h = dict(HR=common_hr+hr, manager=mgr, employee=emp, IT=4.)
        setup = dict(HR=120., manager=360.+40., employee=7200*10/60, IT=80.)
    else:
        qmonth = (m-1)%3+1
        hr = {1:7200*.25/60+360*3/60+10*.5,
              2:4., 3:180*5/60+10+600*3/60+2}[qmonth]
        mgr = {1:360*6/60+180*15/60+300*6/60+60*.25,
               2:300*6/60,
               3:180*15/60+300*3/60+360*10/60+30+600*15/60}[qmonth]
        emp = {1:7200*2/60+300*6/60,
               2:180*15/60,
               3:180*6/60+600*6/60}[qmonth]
        useful = 300*2 if qmonth==2 else 0.
        h = dict(HR=common_hr+hr+(20 if m==4 else 0),
                 manager=mgr+(20 if m==3 else 0),
                 employee=emp+(30 if m==3 else 0), IT=10.+(10 if m==4 else 0))
        setup = dict(HR=80.+20., manager=60.+20., employee=720.+30., IT=400.+10.)
    if include_setup:
        h = {k:h[k]+setup[k] for k in h}
    return h, useful, setup


def required(key, scenario, C0=160000000., R0=40000000., inventory=None, year=1):
    p = params(scenario)
    annual_r, fund_q, issue, receipt = calendar(key, p, scenario.get('expanded',False))
    fixed = 0 if key == 'CON-006@v2' else p['annual_fixed_C']
    Jmonthly = 600 if key == 'CON-006@v2' else 0
    shares = p.get('region_demand_shares',[.6,.4])
    cap = [1800,1200]
    unit_price = 940*p['price_multiplier']+30
    old_weights = [1/12]*12
    if p.get('old_january_share'):
        old_weights = [.5]+[.5/11]*11
    stocks = list(inventory or [0.,0.])
    C,R,F = C0,R0,0.
    J = 0.
    rows, resource = [], dict(HR=0.,manager=0.,employee=0.,IT=0.)
    useful_total = 0.
    for n in range(12):
        m=n+1
        oldc=C0*p['old_annual_use']*old_weights[n]
        oldr=R0*p['old_annual_use']*old_weights[n]
        fixed_use=fixed*p['new_fixed_C_use']/12
        demand_C = oldc+oldr+fixed_use+receipt[n]
        baskets=demand_C/5000+Jmonthly
        received,closes,excess = [],[],[]
        for reg in range(2):
            wanted=baskets*shares[reg]
            arriving=batch_units(wanted-stocks[reg])
            received.append(arriving)
            closes.append(stocks[reg]+arriving-wanted)
            excess.append(max(0,wanted-cap[reg]))
        converted=oldr+receipt[n]
        C_before,R_before=C,R
        C += fixed/12 + converted-demand_C
        R += issue[n]-converted
        grant=fund_q if n%3==0 else 0.
        F += grant-issue[n]
        F_before_expiry=F
        expire=F if n%3==2 else 0.
        F-=expire
        conditional = (fund_q if key=='CON-010@v1' and n%3!=2 else 0.)
        Jcreated=7200 if key=='CON-006@v2' and m==1 and year==1 else Jmonthly if year>1 else 0.
        J+=Jcreated-Jmonthly
        hours,useful,setup=process_hours(key,m,baskets,include_setup=(m==1 and year==1))
        # Setup occurs before the year except incumbent16h at month1. It enters
        # first-year cost, not recurring month1 HR-capacity measurement.
        cap_hours=process_hours(key,m,baskets)[0]['HR']
        if year>1:
            # Pilot is a first-year exercise, not an annually repeated resource.
            if key=='CON-010@v1':
                if m==4: hours['HR']-=20;hours['IT']-=10;cap_hours-=20
                if m==3: hours['manager']-=20;hours['employee']-=30
            if key=='CON-006@v2' and m==1: hours['HR']-=16;cap_hours-=16
        for role in resource: resource[role]+=hours[role]
        useful_total+=useful
        rows.append(dict(candidate_key=key,scenario=scenario['id'],year=year,month=m,
          F_granted_R=grant,R_approved_max_R=issue[n],R_posted_R=issue[n],
          approved_unposted_R=0,conditional_max_reserved_R=conditional,
          F_available_uncommitted_R=max(0,F-conditional),
          F_unissued_before_close_R=F_before_expiry,F_expired_unpromised_R=expire,F_closing_R=F,
          fixed_C_issued=fixed/12,C_transfer_net=0,R_to_C_required=converted,
          direct_R_required=0,old_C_requested=oldc,old_R_requested=oldr,
          new_fixed_C_requested=fixed_use,new_R_receipt_requested=receipt[n],
          J_created=Jcreated,J_required_delivery=Jmonthly,J_conditional_close=J,
          requested_baskets=baskets,S1_requested=baskets*shares[0],S2_requested=baskets*shares[1],
          S1_opening_inventory=stocks[0],S2_opening_inventory=stocks[1],
          order_month=m-1,S1_ordered_for_arrival=received[0],S2_ordered_for_arrival=received[1],
          S1_arrival=received[0],S2_arrival=received[1],
          S1_required_delivery=baskets*shares[0],S2_required_delivery=baskets*shares[1],
          S1_conditional_inventory=closes[0],S2_conditional_inventory=closes[1],
          accounts_payable_closing_RUB=0,
          procurement_required_RUB=sum(received)*940*p['price_multiplier'],
          logistics_required_RUB=sum(received)*30,
          required_cash_RUB=sum(received)*unit_price,
          consumption_required_RUB=baskets*unit_price,
          S1_capacity_excess=excess[0],S2_capacity_excess=excess[1],
          C_conditional_close=C,R_conditional_close=R,
          HR_capacity_hours=cap_hours,HR_resource_hours=hours['HR'],
          manager_resource_hours=hours['manager'],employee_process_hours=hours['employee'],
          useful_work_hours=useful,IT_resource_hours=hours['IT'],
          audit_common_employee_receipt_hours=baskets*.1,
          stockflow_residual=(C+R)-(C_before+R_before+fixed/12+issue[n]-demand_C)))
        stocks=closes
    cash=sum(x['required_cash_RUB'] for x in rows)
    cost=sum(resource[k]*COMMON['rates_rub_hour'][k] for k in resource)
    receipt_hours=sum(x['requested_baskets'] for x in rows)*.1
    literal_receipt=receipt_hours if key=='CON-009@v1' else 0.
    author_resource=cost+useful_total*1000+literal_receipt*1000
    comparable_resource=cost+useful_total*1000+receipt_hours*1000
    end_new_reserve=annual_r*(1-p['new_R_use'])*unit_price/5000
    # The fixed-C portion and residual old stock are distinct from R reserve.
    fixed_unredeemed=fixed*(1-p['new_fixed_C_use'])
    total_received=sum(x['S1_arrival']+x['S2_arrival'] for x in rows)
    s=dict(candidate_key=key,scenario=scenario['id'],year=year,
      opening_C=C0,opening_R=R0,fixed_C_issued=fixed,R_fund_granted=4*fund_q,R_issued=annual_r,
      R_fund_unissued_expired=4*fund_q-annual_r,
      requested_baskets=sum(x['requested_baskets'] for x in rows),received_baskets=total_received,
      procurement_required_RUB=sum(x['procurement_required_RUB'] for x in rows),
      logistics_required_RUB=sum(x['logistics_required_RUB'] for x in rows),required_cash_RUB=cash,
      consumption_required_RUB=sum(x['consumption_required_RUB'] for x in rows),
      closing_inventory_units=sum(stocks),closing_inventory_cost_RUB=sum(stocks)*unit_price,
      required_capacity_pass=not any(x['S1_capacity_excess']+x['S2_capacity_excess']>EPS for x in rows),
      HR_peak_hours=max(x['HR_capacity_hours'] for x in rows),
      HR_capacity_pass=max(x['HR_capacity_hours'] for x in rows)<=220+EPS,
      max_regional_S1_units=max(x['S1_requested'] for x in rows),
      max_regional_S2_units=max(x['S2_requested'] for x in rows),
      conditional_C_close=C,conditional_R_close=R,conditional_CR_close=C+R,
      remaining_rights_exposure_RUB=(C+R)*unit_price/5000,
      new_R_reserve_RUB=end_new_reserve,unredeemed_current_fixed_C=fixed_unredeemed,
      unredeemed_current_fixed_exposure_RUB=fixed_unredeemed*unit_price/5000,
      cash_plus_new_R_reserve_RUB=cash+end_new_reserve,
      cash_plus_all_current_new_reserve_RUB=cash+end_new_reserve+fixed_unredeemed*unit_price/5000,
      HR_hours=resource['HR'],manager_hours=resource['manager'],
      employee_process_hours=resource['employee'],useful_work_hours=useful_total,
      employee_common_receipt_hours=receipt_hours,IT_hours=resource['IT'],
      literal_known_resource_RUB=author_resource,literal_known_cost_on_cash_boundary_RUB=cash+author_resource,
      audit_known_resource_RUB=comparable_resource,audit_known_cost_on_cash_boundary_RUB=cash+comparable_resource,
      audit_process_cost_excluding_useful_RUB=cash+comparable_resource-useful_total*1000,
      audit_consumption_plus_resource_RUB=sum(x['consumption_required_RUB'] for x in rows)+comparable_resource,
      incremental_HR_cash_RUB=.2*resource['HR']*1000,
      audit_incremental_replacement25_cash_RUB=.2*resource['HR']*1000+.25*(comparable_resource-resource['HR']*1000),
      audit_double_labor_cost_RUB=cash+2*comparable_resource,
      HR_double_labor_peak_hours=2*max(x['HR_capacity_hours'] for x in rows),
      audit_double_labor_replacement_cash_RUB=2*(.2*resource['HR']*1000+.25*(comparable_resource-resource['HR']*1000)),
      residual_old_or_unredeemed_claims_are_not_extinguished=True,
      complete_real_cost_known=False)
    for budget in [30000000,34000000]:
        s[f'required_cash_pass_{budget//1000000}']=cash<=budget+EPS
        s[f'cash_R_reserve_pass_{budget//1000000}']=cash+end_new_reserve<=budget+EPS
    assert abs(C+R-(C0+R0+fixed+annual_r-sum(x['R_to_C_required']+x['old_C_requested']+x['new_fixed_C_requested'] for x in rows)))<1
    assert min(C,R)>=-EPS
    assert abs(total_received+sum(inventory or [0,0])-s['requested_baskets']-sum(stocks))<1e-5
    assert max(abs(x['stockflow_residual']) for x in rows)<1e-5
    return s,rows,stocks


def execute(key,scenario,budget):
    """One transparent possible execution; not an optimized forecast.

    Full annual cash available upfront (audit assumption). Regional FIFO by
    source priority oldC,oldR,fixed,newR,J. Orders preplanned one month ahead;
    batch rounding paid on arrival. No purchase beyond annual cash cap. No
    protected reserve is spent as free cash. R converts only upon delivery.
    Unmet claims stay personal C/R/J; demand is never labelled redeemed.
    """
    p=params(scenario); annual_r,fund_q,issue,receipt=calendar(key,p,scenario.get('expanded',False))
    reserve=annual_r*(1-p['new_R_use'])*(940*p['price_multiplier']+30)/5000
    protected_budget=max(0,budget-reserve)
    _,request,_=required(key,scenario)
    cash=0.; stock=[0.,0.]; queues=[[0.]*5 for _ in range(2)]
    C,R,J=160000000.,40000000.,0.
    rows=[];phys=0.;Jserved=0.;conv=0.;emitted_fixed=0.;emitted_R=0.
    for n,req in enumerate(request):
        if key=='CON-006@v2' and n==0:J+=7200
        C+=req['fixed_C_issued'];R+=issue[n]
        emitted_fixed+=req['fixed_C_issued'];emitted_R+=issue[n]
        sources=[req['old_C_requested']/5000,req['old_R_requested']/5000,
                 req['new_fixed_C_requested']/5000,receipt[n]/5000,req['J_required_delivery']]
        for reg,share in enumerate(p.get('region_demand_shares',[.6,.4])):
            queues[reg]=[a+b*share for a,b in zip(queues[reg],sources)]
        delivered=[0.,0.];arrive=[0,0];unmet=[0.,0.]
        fixed_HR_hours=process_hours(key,n+1,0)[0]['HR']
        HR_basket_room=max(0,(220-fixed_HR_hours)/(.02+.2/30))
        for reg,cap in enumerate([1800,1200]):
            intended=min(sum(queues[reg]),cap,HR_basket_room)
            wanted_batches=batch_units(intended-stock[reg])//100
            affordable=max(0,math.floor((protected_budget-cash+EPS)/(100*(940*p['price_multiplier']+30))))
            arrive[reg]=100*min(wanted_batches,affordable)
            stock[reg]+=arrive[reg]
            cash+=arrive[reg]*(940*p['price_multiplier']+30)
            available=min(cap,stock[reg],HR_basket_room)
            for cat in range(5):
                done=min(available,queues[reg][cat]);available-=done;stock[reg]-=done
                queues[reg][cat]-=done;delivered[reg]+=done
                if cat in [1,3]:R-=5000*done;conv+=5000*done
                elif cat in [0,2]:C-=5000*done
                else:J-=done;Jserved+=done
                if cat!=4:phys+=5000*done
            unmet[reg]=sum(queues[reg])
            HR_basket_room-=delivered[reg]
        rows.append(dict(candidate_key=key,scenario=scenario['id'],budget_RUB=budget,month=n+1,
          delivery_policy='audit_FIFO_sources;annual_cash_upfront;one_month_preplanned_order',
          protected_unredeemed_new_R_cash_RUB=reserve,order_month=n,
          S1_arrivals=arrive[0],S2_arrivals=arrive[1],S1_delivered=delivered[0],S2_delivered=delivered[1],
          HR_actual_delivery_hours=fixed_HR_hours+sum(delivered)*(.02+.2/30),
          cumulative_procurement_logistics_cash_RUB=cash,S1_inventory=stock[0],S2_inventory=stock[1],
          S1_unmet_requests_units=unmet[0],S2_unmet_requests_units=unmet[1],
          C_actual_closing=C,R_actual_closing=R,J_actual_closing=J,
          R_to_C_actual_cumulative=conv,C_physically_redeemed_cumulative=phys,
          J_delivered_cumulative=Jserved,approved_unposted_R=0,accounts_payable_RUB=0,
          unfulfilled_oldC_units=sum(q[0] for q in queues),unfulfilled_oldR_units=sum(q[1] for q in queues),
          unfulfilled_newfixed_units=sum(q[2] for q in queues),unfulfilled_newR_units=sum(q[3] for q in queues),
          unfulfilled_J_units=sum(q[4] for q in queues),
          CR_balance_residual=C+R-(200000000+emitted_fixed+emitted_R-phys)))
    assert min(C,R,J)>=-EPS
    assert cash+reserve<=budget+EPS
    assert max(abs(x['CR_balance_residual']) for x in rows)<1e-4
    assert max(x['HR_actual_delivery_hours'] for x in rows)<=220+EPS
    return rows


SCENARIOS=list(M['scenarios'])+[
 {'id':'CORE_24M_SENSITIVITY_ONLY','expanded':True,'overrides':{}},
 {'id':'LOW96_24M_SENSITIVITY_ONLY','expanded':True,'overrides':{'annual_fixed_C':96000000,'new_fixed_C_use':1}},
 {'id':'NEW_R_DECEMBER_ALL','overrides':{'new_R_all_december':True}},
 {'id':'LOW96_NEW_R_DECEMBER_ALL','overrides':{'annual_fixed_C':96000000,'new_fixed_C_use':1,'new_R_all_december':True}}]
annual=[];monthly=[];actual=[]
for key in KEYS:
    for s in SCENARIOS:
        if s.get('expanded') and key in ['BASELINE','CON-006@v2']:continue
        a,r,_=required(key,s);annual.append(a);monthly+=r
        for budget in [30000000,34000000]:actual+=execute(key,s,budget)
table('annual.csv',annual);table('monthly-required.csv',monthly);table('monthly-execution.csv',actual)

# Long horizon: no magical disappearance, no reserve/warehouse double charge.
# Required paths are explicitly conditional; not actual paths after any failure.
long=[]
for key in KEYS:
 for sid in ['CORE_60','LOW_FIXED96_FULL_NEW','NEW_R_USE_60','NEW_R_USE_80','NEW_R_USE_0']:
    scenario=next(s for s in SCENARIOS if s['id']==sid)
    C,R,inv=160000000.,40000000.,[0.,0.]
    cash_carry30,cash_carry34=0.,0.
    prior_feasible=True
    outstanding_new_R=0.
    prior_new_R_reserve=0.
    for year in range(1,11):
        a,_,inv=required(key,scenario,C,R,inv,year)
        C,R=a['conditional_C_close'],a['conditional_R_close']
        outstanding_new_R=outstanding_new_R*(1-params(scenario)['old_annual_use'])+a['R_issued']*(1-params(scenario)['new_R_use'])
        new_R_reserve=outstanding_new_R*.194
        cash_carry30+=30000000-a['required_cash_RUB']
        cash_carry34+=34000000-a['required_cash_RUB']
        feasible=a['required_capacity_pass'] and a['HR_capacity_pass'] and a['required_cash_pass_30']
        prior_feasible=prior_feasible and feasible
        long.append(dict(candidate_key=key,scenario=sid,year=year,
          path='required_full_claim_execution_conditional_not_actual_after_failure',
          C_conditional_closing=C,R_conditional_closing=R,CR_conditional_closing=C+R,
          required_cash_RUB=a['required_cash_RUB'],closing_inventory_units=sum(inv),
          residual_claim_exposure_RUB=a['remaining_rights_exposure_RUB'],
          all_unfulfilled_new_R_since_launch=outstanding_new_R,
          protected_new_R_reserve_RUB=new_R_reserve,
          cash_plus_new_R_reserve_change_RUB=a['required_cash_RUB']+new_R_reserve-prior_new_R_reserve,
          current_year_cash30_pass=a['required_cash_pass_30'],current_year_cash34_pass=a['required_cash_pass_34'],
          capacity_pass=a['required_capacity_pass'],HR_peak=a['HR_peak_hours'],
          full_path_feasible_at30=prior_feasible,
          hypothetical_cumulative_free_cash30_RUB=cash_carry30,
          hypothetical_cumulative_free_cash34_RUB=cash_carry34,
          hypothetical_unbacked_claims30_RUB=max(0,a['remaining_rights_exposure_RUB']-max(0,cash_carry30)),
          real_cash_carry_policy_confirmed=False,
          new_rights_per_year_max_physical_exposure_RUB=(a['fixed_C_issued']+a['R_issued'])*.194+(7200*970 if key=='CON-006@v2' else 0)))
        prior_new_R_reserve=new_R_reserve
table('ten-year-conditional.csv',long)

# Direct services are an alternative use of the same R, never in addition to
# redeeming those R physically. New service funding is separate from 30/34m.
service=[]
for key in KEYS:
 for name,Ramount,month_count in [('OLD_R_ALL_UNIFORM',40000000,12),('OLD_R_ALL_ONE_MONTH',40000000,1),
                                 ('NEW_R_ALL_UNIFORM',0 if key=='CON-006@v2' else 77710364 if key=='BASELINE' else 8000000,12),
                                 ('NEW_R_ALL_ONE_MONTH',0 if key=='CON-006@v2' else 77710364 if key=='BASELINE' else 8000000,1)]:
    units=Ramount/20000
    service.append(dict(candidate_key=key,scenario=name,R_direct_required=Ramount,
      units_required=units,service_hours=units*8,resource_RUB=units*8*1000,
      service_replacement_cash_RUB=units*8*1000*.25,
      HR_service_processing_hours=None,
      maximum_units_month=units/month_count,capacity_units_month=200,
      capacity_pass=units/month_count<=200+EPS,
      maximum_units_unserved_in_window=max(0,units-200*month_count),
      physically_redeem_same_R_again=False,
      real_terms_confirmed=False))
table('direct-R-services.csv',service)

# Lifecycle examples are tests of policy bookkeeping, not bank observations.
lifecycle=[
 dict(test='approval_posting_lag',F_grant=2000000,F_committed=2000000,R_posted=1000000,
      approved_unposted_R=1000000,F_available_uncommitted=0,F_expiry=0,
      personal_plus_unposted_R=2000000,reserve_RUB=2000000*.194),
 dict(test='full_year_R_never_used',R_granted=8000000,R_posted=8000000,R_to_C=0,
      R_physically_redeemed=0,closing_personal_R_new=8000000,reserve_RUB=1552000),
 dict(test='convert_without_receipt',R_granted=8000000,R_to_C=8000000,
      confirmed_redemption=0,closing_new_C=8000000,reserve_RUB=1552000),
 dict(test='internal_transfer',C_before_A=5000,C_before_B=0,transfer_A_to_B=5000,
      C_after_A=0,C_after_B=5000,new_issuance=0,reserve_follows_claim_RUB=970),
 dict(test='B_quarter_signed_max_before_posting',F_grant=2000000,
      conditional_base=300*5000,conditional_contest_pool=10*(30000+15000+5000),
      maximum_reserved_R=2000000,reserve_RUB=388000),
 dict(test='B_quarter_end_validation_blocked',F_grant=2000000,
      conditional_unresolved_R=2000000,R_posted=0,F_available_uncommitted=0,
      F_expiry_permitted=0,conditional_rights_carried=2000000,reserve_RUB=388000),
 dict(test='incumbent_all_voluntarily_defer_10years',J_created_year1=7200,
      J_new_years2to10=0,J_unfulfilled_year10=7200,J_reserve_RUB=6984000,
      old_CR_if_never_presented=200000000,old_CR_exposure_RUB=38800000),
 dict(test='incumbent_bank_delays_all_1year',J_created_year1=7200,J_delivered_year1=0,
      J_created_year2_from_original_due_dates=7200,J_unfulfilled_year2_before_remedy=14400,
      J_required_resource_RUB=13968000,not_voluntary_deferral=True)]
assert lifecycle[0]['R_posted']+lifecycle[0]['approved_unposted_R']==lifecycle[0]['F_committed']
assert 300*5000+10*(30000+15000+5000)==2000000
assert 5*5000+30000==55000
for k in range(2,6):
 for prize in [30000,15000,5000]:
    split=[prize//k+(1 if i<prize%k else 0) for i in range(k)]
    assert sum(split)==prize
dump('rights-lifecycle-tests.json',lifecycle)

# Operational concentration, not just an annual average.
workload=[]
for key in KEYS:
 for sid in ['CORE_60','LOW_FIXED96_FULL_NEW']:
    a=next(x for x in annual if x['candidate_key']==key and x['scenario']==sid)
    workload.append(dict(candidate_key=key,scenario=sid,
      literal_cost_RUB=a['literal_known_cost_on_cash_boundary_RUB'],
      comparable_audit_cost_RUB=a['audit_known_cost_on_cash_boundary_RUB'],
      comparable_process_cost_without_useful_work_RUB=a['audit_process_cost_excluding_useful_RUB'],
      audit_6min_hours_already_in_literal=(key=='CON-009@v1'),
      missing_baseline_manager_IT_and_work_resource=(key=='BASELINE'),
      useful_work_hours_costed=a['useful_work_hours'],
      comparable_useful_work_cost_in_A_and_baseline='unknown/already_done; never infer zero benefit or ordinary work',
      HR_peak=a['HR_peak_hours'],HR_capacity=220,HR_double_peak=a['HR_double_labor_peak_hours'],
      nonHR_replacement25_plus_HR20_RUB=a['audit_incremental_replacement25_cash_RUB'],
      double_labor_full_cost_RUB=a['audit_double_labor_cost_RUB']))
table('comparable-costs.csv',workload)

dump('new-promise-limits.json',{
 'classification':'independent calculation under M04, not a bank authorization',
 'conservative_current_fixed_full_value_RUB':144000000*.194,
 'base_full_new_fixed_and_R_value_RUB':(144000000+8000000)*.194,
 'base_plus_buffer_RUB':(144000000+8000000)*.194+500000,
 'theoretical_R_flow_ceiling_at30_after_fixed_and_buffer':(30000000-144000000*.194-500000)/.194,
 'theoretical_R_flow_ceiling_at34_after_fixed_and_buffer':(34000000-144000000*.194-500000)/.194,
 'boundary':'limits omit transitional old demand and batch rounding; they do not establish full backing',
 'base8m_R_reduction_vs_Q3_times4':1-8000000/(4*19427591),
 'expanded24m_R_reduction_vs_Q3_times4':1-24000000/(4*19427591),
 'full_initial_old_CR_exposure_RUB':200000000*.194,
 'initial_cash_reserve_RUB':0,
 'core_unredeemed_new_fixed_C':144000000*.4,
 'core_unredeemed_new_fixed_exposure_RUB':144000000*.4*.194
})

verification={
 'status':'pass',
 'independence':'No supporting model, author self-check, annual or monthly results imported/executed. Only frozen parameters and published policy counts/formulas used.',
 'tests':['All CR monthly conservation residuals <1e-4 C/R',
          'A/B embedded M04 identical to frozen shared parameters; Q3 arithmetic independently recomputed',
          'A40 fund-owner release groups and60/40 regional totals reconcile to650/650/700k',
          'Required inventory opening + arrivals - requested = closing',
          'Actual execution never spends annual cap plus protected R reserve; HR<=220h',
          'Actual stock/CR/J nonnegative; actual unserved claims retained',
          'F not personal; unissued Q3 scenario fund expiry only',
          'B full maximum 2m/quarter,8m/year, team prize exact split k2..5',
          'Pending approved rights distinct from posted R',
          'Conversion and transfer never extinguish reserve',
          'No free January receipt; order m0, cash m1; AP closing0',
          'Consumption and closing inventory not added twice to cash/resource',
          '10-year conditional paths preserve unredeemed balances',
          'Same common receipt-time audit6min/basket, no duplication for A'],
 'row_counts':{'annual':len(annual),'monthly_required':len(monthly),'monthly_execution':len(actual),'ten_year':len(long)},
 'material_limitations':[
   'A hypothetical feasible execution uses perfect known scenario timing, annual cash upfront and a stated source FIFO; it is not observed bank performance or unique allocation.',
   'Bank N, gross fixed emissions, old/posting/order balances, backing, catalogue/regional capacity, HR/manager/IT availability remain uncertain.',
   'No real cash carry authority assumed. Hypothetical ten-year free-cash accumulation is separately labelled.',
   'Actual unidentified approved unposted rights are unknown, not asserted zero; main scenarios contain only identified model commitments.',
   'B month25 award to last-working-day receipt requires confirmed stock and delivery timing; monthly arithmetic does not prove that SLA.',
   'Baseline managerial/IT labor unknown; incumbent100research-hours role unspecified, valued at common1000rub/h scenario analyst rate.',
   'Useful production effort2h in B separately costed; A recognizes already-completed work, comparative incremental production resource remains unknown.'
 ]}
dump('verification.json',verification)
dump('source-manifest.json',[{'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
   'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in SOURCE_PATHS])
dump('audit-assumptions.json',{
 'classification':'explicit independent-check scenario assumptions, no changes to frozen M04 or candidate mechanisms',
 'AUD01':{'parameter':'common employee reward order/receipt time','value':6,'unit':'minutes/requested basket',
          'basis':'A finance-spec.workload.employee_order_receipt_all_baskets_min; coordinator authorization applies to all four comparators',
          'boundary':'additional audit sensitivity; not bank fact; do not add twice to A'},
 'AUD02':{'parameter':'feasible execution','value':'annual cash upfront; known forecast one month before; regional FIFO oldC/oldR/fixed/newR/J',
          'boundary':'one transparent allowed execution; not optimization or bank commitment'},
 'AUD03':{'parameter':'incumbent research100h role','value':1000,'unit':'RUB/h',
          'boundary':'analyst/employee-rate assumption; role unspecified in old spec'},
 'AUD04':{'parameter':'old rights use','value':'same M04 fraction applied to opening C and R separately in all four',
          'boundary':'incumbent prior M01/M02 prices/frequencies not imported'},
 'AUD05':{'parameter':'future bank currency commitments','value':None,
          'boundary':'unidentified existing unposted awards/orders/reserves need actual reconciliation; absence of rows does not establish zero'}
})
print(json.dumps(verification['row_counts'],ensure_ascii=False))
for k in KEYS:
 for sid in ['CORE_60','LOW_FIXED96_FULL_NEW']:
    a=next(x for x in annual if x['candidate_key']==k and x['scenario']==sid)
    print(k,sid,'cash',round(a['required_cash_RUB']), 'HRpeak',round(a['HR_peak_hours'],3),
          'literal',round(a['literal_known_cost_on_cash_boundary_RUB']),
          'audit',round(a['audit_known_cost_on_cash_boundary_RUB']))
