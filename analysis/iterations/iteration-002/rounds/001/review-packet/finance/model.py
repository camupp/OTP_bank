"""Independent compact financial check of frozen v1 concepts; Python stdlib only.
No preparation models are imported or executed. All outputs stay in checks/finance.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROUND = OUT.parent.parent
EPS = 1e-5
KEYS = ["V01", "V03", "V02"]
POLICIES = {
    "V01": dict(extra_hr_month=0, other_hours_month=0, gifts_year=0),
    "V03": dict(extra_hr_month=40, other_hours_month=40 + 86.66666666666667, gifts_year=0, I_C_per_year=48000000, F_grant_per_quarter_R=0, R_awarded_per_quarter=0),
    "V02": dict(extra_hr_month=18, other_hours_month=60 + 157.5, gifts_year=7200, I_C_per_year=0, F_grant_per_quarter_R=0, R_awarded_per_quarter=0)
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (0.0 if abs(v) < 5e-7 else round(v, 6)) if isinstance(v, float) else v for k, v in r.items()})


def take(queue, capacity):
    served = 0
    while queue and capacity > EPS:
        tag, value = queue[0]
        n = min(value, capacity)
        served += n
        capacity -= n
        if value - n < EPS:
            queue.pop(0)
        else:
            queue[0] = (tag, value - n)
    return served


def qsum(q, tag=None):
    return sum(v for t, v in q if tag is None or t == tag)


def run(m01, key, scenario, year=1, opening=None, extra=None):
    p = dict(m01["common"], **scenario["overrides"])
    policy = POLICIES[key]
    p.update({k: v for k, v in policy.items() if k in p})
    if opening:
        p.update(C0=opening["C_close"], R0=opening["R_close"], opening_supplier_payables_rub=opening["AP_actual_close_rub"])
        assert opening["C_queue_close"] < EPS and opening["R_queue_close"] < EPS and opening["J_close"] < EPS
    if extra:
        p.update(extra)
    assert p["R_conversion_fraction_old_and_new"] + p["R_direct_fraction_old_and_new"] <= 1
    C, R, F, J = p["C0"], p["R0"], p["F0"], 0
    A = opening["C_pool_A"] if opening else C / 2
    B = opening["C_pool_B"] if opening else C / 2
    qc, qr = [], []
    jq_due, purchase_prev, requirement_prev = 0, 0, 0
    old_weights = [1 / 12] * 12 if p["old_requests_calendar"] == "uniform" else [0.5] + [0.5 / 11] * 11
    old_weights[-1] = 1 - sum(old_weights[:-1])
    kprice = p["basket_cost_to_nominal"] * p["purchase_price_multiplier"]
    unit_cost = p["basket_nominal_rub"] * kprice
    months, errors = [], []
    for m in range(1, 13):
        Cs, Rs, Fs, Js = C, R, F, J
        G = p["F_grant_per_quarter_R"] if m % 3 == 1 else 0
        W = p["R_awarded_per_quarter"] * p["R_award_month_shares_in_quarter"][(m - 1) % 3]
        F += G - W
        E = F if m % 3 == 0 else 0
        F -= E
        I = p["I_C_per_year"] / 12
        xold = p["R0"] * old_weights[m - 1] * p["R_conversion_fraction_old_and_new"]
        xnew = W * p["R_conversion_fraction_old_and_new"]
        X = xold + xnew
        dcold = p["C0"] * p["C_old_request_fraction"] * old_weights[m - 1]
        dcnew = I * p["C_new_request_fraction"]
        dcconv = X * p["converted_C_request_fraction"]
        drold = p["R0"] * p["R_direct_fraction_old_and_new"] * old_weights[m - 1]
        drnew = W * p["R_direct_fraction_old_and_new"]
        dc, dr = dcold + dcnew + dcconv, drold + drnew
        qc.extend([("old_C", dcold), ("new_C", dcnew), ("converted_C", dcconv)])
        qr.extend([("old_R", drold), ("new_R", drnew)])
        C += I + X
        R += W - X
        grant_j = policy["gifts_year"] if m == 1 else 0
        due_j = policy["gifts_year"] / 12
        J += grant_j
        jq_due += due_j
        assert qsum(qc) <= C + EPS and qsum(qr) <= R + EPS and jq_due <= J + EPS
        pc = take(qc, p["basket_delivery_capacity_units_per_month"] * p["basket_C_price"])
        pr = take(qr, p["R_direct_capacity_units_per_month"] * p["R_direct_price_per_unit"])
        gift_served = min(jq_due, p["basket_delivery_capacity_units_per_month"] - pc / p["basket_C_price"])
        C -= pc
        R -= pr
        J -= gift_served
        jq_due -= gift_served
        a_available, b_available = A + (I + X) / 2, B + (I + X) / 2
        assert a_available >= p["C_transfer_A_to_B_per_month"] and b_available + p["C_transfer_A_to_B_per_month"] >= p["C_transfer_B_to_A_per_month"]
        transfer = p["C_transfer_A_to_B_per_month"] - p["C_transfer_B_to_A_per_month"]
        A += (I + X - pc) / 2 - transfer
        B += (I + X - pc) / 2 + transfer
        assert min(C, R, F, J, A, B, jq_due) >= -EPS
        # New C authority is a permission, not issued currency or a personal balance.
        authority_grant = 4000000 if key == "V03" else 0
        authority_spent = I if key == "V03" else 0
        authority_lapsed = authority_grant - authority_spent
        assert authority_lapsed >= -EPS
        errors.extend([abs(C - Cs - I - X + pc), abs(R - Rs - W + X + pr), abs(F - Fs - G + W + E),
                       abs(J - Js - grant_j + gift_served), abs(A + B - C),
                       abs(C + R + F - Cs - Rs - Fs - I - G + pc + pr + E)])
        baskets_req, baskets_actual = dc / p["basket_C_price"] + due_j, pc / p["basket_C_price"] + gift_served
        services_req, services_actual = dr / p["R_direct_price_per_unit"], pr / p["R_direct_price_per_unit"]
        procurement_req, procurement_actual = baskets_req * unit_cost, baskets_actual * unit_cost
        same, lag = p["procurement_same_month_payment_fraction"], p["procurement_next_month_payment_fraction"]
        due_ap = p["opening_supplier_payables_rub"] if m == 1 else 0
        cash_req, cash_actual = due_ap + same * procurement_req + lag * requirement_prev, due_ap + same * procurement_actual + lag * purchase_prev
        hr = p["admin_fixed_hours_per_month"] + p["admin_hours_per_basket"] * baskets_req + p["admin_hours_per_R_direct_unit"] * services_req + policy["extra_hr_month"]
        r_resource = services_req * p["R_direct_hours_per_unit"] * p["resource_rub_per_hour"]
        r_cash = r_resource * p["R_direct_cash_share_of_resource"]
        hr_resource = hr * p["resource_rub_per_hour"]
        hr_cash = hr_resource * p["admin_cash_share_of_resource"]
        other_resource = policy["other_hours_month"] * p["resource_rub_per_hour"]
        row = dict(candidate_key=key, scenario=scenario["id"], year=year, month=m, I_C=I, G_R=G, W_R=W, conversion_R_to_C=X,
                   C_requested=dc, R_requested=dr, C_redeemed=pc, R_redeemed=pr, F_expired=E,
                   C_close=C, R_close=R, F_close=F, C_pool_A=A, C_pool_B=B,
                   C_queue_close=qsum(qc), C_queue_old=qsum(qc, "old_C"), C_queue_new=qsum(qc, "new_C"), C_queue_converted=qsum(qc, "converted_C"),
                   R_queue_close=qsum(qr), R_queue_old=qsum(qr, "old_R"), R_queue_new=qsum(qr, "new_R"),
                   J_issued=grant_j, J_due=due_j, J_served=gift_served, J_close=J, J_overdue=jq_due,
                   C_authority_grant=authority_grant, C_authority_used=authority_spent, C_authority_lapsed=authority_lapsed,
                   basket_units_required=baskets_req, basket_units_actual=baskets_actual, R_units_required=services_req, R_units_actual=services_actual,
                   procurement_required_rub=procurement_req, procurement_actual_rub=procurement_actual,
                   reward_cash_required_rub=cash_req, reward_cash_actual_rub=cash_actual,
                   AP_required_close_rub=lag * procurement_req, AP_actual_close_rub=lag * procurement_actual,
                   R_hours_required=services_req * p["R_direct_hours_per_unit"], R_resource_required_rub=r_resource, R_cash_required_rub=r_cash,
                   HR_hours=hr, HR_resource_rub=hr_resource, HR_cash_rub=hr_cash,
                   other_internal_hours=policy["other_hours_month"], other_internal_resource_rub=other_resource,
                   all_cash_required_rub=cash_req + r_cash + hr_cash,
                   scoped_resource_cost_required_rub=procurement_req + r_resource + hr_resource + other_resource,
                   basket_stock_open=p["basket_inventory_units_open_and_close"], basket_stock_close=p["basket_inventory_units_open_and_close"])
        errors.append(abs(row["basket_stock_open"] + baskets_actual - baskets_actual - row["basket_stock_close"]))
        months.append(row)
        requirement_prev, purchase_prev = procurement_req, procurement_actual
    totals = ["I_C", "G_R", "W_R", "conversion_R_to_C", "C_requested", "R_requested", "C_redeemed", "R_redeemed", "F_expired", "J_issued", "J_due", "J_served", "C_authority_grant", "C_authority_used", "C_authority_lapsed", "basket_units_required", "basket_units_actual", "R_units_required", "R_units_actual", "procurement_required_rub", "procurement_actual_rub", "reward_cash_required_rub", "reward_cash_actual_rub", "R_hours_required", "R_resource_required_rub", "R_cash_required_rub", "HR_hours", "HR_resource_rub", "HR_cash_rub", "other_internal_hours", "other_internal_resource_rub", "all_cash_required_rub", "scoped_resource_cost_required_rub"]
    annual = dict(candidate_key=key, scenario=scenario["id"], year=year, C_open=p["C0"], R_open=p["R0"], AP_open_rub=p["opening_supplier_payables_rub"], **{k: sum(r[k] for r in months) for k in totals})
    for k in ["C_close", "R_close", "F_close", "C_pool_A", "C_pool_B", "C_queue_close", "C_queue_old", "C_queue_new", "C_queue_converted", "R_queue_close", "R_queue_old", "R_queue_new", "J_close", "J_overdue", "AP_required_close_rub", "AP_actual_close_rub"]:
        annual[k] = months[-1][k]
    for k in ["basket_units_required", "R_units_required", "HR_hours", "C_queue_close", "R_queue_close", "J_overdue"]:
        annual["peak_" + k] = max(r[k] for r in months)
    annual["capacity_pass"] = annual["peak_basket_units_required"] <= p["basket_delivery_capacity_units_per_month"] + EPS and annual["peak_R_units_required"] <= p["R_direct_capacity_units_per_month"] + EPS and annual["peak_HR_hours"] <= p["admin_capacity_hours_per_month"] + EPS
    annual["external_cash_required_rub"] = annual["R_cash_required_rub"] + annual["HR_cash_rub"]
    if key == "V03":
        annual["scoped_external_envelope_pass"] = annual["R_cash_required_rub"] <= 3000000 + EPS and annual["HR_cash_rub"] <= 600000 + EPS
    elif key == "V02":
        annual["scoped_external_envelope_pass"] = annual["external_cash_required_rub"] <= 2750000 + EPS
    else:
        annual["scoped_external_envelope_pass"] = "not_specified_in_baseline"
    nominal = annual["basket_units_required"] * p["basket_nominal_rub"]
    nominal_dec = months[-1]["basket_units_required"] * p["basket_nominal_rub"]
    for budget in [30000000, 34000000]:
        annual[f"narrow_budget_{budget}_pass"] = max(annual["procurement_required_rub"], annual["reward_cash_required_rub"]) <= budget + EPS
        annual[f"headroom_{budget}_rub"] = budget - max(annual["procurement_required_rub"], annual["reward_cash_required_rub"])
        annual[f"max_kp_{budget}"] = min(budget / nominal, (budget - p["opening_supplier_payables_rub"]) / (nominal - lag * nominal_dec))
    for required in [True, False]:
        suffix = "required" if required else "actual"
        errors.append(abs(annual[f"reward_cash_{suffix}_rub"] - annual["AP_open_rub"] - annual[f"procurement_{suffix}_rub"] + annual[f"AP_{suffix}_close_rub"]))
    annual["remaining_C_R_if_converted_procurement_exposure_rub"] = (C + R) / p["basket_C_price"] * unit_cost
    annual["max_reconciliation_error"] = max(errors)
    assert max(errors) < EPS
    return annual, months


def numeric_claim(value):
    tokens = re.findall(r"\d+(?:[,.]\d+)?", value.replace(" ", ""))
    return [(float(t.replace(",", ".")), 0.50001 * 10 ** (-len(t.split(",")[1]) if "," in t else -len(t.split(".")[1]) if "." in t else 0)) for t in tokens]


# Arithmetic functions retained; administrative original-path validation is excluded from this review copy.
