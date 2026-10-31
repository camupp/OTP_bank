"""Branch B desk calculations. Writes only its own directory; no bank data or model execution."""
from pathlib import Path
from fractions import Fraction
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[1]
ROOT = HERE.parents[6]


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def table(name, rows):
    with (HERE / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def payout(n, unit, ranks, team_shares=None):
    """ranks: list of ties, each list contains unique unit IDs; empty qualification handled outside."""
    shares = [Fraction(4, 10), Fraction(3, 10), Fraction(2, 10), Fraction(1, 10)]
    pool = Fraction(n) * unit
    out = {}
    pos = 0
    for tied in ranks:
        value = sum(shares[pos:pos+len(tied)], Fraction(0)) * pool / len(tied)
        for uid in tied:
            portions = (team_shares or {}).get(uid, {uid: Fraction(1)})
            for person, fraction in portions.items():
                out[person] = int(value * fraction)
        pos += len(tied)
    return out


def fixed_for(month, novice=False):
    y = (month-1)//12
    m = (month-1)%12+1
    if novice and y == 0:
        return {1: 350, 2: 50, 3: 600, 6: 50}.get(m, 0)
    return {1: 150, 2: 50, 6: 50, 12: 1000}.get(m, 0)


def threshold_month(top_award, target, fixed=False, novice=False):
    balance = 0
    for m in range(1, 121):
        if m >= 4 and (m-4) % 3 == 0:
            balance += top_award
        if fixed:
            balance += fixed_for(m, novice)
        if balance >= target:
            return m
    return None


specs = {}
calendars, profiles, workload, edges = [], [], [], []
for e in [24000000, 36000000]:
    unit = Fraction(e * 3, 4) / (7200 * 4)
    contest = int(e * Fraction(3, 4))
    special = e-contest
    t, s = contest/12, special/12
    slots_lo, slots_hi = (50, 25) if e == 24000000 else (100, 25)
    assert slots_lo*5000 + slots_hi*10000 == s
    winner = int(40*unit*Fraction(4, 10))
    team = winner//5
    ordinary_min = winner//4
    specs[str(e)] = {
        "envelope_R_year": e,
        "annual_total_R": e,
        "lower_tier": {"award_R": 0, "annual_max_R": 0, "universal_extra_right": False},
        "stacking": {"personal_top_R_cycle_cap":25000 if e==24000000 else 37500,
                     "personal_all_channels_R_year_cap":120000 if e==24000000 else 170000,
                     "cap_is_nonbinding_for_n_max100":True,
                     "special_plus_top":"Only separate benefitID or independently proven incremental benefit excluded from ordinary metrics; one benefit one special award."},
        "contests": {
            "annual_max_R": contest, "cycles_year": 4,
            "group_pool_R_cycle_formula": f"{float(unit)}*n_unique_eligible",
            "unit_R_per_person_cycle": float(unit),
            "top_shares": [0.4, 0.3, 0.2, 0.1],
            "n40_top_R": [int(40*unit*x) for x in [Fraction(4,10), Fraction(3,10), Fraction(2,10), Fraction(1,10)]],
            "n40_eight_teams_five_member_R": [int(8*unit*x) for x in [Fraction(4,10), Fraction(3,10), Fraction(2,10), Fraction(1,10)]],
            "qualification": "Unrounded Q>=1.10 and all prior role QA/exposure bars. Rank floor(100Q+0.5)/100.",
            "n_range": [1, 100], "sum_unique_eligible_max": 7200,
            "team_rule": "One group pool and one award per team rank, then predeclared FTE shares sum<=1; failed shares remain unissued.",
            "tie_rule": "Equal share of occupied scheduled slots including zeros beyond rank4; final personal floor only; no renormalization.",
            "one_registered_unit": "top0", "one_qualified_of_many": "slot1 only, 40% pool; remaining60% unissued"
        },
        "special": {
            "annual_max_R": special, "monthly_max_R": s,
            "monthly_levels": [{"slots": slots_lo, "award_R": 5000}, {"slots": slots_hi, "award_R": 10000}],
            "personal_awards_year_max": 2, "personal_R_year_max": 20000,
            "team_result_R_max": 10000,
            "qualification": "Implemented benefit used by>=2 colleagues; independent beneficiary confirms actual useful difference;14days no critical/unresolved major; high level>=2 teams/processes.",
            "allocation": "Fixed slots by independently timestamped readiness within level. Exact timestamp ties share occupied slots. No future promise after exhaustion. One benefitID one award, no upgrade repayment.",
            "posting": "Ready by month28, independent U recognized month28, posted next month5; prospective work only.",
            "nomination": "Self-report allowed; recipient never approves own data/level/amount/exception/appeal/posting. Independent owner and separate nonrecipient operator."
        },
        "rights_calendar": {
            "stationary_top_R_month": t, "stationary_special_R_month": s,
            "stationary_total_R_month": e/12,
            "top_window_starts": "Cohorts2400 at month1/2/3 day15 then every3months; no retrospective observations.",
            "top_observation_months": 3, "top_quality_days": 14,
            "top_posting_lag_months": 3, "top_posting_day": 28,
            "special_posting_lag_months": 1, "special_posting_day": 5,
            "first_launch_posted_m1_m12_R": 9*t+11*s,
            "first_launch_promised_m1_m12_R": e,
            "first_launch_tail_m13_m15_R": 3*t+s,
            "gross_unposted_peak_R": 4*t+s,
            "gross_unposted_peak_interval": "day15..28 before prior top quality/posting;4top+current special",
            "day1_to5_unposted_ceiling_R": 3*t+2*s,
            "stop_new_windows_month": 36,
            "terminal_posting_month_top": 39, "terminal_posting_month_special": 37,
            "maximum_does_not_include": "Already personal C/R, legacy orders or existing fixed/unposted rights; these remain separately backed."
        },
        "sku_sensitivity": {
            "certificate_C_per_nominal_RUB": 5, "R_to_C": 1,
            "certificate_procurement_fraction_of_nominal": 1,
            "new_R_all_certificate_procurement_RUB": e/5,
            "M05_mixed_new_R_cost_RUB": e*0.194,
            "all_new_certificate_cost_uplift_vs_mixed_RUB": e*(0.2-0.194),
            "new_R_orders_if_all_500RUB_2500C_certificates": e/2500,
            "new_R_5000C_basket_equivalents": e/5000,
            "fees_service_capacity_bank_prices": None,
            "first_year_full_new_fixed96_old20_mixed_funding_RUB": 31540000 if e==24000000 else 33965000,
            "linear_certificate_only_new_R_adjusted_funding_RUB": (31540000 if e==24000000 else 33965000)+e*(0.2-0.194),
            "limit": "Linear sensitivity, not a recalculated lot/month cash model. Fixed/old backing unchanged. Full finance check required."
        }
    }
    for m in range(1, 40):
        ptop = t if m <= 36 else 0
        pspecial = s if m <= 36 else 0
        posted_t = t if 1 <= m-3 <= 36 else 0
        posted_s = s if 1 <= m-1 <= 36 else 0
        open_top = sum(t for start in range(1,37) if start<=m<start+3)
        unposted_special = s if m<=36 else 0
        calendars.append({"envelope_R_year":e,"month":m,"top_new_conditional_ceiling_R":ptop,
                          "special_new_finite_ceiling_R":pspecial,"top_posted_max_R":posted_t,
                          "special_posted_max_R":posted_s,"posted_total_R":posted_t+posted_s,
                          "end_conditional_top_R":open_top,"end_approved_unposted_special_U_R":unposted_special,
                          "end_not_personal_rights_ceiling_R":open_top+unposted_special,
                          "new_windows_stop_after_m36":True})
    for profile, amount, novice, action in [
        ("ordinary_no_top",0,False,"Q1.00/QA98 and normal exposure; no rank or separate benefit"),
        ("strong_repeat_winner",winner,False,"Q1.20/QA98; first individual place each qualified cycle n40"),
        ("novice",0,True,"Joins T0; Q1.00 after minimum; no top; no prior history"),
        ("team_member",team,False,"8teams*5 equalFTE; Q1.20; first team place, personal1/5"),
        ("part_time",0,False,"FTE0.5; normalized Q1.00/QA98; minimum reached; no top"),
        ("restricted_region",0,False,"Q1.00 no top; no local merch; digital brand/address suitability must be verified")]:
        for with_fixed in [False, True]:
            profiles.append({
                "candidate_key":"CON-017@v1","envelope_R_year":e,"profile":profile,
                "conditions":action,"corporate_events_case":with_fixed,
                "R_each_top_cycle":amount,"R_four_completed_cycles":4*amount,
                "R_calendar_first_year_m1_m12":3*amount,
                "C_corporate_first_year":(1050 if novice else 1250) if with_fixed else 0,
                "first_1500C_300RUB_month":threshold_month(amount,1500,with_fixed,novice),
                "first_2500C_500RUB_month":threshold_month(amount,2500,with_fixed,novice),
                "first_5000C_1000RUB_month":threshold_month(amount,5000,with_fixed,novice),
                "timing_scope":"C1 first top m4; C2/C3 +1/+2 months. Thresholds each independently assume no prior purchases. Actual receipt requires stocked suitableSKU+confirmation/service.",
                "no_old_balance":True,
                "dependence_on_competition":amount>0,
                "independent_confirmation":"Other data/QA owner and separate nonrecipient operator; no self-approval.",
                "alternative_not_assumed":"One separately implemented qualified benefit and an available finite5000R slot can reach5000C in one award; not granted to baseline fixture.",
                "team_or_quality_failure":"Ordinary teamQ1/no-top gives0R; failed QA/exposure gives0top and rights preserved in bank-error dispute.",
                "corporate_future_limit":"If rookie, year2+ uses explicit ordinary1250C/year hypothetical recurring calendar, not repeated rookie grants." if novice else "Only four specified annual events repeat; not all activities."
            })
    nreq = 200
    hr = 60.0
    # Retained operations from reference specification; no lower-removal labor saving.
    mgr = (60*30 + 240*3 + nreq*10 + (slots_lo+slots_hi)*5 + 120*8 + 72*5 + 12*8 + 10*20)/60
    emp = (nreq*6 + 120*5 + 72*3 + 2400*2)/60
    assert abs(mgr - (108.51666666666667 if e==24000000 else 112.68333333333334))<1e-8
    resource = 12*(hr*1000+mgr*1500+emp*1000+13*2000)
    specs[str(e)]["workload"] = {
        "HR_hours_month":hr,"manager_award_hours_month":mgr,"employee_process_hours_month":emp,
        "primary_QA_required_hours_month":800,"secondary_QA_manager_hours_in_award":12,
        "QA_existing_new_split":None,"actual_incremental_QA_formula":"max(0,800-verified_reusable_existing_hours)",
        "IT_recurring_hours_month":13,"ordinary_records_month":2400,"groups_month":60,
        "special_requests_month":nreq,"special_awards_month":slots_lo+slots_hi,
        "appeals_month":120,"corrections_month":72,"recusals_month":12,
        "flow_is_not_access_cap":True,
        "launch_one_off_hours":{"HR":62,"manager":188,"employee":1800,"IT":560},
        "new_vs_parent_one_off_hours":{"HR":4,"manager":4,"employee":0,"IT":16},
        "manual_export_fallback_additional_h_month":{"HR":20,"manager":80,"employee":0},
        "full_missing_source_additional_beyond_export_h_month":{"HR":0,"manager":700,"employee":1300},
        "rates_RUB_hour":{"HR":1000,"manager":1500,"employee":1000,"IT":2000},
        "annual_award_resource_RUB":resource,
        "annual_QA_required_resource_RUB":14400000,
        "annual_award_plus_primary_QA_required_resource_RUB":resource+14400000,
        "annual_award_resource_2x_RUB":2*resource,
        "annual_award_replacement25pct_cash_RUB":resource*.25,
        "annual_QA_plus_award_replacement25pct_cash_if_all_incremental_RUB":(resource+14400000)*.25,
        "launch_one_off_resource_RUB":62*1000+188*1500+1800*1000+560*2000,
        "useful_work_and_initial_evidence_creation_hours":None,
        "special_verification_timing_limit":"10manager minutes/request includes independent evidence reading, not creation or useful work; validate p95, no assumption actual hours zero."
    }
    for role,hours,rate in [("HR",hr,1000),("manager",mgr,1500),("employee",emp,1000),("IT",13,2000),("primary_QA",800,1500)]:
        workload.append({"envelope_R_year":e,"role":role,"required_hours_month":hours,"required_hours_year":hours*12,
                         "rate_RUB_hour":rate,"resource_RUB_year":hours*12*rate,"actual_incremental_hours":None,
                         "classification":"design workload; primaryQA existing/new unknown; resource not automatically additional cash"})
    for n in [1,2,5,10,40,60,100]:
        vals={} if n==1 else payout(n,unit,[[str(x)] for x in range(1,n+1)])
        edges.append({"envelope_R_year":e,"case":f"n{n}_distinct","pool_R":float(n*unit),"personal_payouts_R":json.dumps(vals),"total_posted_R":sum(vals.values()),"unissued_R":float(n*unit)-sum(vals.values())})
    vals=payout(40,unit,[[str(x) for x in range(40)]])
    edges.append({"envelope_R_year":e,"case":"n40_all_tie","pool_R":float(40*unit),"personal_payouts_R":json.dumps(vals),"total_posted_R":sum(vals.values()),"unissued_R":float(40*unit)-sum(vals.values())})
    vals=payout(40,unit,[["one_qualified"]])
    edges.append({"envelope_R_year":e,"case":"n40_one_qualified_of_many","pool_R":float(40*unit),"personal_payouts_R":json.dumps(vals),"total_posted_R":sum(vals.values()),"unissued_R":float(40*unit)-sum(vals.values())})
    vals=payout(40,unit,[[f"team{x}"] for x in range(8)],{f"team{x}":{f"{x}:{p}":Fraction(1,5) for p in range(5)} for x in range(8)})
    edges.append({"envelope_R_year":e,"case":"n40_8teams5_distinct","pool_R":float(40*unit),"personal_payouts_R":json.dumps(vals),"total_posted_R":sum(vals.values()),"unissued_R":float(40*unit)-sum(vals.values())})

spec={
    "schema_version":1,"candidate_key":"CON-017@v1","classification":"All mechanism numbers are design assumptions/calculations; M05 case facts retain locators. No independent finance admission.",
    "N_eligible":7200,"currency":"R; R_to_C=1; no fixed bank RUB exchange; certificate5C/RUB is common design scenario.",
    "scenarios":specs,
    "baseline_events":"supporting/employee-profiles.md, exact1250/1050C first year; no fixed/N or automatic full participation.",
    "unchanged_M05":"fixed96/144, legacyC160m/R40m, old20/35%, budgets30/34, price/capacity/stock rules unchanged. All new fund max is accounted, not expected small success rate.",
    "accounting_controls":["F and encumbered U distinct; U not extra currency","C and R separately balanced; R->C1:1 does not redeem","personal balances/orders/earned rights do not expire","paid suitable inventory counted once against backing","finite unused permissions not personal rights or new guarantee financing"],
    "self_award":"Recipient including HR/managers cannot set/approve own data, level, amount, exception, appeal or posting. Self-report allowed; independent owner and separate nonrecipient operator; no alternate means incident, preserved right.",
    "primary_metric_reference":"supporting/reference-mechanics/concept.md section2; Q/QA/exposure retained, no universallower.",
    "artifacts":{"calendar":"branches/B/calendar.csv","profiles":"branches/B/employee-profiles.csv","workload":"branches/B/workload.csv","edge_cases":"branches/B/edge-cases.csv"},
    "unknown_actual_bank_inputs":["N/groups","existingQA/source interfaces","catalog quote/fees/availability and region address","old/unposted rights and cash/inventory backing","labor capacities and existing/new split","perceived value and causal effect"]
}
save("finance-spec.json",spec)
table("calendar.csv",calendars)
table("employee-profiles.csv",profiles)
table("workload.csv",workload)
table("edge-cases.csv",edges)

assumptions=[
    ("B01","universal extra lower",0,"R/cycle","design","No new universal working-level reward; fixed retained"),
    ("B02","contest share",0.75,"share of E/year","design","Finite4slots40/30/20/10, all7200 pool ceilings"),
    ("B03","achievement share",0.25,"share of E/year","design","E24 50x5000+25x10000/month; E36 100x5000+25x10000/month"),
    ("B04","certificate pricing",5,"C/nominalRUB","common project hypothesis","No actual OTP quote/course; RtoC1:1"),
    ("B05","certificate procurement",1,"fraction of nominal","common cost scenario","No discount assumed; unknown service/fees added separately"),
    ("B06","top cohorts",3,"cohorts of2400people","retained design","Starts15thm1/2/3,3months+14dayquality; firstm4-6"),
    ("B07","achievement next-month posting",1,"month lag","design calendar","28th U/next5thposting; firstpossiblem2"),
    ("B08","special evidence use",2,"colleagues","design operational rule","Independent actual useful difference,14days quality; higher2teams/processes"),
    ("B09","special personal cap",2,"awards/year","retained form,new rates","20000R/year cap, distinct benefitIDs"),
    ("B10","workload requests",200,"requests/month","retained workload assumption","Not participation cap; all larger flow costed by proportional sensitivity"),
    ("B11","new configuration IT",16,"hours once","design","Plus retained544IT and4HR/4manager extra; no saving fromlowerremoval"),
    ("B12","fixed/old/budget/M05","unchanged","C/R/RUB/year","common scenario","Do not reduce existing obligations forpass"),
    ("B13","corporate path",1250,"C/year explicit events","common profile scenario","Newbie1050firstyear; not averagebank issuance"),
    ("B14","primaryQA",800,"hours/month","retained upper requirement","Existing/new unknown; teamQA deduplicated; secondary12separate"),
    ("B15","perceived usefulness","unknown","employee value","hypothesis","500/1000RUB may be more meaningful than small additions; no measured motivational effect")
]
table("assumptions.csv",[dict(zip(["id","parameter","value","unit_period","classification","basis_limit"],x)) for x in assumptions])
save("branch.json",{"branch_id":"B","status":"complete","candidates":[{"candidate_key":"CON-017@v1","path":"branches/B/concept-017.md","parents":["CON-015@v1"],"mechanism":"Corporatefixed retained; new universallower absent; finite larger quarterly4slots plus independent implemented-achievement places, at equalE24/E36."}],"failure_reason":None})

assert len(profiles)==24
assert len(calendars)==78
assert all(x["total_posted_R"]<=x["pool_R"] for x in edges)
for e in [24000000,36000000]:
    c=[x for x in calendars if x["envelope_R_year"]==e]
    assert abs(sum(x["posted_total_R"] for x in c)-3*e)<1e-6
    assert abs(sum(x["posted_total_R"] for x in c[:12])+c[11]["end_not_personal_rights_ceiling_R"]-e)<1e-6
    assert abs(sum(x["posted_total_R"] for x in c[36:])-c[35]["end_not_personal_rights_ceiling_R"])<1e-6
assert threshold_month(0,1500,True)==18
assert threshold_month(0,2500,True)==24
assert threshold_month(2000,2500,True)==7
assert threshold_month(3000,2500,False)==4
source_paths=[ROUND/"inputs/context.md",ROUND/"inputs/evidence.md",ROUND/"inputs/baseline.md",ROUND/"inputs/diagnosis.md",ROUND/"inputs/rubric.json",ROUND/"supporting/reward-basis.md",ROUND/"supporting/employee-profiles.md",ROUND/"supporting/finance-basis/scenario-inputs.json",ROUND/"supporting/reference-mechanics/concept.md"]
save("self-check.json",{
    "candidate_key":"CON-017@v1","status":"desk_arithmetic_pass_not_independent_admission",
    "checks":{"annual_pools_equal_E24_E36":True,"finite_slot_max_sums":True,"payout_never_exceeds_pool":True,"39month_posted_equals_3annual_funds":True,"launch_posted_plus_tail_equals_annual_fund":True,"stop36_tail_preserved":True,"six_profiles_both_funds_both_fixed_cases":True,"no_old_balances_assumed":True,"corporate1250_1050_events":True,"no_self_approval_rule":True,"no_other_branch_read_or_written":True},
    "outputs":{"profile_rows":len(profiles),"calendar_rows":len(calendars),"edge_rows":len(edges),"workload_rows":len(workload)},
    "source_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
    "limits":["No actual bank financial/operational readiness established","No motivational causal effect","No regional address/OTP quote or fee verification","Independent finance/evidence/reviewer required","Annual linear SKU uplift is sensitivity, not complete lot model"]
})
