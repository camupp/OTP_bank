"""Narrow workload delta only. Reads sealed data; never executes parent code."""
import csv, hashlib, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'project/brief.md').exists())
BASE = ROOT / 'analysis/iterations/iteration-008/incumbent'
CAL = ROOT / 'analysis/iterations/iteration-007/incumbent/first-launch.csv'

def read(p):
    with p.open() as f:
        return list(csv.DictReader(f))

def write(name, rows):
    with (HERE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main():
    rates = {'HR': 1000, 'owner_QA': 1500, 'employee': 1000, 'IT': 2000}
    caps = {'HR': 6, 'owner_QA': 240, 'employee': 4, 'IT': 3}
    core = {int(r['month']): r for r in read(CAL) if int(r['E_R_year']) == 24000000}
    old = {(float(r['QA_reuse']), int(r['month']), r['role']): r for r in read(BASE / 'monthly-resource.csv')
           if r['scenario'] == 'EXPECTED' and int(r['fixed_C_year']) == 96000000
           and float(r['labor_multiplier']) == 1 and float(r['substitution']) == 0}
    cases = [('main_q10_QA100', .1, 1, False), ('q30_QA100', .3, 1, False),
             ('fallback_QA100', 1, 1, True), ('main_q10_QA50', .1, .5, False),
             ('main_q10_QA0', .1, 0, False)]
    rows, summaries = [], []
    for case, q, qa, fallback in cases:
        case_rows = []
        for role in rates:
            queue = 0
            for m in range(1, 40):
                parent = old[(qa, m, role)]
                n = float(core[m]['ordinary_cycle_records'])
                old_stage = 0.; new_stage = 0.; support = 0.; posting_actions = 0.
                if role == 'HR':
                    old_stage = 180 * (8 + 4) / 60
                    new_stage = old_stage if fallback else (6 * (8 + 4) + 180 * q * (8 + 4)) / 60
                    posting_actions = 4.
                elif role == 'owner_QA':
                    old_stage = n * 1760 / 2400 * 2 / 60
                    new_stage = old_stage if fallback else q * old_stage
                elif role == 'IT':
                    support = 8.
                demand = float(parent['demand_h']) - old_stage + new_stage + support + posting_actions
                base = float(parent['base_available_h'])
                blocks = min(caps[role], max(0, math.ceil((demand + queue - base) / 20 - 1e-10)))
                booked = blocks * 20
                queue_start = queue
                queue = max(0, queue + demand - base - booked)
                used = min(booked, max(0, demand - base))
                idle = booked - used
                row = dict(case=case, QA_reuse=qa, q=q, month=m, role=role,
                           ordinary_cycle_records=n, parent_demand_h=float(parent['demand_h']),
                           replaced_old_h=old_stage, replacement_h=new_stage, platform_support_h=support,
                           operator_and_receipt_h=posting_actions,
                           new_demand_h=demand, work_delta_h=new_stage + support + posting_actions - old_stage,
                           base_h=base, parent_booked_h=float(parent['booked_h']), new_booked_h=booked,
                           parent_cash_RUB=float(parent['new_operating_cash_RUB']),
                           new_cash_RUB=booked * rates[role],
                           parent_work_cost_RUB=float(parent['activity_cost_RUB']),
                           new_work_cost_RUB=demand * rates[role],
                           new_paid_idle_h=idle,
                           new_full_cost_RUB=(demand + idle) * rates[role],
                           queue_start_h=queue_start, queue_end_h=queue,
                           state='conditional_monthly_capacity' if queue < 1e-7 else 'fail_monthly_capacity')
                rows.append(row); case_rows.append(row)
        for period, lo, hi in [('year1', 1, 12), ('year2', 13, 24), ('year3', 25, 36),
                               ('tail', 37, 39), ('all39', 1, 39)]:
            xs = [r for r in case_rows if lo <= r['month'] <= hi]
            summaries.append(dict(case=case, period=period,
                parent_cash_RUB=sum(r['parent_cash_RUB'] for r in xs),
                new_cash_RUB=sum(r['new_cash_RUB'] for r in xs),
                cash_saved_RUB=sum(r['parent_cash_RUB'] - r['new_cash_RUB'] for r in xs),
                parent_work_cost_RUB=sum(r['parent_work_cost_RUB'] for r in xs),
                new_work_cost_RUB=sum(r['new_work_cost_RUB'] for r in xs),
                work_cost_saved_RUB=sum(r['parent_work_cost_RUB'] - r['new_work_cost_RUB'] for r in xs),
                new_full_cost_RUB=sum(r['new_full_cost_RUB'] for r in xs),
                max_queue_h=max(r['queue_end_h'] for r in xs),
                monthly_capacity='conditional' if all(r['queue_end_h'] < 1e-7 for r in xs) else 'fail'))
    write('monthly-delta.csv', rows); write('annual-delta.csv', summaries)
    manual_posting = []
    for m in range(1, 40):
        c = core[m]
        lines = float(c['ordinary_cycle_records']) + float(c['guarantee_post_all_success_R']) / 2500 + 32
        entry_h, check_h = lines * 2 / 60, lines / 60
        entry_blocks, check_blocks = math.ceil(entry_h / 20 - 1e-10), math.ceil(check_h / 20 - 1e-10)
        assert entry_blocks <= 6 and check_blocks <= 3
        manual_posting.append(dict(month=m, ordinary_records=float(c['ordinary_cycle_records']),
            G_persons=float(c['guarantee_post_all_success_R']) / 2500, special_awards=32,
            potential_positive_lines=lines, entry_h=entry_h, checker_h=check_h,
            entry_pool_max_blocks=6, checker_pool_max_blocks=3,
            booked_entry_h=entry_blocks * 20, booked_checker_h=check_blocks * 20,
            additional_cash_RUB=(entry_blocks + check_blocks) * 20 * 1000,
            status='separate independent pools must be signed and paid before promises'))
    write('posting-fallback.csv', manual_posting)
    manual_cash = sum(r['additional_cash_RUB'] for r in manual_posting)
    assert manual_cash == 6060000
    setup_rows = read(HERE / 'setup-phases.csv')
    for sr in setup_rows:
        cost = sum(float(sr[role + '_h']) * rates[role] for role in rates)
        assert abs(cost - float(sr['cost_RUB'])) < 1e-7
    base_setup = [sr for sr in setup_rows if sr['category'] == 'base']
    functions_setup = [sr for sr in setup_rows if sr['category'] == 'new_functions']
    assert {role:sum(float(sr[role + '_h']) for sr in base_setup) for role in rates} == {'HR':120,'owner_QA':420,'employee':1800,'IT':720}
    assert sum(float(sr['cost_RUB']) for sr in base_setup) == 3990000
    assert sum(float(sr['cost_RUB']) for sr in functions_setup) == 692000
    assert sum(float(sr['cost_RUB']) for sr in base_setup if sr['phase'].startswith('P')) == 1890000
    assert sum(float(sr['cost_RUB']) for sr in base_setup if not sr['phase'].startswith('P')) == 2100000
    all39 = {s['case']:s for s in summaries if s['period'] == 'all39'}
    assert all39['main_q10_QA100']['new_cash_RUB'] == 16380000
    assert all39['q30_QA100']['new_cash_RUB'] == 16860000
    assert all39['fallback_QA100']['new_cash_RUB'] == 19500000
    summary = {'candidate_key': 'CON-027@v2', 'classification': 'scenario, not measured bank savings',
       'scope': 'EXPECTED/fixed96/labor1/substitution0 only; 39 months. Same old source and reward core.',
       'base_setup_RUB': 3990000, 'new_function_setup_RUB': 692000,
       'total_setup_RUB': 4682000, 'platform_maintenance_activity_RUB_month': 16000,
       'operator_and_receipt_HR_h_month':4,
       'operator_and_receipt_activity_RUB_year':48000,
       'operator_and_receipt_activity_RUB_39months':156000,
       'full_posting_fallback_reserve_RUB_39months':manual_cash,
       'conservative_structural_fallback_setup_plus39_RUB':24182000,
       'full_posting_fallback_setup_plus39_RUB':24182000+manual_cash,
       'setup_calendar_checks': {'base_hours_preserved':True,'base_preparation_RUB':1890000,'base_shadow_and_close_RUB':2100000,'new_functions_RUB':692000,'full_shadow_months':3,'critical_functions_ready_before_shadow':True,'close_buffer_paid_from_setup':True},
       'monthly_rows': len(rows), 'summaries': summaries,
       'conservative_funding_rule': 'Until readiness/rehearsal and q are demonstrated, retain full structural fallback booking19.500m plus setup4.682m. Actual operator release2h and independent receipt review2h per month are additional to old monthly control12h. IT8h/month is costed and consumes paid capacity. No automatic fallback pass without financing.',
       'failover_rule': 'Structural fallback restores all old checks plus platform support and HR4h. F4/noBatch additionally requires every positive line entry2min and independent review1min; reserve6.060m/39months in disjoint6+3x20h pools. Without paid signed reserve, F4 failure stays held with rights preserved, not automatically pass.',
       'invariants': {'N':7200, 'G_R':2500, 'G_frequency':'once/12months; both quarters same fixed window',
                      'E_R_year':24000000, 'R_to_C':1, 'certificate500_price_C':2500,
                      'procurement_cap_RUB_year':34000000, 'certificate_sensitivity_procurement_RUB':31684000},
       'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [BASE / 'finance-spec.json', BASE / 'resource-stages.csv',
                             BASE / 'monthly-resource.csv', BASE / 'setup-resource.csv', CAL]}}
    (HERE / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'setup_delta_RUB':692000, 'rows':len(rows),
        'main': [s for s in summaries if s['case']=='main_q10_QA100'],
        'all39_sensitivities': [s for s in summaries if s['period']=='all39']}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
