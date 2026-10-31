"""Read-only checks of simple promises; never imports a candidate/common model."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[7]
ROUND = ROOT / "analysis/iterations/iteration-005/rounds/001"
OUT = ROUND / "checks/evidence"


def run():
    records = []
    files = []

    def check(key, label, actual, expected, unit="R/year"):
        records.append(dict(candidate_key=key, check=label, actual=actual,
                            expected=expected, unit=unit,
                            pass_=abs(actual - expected) < 1e-6))

    check("BASELINE", "Q3_awards_plus_unused", 19427591 + 19112409, 38540000, "R/Q3")
    check("BASELINE", "Q3_award_share_round1", round(19427591 / 38540000 * 100, 1), 50.4, "% Q3 fund")
    p = ROOT / "analysis/iterations/iteration-005/incumbent/finance-spec.json"
    d = json.loads(p.read_text())
    files.append(p)
    a = d["new_R_policy"]
    check("CON-009@v1", "monthly_sum", sum(a["monthly_issuance_ceiling_R"]), 8000000)
    check("CON-009@v1", "owners_quarters", a["fund_owners_count"] * a["fund_owner_quarter_ceiling_R"] * 4, 8000000)
    check("CON-009@v1", "minimum_events", 8000000 / 5000, 1600, "events/year maximum")
    check("CON-009@v1", "maximum_unique_share", 1600 / 7200 * 100, 22.22222222222222, "% scenario population")
    check("CON-009@v1", "reduction_from_Q3_times4", (1 - 8000000 / (19427591 * 4)) * 100, 89.70536285224452, "% scenario comparison")
    for p in sorted((ROUND / "branches").glob("*/CON-*/finance-spec.json")):
        files.append(p)
        d = json.loads(p.read_text())
        key = d["candidate_key"]
        lo = d["lower_tier"]
        n = lo.get("N", lo.get("N_eligible"))
        check(key, "all_eligible_lower", n * lo["cycles_year"] * lo["award_R"], lo["annual_max_R"])
        if key.startswith(("CON-011", "CON-012")):
            top = n * 4 * 62.5
            special = 12 * sum(x["slots"] * x["award_R"] for x in d["special"]["monthly_levels"])
            expected = 0.6 * 14400000 + 0.75 * 1800000 + 12 * (6 * 2500 + 2 * 7500)
            check(key, "forecast_only_not_guarantee", expected, 10350000)
        else:
            top = d["contests"]["groups"] * d["contests"]["cycles_year"] * sum(x["award_R"] * x["places_per_group_cycle"] for x in d["contests"]["top_tiers"])
            special = sum(x["award_R"] * x["max_count_year"] for x in d["special"]["levels"])
            check(key, "forecast_only_not_guarantee", .6 * 14400000 + .6 * 7200000 + .4 * 2400000, 13920000)
            for envelope, vals in d["envelope_policies"].items():
                if envelope.isdigit():
                    check(key, "alternative_calendar_" + envelope, sum(vals["monthly_R"]), int(envelope))
        check(key, "top_max", top, d["contests"]["annual_max_R"])
        check(key, "special_max", special, d["special"]["annual_max_R"])
        check(key, "total_max", lo["annual_max_R"] + top + special, d["annual_total_R"])
        check(key, "monthly_sum", sum(d["monthly_calendar_R"]), d["annual_total_R"])
        check(key, "basket_lower_only", 5000 / 500 / 4, 2.5, "years if every quarter qualifies")
    check("CON-012@v1", "low_base_floor_growth", (1 / max(.8, .95) - 1) * 100, 5.2631578947368425, "%")
    check("CON-012@v1", "strong_baseline_required_level", max(1.15, .98 * 1.30), 1.274, "Q")
    check("CON-014@v1", "team_first_share_six", 7500 / 6, 1250, "R/person/cycle")
    check("CON-013@v1", "four_equal_first_places", (7500 + 5000 + 2500) / 4, 3750, "R/person/cycle top")
    check("CON-014@v1", "four_equal_first_teams", (7500 + 5000 + 2500) / 4, 3750, "R/team/cycle top")
    granularity = []
    for n, thresholds in [(20, [.97, .98]), (8, [.95]), (10, [.9, .95, 1.0]), (60, [.97, .98, .99])]:
        for t in thresholds:
            k = math.ceil(n * t - 1e-12)
            granularity.append(dict(n=n, requested_min_fraction=t, required_passes=k,
                                    effective_min_fraction=k/n, percentage_point_step=100/n,
                                    assumption="Binary success proportion over exactly n equally weighted cases; no weighted QA rubric assumed."))
    frozen = [ROUND / "inputs" / x for x in ["context.md", "evidence.md", "diagnosis.md", "baseline.md", "rubric.json", "manifest.json"]]
    candidate_concepts = sorted((ROUND / "branches").glob("*/CON-*/concept.md"))
    extra = [ROOT / "analysis/iterations/iteration-005/incumbent/concept.md", ROOT / "analysis/iterations/iteration-005/incumbent/finance-projection.json", ROOT / "research/iteration-005/preparation/claims.json", ROOT / "research/iteration-005/preparation/evidence-brief.md", ROUND / "candidate-inputs.json", ROUND / "branches/A/branch.json", ROUND / "branches/B/branch.json"]
    manifest = [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in frozen + candidate_concepts + files + extra]
    result = dict(scope="Simple promise arithmetic and discrete proportions only; not independent recosting or program effectiveness.",
                  records=records, all_simple_checks_pass=all(r["pass_"] for r in records),
                  granularity=granularity, input_manifest=manifest)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "arithmetic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(checks=len(records), all_pass=result["all_simple_checks_pass"], inputs=len(manifest))))


if __name__ == "__main__":
    run()
