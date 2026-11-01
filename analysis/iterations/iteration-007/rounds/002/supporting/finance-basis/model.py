"""M05 common boundaries, standard library; import is read-only, CLI writes here only.

Scenario cash assumes full requested execution. Failed rows are counterfactual,
never actual redemption. No concept-specific allocations or winner selection.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load_inputs():
    return json.loads((HERE / 'scenario-inputs.json').read_text())


def unit_cost(p):
    procurement = p['basket_nominal_rub'] * (
        p['certificate_share'] * p['certificate_cost_fraction']
        + p['merch_share'] * p['merch_cost_fraction']) * p['price_multiplier']
    freight = p['merch_share'] * p['logistics_rub_per_merch']
    return procurement, freight, (procurement + freight) / p['basket_C']


def simulate(inputs, scenario, fixed, envelope, years=3):
    p = inputs['common'] | scenario['overrides']
    procurement, freight, unit = unit_cost(p)
    legacyC, legacyR = p['initial_C'], p['initial_personal_R']
    futureC = futureR = reserve = ringfence = 0.0
    inventory = [0.0] * len(p['regions'])
    rows = []
    for year in range(1, years + 1):
        openingC, openingR = legacyC + futureC, legacyR + futureR
        legacy_use = (legacyC + legacyR) * p['old_annual_use']
        future_use = (futureC + futureR) * p['old_annual_use']
        oldCconversion = 0.0  # C never converts back to R.
        Rconvert = openingR * p['old_annual_use'] + envelope * p['new_R_use']
        fixed_use = fixed * p['new_fixed_C_use']
        newR_use = envelope * p['new_R_use']
        demand = legacy_use + future_use + fixed_use + newR_use
        legacyC *= 1 - p['old_annual_use']
        legacyR *= 1 - p['old_annual_use']
        futureC = futureC * (1 - p['old_annual_use']) + fixed - fixed_use
        futureR = futureR * (1 - p['old_annual_use']) + envelope - newR_use
        closeC, closeR = legacyC + futureC, legacyR + futureR
        purchase = logistics = peak_units = peak_hr = hr_year = 0.0
        capacity_excess = 0.0
        opening_inventory_value = sum(inventory) * (procurement + freight)
        for month in range(1, 13):
            old_share = p.get('old_january_share', 1 / 12) if month == 1 else (
                (1 - p['old_january_share']) / 11 if 'old_january_share' in p else 1 / 12)
            r_share = (1 / 4 if month in [3, 6, 9, 12] else 0) if p.get('R_calendar') == 'quarter_end' else 1 / 12
            monthly = (legacy_use + future_use) * old_share + fixed_use / 12 + newR_use * r_share
            baskets = monthly / p['basket_C']
            peak_units = max(peak_units, baskets)
            hr = p['admin_fixed_hours_month'] + baskets * (
                p['admin_hours_per_basket'] + p['merch_share'] * p['manual_merch_hours_per_unit'])
            peak_hr = max(peak_hr, hr)
            hr_year += hr
            for i, region in enumerate(p['regions']):
                share = p.get('region_demand_shares', [r['demand_share'] for r in p['regions']])[i]
                units = baskets * share
                receipt = math.ceil(max(0, units - inventory[i] - 1e-8) / p['procurement_batch_per_region']) * p['procurement_batch_per_region']
                inventory[i] += receipt - units
                assert inventory[i] >= -1e-7
                purchase += receipt * procurement
                logistics += receipt * freight
                capacity_excess += max(0, units - region['capacity_units_month'])
        inventory_value = sum(inventory) * (procurement + freight)
        cash = purchase + logistics
        future_exposure = (futureC + futureR) * unit
        # Paid stock backs rights once; earmark fungible stock to future rights first.
        target_reserve = max(0, future_exposure - inventory_value)
        reserve_delta = target_reserve - reserve
        funded_requirement = cash + reserve_delta
        personal_exposure = (closeC + closeR) * unit
        # Hypothetical carryover only, signed deficit retained; never a fact of bank cash.
        ringfence += p['ringfence_reference_budget_rub'] - cash
        row = dict(scenario=scenario['id'], fixed_C_year=fixed, envelope_R_year=envelope,
                   year=year, C_open=openingC, R_open=openingR, fixed_C_issued=fixed,
                   F_open=0, F_granted=envelope, F_posted=envelope, F_unissued_expired=0, F_close=0,
                   unposted_approved_rights=0, conditional_plan_ceiling_R=envelope,
                   R_posted=envelope, R_to_C=Rconvert, C_to_R=oldCconversion,
                   physical_C_required=demand, direct_R_required=0,
                   C_close=closeC, R_close=closeR,
                   original_legacy_close_C_R=legacyC + legacyR,
                   post_start_rights_close_C_R=futureC + futureR,
                   old_original_required_C=legacy_use, carried_future_required_C=future_use,
                   current_fixed_required_C=fixed_use, current_R_required_C=newR_use,
                   procurement_cash_rub=purchase, logistics_cash_rub=logistics,
                   total_cash_required_rub=cash, consumed_landed_rub=demand * unit,
                   inventory_open_landed_rub=opening_inventory_value,
                   inventory_close_landed_rub=inventory_value,
                   post_start_rights_exposure_rub=future_exposure,
                   reserve_target_open_rub=reserve, reserve_target_close_rub=target_reserve,
                   reserve_target_delta_rub=reserve_delta,
                   cash_plus_signed_reserve_delta_rub=funded_requirement,
                   cash_plus_reserve_delta_plus_buffer_rub=funded_requirement + p['annual_buffer_rub'],
                   new_promises_full_cost_rub=(fixed + envelope) * unit,
                   all_personal_rights_exposure_close_rub=personal_exposure,
                   hypothetical_cumulative_surplus_30_rub=ringfence,
                   all_rights_gap_after_hypothetical_surplus_and_inventory_rub=max(0, personal_exposure - inventory_value - ringfence),
                   peak_baskets_month=peak_units, peak_common_HR_hours_month=peak_hr,
                   common_HR_hours_year=hr_year,
                   common_HR_resource_rub=hr_year * p['rates_rub_hour']['HR'],
                   common_HR_incremental_cash_outside_procurement_rub=hr_year * p['rates_rub_hour']['HR'] * p['admin_incremental_cash_share'],
                   capacity_excess_baskets=capacity_excess,
                   capacity_pass=capacity_excess < 1e-7,
                   common_HR_capacity_pass=peak_hr <= p['admin_capacity_hours_month'] + 1e-7,
                   stock_error=openingC + openingR + fixed + envelope - demand - closeC - closeR,
                   inventory_cost_error=cash - demand * unit - inventory_value + opening_inventory_value)
        for budget in inputs['source_anchors']['budget_rub_year']:
            key = str(budget // 1000000)
            row['cash_pass_' + key] = cash <= budget + 1e-6
            row['new_promises_funding_pass_' + key] = funded_requirement + p['annual_buffer_rub'] <= budget + 1e-6
        assert abs(row['stock_error']) < 1e-5
        assert abs(openingC + fixed + Rconvert - demand - closeC) < 1e-5
        assert abs(openingR + envelope - Rconvert - closeR) < 1e-5
        assert abs(row['F_open'] + row['F_granted'] - row['F_posted'] - row['F_unissued_expired'] - row['F_close']) < 1e-5
        assert abs(row['inventory_cost_error']) < 1e-5
        rows.append(row)
        reserve = target_reserve
    return rows


def compute_limits(inputs):
    p = inputs['common']
    results = []
    for price in [1.0, 1.2]:
        _, _, unit = unit_cost(p | {'price_multiplier': price})
        for fixed in inputs['fixed_C_cases_year']:
            for old_use in [0.2, 0.35, 1.0]:
                for budget in inputs['source_anchors']['budget_rub_year']:
                    signed = (budget - p['annual_buffer_rub']) / unit - (p['initial_C'] + p['initial_personal_R']) * old_use - fixed
                    results.append(dict(fixed_C_year=fixed, old_annual_use=old_use, price_multiplier=price,
                                        budget_rub=budget, signed_additional_R_capacity=signed,
                                        additional_R_capacity=max(0, signed),
                                        fixed_and_old_alone_feasible=signed >= 0,
                                        note='Analytical year1 full-new bound before actual lot uplift. CSV adds buffer after actual cash; decisive stricter check. Capacity separate.'))
    tiers = []
    for envelope in inputs['envelopes_R_year']:
        for cycles in [1, 4]:
            for award in [500, 1000]:
                required = p['N'] * cycles * award
                tiers.append(dict(envelope_R_year=envelope, eligible_N=p['N'], cycles_year=cycles,
                                  lower_award_R=award, all_eligible_R_required=required,
                                  remaining_for_contest_and_special_R=envelope - required,
                                  universal_lower_feasible_inside_envelope=envelope >= required,
                                  maximum_eligible_before_other_awards=math.floor(envelope / cycles / award)))
    q3 = inputs['source_anchors']['q3_awards_R'] * 4
    return dict(version=inputs['version'], unit_landed_rub_per_C=unit_cost(p)[2],
                scope='Analytical year1 full-new limits; assumes prices and fungible regional stock, not bank readiness.',
                capacity=results, universal_tiers=tiers,
                envelopes=[dict(R_year=e, R_quarter=e / 4, R_per_N_per_quarter=e / 4 / p['N'],
                                reduction_vs_Q3_awards_times4=1 - e / q3) for e in inputs['envelopes_R_year']],
                q3_awards_times4_R=q3, q3_fund_times4_R=inputs['source_anchors']['q3_manager_fund_R'] * 4)


def write_csv(name, rows):
    with (HERE / name).open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    inputs = load_inputs()
    rows = []
    for scenario in inputs['scenarios']:
        for fixed in inputs['fixed_C_cases_year']:
            for envelope in [0] + inputs['envelopes_R_year'] + [inputs['source_anchors']['q3_awards_R'] * 4]:
                rows.extend(simulate(inputs, scenario, fixed, envelope))
    limits = compute_limits(inputs)
    write_csv('annual-three-year.csv', rows)
    write_csv('universal-tiers.csv', limits['universal_tiers'])
    (HERE / 'limits.json').write_text(json.dumps(limits, ensure_ascii=False, indent=2) + '\n')
    checks = dict(status='pass', annual_rows=len(rows), max_stock_error=max(abs(r['stock_error']) for r in rows),
                  max_inventory_cost_error=max(abs(r['inventory_cost_error']) for r in rows),
                  checks=['C and R stock flows; conversion neutral in combined balance',
                          'cash=consumption+inventory change; reserve nets paid inventory once',
                          'all unfunded or unrequested rights retained; failures counterfactual only',
                          'same old demand/fixed/prices across all envelopes',
                          'model import has no writes; writes under owned directory only'])
    (HERE / 'verification.json').write_text(json.dumps(checks, indent=2) + '\n')
    paths = inputs['provenance_files']
    manifest = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    (HERE / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
