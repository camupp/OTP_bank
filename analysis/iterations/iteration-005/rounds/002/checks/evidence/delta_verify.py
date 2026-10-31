"""Targeted delta only; does not repeat QA enumeration or import finance models."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[7]
R=ROOT/'analysis/iterations/iteration-005/rounds/002'
OLD=R/'private/before-targeted-rework'
OUT=R/'checks/evidence'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    before=json.loads((R/'private/versions-before-checks.json').read_text())
    after=json.loads((R/'private/versions-after-rework.json').read_text())
    assert before==after
    mismatches=[p for p,h in after.items() if sha(R/p)!=h]
    assert not mismatches,mismatches
    specs=[]
    records=[]
    for rel,allow in [('branches/A/finance-spec-013.json',{'regional_certificate_example','dated_prefunding','references','first_launch_ref'}),('branches/B/finance-spec-011.json',{'dated_prefunding'})]:
        x=json.loads((OLD/rel).read_text());y=json.loads((R/rel).read_text())
        changed={k for k in set(x)|set(y) if x.get(k)!=y.get(k)}
        assert changed<=allow,(rel,changed)
        unchanged=[k for k in x if k not in allow and x[k]==y[k]]
        for k in ['lower_tier','contests','special','stacking','annual_total_R','no_self_award_controls','workload']:
            assert x[k]==y[k],(rel,k)
        specs.append(y)
        records.append(dict(candidate_key=y['candidate_key'],changed_spec_fields=sorted(changed),unchanged_substantive_fields=unchanged,annual_R=y['annual_total_R'],recognition_rules_unchanged=True))
    cert=specs[0]['regional_certificate_example']
    assert cert['nominal_RUB']==100 and cert['procurement_RUB_under_M05_certificate_fraction1']==100
    assert cert['service_issuance_RUB'] is None and cert['full_SKU_cost_RUB'] is None
    assert 'полная стоимость97' not in (R/'branches/A/concept-013.md').read_text()
    for d in specs:
        x=d['dated_prefunding']
        assert x['promise_day']==14 and x['effort_start_day']==15
        assert x['ordinary_gross_peak_R_from_month4']==7200000
        assert x['special_unconfirmed_max_R']==200000 and x['ordinary_month_close_R']==5400000
    gross=dict(ordinary_peak_R=7200000,special_unconfirmed_max_R=200000,total_gross_R=7400000,
               mixed_gross_exposure_RUB=7400000*.194,
               scope='Gross arithmetic only; net cash/stock and actual supply verified separately by finance.')
    prior=json.loads((OLD/'checks/evidence/verification.json').read_text())
    prior_hash={p['path']:p['sha256'] for p in prior['input_manifest']}
    qa=R/'branches/A/quality-boundaries.csv'
    assert sha(qa)==prior_hash[str(qa.relative_to(ROOT))]
    assert qa.read_bytes()==(OLD/'branches/A/quality-boundaries.csv').read_bytes()
    immutable=['branches/A/first-launch.csv','branches/A/launch-years.csv','branches/A/stationary-m05.csv','branches/A/money-examples.csv']
    for rel in immutable:assert (OLD/rel).read_bytes()==(R/rel).read_bytes(),rel
    for rel,key in [('branches/A/first-launch.json','windows_first_four'),('branches/B/first-launch.json','cohorts')]:
        assert json.loads((OLD/rel).read_text())[key]==json.loads((R/rel).read_text())[key]
    csvrel='branches/B/first-launch.csv'
    x=list(csv.DictReader((OLD/csvrel).open()));y=list(csv.DictReader((R/csvrel).open()))
    assert len(x)==len(y)==45
    cold=[]
    for a,b in zip(x,y):
        assert (a['scenario'],a['month'])==(b['scenario'],b['month'])
        if a!=b:
            assert b['scenario']=='COLD_SHOP_STRESS' and int(b['month'])<=6
            fields=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))
            assert set(fields)<={'combined_HR_fallback_hours','funding_cash_plus_delta_reserve_RUB','common_M05_HR_hours','total_reserve_RUB_close','earned_rights_reserve_RUB_close','combined_HR_hours','total_reserve_RUB_open','conditional_promise_extra_reserve_RUB_close'}
            cold.append(dict(month=int(b['month']),changed_fields=fields))
    assert len(cold)==6
    ledger=R/'checks/finance/date-prefunding.csv'
    rows=list(csv.DictReader(ledger.open()))
    refs=[]
    for key,day in [('CON-013@v2',24),('CON-011@v2',28)]:
        selected=[(i+2,x) for i,x in enumerate(rows) if x['candidate_key']==key]
        assert len(selected)==72
        assert {x['scenario'] for _,x in selected}=={'EXPECTED','FULL_NEW'}
        for _,x in selected:
            m=int(x['month'])
            assert int(x['promise_date_day'])==14 and int(x['effort_start_day'])==15
            assert int(x['prior_quality_close_day'])==day
            assert float(x['ordinary_conditional_peak_R'])==min(m,4)*1800000
            assert float(x['special_unconfirmed_max_R'])==200000
        refs.append(dict(candidate_key=key,row_count=72,m4_csv_lines=[i for i,x in selected if int(x['month'])==4],m12_csv_lines=[i for i,x in selected if int(x['month'])==12],prior_quality_day=day))
    initial_immutable=[]
    for p,h in prior_hash.items():
        if '/inputs/' in p or '/supporting/previous-best/' in p or p.endswith('/001/selected.md'):
            assert sha(ROOT/p)==h,p
            initial_immutable.append(p)
    sourcepaths=[R/p for p in after]+[ledger,R/'private/versions-before-checks.json',R/'private/versions-after-rework.json',OLD/'checks/evidence/verification.json',OLD/'checks/evidence.json']
    result=dict(scope='Only authorized target delta; no new source research, full finance recost or 54220-row re-enumeration.',
       snapshot_manifests_equal=True,frozen_candidate_hashes_checked=len(after),mismatches=mismatches,
       rules=records,certificate=dict(nominal_RUB=100,procurement_RUB=100,full_cost_RUB=None,service_issuance_RUB=None,example_supported=True),
       gross_peak=gross,dated_ledger_refs=refs,dated_ledger_claim_fields_match=True,
       cold_csv_delta=cold,main_expected_full_new_rows_unchanged=True,
       unchanged_artifacts=immutable,QA_boundary_hash_unchanged=sha(qa),QA_rows_reused_not_rerun=54220,
       no_self_award_controls_unchanged=True,first_four_cycles_unchanged=True,prior_unmodified_inputs=initial_immutable,
       initial_findings_archive=str((OLD/'checks/evidence.json').relative_to(ROOT)),
       source_manifest=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sourcepaths],
       limitations=['Dated ledger financial numbers/stock allocation/cash alternatives checked by separate finance owner. Only references/dates/gross fields matched here.','Conditional paid/received/appropriate stock before14th is not observed bank delivery.','Cold scenario amount recost not duplicated; only allowed-field scope and preservation checked.','Supported applies checked claims, not measured effect, actual staffing/catalog/rollout.'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'delta-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(candidate_hashes=len(after),rules_unchanged=True,certificate='supported procurement100/full unknown',QA_rows_reused=54220,ledger_rows=144,cold_changed_months=len(cold))))


if __name__=='__main__':main()
