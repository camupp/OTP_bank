"""Independent narrow finance check. Read data only; never run closed builders."""
from pathlib import Path
import csv, hashlib, json, math

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/'project/brief.md').is_file())
ROUND = HERE.parents[1]
BASE = ROOT/'analysis/iterations/iteration-008/incumbent'
OLD = ROOT/'analysis/iterations/iteration-007/rounds/003'
RATES = {'HR':1000, 'owner_QA':1500, 'employee':1000, 'IT':2000}
CAPS = {'HR':6, 'owner_QA':240, 'employee':4, 'IT':3}
checks = []

def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def js(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name, actual, expected, tol=1e-6):
    ok = abs(actual-expected)<=tol if isinstance(actual,(float,int)) and isinstance(expected,(float,int)) else actual==expected
    checks.append({'check':name,'actual':actual,'expected':expected,'pass':ok})
    return ok
def write(name, data):
    (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def writecsv(name, data):
    with (HERE/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def period(m): return 'year1' if m<=12 else 'year2' if m<=24 else 'year3' if m<=36 else 'tail'
def same_scope(r,qa=1):
    return r['scenario']=='EXPECTED' and int(r['fixed_C_year'])==96000000 and float(r['QA_reuse'])==qa and float(r['labor_multiplier'])==1 and float(r['substitution'])==0

manifest = js(OLD/'snapshot.json')['files']
integrity=[]
for name in ['finance-spec.json','monthly-resource.csv','annual-resource.csv','resource-stages.csv','setup-resource.csv']:
    actual=sha(BASE/name); expected=manifest['branches/B/con-025/'+name]
    integrity.append({'file':str((BASE/name).relative_to(ROOT)),'sha256':actual,'expected':expected})
    check('unchanged_control_'+name,actual,expected)
for rel in ['supporting/finance-basis/annual-three-year.csv','supporting/finance-basis/scenario-inputs.json','checks/finance/budget.csv']:
    actual=sha(OLD/rel);expected=manifest[rel]
    integrity.append({'file':str((OLD/rel).relative_to(ROOT)),'sha256':actual,'expected':expected})
    check('sealed_source_'+rel,actual,expected)
write('source-manifest.json',integrity)

spec=js(BASE/'finance-spec.json')
for rel,expected in spec['money_core_reused_no_reexecution'].items():
    check('money_core_hash_'+rel,sha(ROOT/rel),expected)
for k,v in {'N':7200,'G_R':2500,'E_R_year':24000000,'G_ceiling_R_year':18000000,'top_R_year':4320000,'special_R_year':1680000,'R_to_C':1,'certificate500_price_C':2500}.items():
    check('reward_core_'+k,spec['unchanged'][k],v)
check('G+top+special',18000000+4320000+1680000,24000000)
setup = rows(BASE/'setup-resource.csv')
base_setup=sum(float(r['cash_RUB']) for r in setup)
check('base_setup',base_setup,3990000)
monthly=rows(BASE/'monthly-resource.csv')
parent={(float(r['QA_reuse']),int(r['month']),r['role']):r for r in monthly if same_scope(r,float(r['QA_reuse']))}
main=[r for r in monthly if same_scope(r)]
check('base_main_rows',len(main),156)
check('base_cash_39',sum(float(r['new_operating_cash_RUB']) for r in main),19320000)
for r in main:
    m=int(r['month']);role=r['role'];prefix=f'parent_{m}_{role}'
    d=float(r['demand_h']); b=float(r['booked_h']); base=float(r['base_available_h'])
    check(prefix+'_sum_work',float(r['existing_activity_h'])+float(r['new_activity_h']),d)
    check(prefix+'_cash',b*RATES[role],float(r['new_operating_cash_RUB']))
    check(prefix+'_capacity',float(r['queue_start_h'])+d-float(r['queue_end_h'])<=base+b+1e-7,True)

annual=rows(OLD/'supporting/finance-basis/annual-three-year.csv')
money=[r for r in annual if r['scenario']=='EXPECTED' and int(r['fixed_C_year'])==96000000 and int(r['envelope_R_year'])==24000000]
budget=[]
for r in money:
    y=int(r['year']); f=lambda k:float(r[k])
    check(f'C_flow_y{y}',f('C_open')+f('fixed_C_issued')+f('R_to_C')-f('physical_C_required'),f('C_close'))
    check(f'R_flow_y{y}',f('R_open')+f('R_posted')-f('R_to_C')-f('direct_R_required'),f('R_close'))
    check(f'F_flow_y{y}',f('F_open')+f('F_granted')-f('F_posted')-f('F_unissued_expired'),f('F_close'))
    check(f'combined_flow_y{y}',f('C_open')+f('R_open')+f('fixed_C_issued')+f('R_posted')-f('physical_C_required')-f('direct_R_required'),f('C_close')+f('R_close'))
    check(f'reserve_delta_y{y}',f('reserve_target_close_rub')-f('reserve_target_open_rub'),f('reserve_target_delta_rub'))
    check(f'inventory_flow_y{y}',f('inventory_open_landed_rub')+f('total_cash_required_rub')-f('consumed_landed_rub'),f('inventory_close_landed_rub'))
    check(f'procurement_plus_logistics_y{y}',f('procurement_cash_rub')+f('logistics_cash_rub'),f('total_cash_required_rub'))
    total=f('total_cash_required_rub')+f('reserve_target_delta_rub')+500000
    check(f'funding_bridge_y{y}',total,f('cash_plus_reserve_delta_plus_buffer_rub'))
    adjust=24000000*(.2-.194)
    budget.append({'year':y,'procurement_cash_RUB':f('procurement_cash_rub'),'logistics_cash_RUB':f('logistics_cash_rub'),'cash_RUB':f('total_cash_required_rub'),'reserve_open_RUB':f('reserve_target_open_rub'),'reserve_close_RUB':f('reserve_target_close_rub'),'reserve_delta_RUB':f('reserve_target_delta_rub'),'buffer_RUB':500000,'M05_funding_RUB':total,'certificate500_adjustment_RUB':adjust,'certificate500_funding_RUB':total+adjust,'pass30_with_certificate':total+adjust<=30000000,'pass34_with_certificate':total+adjust<=34000000,'C_open':f('C_open'),'R_open':f('R_open'),'fixed_C_issued':f('fixed_C_issued'),'F_granted':f('F_granted'),'F_posted':f('F_posted'),'F_unissued_expired':f('F_unissued_expired'),'R_posted':f('R_posted'),'R_to_C':f('R_to_C'),'C_redeemed':f('physical_C_required'),'direct_R_redeemed':f('direct_R_required'),'C_close':f('C_close'),'R_close':f('R_close'),'legacy_close_C_R':f('original_legacy_close_C_R'),'new_rights_close_C_R':f('post_start_rights_close_C_R')})
check('funding_y1',budget[0]['certificate500_funding_RUB'],31684000)
check('no_30m_y1',budget[0]['pass30_with_certificate'],False)
check('34m_y1',budget[0]['pass34_with_certificate'],True)
writecsv('procurement-and-currency.csv',budget)
sensitivity=rows(OLD/'checks/finance/budget.csv')
for i,r in enumerate(sensitivity):
    funding=float(r['cash_RUB'])+float(r['signed_reserve_delta_RUB'])+float(r['buffer_RUB'])
    check(f'preserved_budget_bridge_{i}',funding,float(r['M05_funding_RUB']))
    check(f'preserved_budget34_{i}',r['pass34']=='True',float(r['certificate500_funding_RUB'])<=34000000+1e-7)
writecsv('preserved-budget-sensitivity.csv',sensitivity)

launch=rows(ROOT/'analysis/iterations/iteration-007/incumbent/first-launch.csv')
cal={int(r['month']):r for r in launch if int(r['E_R_year'])==24000000}
check('launch_rows',len(cal),39)
check('G_first_month',min(m for m,r in cal.items() if float(r['guarantee_post_all_success_R'])>0),7)
check('first_9cohorts',sum(float(cal[m]['guarantee_post_all_success_R']) for m in range(7,16)),18000000)

# Independent release and manual fallback schedule shared by both implementations.
release=[]
for m,c in sorted(cal.items()):
    old=parent[(1,m,'HR')]
    n=int(c['ordinary_cycle_records'])+int(float(c['guarantee_post_all_success_R'])/2500)+32
    old_h=float(old['booked_h']); demand=float(old['demand_h']);base=float(old['base_available_h'])
    batch_h=max(old_h,20*math.ceil(max(0,demand+4-base)/20-1e-10))
    entry=2*n/60;receipt=n/60
    input_blocks=math.ceil(entry/20-1e-10); receipt_blocks=math.ceil(receipt/20-1e-10)
    release.append({'month':m,'period':period(m),'rows_upper':n,'new_release_activity_h':4,'new_release_activity_RUB':4000,'additional_batch_cash_RUB':(batch_h-old_h)*1000,'manual_input_h':entry,'manual_receipt_h':receipt,'manual_input_blocks20h':input_blocks,'manual_receipt_blocks20h':receipt_blocks,'manual_additional_cash_RUB':(input_blocks+receipt_blocks)*20000,'manual_paid_idle_h':(input_blocks+receipt_blocks)*20-entry-receipt,'double_input_blocks':math.ceil(entry*2/20-1e-10),'double_receipt_blocks':math.ceil(receipt*2/20-1e-10)})
check('manual_peak_rows',max(r['rows_upper'] for r in release),3232)
check('manual_peak_input_blocks',max(r['manual_input_blocks20h'] for r in release),6)
check('manual_peak_receipt_blocks',max(r['manual_receipt_blocks20h'] for r in release),3)
check('manual_cash39',sum(r['manual_additional_cash_RUB'] for r in release),6060000)
check('batch_cash39',sum(r['additional_batch_cash_RUB'] for r in release),180000)
check('batch_activity39',sum(r['new_release_activity_RUB'] for r in release),156000)
extra_exception_h={'owner_QA':120*12/60+72*5/60+12*12/60,'HR':120*6/60+72*5/60+12*38/60,'employee':120*5/60+72*3/60,'IT':12*30/60}
check('exception_stress_activity_h_month',sum(extra_exception_h.values()),77.6)
check('exception_stress_activity_RUB_month',sum(extra_exception_h[k]*RATES[k] for k in RATES),99800)
check('manual_double_input_peak',max(r['double_input_blocks'] for r in release),11)
check('manual_double_receipt_peak',max(r['double_receipt_blocks'] for r in release),6)
writecsv('release-and-fallback.csv',release)

costs={}
A=ROUND/'branches/A'
if (A/'cost-summary.json').exists():
    a=js(A/'cost-summary.json')
    if (A/'setup-phases.csv').exists():
        phases=rows(A/'setup-phases.csv')
        check('A_setup_phases_total_RUB',sum(float(r['cash_RUB']) for r in phases),3990000)
        check('A_setup_preparation_RUB',sum(float(r['cash_RUB']) for r in phases if r['phase']=='preparation'),1890000)
        check('A_setup_shadow_RUB',sum(float(r['cash_RUB']) for r in phases if r['phase']=='shadow_quarter'),2100000)
        check('A_shadow_months',sorted({int(r['month']) for r in phases if r['phase']=='shadow_quarter'}),[-2,-1,0])
        for role,hours in {'HR':120,'owner_QA':420,'IT':720,'employee':1800}.items():check('A_setup_hours_'+role,sum(float(r['hours']) for r in phases if r['role']==role),hours)
        for i,r in enumerate(phases):
            check(f'A_setup_phase_{i}_cash',float(r['hours'])*float(r['rate_RUB_h']),float(r['cash_RUB']))
            check(f'A_setup_phase_{i}_20h',float(r['hours']),float(r['blocks20h'])*20)
    for key,expected in {'new_batch_release_actual_work_RUB_39months':156000,'new_batch_release_booking_cash_RUB_39months':180000,'setup_incremental_to_parent_RUB':0,'batch_total_with_setup_39months_RUB':23490000,'no_batch_total_with_setup_39months_RUB':29550000}.items(): check('A_'+key,a[key],expected)
    arows=rows(A/'manual-posting-calendar.csv')
    check('A_calendar_length',len(arows),39)
    for old,new in zip(release,arows):
        m=old['month']
        for ours,theirs in [('rows_upper','rows_upper'),('additional_batch_cash_RUB','batch_release_extra_cash_RUB'),('manual_additional_cash_RUB','manual_extra_cash_RUB')]:check(f'A_{m}_{ours}',old[ours],float(new[theirs]))
    costs['A']={'candidate_key':a['candidate_key'],'setup_incremental_RUB':0,'setup_allocation_within_base_RUB':252000,'new_activity_RUB_12months':48000,'new_activity_RUB_39months':156000,'additional_cash_RUB_12months':180000,'additional_cash_RUB_39months':180000,'conservative_base_plus_setup_39_RUB':23490000,'full_no_batch_plus_setup_39_RUB':29550000,'manual_additional_cash_RUB_39months':6060000,'cash_after_year1_incremental_RUB_year':0}

B=ROUND/'branches/B'
b_spec=js(B/'finance-spec.json')
if (B/'setup-phases.csv').exists():
    phases=rows(B/'setup-phases.csv')
    for category,expected_cash,expected_hours in [('base',3990000,{'HR':120,'owner_QA':420,'IT':720,'employee':1800}),('new_functions',692000,{'HR':16,'owner_QA':24,'IT':320,'employee':0})]:
        subset=[r for r in phases if r['category']==category]
        check('B_setup_cash_'+category,sum(float(r['cost_RUB']) for r in subset),expected_cash)
        for role,hours in expected_hours.items():check('B_setup_hours_'+category+'_'+role,sum(float(r[role+'_h']) for r in subset),hours)
        for i,r in enumerate(subset):check('B_setup_phase_cash_'+category+'_'+str(i),sum(float(r[role+'_h'])*RATES[role] for role in RATES),float(r['cost_RUB']))
    check('B_shadow_months',sorted({r['phase'] for r in phases if r['phase'].startswith('S')}),['S1','S2','S3'])
    check('B_pilot_not_financial_population',b_spec['shadow_scope']['pilot_people'],40+40+8*5)
    check('B_financial_population',b_spec['shadow_scope']['financial_population'],7200)
if (B/'posting-fallback.csv').exists():
    post=rows(B/'posting-fallback.csv')
    check('B_posting_fallback_months',len(post),39)
    # Column naming is inspected as data; main independently computed control remains release-and-fallback.csv.
    check('B_posting_fallback_spec_cash',b_spec['posting_fallback']['extra_RUB_39months'],6060000)
    check('B_total_setup_conservative',b_spec['conservative_setup_plus39month_cash_RUB'],24182000)
    check('B_total_setup_manual',b_spec['full_posting_fallback_setup_plus39month_cash_RUB'],30242000)
br=rows(B/'monthly-delta.csv')
cases={'main_q10_QA100':(.1,1,False),'q30_QA100':(.3,1,False),'fallback_QA100':(1,1,True),'main_q10_QA50':(.1,.5,False),'main_q10_QA0':(.1,0,False)}
our_b=[]
for name,(q,qa,fallback) in cases.items():
    for role in RATES:
        queue=0
        for m in range(1,40):
            r=parent[(qa,m,role)];n=float(cal[m]['ordinary_cycle_records'])
            old_stage=(180*(8+4)/60 if role=='HR' else n*(1760/2400)*2/60 if role=='owner_QA' else 0)
            new_stage=(old_stage if fallback else (6*(8+4)+180*q*(8+4))/60 if role=='HR' else q*old_stage if role=='owner_QA' else 0)
            support=8 if role=='IT' else 0
            # Physical operator release + independent receipt control are not an automatic signature.
            physical_release=4 if role=='HR' else 0
            demand=float(r['demand_h'])-old_stage+new_stage+support+physical_release
            base=float(r['base_available_h'])
            blocks=max(0,math.ceil((demand+queue-base)/20-1e-10));blocks=min(CAPS[role],blocks)
            booked=blocks*20;queue=max(0,queue+demand-base-booked)
            idle=booked-min(booked,max(0,demand-base))
            our_b.append({'case':name,'month':m,'period':period(m),'role':role,'QA_reuse':qa,'q':q,'new_demand_h':demand,'new_booked_h':booked,'new_cash_RUB':booked*RATES[role],'new_activity_RUB':demand*RATES[role],'new_full_cost_RUB':(demand+idle)*RATES[role],'queue_end_h':queue,'replaced_old_h':old_stage,'replacement_h':new_stage,'support_h':support,'physical_release_h':physical_release})
check('B_rows',len(br),len(our_b))
lookup={(r['case'],int(r['month']),r['role']):r for r in br}
for r in our_b:
    k=(r['case'],r['month'],r['role']);other=lookup[k]
    for field in ['new_demand_h','new_booked_h','new_cash_RUB','queue_end_h']:
        check(f'B_{k}_{field}',r[field],float(other[field]))
    check(f'B_{k}_activity_cost',r['new_activity_RUB'],float(other['new_work_cost_RUB']))
    check(f'B_{k}_full_cost',r['new_full_cost_RUB'],float(other['new_full_cost_RUB']))
writecsv('B-independent-delta.csv',our_b)

periodrows=[]
for name in cases:
    for label,lo,hi in [('year1',1,12),('year2',13,24),('year3',25,36),('tail',37,39),('all39',1,39)]:
        data=[r for r in our_b if r['case']==name and lo<=r['month']<=hi]
        periodrows.append({'case':name,'period':label,'new_cash_RUB':sum(r['new_cash_RUB'] for r in data),'new_activity_RUB':sum(r['new_activity_RUB'] for r in data),'new_full_cost_RUB':sum(r['new_full_cost_RUB'] for r in data),'maximum_queue_h':max(r['queue_end_h'] for r in data)})
writecsv('B-periods.csv',periodrows)
b_main=next(r for r in periodrows if r['case']=='main_q10_QA100' and r['period']=='all39')
b_fallback=next(r for r in periodrows if r['case']=='fallback_QA100' and r['period']=='all39')
check('B_setup',320*2000+16*1000+24*1500,692000)
check('B_IT_support_max',max(r['new_demand_h'] for r in our_b if r['role']=='IT'),38)
check('B_IT_paid_hours',min(r['new_booked_h'] for r in our_b if r['role']=='IT'),40)
costs['B']={'candidate_key':js(B/'finance-spec.json')['candidate_key'],'setup_incremental_RUB':692000,'setup_total_RUB':4682000,'new_support_activity_RUB_12months':192000,'new_support_activity_RUB_39months':624000,'new_release_activity_RUB_12months':48000,'new_release_activity_RUB_39months':156000,'new_activity_gross_RUB_12months':240000,'new_activity_gross_RUB_39months':780000,'additional_cash_conservative_RUB_12months':180000,'additional_cash_conservative_RUB_39months':180000,'conditional_optimized_bookings_RUB_39months':b_main['new_cash_RUB'],'conditional_optimized_setup_plus39_RUB':b_main['new_cash_RUB']+4682000,'conservative_bookings_RUB_39months':b_fallback['new_cash_RUB'],'conservative_setup_plus39_RUB':b_fallback['new_cash_RUB']+4682000,'full_manual_fallback_setup_plus39_RUB':b_fallback['new_cash_RUB']+6060000+4682000,'manual_additional_cash_RUB_39months':6060000,'new_support_added_cash_RUB_39months':0,'cash_saving_is_authorized':False}
write('delivery-summary.json',{'verification_status':'passed' if all(r['pass'] for r in checks) else 'pre_rework_pending','classification':'Project assumptions and independent calculations, not bank observations or approved finance','scope':'EXPECTED/fixed96/old20/E24/baseprices/QA100/labor1/substitution0;39m operating plus setup. Monetary core reused, no new grid.','base_setup_RUB':base_setup,'base_bookings_RUB_39months':19320000,'base_setup_plus39_RUB':23310000,'base_period_bookings_RUB':{label:sum(float(r['new_operating_cash_RUB']) for r in main if period(int(r['month']))==label) for label in ['year1','year2','year3','tail']},'implementations':costs,'procurement_and_currency':budget,'calendar_note':'The annual money model provides a full E24 commitment ceiling. First-launch actual all-success posting calendar is separate and starts G in m7–15; budgets are not reduced by pending or launch ramp.','unknown_bank_inputs':['Actual balances/old approved unposted rights','Actual fixed-C frequency','Real procurement/SKU/fees/region capacity','Paid independent people and daily close capacity','Workflow/batch/ledger semantics','Motivational effect'],'no_claims':['No actual bank payment','No recurring annual4.47m saving','No double semiannual guarantee','No free QA/IT/manual fallback','No money-core reexecution']})
failed=[r for r in checks if not r['pass']]
write('verification.json',{'checks':len(checks),'failed':len(failed),'failures':failed,'scope':'Independent narrow arithmetic, source hashes, preserved currency equations and declared integration deltas. Does not prove live availability or effects.'})
if not failed:
    numeric=lambda r:{k:(float(v) if isinstance(v,str) and v.replace('.','',1).replace('-','',1).isdigit() else v) for k,v in r.items()}
    write('workbook-input.json',{'summary':js(HERE/'delivery-summary.json'),'base_monthly':[numeric(r) for r in main],'launch':[numeric(cal[m]) for m in sorted(cal)],'release':release,'base_setup':[numeric(r) for r in setup],'preserved_budget_sensitivity':sensitivity,'B_periods':periodrows,'source_refs':integrity})
print(json.dumps({'checks':len(checks),'failures':len(failed),'first_failures':failed[:3],'A':costs.get('A'),'B':costs['B']},ensure_ascii=False,indent=2))
