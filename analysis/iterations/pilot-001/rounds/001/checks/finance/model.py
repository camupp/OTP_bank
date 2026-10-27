#!/usr/bin/env python3
"""Reproduce bounded, synthetic finance checks. Python stdlib only.

No bank forecast, no fitted effects, no RUB/C exchange rate. Inputs and outputs
are relative to this file. Real-bank parameters remain None in model-inputs.json.
"""
import copy
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent
DATA = json.loads((HERE / 'model-inputs.json').read_text())


def write_csv(name, rows):
    with (HERE / name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Ledger:
    def __init__(self, opening):
        self.b = dict(opening)
        self.opening = dict(opening)
        self.h = {k: 0 for k in ('A_C', 'B_C', 'A_R', 'B_R')}
        self.f = {k: 0 for k in ('I', 'G', 'W', 'X', 'PC', 'PR', 'UC', 'UR', 'EF', 'J')}
        self.events = []
        self.ids = set()
        self.redemptions = {}
        self.month = 1

    def total(self, currency):
        return sum(v for k, v in self.b.items() if k.endswith('_' + currency))

    def free(self, key):
        return self.b[key] - self.h.get(key, 0)

    def op(self, event_id, kind, amount, account='A', ref=None):
        assert event_id not in self.ids, 'duplicate event'
        assert amount >= 0 and amount == int(amount), 'nonnegative integer units required'
        assert kind in {'I', 'G', 'W', 'X', 'T', 'PC', 'PR', 'UC', 'UR', 'EF',
                        'HC', 'HR', 'releaseC', 'releaseR', 'settleC', 'settleR'}, kind
        c, r = account + '_C', account + '_R'
        if kind in {'X', 'PR'}:
            assert amount <= self.free(r), 'R already spent or held'
        if kind in {'T', 'PC'}:
            assert amount <= self.free(c), 'C already spent or held'
        if kind == 'W':
            assert amount <= self.b['F'], 'fund exhausted'
        if kind == 'EF':
            assert self.month % 3 == 0 and amount == self.b['F'], 'only quarter-end F expires'
        if kind in {'HC', 'HR'}:
            assert amount <= self.free(c if kind == 'HC' else r), 'hold exceeds free balance'
        if kind.startswith('release') or kind.startswith('settle'):
            assert amount <= self.h[c if kind.endswith('C') else r], 'release/settle exceeds hold'
        if kind in {'UC', 'UR'}:
            assert ref in self.redemptions, 'refund needs original redemption'
            order = self.redemptions[ref]
            assert order['currency'] == kind[-1] and order['account'] == account
            assert amount <= order['remaining'], 'duplicate/excess refund'
        if kind in {'PC', 'PR', 'settleC', 'settleR'}:
            self.redemptions[event_id] = {'remaining': amount, 'currency': kind[-1], 'account': account}
        if kind == 'I': self.b[c] += amount; self.f['I'] += amount
        elif kind == 'G': self.b['F'] += amount; self.f['G'] += amount
        elif kind == 'W': self.b['F'] -= amount; self.b[r] += amount; self.f['W'] += amount
        elif kind == 'X': self.b[r] -= amount; self.b[c] += amount; self.f['X'] += amount
        elif kind == 'T':
            self.b[c] -= amount
            self.b[('B' if account == 'A' else 'A') + '_C'] += amount
        elif kind in {'PC', 'PR'}:
            self.b[c if kind == 'PC' else r] -= amount
            self.f[kind] += amount
        elif kind in {'UC', 'UR'}:
            self.b[c if kind == 'UC' else r] += amount
            self.f[kind] += amount
            self.redemptions[ref]['remaining'] -= amount
        elif kind == 'EF': self.b['F'] -= amount; self.f['EF'] += amount
        elif kind in {'HC', 'HR'}: self.h[c if kind == 'HC' else r] += amount
        elif kind.startswith('release'): self.h[c if kind.endswith('C') else r] -= amount
        elif kind.startswith('settle'):
            key = c if kind.endswith('C') else r
            self.h[key] -= amount
            self.b[key] -= amount
            self.f['PC' if kind.endswith('C') else 'PR'] += amount
        self.ids.add(event_id)
        assert all(v >= 0 for v in self.b.values())
        assert all(0 <= v <= self.b[k] for k, v in self.h.items())
        C0 = self.opening['A_C'] + self.opening['B_C']
        R0 = self.opening['A_R'] + self.opening['B_R']
        assert self.total('C') == C0 + self.f['I'] + self.f['X'] - self.f['PC'] + self.f['UC']
        assert self.total('R') == R0 + self.f['W'] - self.f['X'] - self.f['PR'] + self.f['UR']
        assert self.b['F'] == self.opening['F'] + self.f['G'] - self.f['W'] - self.f['EF']
        assert sum(self.b.values()) == sum(self.opening.values()) + self.f['I'] + self.f['G'] - self.f['PC'] - self.f['PR'] - self.f['EF'] + self.f['UC'] + self.f['UR']
        self.events.append({'month': self.month, 'event_id': event_id, 'kind': kind,
                            'amount_units': amount, 'account': account, 'ref': ref or '',
                            **self.b, 'held_C': self.h['A_C'] + self.h['B_C'],
                            'held_R': self.h['A_R'] + self.h['B_R'],
                            'minimum_free_personal_balance': min(self.free(k) for k in self.h)})


def currency_scenario(candidate, sid):
    spec = DATA['synthetic_currency_fixture']
    ledger = Ledger(spec['opening'])
    stock = spec['inventory']['initial_C_reward_units']
    delivered_C = delivered_R = requested_C = requested_R = receipt_total = 0
    pending_C = pending_R = 0
    peak_hours = 0
    months = []
    for q in range(1, 5):
        flow = copy.deepcopy(spec['quarter'])
        additional_I = 0
        if sid in {'N6_more_issuance', 'N7_more_issuance_and_use'}:
            # One valid A -> B Thanks per quarter; each individual's monthly count=1<=5.
            additional_I = 50 + 100
            flow['W_R'] += 200
        if sid == 'N7_more_issuance_and_use':
            flow['X_RtoC'] += 200
            flow['requested_C'] += 350
        if q == 1 and sid == 'N1_old_C': flow['requested_C'] += 800
        if q == 1 and sid == 'N2_convert_R':
            flow.update(X_RtoC=700, requested_C=800, requested_R=0)
        if q == 1 and sid == 'N3_direct_R':
            flow.update(X_RtoC=0, requested_R=700)
        if sid == 'N5_season':
            flow.update(requested_C=800 if q == 1 else 0, requested_R=200 if q == 1 else 0)
        receipts = 0 if sid == 'N4_supply_zero' else spec['inventory']['receipts_per_quarter']
        for offset in range(3):
            ledger.month = (q - 1) * 3 + offset + 1
            prefix = f'q{q}m{ledger.month}'
            if offset == 0:
                for kind, key in [('G', 'G_R'), ('I', 'I_C'), ('W', 'W_R'), ('T', 'T_A_to_B'), ('X', 'X_RtoC')]:
                    ledger.op(prefix + '-' + kind, kind, flow[key])
                if additional_I:
                    ledger.op(prefix + '-thanks-send', 'I', 50, 'A')
                    ledger.op(prefix + '-thanks-receive', 'I', 100, 'B')
                stock += receipts
                receipt_total += receipts
            if offset == 1:
                priceC = spec['inventory']['price_C_per_unit']
                priceR = spec['direct_R']['price_R_per_slot']
                nC = min(flow['requested_C'] // priceC, stock)
                nR = min(flow['requested_R'] // priceR,
                         spec['direct_R']['slots_per_quarter'],
                         spec['direct_R']['hours_per_quarter'] // spec['direct_R']['hours_per_slot'])
                for currency, request, fulfil in [('C', flow['requested_C'], nC * priceC), ('R', flow['requested_R'], nR * priceR)]:
                    # Proposed atomic holds are exercised only for CON-002. Other candidates'
                    # actual debit timing is unknown; the common fixture uses settlement.
                    if candidate == 'CON-002@v1':
                        ledger.op(prefix + '-hold-' + currency, 'H' + currency, request)
                        ledger.op(prefix + '-settle-' + currency, 'settle' + currency, fulfil)
                        ledger.op(prefix + '-release-' + currency, 'release' + currency, request - fulfil)
                    else:
                        ledger.op(prefix + '-pay-' + currency, 'P' + currency, fulfil)
                stock -= nC
                requested_C += flow['requested_C']; requested_R += flow['requested_R']
                delivered_C += nC * priceC; delivered_R += nR * priceR
                pending_C += flow['requested_C'] - nC * priceC
                pending_R += flow['requested_R'] - nR * priceR
                peak_hours = max(peak_hours, nR * spec['direct_R']['hours_per_slot'])
            if offset == 2:
                personal_before = (ledger.total('C'), ledger.total('R'))
                ledger.op(prefix + '-expire', 'EF', ledger.b['F'])
                assert personal_before == (ledger.total('C'), ledger.total('R'))
            months.append({'candidate_key': candidate, 'scenario_id': sid, 'month': ledger.month,
                           'C_units': ledger.total('C'), 'R_units': ledger.total('R'), 'F_units': ledger.b['F'],
                           'C_stock_reward_units': stock, 'pending_C_demand_units': pending_C,
                           'pending_R_demand_units': pending_R, 'held_C_units': sum(v for k, v in ledger.h.items() if k.endswith('_C')),
                           'held_R_units': sum(v for k, v in ledger.h.items() if k.endswith('_R'))})
    assert stock == spec['inventory']['initial_C_reward_units'] + receipt_total - delivered_C // spec['inventory']['price_C_per_unit']
    assert requested_C == delivered_C + pending_C and requested_R == delivered_R + pending_R
    result = {'candidate_key': candidate, 'scenario_id': sid, 'scope': 'synthetic_12_month_unit_test_only',
              'I_C_units': ledger.f['I'], 'G_R_units': ledger.f['G'], 'W_R_units': ledger.f['W'],
              'X_RtoC_units': ledger.f['X'], 'P_C_units': ledger.f['PC'], 'P_R_units': ledger.f['PR'],
              'expired_F_units': ledger.f['EF'], 'ending_C_units': ledger.total('C'),
              'ending_R_units': ledger.total('R'), 'ending_F_units': ledger.b['F'],
              'ending_stock_units': stock, 'pending_C_demand_units': pending_C,
              'pending_R_demand_units': pending_R, 'peak_R_hours_per_quarter': peak_hours,
              'formal_balance_gate': 'pass', 'all_requested_rewards_fulfilled': 'fail' if pending_C or pending_R else 'pass',
              'real_bank_budget_gate': 'uncertain', 'real_bank_currency_gate': 'uncertain'}
    return result, months, [dict(candidate_key=candidate, scenario_id=sid, **e) for e in ledger.events]


def cash_scenarios():
    rows = []
    f = DATA['synthetic_cash_fixture']
    for candidate in DATA['candidate_keys']:
        for s in f['scenarios']:
            gross = int(Decimal(str(f['variable_current_year_RUB'])) * Decimal(str(s['price_multiplier']))) + f['fixed_current_year_RUB'] + s['accelerate_RUB'] + s['extra_current_invoice_RUB']
            net = gross - s['supplier_refund_RUB']
            future = f['next_year_other_payment_RUB'] + f['opening_next_year_committed_payment_RUB'] - s['accelerate_RUB']
            assert s['accelerate_RUB'] <= f['opening_next_year_committed_payment_RUB']
            for B in f['budget_limits_RUB_per_year']:
                gross_gate = 'pass' if gross <= B else 'fail'
                net_gate = 'pass' if net <= B else 'fail'
                unknown_gate = gross_gate if gross_gate == net_gate else 'uncertain'
                rows.append({'candidate_key': candidate, 'scenario_id': s['id'], 'status': 'synthetic_invoice_arithmetic_not_bank',
                             'budget_RUB_per_year': B, 'g_multiplier': s['price_multiplier'],
                             'pi_rate': str(Decimal(str(s['price_multiplier'])) - 1),
                             'gross_payment_year1_RUB': gross, 'supplier_cash_refund_year1_RUB': s['supplier_refund_RUB'],
                             'net_cash_year1_RUB': net, 'budget_usage_if_refund_offset_0_RUB': gross,
                             'budget_usage_if_refund_offset_1_RUB': net,
                             'headroom_if_offset_0_RUB': B - gross, 'headroom_if_offset_1_RUB': B - net,
                             'scenario_gate_if_offset_0': gross_gate, 'scenario_gate_if_offset_1': net_gate,
                             'scenario_gate_with_unknown_offset_rule': unknown_gate,
                             'committed_payment_year2_RUB': future, 'year2_gate': 'pass' if future <= B else 'fail',
                             'two_year_net_cash_RUB': net + future, 'real_bank_budget_gate': 'uncertain'})
    return rows


def control_tests():
    checks = []
    def expected_rejection(name, action):
        try:
            action()
        except AssertionError as e:
            checks.append({'test': name, 'result': 'pass', 'detail': 'rejected: ' + str(e)})
        else:
            raise AssertionError('not rejected: ' + name)
    l = Ledger(DATA['synthetic_currency_fixture']['opening'])
    l.op('full-conversion', 'X', 400)
    expected_rejection('same_R_cannot_be_spent_directly_after_conversion', lambda: l.op('double-R', 'PR', 1))
    expected_rejection('duplicate_event_id', lambda: l.op('full-conversion', 'X', 1))
    l.op('hold', 'HC', 300)
    before = l.total('C')
    expected_rejection('held_C_cannot_be_transferred', lambda: l.op('held-spend', 'T', 901))
    l.op('cancel', 'releaseC', 100)
    assert l.total('C') == before
    l.op('settle', 'settleC', 200)
    l.op('refund', 'UC', 200, ref='settle')
    assert l.total('C') == before and sum(l.h.values()) == 0
    expected_rejection('refund_cannot_exceed_original_debit', lambda: l.op('refund-twice', 'UC', 1, ref='settle'))
    expected_rejection('refund_requires_link', lambda: l.op('unlinked-refund', 'UR', 1, ref='missing'))
    expected_rejection('fund_cannot_expire_mid_quarter', lambda: l.op('early-expiry', 'EF', l.b['F']))
    l.month = 3
    p = (l.total('C'), l.total('R'))
    l.op('quarter-expiry', 'EF', l.b['F'])
    assert p == (l.total('C'), l.total('R')) and l.b['F'] == 0
    checks.append({'test': 'holds_refunds_quarter_expiry', 'result': 'pass', 'detail': 'holds do not burn balance; cancellation creates no refund; linked refund once; only F expires'})
    assert 50 * min(6, 5) + 100 * min(6, 5) == 750
    checks.append({'test': 'Thanks_monthly_cap', 'result': 'pass', 'detail': '750 C/person/month is a ceiling, not a bank forecast or a RUB value'})
    # Recompute the exact branch B quarterly example independently.
    C = 1000 + 150 + 100 - 200
    R = 400 + 300 - 100 - 50
    F = 600 + 500 - 300
    assert (C, R, F) == (1050, 550, 800)
    assert C + R == 2000 + 150 + 500 - 200 - 50 - F == 1600
    checks.append({'test': 'branch_B_normalized_quarter', 'result': 'pass', 'detail': 'C=1050; R=550; pre-expiry F=800; after-expiry sum=1600'})
    assert 19427591 + 19112409 == 38540000
    assert round(100 * 19427591 / 38540000, 1) == 50.4
    checks.append({'test': 'case_Q3_fund_arithmetic', 'result': 'pass', 'detail': '19427591+19112409=38540000 R; 50.4% rounded; no cash or annualization inferred'})
    return checks


def main():
    assert all(v is None for v in DATA['actual_bank_parameters'].values())
    manifests = json.loads((ROUND / 'inputs/manifest.json').read_text())
    for path, expected in manifests['files'].items():
        assert hashlib.sha256((ROUND / 'inputs' / path).read_bytes()).hexdigest() == expected
    summaries, monthly, events = [], [], []
    for c in DATA['candidate_keys']:
        for s in DATA['synthetic_currency_fixture']['scenarios']:
            result, months, ev = currency_scenario(c, s['id'])
            summaries.append(result); monthly.extend(months); events.extend(ev)
    # Mechanism-neutral conditions must yield identical aggregate results for all five.
    for s in DATA['synthetic_currency_fixture']['scenarios']:
        rows = [{k: v for k, v in row.items() if k != 'candidate_key'} for row in summaries if row['scenario_id'] == s['id']]
        assert all(row == rows[0] for row in rows)
    write_csv('scenario-results.csv', summaries)
    write_csv('monthly-balances.csv', monthly)
    write_csv('event-ledger.csv', events)
    cash = cash_scenarios()
    write_csv('cash-scenarios.csv', cash)
    boundaries = []
    f = DATA['synthetic_cash_fixture']
    for B in f['budget_limits_RUB_per_year']:
        boundaries.append({'scope': 'same_synthetic_invoice_fixture', 'budget_RUB_per_year': B,
                           'neutral_g': 1, 'neutral_pi': 0,
                           'max_g': str((Decimal(B) - f['fixed_current_year_RUB']) / f['variable_current_year_RUB']),
                           'max_pi': str((Decimal(B) - f['fixed_current_year_RUB']) / f['variable_current_year_RUB'] - 1),
                           'max_extra_same_year_payment_RUB': B - f['fixed_current_year_RUB'] - f['variable_current_year_RUB']})
    write_csv('cash-boundaries.csv', boundaries)
    checks = control_tests()
    checks += [{'test': 'frozen_input_sha256', 'result': 'pass', 'detail': 'all five files match manifest'},
               {'test': 'same_exogenous_conditions_all_five', 'result': 'pass', 'detail': 'all 8 scenarios have equal aggregates across candidates; CON-002 additionally exercises atomic holds'},
               {'test': 'all_events_stock_flow_personal_nonnegative_inventory', 'result': 'pass', 'detail': f'{len(events)} events, {len(monthly)} month snapshots; currency, fund, inventory and demand residuals asserted'}]
    audit = {'status': 'pass', 'scope': 'synthetic arithmetic and internal consistency only; bank gates uncertain',
             'currency_candidate_scenario_rows': len(summaries), 'monthly_rows': len(monthly),
             'event_rows': len(events), 'cash_candidate_scenario_limit_rows': len(cash), 'checks': checks,
             'known_omissions': ['no live-bank reconciliation', 'no actual approval of refunds, holds or corrections',
                                'no fitted behavioral effects or cost estimates', 'no aggregate bank C/R-to-RUB valuation'],
             'input_sha256': hashlib.sha256((HERE / 'model-inputs.json').read_bytes()).hexdigest(),
             'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE / 'validation.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: audit[k] for k in ('status', 'currency_candidate_scenario_rows', 'monthly_rows', 'event_rows', 'cash_candidate_scenario_limit_rows')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
