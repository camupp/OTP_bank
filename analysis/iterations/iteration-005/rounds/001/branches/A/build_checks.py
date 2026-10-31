"""Branch-owned arithmetic; reads only five frozen inputs. No shared writes."""
import json, csv, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]/'inputs'
text=(BASE/'baseline.md').read_text()
M=json.loads(text.split('```json\n',1)[1].split('\n```',1)[0])
C=M['common']

def run(E,fixed,scenario):
    o=scenario['overrides']; old=o.get('old_annual_use',C['old_annual_use']); fu=o.get('new_fixed_C_use',C['new_fixed_C_use']); ru=o.get('new_R_use',C['new_R_use'])
    price=o.get('price_multiplier',1); cost=940*price+30; unit=cost/5000
    shares=o.get('region_demand_shares',[.6,.4]); inv=[0.,0.]; oldC=160e6; oldR=40e6; newC=newR=reserve=0.; out=[]
    for year in range(1,4):
        openC=oldC+newC; openR=oldR+newR; invopen=sum(inv)
        rcal=[E/12]*12 if o.get('R_calendar')!='quarter_end' else [0,0,E/4]*4
        olduseC=(oldC+newC)*old; olduseR=(oldR+newR)*old
        demand_old=olduseC+olduseR
        oldcal=[demand_old/12]*12
        if o.get('old_january_share') is not None: oldcal=[demand_old*.5]+[demand_old*.5/11]*11
        purchased=0.; redeemed_C=0.; maxd=maxs2=maxhr=0.; cap=True
        for m in range(12):
            d=(oldcal[m]+fixed*fu/12+rcal[m]*ru)/5000
            redeemed_C+=d*5000
            maxd=max(maxd,d); maxs2=max(maxs2,d*shares[1]); maxhr=max(maxhr,80+d*(.02+.2/30))
            for j,s in enumerate(shares):
                q=d*s; cap &= q<=[1800,1200][j]+1e-8
                buy=max(0,math.ceil((q-inv[j]-1e-8)/100)*100)
                inv[j]+=buy-q; purchased+=buy
        oldC*=1-old; oldR*=1-old
        newC=newC*(1-old)+fixed*(1-fu); newR=newR*(1-old)+E*(1-ru)
        invvalue=sum(inv)*cost; target=max(0,(newC+newR)*unit-invvalue)
        cash=purchased*cost; required=cash+target-reserve+500000
        # Independent conservation, with all used R converted 1:1 then redeemed in C.
        totalclose=oldC+oldR+newC+newR
        converted_R=olduseR+E*ru
        assert abs((openR+E-converted_R)-(oldR+newR))<1e-5
        assert abs((openC+fixed+converted_R-redeemed_C)-(oldC+newC))<1e-5
        assert abs(openC+openR+fixed+E-redeemed_C-totalclose)<1e-5
        assert abs(invopen+purchased-redeemed_C/5000-sum(inv))<1e-6
        assert abs(cash-(redeemed_C/5000+sum(inv)-invopen)*cost)<1e-5
        out.append(dict(scenario=scenario['id'],E_R=E,fixed_C=fixed,year=year,cash_RUB=round(cash,6),reserve_open_RUB=round(reserve,6),reserve_close_RUB=round(target,6),required_including_buffer_RUB=round(required,6),budget30_pass=required<=30e6+1e-6,budget34_pass=required<=34e6+1e-6,personal_C=round(oldC+newC,6),personal_R=round(oldR+newR,6),new_rights_C_R=round(newC+newR,6),paid_inventory_units=round(sum(inv),6),max_baskets_month=round(maxd,6),max_S2_baskets_month=round(maxs2,6),basket_capacity_pass=cap,common_HR_peak_hours=round(maxhr,6),common_HR220_pass=maxhr<=220))
        reserve=target
    return out

rows=[]
for E in [12e6,16.8e6,24e6,36e6]:
    for fixed in M['fixed_C_cases_year']:
        for scenario in M['scenarios']: rows+=run(E,fixed,scenario)
with (ROOT/'arithmetic-checks.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# Exact frozen controls, not hidden imports from previous writing models.
control={(r['fixed_C'],r['E_R'],r['scenario']):r for r in rows if r['year']==1}
for key,cash in {(96e6,12e6,'EXPECTED'):21340000,(96e6,24e6,'EXPECTED'):23668000,(144e6,24e6,'FULL_NEW'):40449000}.items():
    assert abs(control[key]['cash_RUB']-cash)<1e-5,(key,control[key]['cash_RUB'],cash)
assert 7200*4*500+7200*4*62.5+12*50000==16800000

# Process flow is separate from M05 basket handling. Hours are incremental to M05.
for number in [11,12]:
    extraHR=0 if number==11 else 8
    extraMgr=0 if number==11 else 20
    expectedHR=10+10+40*4/60+48*6/60+24*5/60+12*5/60+6+10*10/60+extraHR
    fullHR=10+10+100*4/60+120*6/60+72*5/60+12*5/60+6+10*10/60+extraHR
    expectedMgr=2400*20/60+30+240*3/60+40*10/60+12*5/60+48*8/60+24*5/60+12*8/60+10*20/60+extraMgr
    fullMgr=2400*20/60+30+240*3/60+100*10/60+12*5/60+120*8/60+72*5/60+12*8/60+10*20/60+extraMgr
    expectedEmp=2400*2/60+40*6/60+48*5/60+24*3/60
    fullEmp=2400*2/60+100*6/60+120*5/60+72*3/60
    initHR=54+(30 if number==12 else 0);initMgr=180+(120 if number==12 else 0)
    it=520 if number==11 else 680; recurring=144 if number==11 else 240
    costs={}
    for label,h,m,e in [('expected',expectedHR,expectedMgr,expectedEmp),('full_flow',fullHR,fullMgr,fullEmp)]:
        annual=dict(HR=h*12+initHR,manager=m*12+initMgr,employee=e*12+1800,IT=it+recurring)
        resource=annual['HR']*1000+annual['manager']*1500+annual['employee']*1000+annual['IT']*2000
        costs[label]=dict(hours_year1=annual,resource_RUB_year1=round(resource,2),double_labor_RUB_year1=round(resource*2,2),replacement25pct_RUB_year1=round(resource*.25,2),double_labor_plus_replacement25pct_RUB_year1=round(resource*2*1.25,2))
    d=ROOT/f'CON-{number:03}-v1'; d.mkdir(exist_ok=True)
    spec={
      'schema_version':1,'candidate_key':f'CON-{number:03}@v1','classification':'Design assumptions and calculations, not bank observations; M05 unchanged.',
      'currency':'R; R_to_C=1; RUB conversion is scenario procurement cost, not cash redemption',
      'envelope_R_year':24000000,'selected_envelope_R':24000000,'annual_total_R':16800000,'unused_envelope_R':7200000,
      'N_eligible':7200,'eligibility':'All staff incl HR/managers in objectively defined comparable role/task strata with independent logs; no prescreening by expected success. Exposure conditions affect qualified result, not financing denominator. Four rights/year per employee maximum; all7200 reserved.',
      'lower_tier':{'N_eligible':7200,'cycles_year':4,'award_R':500,'max_awards_person_year':4,'base_formula':'7200*4*500','annual_max_R':14400000,'qualification_rule':'concept.md section2; every qualifying employee receives500, no places/lottery'},
      'base_formula':'N_all_eligible*4*500=14400000R/year',
      'contests':{'groups':'Design:180 comparable strata x40; fund invariant for arbitrary group sizes with sum n_g<=7200. Groups stay inside department; no cross-profession raw KPI ranking.', 'cycles_year':4,'group_pool_R_cycle_formula':'62.5*n_g; nominal40 gives2500R. n_g includes all eligible before success, not only applicants.', 'top_tiers':([{'places':1,'share_group_pool':.8,'nominal_award_R_n40':2000},{'places':1,'share_group_pool':.2,'nominal_award_R_n40':500}] if number==11 else [{'lane':'progress','share_group_pool':.5,'places':2,'split':[.8,.2]},{'lane':'stable_high','share_group_pool':.3,'places':2,'split':[.8,.2]},{'lane':'new_no_base','share_group_pool':.2,'places':2,'split':[.8,.2]}]),'formula':'sum_g(62.5*n_g)*4 <=1800000','annual_max_R':1800000,'tie_rule':'Split sum of occupied tied prize slots equally among tied employees; ties spanning unpaid boundary split only paid slots; no added funds. Round down to whole R, residue unissued.', 'small_groups':'n=1 no top opponent: top unissued; n=2+ same pool rule; unpublished personal statements. No group pool reallocation after effort.', 'team_rule':'Operational team mode if individual attribution unsafe: team fund <=62.5*n_members, 80/20 by team ranks, shares fixed by contracted FTE before period; all team shares together <=group pool. One membership for one result; cross-department fund portions sum once. Individual baseline500 only once per person/cycle.'},
      'top_tiers_formula':'4*62.5*sum(n_g)<=1800000R/year',
      'special':{'monthly_levels':[{'slots':8,'award_R':2500},{'slots':4,'award_R':7500}],'special_maximum':'12*(8*2500+4*7500)=600000R/year','annual_max_R':600000,'monthly_max_R':50000,'personal_awards_year_max':2,'personal_R_year_max':15000,'team_result_R_max':7500,'approval':'Other authorized benefit owner verifies ID, actual outcome and quality; other HR posts. Manager own contribution: peer/executive outside recipient reporting dependency; HR own: nonrecipient HR deputy + business benefit owner. Named alternate; recipient cannot pick amount or exception.','scarcity':'Finite recognition, no guarantee for all special nominations. Ready verified records ordered by confirmation timestamp then benefitID; published remaining fund. Same-value tied timestamp divides remaining slot without enlarging fund; no earned award revoked.'},
      'special_maximum':'600000R/year',
      'stacking':{'base_plus_top':True,'special_plus_regular':'Only distinct benefitID or independently evidenced incremental benefit excluded from ordinary metric; same benefit cannot be paid in two channels. Fallback not a second base.', 'personal_top_R_cycle_cap':2500,'personal_all_channels_R_year_cap':27000,'team_result_special_R_cap':7500,'maximum_formula':'base2000 + top10000 + special15000=27000/person/year. Any excess top share unissued; whole fund reserve does not rely on cap savings.','salary_KPI':'Good work within duties can qualify; performance bonus already paying same benefit is declared. If monetary duplicate exists no special award; ordinary recognition is announced as distinct small recognition, no salary bonus formula altered.'},
      'monthly_calendar_R':[1400000]*12,
      'rights_calendar':{'lower_R':[1200000]*12,'top_R':[150000]*12,'special_R':[50000]*12,'cohorts':'3 equal administrative calendars of2400, 4 rolling90-day observations/person/year. Everyone eligible every quarter; cohorts are not competitive admission or annual rotation. Cohorts set before effort, equal exposure rules. Prelaunch90-day observation after rules published; operating-year model includes full12 months of rights. Startup cannot claim faster accrual.', 'earned':'Observation closes15th; quality/reopen window ends29th -> confirmed right29th. Data posting by next working day; requests and immediate certificate access after posting, merch <=30days when preordered. Dates are proposed service standards.', 'full_unposted_stress_R_one_quarter':4200000,'unposted_control':'At delay keep confirmed rights U separate from F; no expiration, reserve includes U once. Contingency signed dated claim and authorized alternative posting, no conversion of old earned rights into next-quarter F.'},
      'expected_award_flow_not_M05':{'lower_success_fraction':.6,'top_used_fraction':.75,'special_approved_monthly':{'small':6,'large':2},'monthly_expected_posted_R':862500,'annual_expected_posted_R':10350000,'note':'Process demand forecast only. M05 EXPECTED redemption still funds/issues maximum16.8mR and uses new_R_use100%; no guarantee financed by nonparticipation.'},
      'workload':{'HR_hours_monthly':[expectedHR]*12,'manager_hours_monthly':[expectedMgr]*12,'employee_process_hours_monthly':[expectedEmp]*12,'full_flow_HR_hours_monthly':[fullHR]*12,'full_flow_manager_hours_monthly':[fullMgr]*12,'full_flow_employee_process_hours_monthly':[fullEmp]*12,'IT_initial_hours':it,'IT_recurring_hours_year':recurring,'IT_recurring_hours_monthly':[recurring/12]*12,'employee_useful_work_hours_year':None,'employee_useful_work_note':'Ordinary paid work is not invented incremental labor. Actual useful work hours measured in pilot; process hours above never substitute for useful work.', 'prelaunch_hours':{'HR':initHR,'manager':initMgr,'employee':1800,'schedule':'Two months before operating year: half each month; separate90-day observation after announcement. These hours added to year1resource cost, not omitted.'},'minutes_and_denominators':{'monthly_observation_records':2400,'monthly_groups_exported':60,'HR_export_min_group':10,'manager_export_min_group':30,'HR_batch_min_record':.25,'primary_quality_cases_per_employee_record':20,'primary_quality_minutes_per_case':1,'primary_quality_manager_hours_month':800,'QA_sample_records':240,'manager_QA_min_record':3,'special_requests_expected_full':[40,100],'HR_special_min_request':4,'manager_special_min_request':10,'other_approver_min_awarded_special':5,'awarded_special_max_month':12,'appeal_requests_expected_full':[48,120],'HR_appeal_min':6,'manager_appeal_min':8,'employee_appeal_min':5,'corrections_expected_full':[24,72],'HR_manager_correction_min_each':5,'employee_correction_min':3,'own_award_recusals_month':12,'HR_recusal_min':5,'other_manager_recusal_min':8,'HR_fixed_admin_h_month':6,'rule_changes_groups_month':10,'HR_rule_min':10,'manager_rule_min':20,'employee_statement_min_record':2,'employee_special_request_min':6,'extra_baseline_HR_h_month':extraHR,'extra_baseline_manager_h_month':extraMgr,'prelaunch_HR_rules_h':30+(30 if number==12 else 0),'prelaunch_HR_training_h':24,'prelaunch_manager_rules_h':90+(120 if number==12 else 0),'prelaunch_manager_training_h':90,'prelaunch_employee_training_min_person':15},'manual_fallback_additional_h_month':{'HR':20,'manager':80,'employee':0},'high_flow_is_assumption_not_theoretical_request_bound':True,'all_eligible_requests_peak':{'special_requests_month':7200,'ordinary_appeals_month':2400,'HR_extra_hours_above_full_flow':(7200-100)*4/60+(2400-120)*6/60,'manager_extra_hours_above_full_flow':(7200-100)*10/60+(2400-120)*8/60,'employee_extra_hours_above_full_flow':(7200-100)*6/60+(2400-120)*5/60,'capacity':'Fail220. Not promised staffed capacity; preserves earned ordinary rights, no contingent special reward promised to every nomination.'},'process_includes_unsuccessful_requests':True,'common_M05_basket_hours_excluded':True,'resource_costs':costs,'capacity':'Combined with common M05 HR220h/month. Regional1800/1200 baskets unchanged. Manager/employee/IT available hours unknown: numeric requirement is not evidence of capacity.'},
      'data_requirements':['Immutable exported assignment, taskclass, actual available exposure and completion/quality logs; assumed source not confirmed API.','Freeze complexity weights and role benchmark before period; archive query version, hash and full denominator.','Independent data owner approves corrections with before/after, reason, timestamp; recipient cannot confirm own logs.','Monthly crosscheck 10% records + all exceptions, sample independence and delayed defects; external to subject manager if subject is manager/HR.','If historical log absent: prospectively signed register for whole period with independent owner and QA; no unsupported metric earns right, no discretionary replacement. Bank data failure preserves proved or reconstructible earned right.'],
      'no_self_award_controls':['Self nomination allowed as factual report only, no rate/level choice.','Automatic formula runs from other-owned locked data; dual control on recipient-admin own data and posting.','No ad hoc recipient exception; future rules approved by methodology owner and independent HR. Named deputies for conflict or absence.'],
      'M05_checks':{'source':'inputs/baseline.md frozen machine-readable M05 block','results_csv':'branches/A/arithmetic-checks.csv','scenario_count_in_csv':12,'E_values_R':[12000000,16800000,24000000,36000000],'years':[1,2,3],'fixed_C':[144000000,96000000],'budgets_RUB':[30000000,34000000],'note':'E12/24/36 are common scale controls; actual candidate max16.8m, invalid within E12. They are not altered lower-tier promises. Actual guarantee only selectedE24 with16.8m allocation before effort. No financial self-admission; independent finance check required.'},
      'assumptions':[{'id':'A01','value':500,'unit':'R/person/quarter','type':'design'},{'id':'A02','value':62.5,'unit':'R/eligible group member/quarter top pool','type':'design'},{'id':'A03','value':50000,'unit':'R/month special fund','type':'design'},{'id':'A04','value':2400,'unit':'eligible observations completed/month','type':'design capacity requiring equal calendars'},{'id':'A05','value':.6,'unit':'fraction lower success forecast','type':'process assumption not financing'},{'id':'A06','value':.75,'unit':'fraction top used forecast','type':'process assumption not financing'}]
    }
    (d/'finance-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    with (d/'assumptions.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','parameter','value','unit_period_denominator','type','source_locator','validation'])
        for a in spec['assumptions']:w.writerow([a['id'],a['type'],a['value'],a['unit'],'new_design_assumption','concept.md sections2/4','pilot + independent finance'])
        w.writerow(['M05','all_shared_parameters','unchanged','see frozen baseline M05 block','common_frozen_assumptions','inputs/baseline.md #Machine-readable common parameters','control rows in arithmetic-checks.csv'])
        w.writerow(['A07','workload_all_components','see finance-spec.workload','minutes per request/group/person; hours/year','new_design_assumptions','finance-spec.json workload.minutes_and_denominators','time and motion in pilot'])
        w.writerow(['A08','metric_weights_quality_exposure','see concept section2','per comparable role per90days','new_design_assumptions','concept.md section2','audit comparability before launch'])
        w.writerow(['A09','newcomer_high_base_rules','see concept section2','per person per90days','new_design_assumptions','concept.md section2','counterexamples and pilot'])
        w.writerow(['A10','catalog_access_SLA','certificate immediate; merch30days','after posted right; stock ordered1month before','new_design_assumption','concept.md section5','regional dry run; not verified catalogue'])
    # Candidate workload overlap under selected max; budget result remains a calculation, not authorization.
    selected=[r for r in rows if r['E_R']==16.8e6]
    overlap=[]
    for r in selected:
        combined=r['common_HR_peak_hours']+fullHR
        overlap.append({'scenario':r['scenario'],'fixed_C':r['fixed_C'],'year':r['year'],'full_HR_peak_hours':round(combined,6),'HR220_pass':combined<=220,'full_flow_manual_fallback_HR_peak_hours':round(combined+20,6),'manual_HR220_pass':combined+20<=220,'double_all_labor_HR_peak_hours':round(combined*2,6),'double_HR220_pass':combined*2<=220})
    spec['full_new_synchronous_quarter_peak']={'full_R_at_quarter_end':4200000,'baskets_month':(40e6/12+96e6/12+4.2e6)/5000,'S1_baskets':1864,'S2_baskets':1242.6666666666667,'physical_capacity_pass':False,'HR_peak_with_full_candidate':80+((40e6/12+96e6/12+4.2e6)/5000)*(.02+.2/30)+fullHR,'note':'Extra FULL_NEW check; frozen QUARTER_END_R uses expected fixed60%, not full-new. Rights not delayed into a queue.'}
    (d/'finance-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    (d/'workload-overlap.json').write_text(json.dumps(overlap,ensure_ascii=False,indent=2)+'\n')
summary={'status':'arithmetic_verified_not_financial_admission','csv_rows':len(rows),'frozen_control_rows_match':True,'annual_max_R':16800000,'monthly_sum_matches':sum([1400000]*12)==16800000,'all_eligible_lower_max_R':14400000,'top_max_R':1800000,'special_max_R':600000,'candidate_count':2,'balance_assertions':'C/R separately, combined rights, inventory, cash/issuance cost across288rows','checks':['Full eligible guarantee, no success-probability funding','fixed96/144 and budgets30/34 with years1-3; expected/fullnew/old35/price20/fullold/R60/R0/quarter/Jan/region','Three frozen cash controls exactly matched; local scenario calculations do not replace coordinator finance','Single-person27000 annual cap does not reduce maximum reserve; tied slots never multiply fund','Quality/no-self/data fallback counterexamples in concept.md'],'unresolved':['Actual data/group sizes/benchmarks/exposure and capacity unknown','Actual cash ringfencing and old/unposted rights unknown','Quarter-synchronous, regional80, Jan and 2x labor can fail; no queue declared saving','Usefulness of500R and little small-group top amounts requires regional catalogue/pilot test']}
(ROOT/'self-check.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'rows':len(rows),'max_R':16800000,'fullnew_fixed96_year1':control[(96e6,16.8e6,'FULL_NEW')],'expected_fixed96_year1':control[(96e6,16.8e6,'EXPECTED')]},ensure_ascii=False,indent=2))
