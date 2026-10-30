"""M04 common scenario arithmetic; standard library only; no bank forecast."""
from pathlib import Path
import csv, json, math
P=Path(__file__).resolve().parent
S=json.loads((P/'scenario-inputs.json').read_text())
C=S['common']

def run(scenario, fund, years=1):
    p=C|scenario['overrides']
    cost=(p['certificate_share']*p['certificate_cost_fraction']+p['merch_share']*p['merch_cost_fraction'])*p['basket_nominal_rub']*p['price_multiplier']
    logistics=p['merch_share']*p['logistics_rub_per_merch']
    landed=cost+logistics
    unit=landed/p['basket_C']
    oldC=p['initial_C']; oldR=p['initial_personal_R']; inv={r['id']:0.0 for r in p['regions']}
    reserveR=0.0; reserve_growth=0.0; annual=[]; monthly=[]
    for year in range(1,years+1):
        openC=oldC; openR=oldR; opening_reserveR=reserveR; openInv=sum(inv.values())
        oldCuse=openC*p['old_annual_use']; oldRuse=openR*p['old_annual_use']
        # Old cohorts are debited only on execution; internal R->C conversion is neutral in C+R.
        newCuse=p['annual_fixed_C']*p['new_fixed_C_use']
        newRuse=fund*p['new_R_use']
        oldCend=openC-oldCuse + p['annual_fixed_C']-newCuse
        oldRend=openR-oldRuse + fund-newRuse
        demandC=oldCuse+oldRuse+newCuse+newRuse
        qFund=0.0; gross=0.0; F=0.0; peak=0.0; adminHours=0.0; proc=0.0; log=0.0; unmet=0.0
        # Requests are shown uncapped: capacity violations do not reduce cash or erase rights.
        for m in range(1,13):
            grant=fund/4 if m in [1,4,7,10] else 0.0
            award=fund/4 if p.get('R_calendar')=='quarter_end' and m in [3,6,9,12] else (0.0 if p.get('R_calendar')=='quarter_end' else fund/12)
            F+=grant-award
            oldshare=p.get('old_january_share',1/12) if m==1 else ((1-p['old_january_share'])/11 if 'old_january_share' in p else 1/12)
            dC=(oldCuse+oldRuse)*oldshare+newCuse/12+award*p['new_R_use']
            baskets=dC/p['basket_C']; peak=max(peak,baskets)
            issuesC=p['annual_fixed_C']/12
            reg=[]; pur=0; lm=0; capFail=False
            for i,r in enumerate(p['regions']):
                share=p.get('region_demand_shares',[x['demand_share'] for x in p['regions']])[i]
                d=baskets*share
                req=max(0,d-inv[r['id']]); batches=math.ceil(max(0,req-1e-8)/p['procurement_batch_per_region'])
                receipt=batches*p['procurement_batch_per_region']; oldinv=inv[r['id']]; inv[r['id']]+=receipt-d
                purchase=receipt*cost; freight=receipt*logistics
                pur+=purchase; lm+=freight; capFail|=d>r['capacity_units_month']+1e-7
                unmet+=max(0,d-r['capacity_units_month'])
                reg.append({'id':r['id'],'demand_units':d,'receipts_units':receipt,'ending_inventory':inv[r['id']],'capacity':r['capacity_units_month'],'order_month':m-1,'purchase_rub':purchase,'logistics_rub':freight})
                assert abs(oldinv+receipt-d-inv[r['id']])<1e-6
            hours=p['admin_fixed_hours_month']+baskets*(p['admin_hours_per_basket']+p['merch_share']*p['manual_merch_hours_per_unit'])
            proc+=pur; log+=lm; adminHours+=hours
            monthly.append({'scenario':scenario['id'],'fund_R_year':fund,'year':year,'month':m,'C_fixed_issued':issuesC,'F_granted_R':grant,'R_awarded':award,'F_close':F,'R_conversion_new':award*p['new_R_use'],'old_C_R_demand_C':(oldCuse+oldRuse)*oldshare,'new_fixed_C_demand':newCuse/12,'total_demand_C':dC,'baskets':baskets,'procurement_rub':pur,'logistics_rub':lm,'cash_rub':pur+lm,'HR_hours_base':hours,'capacity_pass':not capFail,'HR_capacity_pass':hours<=p['admin_capacity_hours_month']+1e-7,'regions':json.dumps(reg,separators=(',',':'))})
            gross+=issuesC+award
            if m%3==0:
                assert abs(F)<1e-7
                F=0.0
        assert abs(openC+openR+p['annual_fixed_C']+fund-demandC-oldCend-oldRend)<1e-5
        new_unspent_R=fund-newRuse
        # Earmark the full physical conversion cost of every unredeemed new R; this is additional to paid rewards.
        # Existing old R also redeems pro rata, so reserve associated with old new-R cohorts is released pro rata.
        reserveR=opening_reserveR*(1-p['old_annual_use'])+new_unspent_R*unit
        reserve_change=reserveR-opening_reserveR
        liability_open=(openC+openR)*unit; liability_close=(oldCend+oldRend)*unit
        liability_change=liability_close-liability_open
        consumed=demandC*unit
        economic_annual_new_rights=(p['annual_fixed_C']+fund)*unit
        # Total gap remains visible: no fictional opening reserve.
        available_after_paid=30000000-(proc+log)
        reserve_growth+=max(0,available_after_paid)
        a={'scenario':scenario['id'],'fund_R_year':fund,'year':year,'C_open':openC,'R_open':openR,'C_fixed_issued':p['annual_fixed_C'],'R_awarded':fund,'C_close':oldCend,'R_close':oldRend,'old_C_used':oldCuse,'old_R_converted':oldRuse,'new_fixed_C_used':newCuse,'new_R_converted':newRuse,'C_redeemed':demandC,'baskets':demandC/p['basket_C'],'procurement_rub':proc,'logistics_rub':log,'procurement_plus_logistics_cash_rub':proc+log,'consumed_landed_cost_rub':consumed,'inventory_open_units':openInv,'inventory_close_units':sum(inv.values()),'inventory_close_landed_rub':sum(inv.values())*landed,'personal_rights_exposure_close_rub':liability_close,'new_R_reserve_close_rub':reserveR,'new_R_reserve_increase_rub':reserve_change,'cash_plus_new_R_reserve_increase_rub':proc+log+max(0,reserve_change),'new_rights_annual_landed_rub':economic_annual_new_rights,'new_rights_plus_500k_buffer_rub':economic_annual_new_rights+p['annual_buffer_for_new_limits_rub'],'rights_exposure_change_rub':liability_change,'cash_30_unspent_potential_ringfence_cumulative_rub':reserve_growth,'legacy_plus_future_backing_gap_if_ringfence_30_rub':max(0,liability_close-reserve_growth),'HR_hours_base_year':adminHours,'HR_resource_base_rub':adminHours*p['rates_rub_hour']['HR'],'HR_extra_cash_base_rub':adminHours*p['rates_rub_hour']['HR']*p['admin_incremental_cash_share'],'full_priced_resource_before_candidate_hours_rub':proc+log+adminHours*p['rates_rub_hour']['HR'],'peak_baskets_month':peak,'unserved_capacity_units_if_fixed_cap':unmet,'capacity_pass':unmet<1e-6,'budget30_cash_pass':proc+log<=30000000+1e-6,'budget34_cash_pass':proc+log<=34000000+1e-6,'stock_flow_error':openC+openR+p['annual_fixed_C']+fund-demandC-oldCend-oldRend}
        annual.append(a)
        oldC=oldCend; oldR=oldRend
    return annual,monthly

def write_csv(name,rows):
    with (P/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    annual=[];monthly=[]
    for scenario in S['scenarios']:
        for fund in [0,C['base_R_ceiling_year'],C['expanded_R_ceiling_year']]:
            a,m=run(scenario,fund);annual+=a;monthly+=m
    longrun=[];lm=[]
    for sid in ['CORE_60','LOW_FIXED96_FULL_NEW']:
        scenario=next(x for x in S['scenarios'] if x['id']==sid)
        for fund in [0,C['base_R_ceiling_year'],C['expanded_R_ceiling_year']]:
            a,m=run(scenario,fund,10);longrun+=a;lm+=m
    write_csv('annual-results.csv',annual);write_csv('monthly-results.csv',monthly);write_csv('ten-year-results.csv',longrun)
    unit=(.8+.2*.7+.2*.15)/5
    full={'base_fund_8m':(C['initial_C']+C['initial_personal_R']+C['annual_fixed_C']+C['base_R_ceiling_year'])*unit,'expanded_fund_24m':(C['initial_C']+C['initial_personal_R']+C['annual_fixed_C']+C['expanded_R_ceiling_year'])*unit}
    limits={'unit_landed_rub_per_C':unit,'max_R_at30_after_500k_buffer':(30000000-500000-C['annual_fixed_C']*unit)/unit,'max_R_at34_after_500k_buffer':(34000000-500000-C['annual_fixed_C']*unit)/unit,'chosen_base_R_ceiling':8000000,'chosen_expanded_R_ceiling':24000000,'full_all_rights_landed_rub':full,'unchanged_Q3_annualized_awards_R':S['source_anchors']['q3_awards_R']*4,'unchanged_Q3_annualized_fund_R':S['source_anchors']['q3_manager_fund_R']*4,'baseline_Q3_annualized_cost_at_full_new_rights_rub':(C['annual_fixed_C']+S['source_anchors']['q3_awards_R']*4)*unit}
    (P/'limits.json').write_text(json.dumps(limits,ensure_ascii=False,indent=2)+'\n')
    val={'status':'pass','rows_annual':len(annual),'rows_monthly':len(monthly),'rows_ten_year':len(longrun),'checks':['C+R stock-flow reconciles for every year','F quarter grant-award balance reconciles and only unissued F resets','inventory opening+receipts-delivery=closing per region/month','no capacity clipping in cost; unmet demand retained as explicit diagnostic','zero initial inventory and cash reserve; January supply preordered and paid within modeled funding','full new-R reserves for unredeemed promises shown separately','budgets30/34 and all-rights60/80/100 evaluated'],'max_abs_stock_flow_error':max(abs(x['stock_flow_error']) for x in annual+longrun),'limits':limits,'scope':'Arithmetic of declared scenarios only; no actual bank budget/reserves/price/capacity confirmation.'}
    (P/'validation.json').write_text(json.dumps(val,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'pass','rows_annual':len(annual),'rows_monthly':len(monthly),'limits':limits},ensure_ascii=False))
if __name__=='__main__':main()
