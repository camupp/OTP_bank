"""Independent simple checks; reads frozen artifacts, writes only evidence/ ."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal, ROUND_DOWN
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[7]
R = ROOT / 'analysis/iterations/iteration-005/rounds/002'
OUT = R / 'checks/evidence'


def main():
    checks = []

    def check(key, name, actual, expected, unit='R'):
        checks.append(dict(candidate_key=key, name=name, actual=actual,
                           expected=expected, unit=unit,
                           passed=abs(float(actual)-float(expected)) < 1e-6))

    paths = [R/'branches/A/finance-spec-013.json', R/'branches/B/finance-spec-011.json']
    specs = [json.loads(p.read_text()) for p in paths]
    for d in specs:
        key = d['candidate_key']
        check(key, 'lower_all7200', 7200*4*500, d['lower_tier']['annual_max_R'])
        check(key, 'top_all7200', 7200*4*250, d['contests']['annual_max_R'])
        check(key, 'special_monthly', 12*200000, d['special']['annual_max_R'])
        check(key, 'total24m', sum(d[x]['annual_max_R'] for x in ['lower_tier','contests','special']), 24000000)
        check(key, 'stationary_calendar', sum(d['monthly_calendar_R']), 24000000)
        check(key, 'launch_year1_posted', 3*200000+9*2000000, 18600000)
        check(key, 'first_four_cycles_ordinary', 12*1800000, 21600000)
        check(key, 'first_four_cycles_ordinary_by_m15', 12*2000000-12*200000, 21600000)
        check(key, 'month_end_unearned_m12', 12*1800000-9*1800000, 5400000)
        check(key, 'ordinary_overlap_before_quality_close', 4*1800000, 7200000)
        check(key, 'overlap_gross_exposure_RUB', 7200000*.194, 1396800, 'RUB gross, before stock/other backing')
        check(key, 'extra_overlap_vs_month_end_RUB', 1800000*.194, 349200, 'RUB gross, not proven cash shortfall')
    check('BASELINE', 'Q3_fund', 19427591+19112409, 38540000)
    check('CON-013@v1', 'unchanged_Rmax', 14400000+7200000+2400000, 24000000)
    key = 'CON-011@v2'
    check(key, '40_people_first_team', 250*40*.8, 8000)
    check(key, '40_people_first_member_five', 8000/5, 1600)
    check(key, '40_people_second_member_five', 2000/5, 400)
    check(key, 'eight_tied_teams_member', 10000/8/5, 250)
    check(key, 'all40_person_tie', 10000/40, 250)
    check(key, 'three_tied_persons_paid', 3333*3, 9999)
    check(key, '3and7_member_paid', (2000//3)*3+(500//7)*7, 2495)
    check(key, 'top_cap_nonbinding_n100', 100*250*.8, 20000)
    check(key, 'personal_cap', 4*500+4*20000+2*7500, 97000)
    check(key, 'QA_score_minor', max(0,100-2*1-10*0), 98, 'rubric score')
    check(key, 'QA_mean20', (10*96+10*98)/20, 97, 'rubric score mean')
    check(key, 'QA_required_total_hours', 2400*20/60, 800, 'h/month total, existing/new unknown')
    check(key, 'QA_total_valued_resource', 800*1500*12, 14400000, 'RUB/year total, not new cash')
    check(key, 'source_capture_employee', 144000*.5/60+24000*.25/60, 1300, 'h/month additional sensitivity')
    check(key, 'source_acceptance_owner', 144000*.25/60+24000*.25/60, 700, 'h/month additional sensitivity')
    key = 'CON-013@v2'
    check(key, 'eight_tied_teams_lower_plus_top', 500+10000/8/5, 750)
    check(key, 'single_L2_n1', 500+250*.5, 625)
    check(key, 'group5_single_winner', 500+1250*.5, 1125)
    check(key, 'QA_metric_h', 1440*42.5*.5/60, 510, 'h/month')
    check(key, 'QA_artifact_h', 960*3*12/60, 576, 'h/month')
    check(key, 'QA_total_h', 510+576, 1086, 'h/month')
    check(key, 'evidence_creation_h', 1440*42.5*.25/60+960*3*20/60, 1215, 'h/month')
    check(key, 'QA_existing_h', 1086*.7, 760.2, 'h/month scenario')
    check(key, 'QA_new_h', 1086*.3, 325.8, 'h/month scenario')
    check(key, 'classification_existing', (760.2*1500+927*1000)*12, 24807600, 'RUB/year scenario')
    check(key, 'classification_incremental', (45.2*1000+float(specs[0]['workload']['classification_monthly']['required_incremental_program']['manager_hours'])*1500+431.2*1000+10*2000)*12, 13849200, 'RUB/year scenario')
    check(key, 'classification_sum', 24807600+13849200, 38656800, 'RUB/year valued process, excludes useful work')
    check(key, 'isolated_recheck_reduction', 2400*4/60-(1680*1+720*3+168*2)/60, 90.4, 'h/month conditional isolated, not total saving')
    concept=(R/'branches/A/concept-013.md').read_text()
    cost=re.search(r'полная стоимость\s*(\d+(?:[,.]\d+)?)\s*руб',concept)
    if cost:
        check(key, 'individual_certificate_nominal100_cost', float(cost.group(1).replace(',','.')), 100, 'RUB procurement alone at100% nominal; full service cost unknown; mixed coefficient inapplicable')

    # Do not import the candidate generator. Recompute every saved boundary.
    p = R/'branches/A/quality-boundaries.csv'
    rows = list(csv.DictReader(p.open()))
    errors = []
    levels = {}
    min_s = {'IT':90,'backoffice':97,'support':90}
    for i,row in enumerate(rows,2):
        n,s,q,c = [int(row[k]) for k in ['n','s','q','critical']]
        rr = Fraction(row['normalized_upper_median_ratio'])
        eligible = 100*s >= min_s[row['family']]*n and 100*q >= 98*n and c==0
        level = (3 if rr <= Fraction(90,100) else 2 if rr <= Fraction(95,100) else 1) if eligible else 0
        minimum_s=(min_s[row['family']]*n+99)//100
        minimum_q=(98*n+99)//100
        if [int(row['level']),int(row['lower_R']),int(row['minimum_s']),int(row['minimum_q'])] != [level,500 if level else 0,minimum_s,minimum_q]:
            errors.append(i)
        if eligible: levels.setdefault(str(n),set()).add(level)
    boundary=dict(rows=len(rows), errors=errors[:20], all_pass=not errors,
                  reachable_levels={n:sorted(v) for n,v in levels.items()},
                  scope='Binary full-registry s/q gates plus independent exact r; critical>0 rejection checked separately in text, CSV contains critical0.')
    assert boundary['all_pass']

    # Date-based overlap: at day15 of m4, A4/C1cycle2 has started, while
    # the first ordinary right remains contingent until day24 or28.
    overlap=[]
    for key,quality_day in [('CON-013@v2',24),('CON-011@v2',28)]:
        open_windows=[]
        for start_month in range(1,5):
            end_month=start_month+3
            if (start_month,15)<=(4,15)<(end_month,quality_day):
                open_windows.append(dict(start_month=start_month,quality_final_month=end_month,quality_final_day=quality_day,max_R=1800000))
        overlap.append(dict(candidate_key=key,as_of='2027-04-15',open_conditional_windows=open_windows,
                            conditional_total_R=sum(x['max_R'] for x in open_windows),
                            month_end_reported_R=5400000,
                            interpretation='Gross contingent exposure only. Monthly closing reserves do not independently establish before-effort daily backing. Not a proven annual budget overrun or net cash deficit.'))

    input_paths=[R/'candidate-inputs.json',R/'clarifications.md']+sorted((R/'inputs').glob('*'))
    input_paths += paths+[R/'branches/A/concept-013.md',R/'branches/B/concept-011.md',R/'branches/A/first-launch.json',R/'branches/B/first-launch.json',R/'branches/A/first-launch.csv',R/'branches/B/first-launch.csv',R/'branches/A/launch-years.csv',p]
    input_paths+=sorted((R/'supporting/previous-best').glob('*'))+[R.parent/'001/selected.md',R.parent/'001/checks/evidence.json']
    manifest=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in input_paths if p.is_file()]
    unchanged_frozen={p.name:p.read_bytes()==(R.parent/'001/inputs'/p.name).read_bytes() for p in (R/'inputs').glob('*') if (R.parent/'001/inputs'/p.name).exists() and p.name!='manifest.json'}
    data=dict(checks=checks,all_simple_checks_pass=all(x['passed'] for x in checks),boundary_check=boundary,
              intra_month_overlap=overlap,input_manifest=manifest,frozen_equal_to_round001=unchanged_frozen,
              limitations='Independent simple arithmetic, exact quality boundaries and timing, not full cash/stock/finance recost or measured OTP effects.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(simple_checks=len(checks),all_pass=data['all_simple_checks_pass'],quality_rows=len(rows),quality_all_pass=boundary['all_pass'],inputs=len(manifest))))


if __name__=='__main__':
    main()
