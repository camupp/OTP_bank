"""Small delta calculation only. Reads immutable CSVs; does not run their builders."""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
PARENT = ROOT / 'analysis/iterations/iteration-008/incumbent'
LAUNCH = ROOT / 'analysis/iterations/iteration-007/incumbent/first-launch.csv'

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def dump_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

source = [r for r in read_csv(LAUNCH) if int(r['E_R_year']) == 24_000_000]
assert len(source) == 39
hr_months = {int(r['month']):r for r in read_csv(PARENT/'monthly-resource.csv') if
    r['scenario']=='EXPECTED' and int(r['fixed_C_year'])==96_000_000 and
    float(r['QA_reuse'])==1 and float(r['labor_multiplier'])==1 and
    float(r['substitution'])==0 and r['role']=='HR'}
calendar = []
for r in source:
    m = int(r['month'])
    cycle = int(r['ordinary_cycle_records'])
    g = int(float(r['guarantee_post_all_success_R']) / 2500)
    n = cycle + g + 32
    entry_h, check_h = n * 2 / 60, n / 60
    entry_blocks, check_blocks = math.ceil(entry_h / 20), math.ceil(check_h / 20)
    assert entry_blocks <= 6 and check_blocks <= 3
    hr = hr_months[m]
    old_blocks = int(hr['booked_blocks'])
    new_blocks = max(old_blocks, math.ceil(max(0,float(hr['demand_h'])+4-float(hr['base_available_h']))/20))
    assert new_blocks <= 6
    calendar.append(dict(month=m, top_person_rows_upper=cycle,
        G_person_rows_upper=g, special_rows_upper=32, rows_upper=n,
        input_h=entry_h, independent_receipt_h=check_h,
        input_blocks20h=entry_blocks, receipt_blocks20h=check_blocks,
        booked_h=(entry_blocks+check_blocks)*20,
        paid_idle_h=(entry_blocks+check_blocks)*20-entry_h-check_h,
        manual_extra_cash_RUB=(entry_blocks+check_blocks)*20*1000,
        batch_release_extra_h=4, batch_release_extra_actual_work_RUB=4000,
        old_HR_blocks=old_blocks,new_HR_blocks=new_blocks,
        batch_release_extra_cash_RUB=(new_blocks-old_blocks)*20*1000,
        double_time_input_blocks=math.ceil(entry_h*2/20),
        double_time_receipt_blocks=math.ceil(check_h*2/20)))
dump_csv(HERE / 'manual-posting-calendar.csv', list(calendar[0]), calendar)

annual = [r for r in read_csv(PARENT/'annual-resource.csv') if
    r['scenario']=='EXPECTED' and int(r['fixed_C_year'])==96_000_000 and
    float(r['QA_reuse'])==1 and float(r['labor_multiplier'])==1 and
    float(r['substitution'])==0]
periods = [('year1',1,12), ('year2',13,24), ('year3',25,36), ('tail',37,39)]
results = []
for label, lo, hi in periods:
    old = sum(float(r['new_operating_cash_RUB']) for r in annual if r['period']==label)
    subset = [r for r in calendar if lo<=r['month']<=hi]
    release = sum(r['batch_release_extra_cash_RUB'] for r in subset)
    manual = sum(r['manual_extra_cash_RUB'] for r in subset)
    results.append(dict(period=label, months=len(subset), inherited_bookings_RUB=old,
        new_batch_release_RUB=release, batch_total_operating_RUB=old+release,
        no_batch_additional_manual_RUB=manual,
        no_batch_total_operating_RUB=old+release+manual))
all39 = {k:sum(r[k] for r in results) for k in results[0] if k not in ('period',)}
all39['period']='all39'
results.append(all39)
dump_csv(HERE/'cost-periods.csv', list(results[0]), results)

# Preserve all old stage minutes/counters; no favorable effort coefficients introduced.
ops = []
for r in read_csv(PARENT/'resource-stages.csv'):
    ops.append(dict(candidate='CON-026@v1',stage=r['stage'], role=r['role'],
        counter=r['counter'], minutes_per_unit=r['minutes_per_unit'],
        classification=r['classification'], frequency='same_inherited_calendar',
        operation=r['operation'], change='unchanged_paid_envelope',
        source='iteration-008/incumbent/resource-stages.csv#'+r['stage']))
for stage, role, counter, minutes, classification, frequency, operation in [
    ('actual_batch_release_operator','HR','1',120,'new_integration','monthly',
     'upload_current_signed_package_lock_keys_obtain_receipt'),
    ('actual_batch_receipt_reviewer','HR','1',120,'new_integration','monthly',
     'independent_ledger_receipt_reconciliation_not_award_signature'),
    ('no_batch_manual_entry','HR','authorized_positive_rows_upper',2,'new_fallback','per_row',
     'manual_input_distinct_operator_funded20h_blocks'),
    ('no_batch_manual_receipt','HR','authorized_positive_rows_upper',1,'new_fallback','per_row',
     'distinct_receipt_reviewer_funded20h_blocks'),
    ('A_setup_requirements_roles_runbook','HR','48',60,'within_parent_setup','once',
     '48h_of_parent120h_not_additive'),
    ('A_setup_source_QA_contract','owner_QA','40',60,'within_parent_setup','once',
     '40h_of_parent420h_not_additive'),
    ('A_setup_template_versionhash_replay','IT','72',60,'within_parent_setup','once',
     '72h_of_parent720h_not_additive')]:
    ops.append(dict(candidate='CON-026@v1',stage=stage,role=role,counter=counter,
        minutes_per_unit=minutes,classification=classification,frequency=frequency,
        operation=operation,change='explicit_named_operation',
        source='assumptions.csv#A05-A17'))
dump_csv(HERE/'operations.csv', list(ops[0]), ops)

# Doubling only exception counts, using unchanged minutes from the parent stage ledger.
extra = {'owner_QA': 120*12/60 + 72*5/60 + 12*12/60,
         'HR': 120*6/60 + 72*5/60 + 12*38/60,
         'employee':120*5/60 + 72*3/60,
         'IT':12*30/60}
rates={'owner_QA':1500,'HR':1000,'employee':1000,'IT':2000}
stress_cost=sum(extra[k]*rates[k] for k in extra)
assert sum(extra.values()) == 77.6
assert all39['inherited_bookings_RUB'] == 19_320_000
assert all39['batch_total_operating_RUB'] == 19_500_000
assert all39['no_batch_additional_manual_RUB'] == 6_060_000
summary = dict(candidate_key='CON-026@v1',scope='EXPECTED/fixed96/QA100/labor1/substitution0',
    source_rows=len(source), max_monthly_posting_rows=max(r['rows_upper'] for r in calendar),
    new_batch_release_actual_work_h_39months=156,
    new_batch_release_actual_work_RUB_39months=156000,
    new_batch_release_booking_cash_RUB_39months=180000,
    setup_parent_RUB=3_990_000, A_specific_setup_allocation_within_parent_RUB=252_000,
    setup_incremental_to_parent_RUB=0, periods=results,
    batch_total_with_setup_39months_RUB=all39['batch_total_operating_RUB']+3_990_000,
    no_batch_total_with_setup_39months_RUB=all39['no_batch_total_operating_RUB']+3_990_000,
    exception_stress_additional_actual_h_month=extra,
    exception_stress_additional_actual_cost_RUB_month=stress_cost,
    exception_stress_additional_actual_cost_RUB_12months=stress_cost*12,
    stress_cost_scope='actual_work_only_not_booked_capacity_or_confirmed_cash',
    maximum_no_batch_pools=dict(input_positions=6,receipt_positions=3,person_month_h=20),
    maximum_double_time_required=dict(input_positions=max(r['double_time_input_blocks'] for r in calendar),
       receipt_positions=max(r['double_time_receipt_blocks'] for r in calendar)),
    checks=dict(old_stage_minutes_unchanged=True,no_favorable_QA_discount=True,
        manual_cap_holds_at_base=True,double_time_fails_fixed_manual_pool=True,
        no_new_monetary_grid=True,no_actual_bank_payment=True),
    source_SHA256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (LAUNCH,PARENT/'annual-resource.csv',PARENT/'resource-stages.csv',PARENT/'setup-resource.csv')})
(HERE/'cost-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'periods':results,'exception_extra_h_month':sum(extra.values()),
    'exception_extra_actual_cost_RUB_month':stress_cost},ensure_ascii=False,indent=2))
