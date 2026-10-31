"""Reproducible local design checks; writes only this owned branch. No financial admission."""
from pathlib import Path
import calendar, csv, datetime as dt, json, math

P = Path(__file__).resolve().parent
KEY = 'CON-011@v2'
def dump(name, obj):
    (P/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def date(m, day):
    return dt.date(2027+(m-1)//12, (m-1)%12+1, day).isoformat()
def regular(m): return 1800000 if m >= 4 else 0
def events(m):
    c=(m-1)%3+1; cycle=(m-c)//3+1
    return {'cohort':f'C{c}', 'cycle':cycle, 'start':date(m,15),
            'observation_end':date(m+3,14), 'quality_close_and_right':date(m+3,28),
            'posting':date(m+3,28), 'max_R':1800000,
            'promise':date(m,14), 'benchmark':'project role standard frozen before first effort'}

flow = {'records':2400, 'groups':60, 'primary_QA_cases_record':20,
        'primary_QA_minutes_case':1, 'secondary_records':240, 'secondary_minutes':3,
        'special_requests':200, 'special_HR_min':4, 'special_manager_min':10,
        'special_awards':48, 'independent_approval_min':5,
        'appeals':120, 'appeal_HR_min':6, 'appeal_manager_min':8, 'appeal_employee_min':5,
        'corrections':72, 'correction_HR_manager_min':5, 'correction_employee_min':3,
        'own_award_recusals':12, 'recusal_HR_min':5, 'recusal_independent_manager_min':8,
        'HR_fixed_h':6, 'rule_changes':10, 'rule_HR_min':10, 'rule_manager_min':20,
        'export_HR_min_group':10, 'export_manager_min_group':30,
        'HR_batch_min_record':.25, 'statement_employee_min_record':2,
        'special_employee_min':6}
hr = 6+(60*10+2400*.25+200*4+120*6+72*5+12*5+10*10)/60
manager = (2400*20+60*30+240*3+200*10+48*5+120*8+72*5+12*8+10*20)/60
manager_award = manager-800
employee = (2400*2+200*6+120*5+72*3)/60
hr_early=6+(200*4+12*5+10*10)/60
mgr_early=(200*10+48*5+12*8+10*20)/60
emp_early=200*6/60
prep={'HR':[38,8,8], 'manager':[120,30,30], 'employee':[600,600,600], 'IT':[120,200,200]}

def launch(scenario, fixed_use, cold=False):
    # Normalized baskets. Existing shop may place M05 m0 order, paid/received m1.
    inv=[0.,0.]; incoming=[0.,0.] if cold else [math.ceil(((40000000/12+8000000*fixed_use+200000)/5000)*s/100)*100 for s in [.6,.4]]; queues=[[],[]]
    wallet={'old_C':160000000., 'old_R':40000000., 'new_fixed_C':0., 'new_R_C':0.}
    new_R=0.; F=0.; reserve_open=0.; records=[]
    shares=[.6,.4]; caps=[1800,1200]
    annual_old_C=160000000.; annual_old_R=40000000.; annual_new_carry=0.
    for m in range(1,16):
        if m==13:
            annual_old_C=wallet['old_C']; annual_old_R=wallet['old_R']
            annual_new_carry=wallet['new_fixed_C']
        row={'scenario':scenario,'month':m,'calendar_month':date(m,1)[:7],
             'budget_year':2027+(m-1)//12, 'cohort_start':f'C{(m-1)%3+1}',
             'cycle_start':(m-1)//3+1, 'observation_start':date(m,15),
             'observation_end':date(m+3,14), 'promise_date_before_effort':date(m,14),
             'promised_ordinary_max_R':1800000, 'promised_special_max_R':200000,
             'confirmed_cohort':f'C{(m-4)%3+1}' if m>=4 else '',
             'confirmed_cycle':(m-4)//3+1 if m>=4 else '',
             'quality_close':date(m,28), 'posting_date':date(m,28),
             'confirmed_R':regular(m)+200000,'U_open_R':0,
             'U_peak_R':regular(m)+200000,'U_close_R':0,
             'F_open_R':F, 'F_grant_R':2000000,'F_expired_unencumbered_R':0,
             'personal_R_open':wallet['old_R']+new_R,
             'personal_C_open':wallet['old_C']+wallet['new_fixed_C']+wallet['new_R_C']}
        posted=regular(m)+200000; F += 2000000-posted
        wallet['new_fixed_C'] += 8000000
        new_R += posted
        old_R_convert=annual_old_R*.2/12
        wallet['old_R'] -= old_R_convert; wallet['old_C'] += old_R_convert
        wallet['new_R_C'] += new_R; new_convert=new_R; new_R=0
        demand={'old_C':annual_old_C*.2/12+old_R_convert,
                'new_fixed_C':8000000*fixed_use+annual_new_carry*.2/12,
                'new_R_C':posted}
        req=sum(demand.values()); deliver={'old_C':0.,'new_fixed_C':0.,'new_R_C':0.}
        receipt=list(incoming); cash=sum(receipt)*970
        region_delivered=[]
        for j in range(2):
            inv[j]+=incoming[j]
            queues[j].append({k:v*shares[j]/5000 for k,v in demand.items()})
            qtotal=sum(sum(q.values()) for q in queues[j])
            units=min(inv[j],caps[j],qtotal); remaining=units
            while remaining>1e-8 and queues[j]:
                q=queues[j][0]; qt=sum(q.values()); take=min(remaining,qt)
                for k,v in list(q.items()):
                    used=take*v/qt; q[k]-=used; deliver[k]+=used*5000
                remaining-=take
                if sum(q.values())<1e-8: queues[j].pop(0)
            inv[j]-=units; region_delivered.append(units)
            next_old=annual_old_C*.2/12+annual_old_R*.2/12
            next_carry=annual_new_carry*.2/12
            # At year boundary update exact next-year projection; queue is cleared before m13.
            if m==12:
                next_old=(wallet['old_C']-demand['old_C']+wallet['old_R'])*.2/12
                next_carry=(wallet['new_fixed_C']-demand['new_fixed_C'])*.2/12
            next_req=next_old+8000000*fixed_use+next_carry+regular(m+1)+200000
            backlog=sum(sum(q.values()) for q in queues[j])
            incoming[j]=max(0,math.ceil((backlog+next_req*shares[j]/5000-inv[j]-1e-9)/100))*100
        for k,v in deliver.items(): wallet[k]-=v
        pending=sum(sum(sum(q.values()) for q in qs) for qs in queues)*5000
        new_personal=wallet['new_fixed_C']+wallet['new_R_C']+new_R
        inv_value=sum(inv)*970
        # Conditional promised maximum is backed before effort; never counted as earned U.
        target=max(0,(new_personal+F)*.194-inv_value)
        earned_target=max(0,new_personal*.194-inv_value)
        common_hr=80+sum(region_delivered)*(.02+.2/30)
        extra_hr=hr if m>=4 else hr_early
        extra_mgr=manager_award if m>=4 else mgr_early
        extra_emp=employee if m>=4 else emp_early
        for role, base in [('HR',extra_hr),('manager',extra_mgr),('employee',extra_emp)]:
            row[role+'_recognition_hours']=base
            row[role+'_launch_hours']=prep[role][m-1] if m<=3 else 0
            row[role+'_total_hours']=base+row[role+'_launch_hours']
        row.update({'posted_R':posted,'F_close_R':F,'conditional_unearned_close_R':F,
                    'personal_R_close':wallet['old_R']+new_R,
                    'personal_C_close':sum(wallet[k] for k in ['old_C','new_fixed_C','new_R_C']),
                    'fixed_C_issued':8000000,'R_to_C':old_R_convert+new_convert,
                    'requested_C':req,'received_and_redeemed_C':sum(deliver.values()),
                    'unfulfilled_orders_C_close':pending,'new_personal_unredeemed_C_R':new_personal,
                    'old_personal_unredeemed_C_R':wallet['old_C']+wallet['old_R'],
                    'inventory_units_close':sum(inv),'inventory_value_RUB':inv_value,
                    'S1_received_baskets':region_delivered[0],'S2_received_baskets':region_delivered[1],
                    'S1_inventory_close':inv[0],'S2_inventory_close':inv[1],
                    'S1_supplier_receipt_baskets':receipt[0],'S2_supplier_receipt_baskets':receipt[1],
                    'S1_order_for_next_month':incoming[0],'S2_order_for_next_month':incoming[1],
                    'procurement_cash_RUB':sum(receipt)*940,'logistics_cash_RUB':sum(receipt)*30,
                    'procurement_including_logistics_cash_RUB':cash,
                    'earned_rights_reserve_RUB_close':earned_target,
                    'conditional_promise_extra_reserve_RUB_close':target-earned_target,
                    'total_reserve_RUB_open':reserve_open,'total_reserve_RUB_close':target,
                    'funding_cash_plus_delta_reserve_RUB':cash+target-reserve_open,
                    'common_M05_HR_hours':common_hr,
                    'combined_HR_hours':common_hr+row['HR_total_hours'],
                    'combined_HR_capacity_220_pass':common_hr+row['HR_total_hours']<=220+1e-8,
                    'combined_HR_fallback_hours':common_hr+row['HR_total_hours']+20,
                    'IT_initial_hours':prep['IT'][m-1] if m<=3 else 0,'IT_recurring_hours':12,
                    'primary_QA_total_hours':800 if m>=4 else 0,
                    'primary_QA_verified_existing_hours':None,
                    'primary_QA_actual_incremental_hours':None,
                    'primary_QA_if_no_reusable_source_incremental_hours':800 if m>=4 else 0,
                    'manager_quality_plus_award_required_hours':row['manager_total_hours']+(800 if m>=4 else 0),
                    'no_queue':pending<1e-5,'old_U_actual_unknown':True})
        assert abs(row['personal_C_open']+8000000+row['R_to_C']-row['received_and_redeemed_C']-row['personal_C_close'])<1e-5
        assert abs(row['personal_R_open']+posted-row['R_to_C']-row['personal_R_close'])<1e-5
        assert abs(row['F_open_R']+row['F_grant_R']-posted-F)<1e-5
        assert pending <= row['personal_C_close']+1e-5
        records.append(row); reserve_open=target
    return records

allrows=[]; scenarios={}
for name, use, cold in [('FULL_NEW',1.,False),('EXPECTED',.6,False),('COLD_SHOP_STRESS',1.,True)]:
    rows=launch(name,use,cold); allrows+=rows
    yearly={}
    for label, rr in [('year1_months1_12',rows[:12]),('year2_partial_months13_15',rows[12:])]:
        cash=sum(r['procurement_including_logistics_cash_RUB'] for r in rr)
        fund=sum(r['funding_cash_plus_delta_reserve_RUB'] for r in rr)
        yearly[label]={'posted_R':sum(r['posted_R'] for r in rr),
                      'procurement_cash_including_logistics_RUB':cash,
                      'cash_plus_delta_total_reserve_RUB':fund,
                      'annual_buffer_RUB':500000 if label.startswith('year1') else None,
                      'funding_with_annual_buffer_RUB':fund+500000 if label.startswith('year1') else None,
                      'no_queue_every_month':all(r['no_queue'] for r in rr),
                      'HR_combined_peak_hours':max(r['combined_HR_hours'] for r in rr),
                      'recognition_hours_by_role':{role:sum(r[role+'_recognition_hours'] for r in rr) for role in ['HR','manager','employee']},
                      'launch_hours_by_role':{role:sum(r[role+'_launch_hours'] for r in rr) for role in ['HR','manager','employee']},
                      'primary_QA_required_total_hours_existing_new_split_unknown':sum(r['primary_QA_total_hours'] for r in rr),
                      'IT_initial_hours':sum(r['IT_initial_hours'] for r in rr),
                      'IT_recurring_hours':sum(r['IT_recurring_hours'] for r in rr),
                      'year2_pass_claimed':False}
    scenarios[name]={'rows':rows,'budget_year_summaries':yearly}
first={'candidate_key':KEY,'classification':'Project assumptions/calculations, M05 unchanged. Not bank data or admission.',
       'launch_announcement':'2027-01-01','launch_date_is_assumption':True,
       'preannouncement_rewarded_work_hours':0,'preannouncement_observations':0,
       'existing_shop_m0_order':'Main case: M05 permitted m0 order, payment/receipt m1, opening stock still0. Organizational procurement is not a preannouncement contest achievement. No real bank inventory asserted. Cold shop without incoming order separately stressed.',
       'cohort_size':2400,'cohorts':[{'id':f'C{c}','initial_start':date(c,15),
                                    'first_four_cycles':[events(c+3*i) for i in range(4)]} for c in [1,2,3]],
       'promise_and_right_policy':'Before effort each monthly cohort receives max1.8m conditional ordinary promise. Observation closes start+3months day14, quality day28 at18:00 =>earned U; automatic posting day28 at19:00. No delay for smoothing. Separate special200k/month, announced day1, no before-announcement benefit.',
       'special_dates_in_rows':'Monthly maximum scenario concentrates special ready confirmations on day28, posting immediately. This is a scenario arrival pattern, not a rule to hold earlier confirmed special rights until month-end. Actual earlier confirmation creates U/available posting immediately under SLA; monthly cash maximum unchanged, daily delivery not proven by this CSV.',
       'source_and_quality_preparation':'Jan1 announcement; Jan2-14 synthetic tests, engineered project role benchmark, rules, deputies. Existing shop forecast order m0 is organizational preparation only. No rewarded employee historical work. C2/C3 training before their own starts.',
       'sampling_and_currency':'All issued R immediately converted/requested in stress. C is locked on request, redeemed only on actual receipt; pending orders remain in personal C and reserve. C/R transfers zero; no direct R services in rows. Normalized5000C baskets are model units, not mandatory SKU.',
       'cold_start':'Separate COLD_SHOP_STRESS: opening stock0, no m0 incoming order, lead1month =>zero receipts m1. Orders/requested rights preserved; no_queue fails early. Main case requires existing-shop m0 forecast order, as M05 permits; not real inventory claim.',
       'U_and_old_rights':'Confirmed/posting same month: U_peak explicit; U_close0 only scenario. Old unposted rights unknown, not extinguished. At posting outage keep U/committed F once, replace manual signed posting; no expiry.',
       'F_definition':'F contains conditional promises plus encumbered U; unencumbered residual alone expires quarterly. Maximum scenario residual expiry0; Fclose5.4m after ramp is unearned, not savings or personal right.',
       'reserve_definition':'max(0,0.194*(all new unredeemed personal rights+conditional F)-paid appropriate inventory), inventory credited once. Earned-only reserve and conditional increment separately. Initial old-right backing unknown/not manufactured.',
       'budget_boundary':'2027=m1..12. 2028=m13..15 partial only. C1 fourth right m13; C2 m14; C3 m15.15months extends required14 to include late tail. No full year2 pass.',
       'opening_old_C':160000000,'opening_old_R':40000000,'fixed_C_year':96000000,
       'M05_ref':'inputs/baseline.md #Машиночитаемые общие параметры M05-2026-10-31',
       'scenarios':scenarios}
dump('first-launch.json',first)
with (P/'first-launch.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)

workload={'HR_hours_monthly':[hr]*12,'manager_hours_monthly':[manager_award]*12,
          'manager_quality_plus_award_required_hours_monthly':[manager]*12,
          'employee_process_hours_monthly':[employee]*12,
          'IT_initial_hours':520,'IT_recurring_hours_year':144,
          'employee_useful_work_hours_year':None,
          'useful_work_note':'Ordinary paid useful production unknown; not silently counted as zero incremental work. Raw evidence capture is existing work only if verified; no separate employee reward dossier required.',
          'minutes_and_denominators':flow,'process_flow_is_not_access_cap':True,
          'launch_hours':{'HR':54,'manager':180,'employee':1800,'IT':520},
          'IT_initial_schedule':'120h in m1 before C1 Jan15 for tested signed register/spreadsheet calculation;200h m2 before C2 and200h m3 before C3 for replication/interface automation. No need for full520 before Jan15. Capacity/holiday calendar must be staffed, not assumed free.',
          'primary_QA_reconciliation':{'required_total_hours_month':800,'v1_total_hours_month':800,
              'verified_existing_source':None,'verified_existing_hours_month':None,
              'actual_existing_hours_month':None,'actual_incremental_hours_month':None,
              'no_reusable_existing_source_scenario_credit_hours_month':0,'no_reusable_existing_source_scenario_new_hours_month':800,
              'net_new_formula':'max(0,800-verified_reusable_existing_hours); total QA remains800, existing labor valued1500RUB/h, never free. Actual source split unknown; 800 new is explicit absent-source sensitivity, not base incremental cost/headcount claim.',
              'secondary_award_verification_hours_month':12,
              'team_QA_deduplication':'800h is comparable upper requirement for2400 distinct individual records x20. Actual requirement=sum(sample_size*minutes) over unique QA acts. One team act reused across members, not rescored per person; case n<20 reduces sample. No bank staffing mix asserted.',
              'common800_sensitivity':'If finance adds common800 to all candidates, remove same800 from this candidate incremental subtotal only, retaining total workload once. Do not add or erase800 twice.'},
          'manual_fallback_additional_h_month':{'HR':20,'manager':80,'employee':0},
          'manual_fallback_scope':'Complete source exists but export is unusable:60 group exports/reconciliation at20HR+80manager hours. Prospective independently signed operation/exposure/QA register; primary800 and secondary12 retained. Source entirely absent is the separately costed full source-creation fallback below, never claimed covered by80h.',
          'source_creation_fallback_additional_h_month':{'HR':0,'manager':700,'employee':1300},
          'source_creation_fallback_denominators':{'planning_cases_per_record':60,'records_month':2400,
              'employee_capture_minutes_case':.5,'independent_acceptance_minutes_case':.25,
              'exposure_rows_record':10,'employee_exposure_minutes_row':.25,'owner_exposure_minutes_row':.25,
              'formulas':'Employee144000*.5/60+24000*.25/60=1300; manager144000*.25/60+24000*.25/60=700. Add export fallback20HR+80manager AND primary800. Actual cases/exposure rows scale linearly;60/10 not access caps.'},
          'common_M05_basket_hours_excluded':True,
          'own_award_recusals_included':True,
          'capacity':'HR common220 unchanged. Stationary FULL_NEW fixed96 old20:151.1111 common+60=211.1111; fallback231.1111 fail. Manager/employee/IT capacity unknown.',
          'added_capacity_scenario':{'HR_extra_hours_month':20,'resource_RUB_month':20000,'replacement25pct_cash_RUB_month':5000,
              'condition':'Named independent alternate, funded scheduled20h; total staffing240 is a separate scenario, not M05 pass.'}}
rates={'HR':1000,'manager':1500,'employee':1000,'IT':2000}
stationary_cost=12*(hr*1000+manager_award*1500+employee*1000)+144*2000
workload['resource_costs_RUB']={'stationary_recognition':stationary_cost,
    'launch_one_off':54*1000+180*1500+1800*1000+520*2000,
    'primary_QA_component_stationary':800*12*1500,
    'stationary_quality_plus_award_required_total':stationary_cost+800*12*1500,
    'stationary_actual_incremental_total':None,
    'stationary_if_no_reusable_QA_source_incremental_total':stationary_cost+800*12*1500,
    'stationary_2x_labor':stationary_cost*2,
    'stationary_replacement25pct_additional_cash':stationary_cost*.25,
    'stationary_2x_plus25pct_replacement_resource':stationary_cost*2*1.25,
    'stationary_full_source_creation_fallback_excluding_unknown_incremental_QA':stationary_cost+12*(20*1000+780*1500+1300*1000),
    'stationary_full_source_creation_and_no_reusable_QA_scenario':stationary_cost+12*(20*1000+780*1500+1300*1000)+800*12*1500,
    'stationary_full_source_fallback_replacement25pct_cash_excluding_unknown_incremental_QA':(stationary_cost+12*(20*1000+780*1500+1300*1000))*.25,
    'first_launch_year1_recognition_and_one_off':660*1000+1263.2*1500+2882.4*1000+664*2000,
    'first_launch_year1_primary_QA_required_total_existing_new_unknown':7200*1500,
    'first_launch_year1_quality_plus_award_resource_required':660*1000+8463.2*1500+2882.4*1000+664*2000}
spec={'schema_version':1,'candidate_key':KEY,'parents':['CON-011@v1'],
      'classification':'All mechanism values design assumptions, calculations; frozen case facts only by locator; not independent financial admission.',
      'envelope_R_year':24000000,'currency':'R; R_to_C=1; no RUB redemption right',
      'N_eligible':7200,'eligibility':'Open objective role/task allocation including HR/managers, no admission list; all7200 financed. One person/source group/cycle, comparable strata <=100 split before effort.',
      'lower_tier':{'N_eligible':7200,'cycles_year':4,'award_R':500,'max_awards_person_year':4,
                    'formula':'7200*4*500','annual_max_R':14400000,
                    'qualification':'Current normalized Q>=1; exposure and rubric QA pass; no quota, no personal improvement condition.'},
      'contests':{'groups':'Design nominal180 comparable groups40, inside department; size1..100; sum unique eligible<=7200.',
                  'cycles_year':4,'group_pool_R_cycle_formula':'250*n_unique_eligible',
                  'top_tiers':[{'places':1,'share_group_pool':.8,'award_R_n40':8000}, {'places':1,'share_group_pool':.2,'award_R_n40':2000}],
                  'annual_max_R':7200000,'formula':'250*7200*4',
                  'ranking':'Current Q>=1.10, rank floor(100*Q+0.5)/100 descending; lower uses unrounded Q>=1.00. Individual/team mode fixed before effort.',
                  'team_rule':'Same full group pool250*n; teams occupy first/second slots8000/2000 at n40, NOT250*n_team cap. One team sum split by predeclared independent FTE shares; absent/unqualified members share unissued, not moved to others. All group/team/person awards together <=pool.',
                  'tie_rule':'A tie occupying ranks r..r+k-1 shares sum of prize slots at those ranks equally across all tied units, including beyond rank2. Then FTE division; floor final personal R; residual stays unissued. No lexical tie-break money.',
                  'small_groups':'Only1 registered competing eligible unit BEFORE results =>top0. Two+ registered units use both slots even if only1 qualifies (then first slot80% paid, second unissued). Fewer qualifying units leaves unoccupied slot unissued. Teams not split artificially to invent an opponent.',
                  'cross_department':'One benefitID, one owning department/source group; participating persons counted once in that group budget and cannot enter another ordinary group same cycle; shares sum<=1. No duplicate department award.',
                  'n40_eight_teams_five_example':{'pool_R':10000,'first_team_R':8000,'second_team_R':2000,'first_member_R':1600,'second_member_R':400,'team_member_cap_by_headcount':None}},
      'special':{'monthly_levels':[{'slots':32,'award_R':2500},{'slots':16,'award_R':7500}],
                 'annual_max_R':2400000,'monthly_max_R':200000,'personal_awards_year_max':2,'personal_R_year_max':15000,
                 'team_result_R_max':7500,'approval':'Independent benefit owner verifies; separate nonrecipient HR posts; HR/manager own benefit outside their reporting/control chain, named alternate. No recipient selects amount or exception.',
                 'allocation':'Within each prequalified level, timestamp of independent ready confirmation; exact timestamp tie shares occupied fixed slots of that level. Personal cap checked before assignment; next eligible record fills empty slot. No promise for every nomination; assigned awards are irrevocable rights.'},
      'stacking':{'base_plus_top':True,'special_plus_regular':'Only different benefitID or evidenced incremental benefit excluded from ordinary metric; no duplicate same benefit.',
                  'personal_top_R_cycle_cap':20000,'personal_all_channels_R_year_cap':97000,
                  'cap_formula':'4*500+4*20000+2*7500=97000; n<=100 makes top cap nonbinding. One lower/ordinary group/person/cycle; no cap savings used for funding.'},
      'annual_total_R':24000000,'monthly_calendar_R':[2000000]*12,
      'rights_calendar':{'lower_R':[1200000]*12,'top_R':[600000]*12,'special_R':[200000]*12,
          'definition':'Stationary, all cohorts already in operation. First-launch14months is separate; no preannouncement work. Monthly24m comparable policy, not observed issue.',
          'first_launch_json':'branches/B/first-launch.json','first_launch_csv':'branches/B/first-launch.csv','first_launch_months':15},
      'workload':workload,
      'operational_metrics_assumptions':{
          'reference':'Engineered role/time standard, synthetic calibrated examples before effort; no bank history assumed. Q weighted ratios of standard units/available production hour, strata complexity/channel/shift fixed before effort; production downtime/help hours independently verified excluded. Freeze for year; only future periods change standards.',
          'support':{'weights':[1,2,4],'min_units':100,'min_independent_cases':20,'min_exposure_days':10,'QA_sample_n':20,'QA_mean_min':97,'repeat_fraction_all_cases_max':.05},
          'backoffice':{'weights':[1,3,5],'min_units':80,'min_independent_cases':20,'min_exposure_days':10,'QA_sample_n':20,'QA_mean_min':98,'return_fraction_all_cases_max':.02},
          'IT_team':{'weights':[1,2,4],'min_closed_cases':8,'min_person_exposure_days':10,'QA_sample_n_formula':'min(20,n)','QA_mean_min':98,'reopen_14day_fraction_all_max':.05,'SLA_fraction_all_min':.95},
          'QA_rubric':{'scale':'0..100, not binary','case_score':'max(0,100-2*minor_error_count-10*major_error_count)',
                       'critical_error':'Any independently verified critical regulatory/client/security error in entire registry or14day window =>fail, regardless of mean.',
                       'sampling':'All cases if n<=20; otherwise20 lowest SHA256(windowID,benefitID,caseID,published seed); seed fixed by independent owner after case registry frozen; no replacement samples.',
                       'aggregation':'Arithmetic mean of case scores, no rounding before threshold. Minor/major checklist and critical taxonomy fixed with process safety owner before effort; each defect counted once at highest severity.',
                       'error_correction':'Independent owner corrects before/after+reason+signature, same seed/sample rule re-executed; disputes preserve contingent/provable rights, no automatic zero for unavailable data.'}},
      'data_requirements':['Full eligible/assignment/exposure/completion registry with independent owner; assumed source/API not confirmed.',
          'Primary QA20/sample independent cases per record max; total800h required, existing source reuse not verified.',
          'Before launch synthetic tests/source register; after effort unavailable data =>restore and retain provable U/conditional disputed claim, no zero by missing file.',
          'Edits before/after/reason/time/other signer, archive query/hash/sample seed and full denominator.'],
      'no_self_award_controls':['Self factual report allowed; recipient chooses neither level nor amount.',
          'Data verifier, benefit approver, posting operator independent of recipient benefit; HR/manager own records go to external-to-control-chain owner and alternate nonrecipient HR.',
          'Rules/corrections/own exceptions cannot be approved by recipient; second independent signer, immutable audit trail; own checks costed in12recusals/month.'],
      'assumptions':[{'id':'B01','parameter':'lower_R_person_cycle','value':500}, {'id':'B02','parameter':'top_R_eligible_cycle','value':250},
          {'id':'B03','parameter':'special_R_month','value':200000},{'id':'B04','parameter':'records_month_stationary','value':2400},
          {'id':'B05','parameter':'source_QA_existing_reusable_hours','value':None}, {'id':'B06','parameter':'source_QA_planning_reuse_credit_hours','value':0}],
      'finance_handoff':{'M05':'unchanged; inputs/baseline.md machine readable block',
          'actual_and_Rmax':24000000,'controls_R':[12000000,24000000,36000000],
          'years':[1,2,3],'required_scenarios':'All12 frozen M05 scenarios, fixed96/144, budget30/34; independent finance required. R12 cannot finance this lower+top/special unchanged.',
          'shared_reference':'M05 fixed96 old20 E24: stationary expected cash23.668m, total cash+deltaReserve+buffer31.540m; full-new cash31.040m, total31.540m. Conditional area34m, not30. Fixed144/old35/price20/full-old stress fail as frozen.',
          'no_admission':'Only reproducible local amount/calendar/workload checks performed. Budget gate remains for independent analyst; no_queue assessed separately for main and cold-shop stress.'}}
dump('finance-spec-011.json',spec)

def top(n, units, competing_units=None):
    # units=[(Q, [FTE fractions])]; nonqualifying units omitted after objective qualification.
    if (len(units) if competing_units is None else competing_units)<2: return [0 for _,ss in units for _ in ss]
    units=[u for u in units if u[0]>=1.10]
    units=sorted(units,key=lambda x:-math.floor(x[0]*100+.5)); out=[]; pos=1; i=0
    while i<len(units):
        q=math.floor(units[i][0]*100+.5); j=i
        while j<len(units) and math.floor(units[j][0]*100+.5)==q: j+=1
        tied=j-i; amount=sum({1:200*n,2:50*n}.get(r,0) for r in range(pos,pos+tied))/tied
        for _,shares in units[i:j]:out.extend(math.floor(amount*s+1e-9) for s in shares)
        pos+=tied;i=j
    assert sum(out)<=250*n
    return out
tests=[]
for name,n,uu,expected in [
    ('40_people_8_teams5',40,[(1.8-i*.05,[.2]*5) for i in range(8)], [1600]*5+[400]*5+[0]*30),
    ('all8_teams_tie',40,[(1.2,[.2]*5) for i in range(8)], [250]*40),
    ('all40_individuals_tie',40,[(1.2,[1]) for i in range(40)], [250]*40),
    ('three_way_boundary_tie',40,[(1.2,[1]) for i in range(3)],[3333]*3),
    ('unequal_team_3_7',10,[(1.3,[1/3]*3),(1.2,[1/7]*7)],[666]*3+[71]*7),
    ('singleton',1,[(1.2,[1])],[0]),
    ('two_individuals',2,[(1.3,[1]),(1.2,[1])],[400,100]),
    ('n10_individual',10,[(1.3,[1]),(1.2,[1])],[2000,500]),
    ('n20_individual',20,[(1.3,[1]),(1.2,[1])],[4000,1000]),
    ('n60',60,[(1.3,[1]),(1.2,[1])],[12000,3000]),
    ('n100_cap',100,[(1.3,[1]),(1.2,[1])],[20000,5000]),
    ('cross_department_single_source',40,[(1.3,[.25,.75]),(1.2,[1])],[2000,6000,2000])]:
    result=top(n,uu);assert result==expected,(name,result,expected)
    tests.append({'test':name,'n':n,'personal_top_R':result,'paid_R':sum(result),'pool_R':250*n,'residual_unissued_R':250*n-sum(result),'pass':True})
one=top(40,[(1.2,[1])],competing_units=40)
assert one==[8000]
tests.append({'test':'40registered_only1qualifies','n':40,'personal_top_R':one,'paid_R':8000,'pool_R':10000,'residual_unissued_R':2000,'pass':True})
near=top(40,[(1.09999,[1]),(1.2,[1])])
assert near==[8000]
tests.append({'test':'unrounded_Q1.09999_not_top_even_if_rounds1.10','personal_top_R':near,'registered_units':2,'pass':True})
def lower(q, qa, n, min_n=20, threshold=97, exposure=10, critical=0):
    return 500 if q>=1 and qa>=threshold and n>=min_n and exposure>=10 and critical==0 else 0
boundaries=[('newcomer_at_level',1,98,20,500),('stable_same_level',1,98,20,500),
            ('Q_unrounded_below1',.99999,98,20,0),('n19',1.2,100,19,0),
            ('QA_below97',1.2,96.9999,20,0),('QA_exact97',1,97,20,500)]
lower_tests=[]
for name,q,qa,n,want in boundaries:
    got=lower(q,qa,n);assert got==want
    lower_tests.append({'test':name,'Q':q,'QA':qa,'n':n,'lower_R':got,'pass':True})
assert lower(2,100,60,critical=1)==0
assert 1.09999<1.1 # top qualification uses unrounded Q, irrespective of rounded ranking key
qa_tests=[]
for n, sample, score, support_ok, back_ok in [(10,10,98,False,False),(20,20,98,True,True),(60,20,97,True,False)]:
    qa_tests.append({'n_registry':n,'n_sample':sample,'sample_mean':score,'support_lower_Q1_R':500 if support_ok else 0,
                     'backoffice_lower_Q1_R':500 if back_ok else 0,
                     'IT_team_eligible_member_lower_Q1_R':500 if score>=98 and n>=8 else 0,
                     'assumption':'Other minima/exposure/critical0/returns/SLA pass; no top without Q>=1.10.'})
stress={'stationary_full_new_baskets':(40000000+96000000+24000000)/12/5000,
        'synchronous_quarter_peak_baskets':(40000000/12+96000000/12+6000000)/5000,
        'full_new_region80_S2_baskets':(40000000+96000000+24000000)/12/5000*.8,
        'stationary_common_HR_hours':80+(40000000+96000000+24000000)/12/5000*(.02+.2/30),
        'stationary_HR_total':80+(40000000+96000000+24000000)/12/5000*(.02+.2/30)+hr,
        'stationary_HR_fallback_total':80+(40000000+96000000+24000000)/12/5000*(.02+.2/30)+hr+20,
        'all7200_special_and2400_appeals_HR_extra_above_planned':(7200-200)*4/60+(2400-120)*6/60,
        'all7200_special_and2400_appeals_manager_extra_above_planned':(7200-200)*10/60+(2400-120)*8/60,
        'all7200_special_and2400_appeals_employee_extra_above_planned':(7200-200)*6/60+(2400-120)*5/60}
checks={'candidate_key':KEY,'status':'local self-check only; independent finance/evidence pending',
        'amount_tests':tests,'lower_boundary_tests':lower_tests,'QA_tests':qa_tests,
        'controls_tests':[{'case':'HR_or_manager_own_data_approval_or_posting','required':'Reject self sign; other independent verifier and poster, no own exception','status':'design specified; bank access roles not tested'},
                          {'case':'unusable_export_after_proven_right','required':'Preserve U and reserve; restore or signed alternate posting, notQ0','status':'design specified; bank source not tested'},
                          {'case':'posting_outage_month2mR','U_R':2000000,'encumbered_F_R':2000000,'free_F_R':0,'expiry_of_right_R':0,'counted_rights_R':2000000,'status':'ledger identity; not2xU+F'}],
        'annual_sums':{'lower_R':14400000,'top_R':7200000,'special_R':2400000,'total_R':24000000},
        'calendar_checks':{'rows_per_scenario':15,'preannouncement_rewarded_work':0,'first_year_posted_R':18600000,
             'first_year_promised_R':24000000,'first_year_future_unearned_R':5400000,
             'C1_fourth_right':date(13,28),'C2_fourth_right':date(14,28),'C3_fourth_right':date(15,28),
             'year2_partial_not_pass':True,'C_R_F_balances_all_rows_pass':True},
        'stress':stress,'QA_v1_v2':{'v1_primary_total_h_month':800,'v2_primary_total_h_month':800,
            'new_source_credit':0,'secondary_award_check_h_month':12,'primaryQA_not_in_common_M05_baskets':True},
        'critical_limits':['Main launch requires existing-shop M05 m0 incoming order; cold-shop stress with no m0 order fails no_queue; requests/rights/stock/reserves retained.',
            'Fallback/full workload and2x labor exceed220h. Named +20h staffing scenario is not baseM05.',
            'Region80 and synchronized quarter full-new fail physical capacity; no silent right delay.',
            'Actual QA source and bank quality thresholds unknown.20sample1minute is planning assumption, not safety certification.']}
assert sum(spec['monthly_calendar_R'])==spec['annual_total_R']==24000000
assert hr==60
assert all(r['conditional_unearned_close_R']==5400000 for r in allrows if r['month']>=3)
assert all(len(s['rows'])==15 for s in scenarios.values())
dump('self-check-011.json',checks)

assumptions=[
('B01','lower',500,'R/person/quarter','new_design','concept-011.md §2; finance-spec-011.json lower_tier','Guarantee all7200, not observed success'),
('B02','top_pool',250,'R/unique eligible/cycle','new_design','finance-spec-011.json contests','Nominal n40 pool10000; no team headcount cap'),
('B03','special',200000,'R/month','new_design','finance-spec-011.json special','32x2500+16x7500; finite places'),
('B04','normal_month_records',2400,'persons/month','new_design','finance-spec-011.json workload','60 groups40, quarterly three cohorts'),
('B05','primary_QA',800,'total required hours/month at2400x20x1min','design_requirement_existing_new_split_unknown','finance-spec-011.json workload.primary_QA_reconciliation','Existing source unknown; valued1500RUB/h; NOT all incremental hiring/cash'),
('B06','QA_rubric','100-2minor-10major','points/case then mean of sample','new_design','finance-spec-011.json operational_metrics_assumptions.QA_rubric','Not binary; independent scoring and whole-registry critical barrier'),
('B07','QA_source_reuse','unknown; absent-source sensitivity credits0','hours/month reusable existing QA','unknown_with_explicit_sensitivity','finance-spec-011.json workload.primary_QA_reconciliation','Not assertion no QA exists; actual new max(0;800-existing) unknown; total800 valued'),
('B08','metrics_and_reference','see operational_metrics_assumptions','role standard units/hour','new_design','concept-011.md §2','Engineered synthetic benchmark before effort; no historical bank observations'),
('B09','full_process_flow','200special/120appeals/72corrections/12recusals','requests/month stationary','new_design_forecast_not_access_cap','finance-spec-011.json workload.minutes_and_denominators','All unsuccessful requests included; all-eligible stress separate'),
('B10','workload','HR60/manager106.2667/employee113.6; QA800 total separate','hours/month stationary award procedure additional to M05','calculation_from_design','finance-spec-011.json workload','QA existing/new split unknown, joint manager requirement906.2667; source creation separately measured'),
('B11','startup_hours','HR54/manager180/employee1800/IT520','hours first launch, all after2027-01-01','new_design','first-launch.json rows','IT120/200/200 in m1/m2/m3 before respective starts; tested manual batch readyC1; named capacity unknown'),
('B12','start_dates','2027-01/02/03 day15','three2400 cohorts, 3calendar-month windows','new_design','first-launch.json cohorts','Rules/promise day14, close plus3months day14, quality day28 18:00, posting day28 19:00'),
('B13','fallback','export HR20/manager80; source creation manager700/employee1300','additional hours/month at144000cases+24000exposure rows','new_design','finance-spec-011.json workload.manual_fallback_scope; source_creation_fallback_denominators','Source creation additional to export and QA800; scales with actual counts; >220 base capacity'),
('B14','regional_low_values','100/250/500C','candidate useful catalogue denominations','unverified_design_requirement','concept-011.md §5','No claim catalogue exists; obtain supply/terms before promised value'),
('B15','first_launch_model','existing shop m0 order; cold shop separate stress','15months, fixed96 old20, full/expected/cold','calculation_under_frozen_M05','first-launch.json','C3 fourth right m15; no fabricated opening inventory'),
('B16','fixed_and_currency','unchanged','annual fixed96/144; personal C/R/U survive','common_frozen_fact_and_scenarios','inputs/baseline.md M05 machine readable; evidence C01/E09','M05 values are assumptions; case rules PDF10-12 facts'),
('B17','additional_HR_capacity',20,'hours/month separate staffing scenario','new_design','finance-spec-011.json workload.added_capacity_scenario','20kRUB resource/month;25pct replacement5k; M05 remains220'),
('B18','lead_and_receipt','1month;100unit regional batches','M05; request lock before receipt redemption','common_frozen_assumption','inputs/baseline.md M05 common','Main m0 order paid m1; cold stress m1 receipts0; no rewarded work before announcement'),
]
with (P/'assumptions-011.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['id','parameter','value','unit_period_denominator','type','source_locator','validation_limit']);w.writerows(assumptions)
print(json.dumps({'candidate_key':KEY,'amount_tests':len(tests),'lower_tests':len(lower_tests),
                  'months_per_scenario':15,'annual_R':24000000,
                  'award_procedure_hours':[hr,manager_award,employee],
                  'primary_QA_max_hours':800,'award_resource_RUB_year':stationary_cost},ensure_ascii=False))
