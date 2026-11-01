"""Independent CSV/source arithmetic. Does not import candidate or sealed models.

Run with Python 3.12 from any directory. Writes only this finance/ directory.
Metric-level decisions outside base are checked as declared inputs to allocation;
the separate evidence check owns independent semantic verification of all gates.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
import importlib.util
import json
import math
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RD = HERE.parents[1]
RUN = RD.parents[1]
ROOT = RUN.parents[2]
OLD = ROOT / "analysis/iterations/iteration-006/rounds/001/checks/finance"
INC = RUN / "incumbent"
FIX = RD / "supporting/fixtures"
PATHS = {
    "CON-018@v1": RD / "branches/A/con-018",
    "CON-019@v1": RD / "branches/A/con-019",
    "CON-020@v1": RD / "branches/B/con-020",
    "CON-021@v1": RD / "branches/B/con-021",
}
CHECKS = []
FAILURES = []


def read(p):
    return json.loads(p.read_text())


def rows(p):
    return list(csv.DictReader(p.open()))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def table(name, data):
    if not data:
        return
    fields = list(dict.fromkeys(k for r in data for k in r))
    with (HERE / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)


def check(name, passed, detail=None):
    rec = {"name": name, "pass": bool(passed)}
    if detail is not None:
        rec["detail"] = detail
    CHECKS.append(rec)
    if not passed:
        FAILURES.append(rec)


def close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def truth(x):
    return x is True or x == "True"


def money_policy(d):
    out = json.loads(json.dumps({k: d[k] for k in (
        "N_eligible", "scenario_parameters", "guarantee", "contests", "special",
        "stacking", "calendar", "dated_prefunding", "no_self_award_controls",
    )}))
    for k in ("qualification", "part_time", "nonqualification", "newcomer"):
        out["guarantee"].pop(k)
    out["contests"].pop("ranking")
    out["calendar"].pop("source")
    return out


parent = read(INC / "finance-spec.json")
specs = {k: read(p / "finance-spec.json") for k, p in PATHS.items()}
pin = read(RD / "private/versions-before-checks.json")["files"]
pin_bad = [n for n, digest in pin.items() if sha(RD / n) != digest]
check("pinned finished candidates and inputs unchanged", not pin_bad, pin_bad)
check("source manifest unchanged", sha(FIX / "manifest.json") ==
      "2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc")
for key, s in specs.items():
    check(key + " monetary policy invariant", money_policy(s) == money_policy(parent))
for E, G, top, special in [(24000000, 2500, 4320000, 1680000),
                            (36000000, 3750, 6480000, 2520000)]:
    pars = parent["scenario_parameters"][str(E)]
    check(f"E{E} guarantee maximum", 7200 * G == pars["guarantee_max_R_year"])
    check(f"E{E} channel sum", 7200 * G + top + special == E)
    check(f"E{E} top annual", 7200 * 4 * pars["contest_R_eligible_cycle"] == top)
    check(f"E{E} special annual", 12 * sum(x["award_R"] * x["slots"]
          for x in pars["special_slots_month"]) == special)

# Reconcile stored, independently checked cash/stock trajectories without models.
core = []
for filename in ("structural-monthly.csv", "calendar-monthly.csv"):
    source = rows(OLD / filename)
    max_C = max_R = max_F = max_stock = max_reserve = 0.0
    for r in source:
        num = lambda k: float(r[k])
        max_C = max(max_C, abs(num("C_open") + num("fixed_C_issued") +
                    num("R_to_C") - num("required_redemption_C") - num("C_close")))
        max_R = max(max_R, abs(num("R_open") + num("R_posted") -
                    num("R_to_C") - num("R_close")))
        max_F = max(max_F, abs(num("F_granted") - num("F_posted") -
                    num("F_unissued_expired") - num("F_close")))
        # Cash includes landed procurement; inventory and issue reconcile at0.194/C.
        unit = 0.2316 if "PRICE20" in r["scenario"] else 0.194
        max_stock = max(max_stock, abs(num("inventory_open_RUB") + num("required_cash_RUB") -
                        num("required_redemption_C") * unit - num("inventory_close_RUB")))
        max_reserve = max(max_reserve, abs(num("reserve_close_RUB") -
                         max(0, num("new_personal_exposure_RUB") - num("inventory_close_RUB"))))
    residuals = dict(C=max_C, R=max_R, F=max_F, cash_stock=max_stock, reserve=max_reserve)
    check(filename + " independent balance equations", max(residuals.values()) < 1e-5, residuals)
    core.append(dict(file=filename, sha256=sha(OLD / filename), rows=len(source),
                     **{k + "_max_residual": v for k, v in residuals.items()}))
table("core-reconciliation.csv", core)

# Recompute9cohort all-success ceilings and conditional windows, months1..39.
calendar = []
for E in (24000000, 36000000):
    G = 2500 if E == 24000000 else 3750
    rate = F(150 if E == 24000000 else 225)
    stored = {int(r["month"]): r for r in rows(INC / "first-launch.csv") if int(r["E_R_year"]) == E}
    for m in range(1, 40):
        ordinary = [(c + 3 * k, c + 3 * k + 3) for c in range(1, 10)
                    for k in range(12) if c + 3 * k <= 36]
        windows = [(c + 12 * k, c + 12 * k + 6) for c in range(1, 10)
                   for k in range(3) if c + 12 * k <= 36]
        records = 800 * sum(end == m for start, end in ordinary)
        persons = 800 * sum(end == m for start, end in windows)
        g_open = 800 * G * sum(start <= m < end for start, end in windows)
        g_gross = 800 * G * sum(start <= m <= end for start, end in windows)
        top_open = 800 * rate * sum(start <= m < end for start, end in ordinary)
        special = F(140000 if E == 24000000 else 210000) if m <= 36 else F(0)
        post = persons * G + records * rate + special
        r = stored[m]
        pairs = {"ordinary_cycle_records": records, "guarantee_post_all_success_R": persons * G,
                 "top_full_all_success_R": records * rate, "special_full_R": special,
                 "R_post_all_success_max": post, "guarantee_conditional_open_endmonth_R": g_open,
                 "guarantee_gross_open_before_quality_close_R": g_gross,
                 "top_conditional_open_endmonth_R": top_open,
                 "total_conditional_open_endmonth_R": g_open + top_open}
        check(f"E{E}/m{m} independent cohort reconciliation", all(close(r[k], v) for k, v in pairs.items()))
        calendar.append(dict(E_R_year=E, month=m, ordinary_records=records, guarantee_persons=persons,
                             guarantee_R=persons * G, top_R=float(records * rate), special_R=float(special),
                             total_R=float(post), G_open_R=g_open, G_gross_R=g_gross,
                             top_open_R=float(top_open)))
table("calendar-reconciliation.csv", calendar)
for E in (24000000, 36000000):
    yr1 = sum(r["total_R"] for r in calendar if r["E_R_year"] == E and r["month"] <= 12)
    check(f"E{E} firstyear post bound", close(yr1, 15840000 * E / 24000000))

# Current monetary allocation: verify four-slot/tie/share arithmetic for all23source variants.
# The semantic correctness of the declared normal/stretch is not inferred from this check.
allocation = []
for key, p in PATHS.items():
    decisions = rows(p / "decisions.csv")
    is_A = "CON-018" in key or "CON-019" in key
    if is_A:
        groups = defaultdict(list)
        for r in decisions:
            groups[(r["scenario"], r["period_id"], r["group_id"])].append(r)
        for (scenario, period, group), people in groups.items():
            units = defaultdict(list)
            for r in people:
                units[r["unit_id"]].append(r)
            pool = 150 * len({r["subject_id"] for r in people})
            qualified = [u for u, ps in units.items() if any(truth(x["stretch"]) for x in ps)]
            kval = {u: Decimal(units[u][0]["value"]).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                    for u in qualified}
            ordered = sorted(set(kval.values()), reverse=True)
            expected = {}; pos = 0
            for val in ordered:
                tied = [u for u in qualified if kval[u] == val]
                prize = F(pool) * sum([F(4, 10), F(3, 10), F(2, 10), F(1, 10)][pos:pos + len(tied)]) / len(tied)
                expected.update({u: prize for u in tied}); pos += len(tied)
            for u, ps in units.items():
                for r in ps:
                    want = math.floor(expected.get(u, 0) * F(r["share"])) if truth(r["exposure_pass"]) else 0
                    check(f"{key}/{scenario}/{period}/{r['subject_id']} top arithmetic", close(want, r["top_R"]))
            posted = sum(float(r["top_R"]) for r in people)
            check(f"{key}/{scenario}/{period}/{group} pool bound", posted <= pool + 1e-6)
            allocation.append(dict(candidate_key=key, scenario=scenario, period=period, group=group,
                                   unique_people=len({r["subject_id"] for r in people}), pool_R=pool,
                                   declared_calculated_R=posted,
                                   group_held=any(truth(r["top_pending"]) for r in people)))
        wins = defaultdict(list)
        for r in decisions:
            wins[(r["scenario"], r["subject_id"], r["window_id"])].append(r)
        monetary = rows(p / "money-examples.csv")
        for (sc, person, window), ps in wins.items():
            want = 2500 if len(ps) == 2 and all(truth(r["normal"]) for r in ps) else 0
            actual = sum(float(r["guarantee_R"]) for r in monetary
                         if r["scenario"] == sc and r["subject_id"] == person and r["window_id"] == window)
            check(f"{key}/{sc}/{person} one G per fixed window", close(actual, want))
    else:
        units_all = rows(p / "unit-decisions.csv")
        groups = defaultdict(list)
        for r in units_all:
            groups[(r["scenario"], r["period"], r["group"])].append(r)
        for (scenario, period, group), units in groups.items():
            people = [r for r in decisions if r["scenario"] == scenario and r["period"] == period and r["group"] == group]
            pool = 150 * len({r["subject"] for r in people})
            held = any(r["state"] in ("pending", "not_computable") or r["stretch_state"] == "pending" for r in units)
            qualified = [r for r in units if truth(r["stretch"])]
            kval = {r["subject"]: tuple(F(x) for x in json.loads(r["rank_key"])) for r in qualified}
            expected = {}; pos = 0
            for val in sorted(set(kval.values()), reverse=True):
                tied = [u for u in kval if kval[u] == val]
                prize = F(pool) * sum([F(4, 10), F(3, 10), F(2, 10), F(1, 10)][pos:pos + len(tied)]) / len(tied)
                expected.update({u: prize for u in tied}); pos += len(tied)
            for r in people:
                want = math.floor(expected.get(r["unit"], 0) * F(r["share"])) if not held and r["state"] == "earned" else 0
                check(f"{key}/{scenario}/{period}/{r['subject']} top arithmetic", close(want, r["top_R"]))
            paid = sum(float(r["top_R"]) for r in people)
            check(f"{key}/{scenario}/{period}/{group} pool bound", paid <= pool + 1e-6)
            allocation.append(dict(candidate_key=key, scenario=scenario, period=period, group=group,
                                   unique_people=len({r["subject"] for r in people}), pool_R=pool,
                                   declared_calculated_R=paid, group_held=held))
        windows = rows(p / "window-guarantee.csv")
        for r in windows:
            ps = [x for x in decisions if x["scenario"] == r["scenario"] and x["subject"] == r["subject"] and x["window_id"] == r["window_id"]]
            want = 2500 if len(ps) == 2 and all(x["state"] == "earned" for x in ps) else 0
            check(f"{key}/{r['scenario']}/{r['subject']} one G per fixed window", close(want, r["guarantee_R"]))
table("allocation-controls.csv", allocation)

# Source-derived base metrics and money, without a candidate evaluator.
base = read(FIX / "source/base.json")
base_checks = []
for period in ("P1", "P2"):
    for subject in ("S01", "S02", "B01", "B02", "T01", "T02"):
        ev = [r for r in base["work_events"] if r["period_id"] == period and r["subject_id"] == subject]
        roots = {r["root_id"] for r in ev}
        acts = [r for r in base["quality_acts"] if r["period_id"] == period and r["subject_id"] == subject]
        scores = [max(0, 100 - 2 * r["minor"] - 10 * r["major"]) for r in acts]
        cap = next(r for r in base["roster_capacity"] if r["period_id"] == period and r["subject_id"] == subject)
        classes = {r["type_id"]: r["standard_units"] for r in base["classifier"]}
        volume = sum(classes[r["type_id"]] for r in ev)
        hours = (cap["scheduled_hours"] - cap["leave_hours"] - cap["training_hours"]) * cap["allocation_fraction"]
        normal18 = subject[0] != "T"
        stretch18 = subject in ("S02", "B02")
        normal19 = True; stretch19 = subject != "B01"
        normal20 = True; stretch20 = subject != "B01"
        normal21 = subject[0] == "T"; stretch21 = False
        # Base has accepted/resolved all roots; only B01 has one late SLA operation.
        for key, normal, stretch in [("CON-018@v1", normal18, stretch18), ("CON-019@v1", normal19, stretch19),
                                     ("CON-020@v1", normal20, stretch20), ("CON-021@v1", normal21, stretch21)]:
            rr = rows(PATHS[key] / ("decisions.csv" if key.startswith(("CON-018", "CON-019")) else "unit-decisions.csv"))
            actual = [r for r in rr if r["scenario"] == "base" and r.get("period_id", r.get("period")) == period
                      and r.get("unit_id", r.get("subject")) == subject]
            check(f"{key}/base/{period}/{subject} independent base normal/stretch", actual and
                  all(truth(r["normal"]) == normal and truth(r["stretch"]) == stretch for r in actual))
        base_checks.append(dict(period=period, subject=subject, unique_roots=len(roots), source_parts=len(ev),
                                compatible_QA_inspections=len(acts), mean_QA=sum(scores)/len(scores),
                                accepted_standard_units=volume, allocated_hours=hours,
                                capacity_ratio=volume/hours, project_root_norm_observed=False if subject[0]=="T" else "not applicable"))
table("base-source-controls.csv", base_checks)

# Resource figures: own algebra, source inspection units, common mix/readiness.
rates = {"HR": 1000, "manager": 1500, "employee": 1000, "IT": 2000}
existing_QA_h = (800 * 38 + 800 * 22 + 160 * 4.5) * 3 / 60
gap_census_h = (800 * 38 + 800 * 22 + 160 * 4.5) * 5 / 60
resource = []
# Control keeps its sampling requirement, adjusted from60to180same-size groups.
control = {"HR": 64 + 20 + 8, "manager": 106.26666666666665 + 60,
           "employee": 113.6, "IT": 15}
profiles = {
    "CON-016@v2": (control, (800*20+800*20+160*4.5)*5/60, "20-case capped sample; not census; computational coverage not admitted"),
    "CON-018@v1": ({"HR":96,"manager":442.26666666666665,"employee":113.6,"IT":15},gap_census_h,"all source case/part inspections"),
    "CON-019@v1": ({"HR":96,"manager":431.6,"employee":113.6,"IT":15},gap_census_h,"all source case/part inspections"),
    "CON-020@v1": ({"HR":72,"manager":244.26666666666668,"employee":0,"IT":24},gap_census_h,"common case/part scope; special operations not explicitly allocated"),
    "CON-021@v1": ({"HR":72,"manager":404.26666666666665,"employee":0,"IT":24},gap_census_h,"common case/part scope; special operations not explicitly allocated"),
}
for key, (roles, gaps, note) in profiles.items():
    for reuse in (0, 0.5, 1):
        for multiplier in (1, 2):
            gap = gaps*(1-reuse)
            recognition = sum(roles[k] * rates[k] for k in roles) * 12
            total = (recognition + gap * rates["manager"] * 12) * multiplier
            resource.append(dict(candidate_key=key, QA_compatible_reuse=reuse, labor_multiplier=multiplier,
                                 HR_new_h_month=roles["HR"]*multiplier,
                                 manager_recognition_h_month=roles["manager"]*multiplier,
                                 employee_process_h_month=roles["employee"]*multiplier,
                                 IT_h_month=roles["IT"]*multiplier, new_QA_h_month=gap*multiplier,
                                 existing_QA_h_month_separate=existing_QA_h,
                                 existing_QA_resource_RUB_year=existing_QA_h*1500*12,
                                 new_resource_RUB_year=total, substitution25pct_cash_RUB_year=total*.25,
                                 scope_note=note))
table("resources-comparable.csv", resource)

# Time-correct HR comparison: same source calendar, same fixed/old shop in each month.
cash_calendar = [r for r in rows(OLD / "calendar-monthly.csv") if r["candidate_key"]=="CON-016@v2"
                 and r["calendar"]=="all_good" and r["scenario"] in ("EXPECTED","FULL_NEW","JAN_OLD50","REGION80")]
timed = []
cal_index={(r["E_R_year"], r["month"]):r for r in calendar}
for r in cash_calendar:
    E = int(r["available_R_year"]);m=int(r["month"]);c=cal_index[E,m]
    records=c["ordinary_records"];Gpersons=c["guarantee_persons"]
    # M05 contains0.02h/basket plus manual merchandise. NewR certificates replace,
    # rather than add to, their mixed order handling; full certificate cost below is sensitivity.
    common=float(r["common_HR_h"])
    extra_small=float(r["R_posted"])*(1/2500-1/5000)*.02
    new_R_old_handling=float(r["R_posted"])/5000*(.02+.2*(2/60))
    fixed_old=common-new_R_old_handling
    new_R_certificate=float(r["R_posted"])/2500*.02
    for key in ("CON-016@v2",)+tuple(PATHS):
        if key.startswith(("CON-018", "CON-019")):
            recog=74+records*.35/60 # HR88 steady minus14record-related, source rule ledger0.1min+batch0.25min
        elif key.startswith(("CON-020", "CON-021")):
            recog=62+records*.15/60+Gpersons*.1/60
        else:
            recog=64 # original quote, common180group correction separate
        total=fixed_old+new_R_certificate+recog
        timed.append(dict(candidate_key=key,E_R_year=E,scenario=r["scenario"],fixed_C_year=r["fixed_C_year"],month=m,
                          fixed_old_shop_HR_h=fixed_old,new_R_certificate500_HR_h=new_R_certificate,
                          recognition_HR_h=recog,total_HR_h=total,capacity220_pass=total<=220,
                          boundary="time-correct declared recognition; control common180groups adds20h; unallocated special must be added"))
table("time-correct-HR.csv", timed)

# Cash gates scoped to M05procurement, not total labor funding or real readiness.
budget=[]
struct=rows(OLD/"structural-annual.csv")
cert=rows(OLD/"certificate-sensitivity.csv")
for E in (24000000,36000000):
    for scenario in ("EXPECTED","FULL_NEW","EXPECTED_OLD35","EXPECTED_PRICE20"):
        source=[r for r in struct if r["candidate_key"]=="CON-016@v2" and int(r["available_R_year"])==E and
                int(r["fixed_C_year"])==96000000 and r["scenario"]==scenario and int(r["year"])==1]
        if not source:continue
        r=source[0]; funding=float(r["cash_reserve_buffer_RUB"])
        # Nominal certificate price:0.2/C versus0.194/C; all new R redeemed, fee0.
        cert_total=funding+E*(.2-.194)
        for key in tuple(PATHS)+("CON-016@v2","BASELINE"):
            budget.append(dict(candidate_key=key,E_R_year=E,scenario=scenario,fixed_C_year=96000000,year=1,
                               mixed_cash_reserve_buffer_RUB=funding,new_R_certificate_total_RUB=cert_total,
                               mixed_pass30=funding<=30000000,mixed_pass34=funding<=34000000,
                               certificate_pass34=cert_total<=34000000,
                               scope="same envelope maximum, not measured bank budget/current personal allocation"))
table("budget-comparable.csv",budget)

save("verification.json", {"python":sys.version.split()[0],"method":"Own arithmetic; candidate/sealed models never imported or run; public JSON/CSV read only",
                          "checks":len(CHECKS),"failures":FAILURES,"all_arithmetic_checks_pass":not FAILURES,
                          "base_eligibility_check":"source-derived12role-periods; all other scenarios allocation arithmetic conditional on declared levels; evidence checks semantics separately",
                          "resource_scope":"published minutes are assumptions, incomplete special and QAcoverage flagged in report; actual bank labor unknown",
                          "checks_detail":CHECKS})
save("source-manifest.json", {str(p.relative_to(ROOT)):sha(p) for p in [INC/"finance-spec.json",INC/"first-launch.csv",FIX/"source/base.json",
    OLD/"structural-monthly.csv",OLD/"calendar-monthly.csv",OLD/"structural-annual.csv",OLD/"certificate-sensitivity.csv"]+
    [p/n for p in PATHS.values() for n in ("finance-spec.json","metrics-spec.json","decisions.csv","money-examples.csv")]})
print(json.dumps({"checks":len(CHECKS),"failures":FAILURES[:20],"outputs":len(list(HERE.glob('*.csv')))},ensure_ascii=False))
