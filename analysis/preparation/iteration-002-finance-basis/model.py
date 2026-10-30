"""Compact common-basis model; stdlib only. Writes only beside this script."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "scenario-inputs.json"
data = json.loads(INPUT.read_text())
TOL = 0.00001


def write_csv(name, rows):
    with (ROOT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: round(v, 6) if isinstance(v, float) else v for k, v in row.items()})


def simulate(spec):
    p = dict(data["common"], **spec["overrides"])
    assert p["R_conversion_fraction_old_and_new"] + p["R_direct_fraction_old_and_new"] <= 1
    assert abs(sum(p["R_award_month_shares_in_quarter"]) - 1) < TOL
    assert abs(p["procurement_same_month_payment_fraction"] + p["procurement_next_month_payment_fraction"] - 1) < TOL
    C, R, F = p["C0"], p["R0"], p["F0"]
    group_a = group_b = C / 2  # Two synthetic pools, not individual employee data.
    queue_c = queue_r = prev_purchase = prev_required_purchase = 0.0
    annual = {k: 0.0 for k in [
        "I_C", "G_R", "W_R", "X_R_to_C", "F_expired_R", "C_requested", "C_redeemed",
        "R_direct_requested", "R_direct_redeemed", "basket_units_required", "basket_units_served",
        "R_units_required", "R_units_served", "procurement_required_rub", "procurement_actual_rub",
        "reward_cash_required_rub", "reward_cash_actual_rub", "R_resource_required_rub",
        "R_resource_actual_rub", "R_cash_required_rub", "R_cash_actual_rub", "admin_hours", "admin_resource_rub",
        "admin_cash_rub"]}
    max_errors, rows = [], []
    peak_basket = peak_direct = peak_admin = 0.0
    weights = [1 / 12] * 12 if p["old_requests_calendar"] == "uniform" else [0.5] + [0.5 / 11] * 11
    weights[-1] = 1 - sum(weights[:-1])
    unit_cost = p["basket_nominal_rub"] * p["basket_cost_to_nominal"] * p["purchase_price_multiplier"]
    for m in range(1, 13):
        C_start, R_start, F_start = C, R, F
        G = p["F_grant_per_quarter_R"] if (m - 1) % 3 == 0 else 0
        W = p["R_awarded_per_quarter"] * p["R_award_month_shares_in_quarter"][(m - 1) % 3]
        F += G
        assert W <= F + TOL
        F -= W
        E = F if m % 3 == 0 else 0
        F -= E
        I = p["I_C_per_year"] / 12
        cohort_r = p["R0"] * weights[m - 1] + W
        X = cohort_r * p["R_conversion_fraction_old_and_new"]
        req_r = cohort_r * p["R_direct_fraction_old_and_new"]
        req_c = p["C0"] * p["C_old_request_fraction"] * weights[m - 1] + I * p["C_new_request_fraction"] + X * p["converted_C_request_fraction"]
        R += W - X
        C += I + X
        queue_c += req_c
        queue_r += req_r
        # Reservations are included in C/R. Only fulfilled rewards debit rights.
        assert queue_c <= C + TOL and queue_r <= R + TOL
        served_c = min(queue_c, p["basket_delivery_capacity_units_per_month"] * p["basket_C_price"])
        served_r = min(queue_r, p["R_direct_capacity_units_per_month"] * p["R_direct_price_per_unit"])
        C -= served_c
        R -= served_r
        queue_c -= served_c
        queue_r -= served_r
        net_transfer = p["C_transfer_A_to_B_per_month"] - p["C_transfer_B_to_A_per_month"]
        # Emission, conversion and redemptions split equally between the pools.
        available_a = group_a + (I + X) / 2
        available_b = group_b + (I + X) / 2
        assert available_a >= p["C_transfer_A_to_B_per_month"]
        assert available_b + p["C_transfer_A_to_B_per_month"] >= p["C_transfer_B_to_A_per_month"]
        group_a += (I + X - served_c) / 2 - net_transfer
        group_b += (I + X - served_c) / 2 + net_transfer
        assert min(C, R, F, group_a, group_b, queue_c, queue_r) >= -TOL
        errors = [C - C_start - I - X + served_c,
                  R - R_start - W + X + served_r,
                  F - F_start - G + W + E,
                  C + R + F - C_start - R_start - F_start - I - G + served_c + served_r + E,
                  C - group_a - group_b]
        max_errors.extend(abs(x) for x in errors)
        basket_req, basket_served = req_c / p["basket_C_price"], served_c / p["basket_C_price"]
        direct_req, direct_served = req_r / p["R_direct_price_per_unit"], served_r / p["R_direct_price_per_unit"]
        purchase_req, purchase = basket_req * unit_cost, basket_served * unit_cost
        opening_due = p["opening_supplier_payables_rub"] if m == 1 else 0
        same, lag = p["procurement_same_month_payment_fraction"], p["procurement_next_month_payment_fraction"]
        cash_req = opening_due + purchase_req * same + prev_required_purchase * lag
        cash = opening_due + purchase * same + prev_purchase * lag
        admin_h = p["admin_fixed_hours_per_month"] + basket_req * p["admin_hours_per_basket"] + direct_req * p["admin_hours_per_R_direct_unit"]
        admin_cost = admin_h * p["resource_rub_per_hour"]
        r_unit_resource = p["R_direct_hours_per_unit"] * p["resource_rub_per_hour"]
        row = dict(scenario=spec["id"], month=m, I_C=I, G_R=G, W_R=W, X_R_to_C=X, F_expired_R=E,
                   C_requested=req_c, C_redeemed=served_c, R_direct_requested=req_r, R_direct_redeemed=served_r,
                   C_close=C, R_close=R, F_close=F, C_request_backlog=queue_c, R_request_backlog=queue_r,
                   basket_units_required=basket_req, basket_units_served=basket_served,
                   R_units_required=direct_req, R_units_served=direct_served,
                   procurement_required_rub=purchase_req, procurement_actual_rub=purchase,
                   reward_cash_required_rub=cash_req, reward_cash_actual_rub=cash,
                   R_resource_required_rub=direct_req * r_unit_resource,
                   R_resource_actual_rub=direct_served * r_unit_resource,
                   R_cash_required_rub=direct_req * r_unit_resource * p["R_direct_cash_share_of_resource"],
                   R_cash_actual_rub=direct_served * r_unit_resource * p["R_direct_cash_share_of_resource"],
                   admin_hours=admin_h, admin_resource_rub=admin_cost,
                   admin_cash_rub=admin_cost * p["admin_cash_share_of_resource"])
        for k in annual:
            annual[k] += row[k]
        peak_basket, peak_direct, peak_admin = max(peak_basket, basket_req), max(peak_direct, direct_req), max(peak_admin, admin_h)
        rows.append(row)
        prev_purchase, prev_required_purchase = purchase, purchase_req
    ap = prev_purchase * lag
    ap_req = prev_required_purchase * lag
    cash_err = annual["reward_cash_actual_rub"] - p["opening_supplier_payables_rub"] - annual["procurement_actual_rub"] + ap
    req_cash_err = annual["reward_cash_required_rub"] - p["opening_supplier_payables_rub"] - annual["procurement_required_rub"] + ap_req
    max_errors.extend([abs(cash_err), abs(req_cash_err)])
    assert max(max_errors) < TOL
    factor = p["basket_cost_to_nominal"] * p["purchase_price_multiplier"]
    nominal = annual["C_requested"] * p["basket_nominal_rub"] / p["basket_C_price"]
    nominal_dec = rows[-1]["C_requested"] * p["basket_nominal_rub"] / p["basket_C_price"]
    result = dict(scenario=spec["id"], **annual, C_close=C, R_close=R, F_close=F,
                  C_request_backlog=queue_c, R_request_backlog=queue_r,
                  supplier_AP_close_rub=ap, supplier_AP_required_close_rub=ap_req,
                  basket_inventory_units_open=p["basket_inventory_units_open_and_close"],
                  basket_inventory_units_close=p["basket_inventory_units_open_and_close"],
                  peak_basket_units_required=peak_basket, peak_R_units_required=peak_direct, peak_admin_hours=peak_admin,
                  cost_factor_including_prices=factor,
                  full_resource_cost_required_rub=annual["procurement_required_rub"] + annual["R_resource_required_rub"] + annual["admin_resource_rub"],
                  all_cash_required_rub=annual["reward_cash_required_rub"] + annual["R_cash_required_rub"] + annual["admin_cash_rub"],
                  all_cash_actual_rub=annual["reward_cash_actual_rub"] + annual["R_cash_actual_rub"] + annual["admin_cash_rub"],
                  all_remaining_rights_if_converted_procurement_exposure_rub=(C + R) * unit_cost / p["basket_C_price"],
                  max_reconciliation_error=max(max_errors))
    checks = dict(scenario=spec["id"], currency_balances="pass", scope="aggregate illustrative pools, not actual employee subledger",
                  capacity="pass" if peak_basket <= p["basket_delivery_capacity_units_per_month"] + TOL and peak_direct <= p["R_direct_capacity_units_per_month"] + TOL and peak_admin <= p["admin_capacity_hours_per_month"] + TOL else "fail",
                  actual_bank_feasibility="uncertain", narrow_budget={})
    for B in p["budgets_rub_year"]:
        required = max(annual["reward_cash_required_rub"], annual["procurement_required_rub"])
        result[f"narrow_headroom_{B}_rub"] = B - required
        result[f"max_cost_factor_{B}"] = min(B / nominal, (B - p["opening_supplier_payables_rub"]) / (nominal - lag * nominal_dec))
        checks["narrow_budget"][str(B)] = "pass" if required <= B + TOL else "fail"
    return result, rows, checks


if __name__ == "__main__":
    for source in data["sources"].values():
        if "sha256" in source:
            assert hashlib.sha256((ROOT.parents[2] / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    assert data["source_anchors"]["quarter_q3_distributed_R_contextual_interpretation"] + data["source_anchors"]["quarter_q3_unused_R"] == data["source_anchors"]["quarter_q3_fund_R"]
    assert abs(data["common"]["basket_certificate_nominal_share"] * data["common"]["certificate_cost_to_nominal"] + data["common"]["basket_merch_nominal_share"] * data["common"]["merch_cost_to_nominal"] - data["common"]["basket_cost_to_nominal"]) < TOL
    annual, monthly, checks = [], [], []
    for scenario in data["scenarios"]:
        a, m, c = simulate(scenario)
        annual.append(a)
        monthly.extend(m)
        checks.append(c)
    write_csv("annual-results.csv", annual)
    write_csv("monthly-results.csv", monthly)
    report = dict(schema_version=1, phase="shared preparation before concept generation", results=[],
                  scenario_scope="Eight fully specified illustrative scenarios; narrow procurement/payment checks at30 and34million RUB, not bank forecasts or candidate gates",
                  basis_validation={"currency_balances": "pass", "budget": "uncertain", "explanation": "Arithmetic and specified stock-flow cases verified. Several adverse cases exceed budget/capacity. No candidate assessed and no actual bank parameter set verified."},
                  scenario_checks=checks, evidence_refs=data["sources"], assumption_refs=["assumptions.csv", "scenario-inputs.json"],
                  calculation_paths=["model.py", "annual-results.csv", "monthly-results.csv", "validation.json"],
                  findings=["Queued requests remain inside personal balances and are not additional currency stocks.", "Full-demand requirements drive narrow budget checks; constrained deliveries cannot create a budget pass.", "Cash for direct R rewards and HR administration is outside30/34million procurement cap and needs separately disclosed funding.", "No legal accounting liability or actual funding outside procurement cap is inferred."])
    (ROOT / "finance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    validation = dict(status="pass", scenarios=len(annual), monthly_rows=len(monthly),
                      tolerance_units_and_rub=TOL, max_reconciliation_error=max(a["max_reconciliation_error"] for a in annual),
                      checks=["primary PDF and organizer export SHA-256", "Q3 fund arithmetic", "base basket weighted cost", "all monthly C/R/F and combined identities", "internal transfers conserve C and synthetic pools stay nonnegative", "only unissued F expires quarterly", "requests/reservations are bounded by personal balances", "procurement-payment-payable identity for required and actual delivery", "no personal expiry or negative balance"],
                      limitations=["Fractional normalized rewards represent an aggregate portfolio; no indivisible-person schedule verified", "No actual bank ledger or procurement quotations", "Not all sensitivity-bound combinations tested", "Service backlog admin rework not priced; candidate dependency must be checked"],
                      sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [INPUT, Path(__file__)]})
    (ROOT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(status="pass", scenarios=len(annual), monthly_rows=len(monthly), max_reconciliation_error=validation["max_reconciliation_error"])))
