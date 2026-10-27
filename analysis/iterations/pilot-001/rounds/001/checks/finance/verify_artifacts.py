#!/usr/bin/env python3
"""Verify inputs/results and write owned report; --reproduce reruns before seal only."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent
RESULTS = ['scenario-results.csv', 'monthly-balances.csv', 'event-ledger.csv',
           'cash-scenarios.csv', 'cash-boundaries.csv', 'validation.json']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    reproduced = False
    if '--reproduce' in sys.argv:
        assert json.loads((ROUND / 'round.json').read_text())['status'] == 'working', 'do not rewrite sealed round'
        previous = {n: digest(HERE / n) for n in RESULTS}
        subprocess.run([sys.executable, str(HERE / 'model.py')], check=True)
        assert previous == {n: digest(HERE / n) for n in RESULTS}, 'model outputs not deterministic'
        reproduced = True
    f = json.loads((ROUND / 'checks/finance.json').read_text())
    required = {'candidate_key', 'scenario_scope', 'gates', 'evidence_refs', 'assumption_refs', 'findings', 'calculation_paths'}
    keys = {'BASELINE', 'CON-001@v1', 'CON-002@v1', 'CON-003@v1', 'CON-004@v1'}
    assert {x['candidate_key'] for x in f['results']} == keys and len(f['results']) == 5
    for row in f['results']:
        assert required <= row.keys()
        assert row['gates'] == {'budget': 'uncertain', 'currency_balances': 'uncertain'}
        for path in row['calculation_paths']:
            # This report is emitted at the end of this verifier.
            assert path == 'checks/finance/artifact-validation.json' or (ROUND / path).is_file(), path
        for ref in row['evidence_refs'] + row['assumption_refs']:
            assert (ROUND / ref.split('#')[0]).is_file(), ref
    counts = {}
    for path in sorted(HERE.glob('*.csv')):
        rows = list(csv.DictReader(path.open(encoding='utf-8')))
        assert rows and all(None not in row and all(v is not None for v in row.values()) for row in rows), path
        counts[path.name] = len(rows)
    assert counts['scenario-results.csv'] == 40 and counts['cash-scenarios.csv'] == 60
    rows = list(csv.DictReader((HERE / 'scenario-results.csv').open()))
    assert all(r['formal_balance_gate'] == 'pass' and r['real_bank_currency_gate'] == 'uncertain' for r in rows)
    assert all(r['all_requested_rewards_fulfilled'] == 'fail' for r in rows if r['scenario_id'] in {'N1_old_C','N3_direct_R','N4_supply_zero'})
    source_paths = [*(ROUND / 'inputs').glob('*.md'), ROUND / 'inputs/rubric.json',
                    *(ROUND / 'branches/A').glob('*.md'), ROUND / 'branches/A/assumptions.csv', ROUND / 'branches/A/branch.json',
                    *(ROUND / 'branches/B').glob('*.md'), ROUND / 'branches/B/assumptions.csv', ROUND / 'branches/B/branch.json']
    out = {'status': 'pass', 'reproduced_identical_model_outputs': reproduced,
           'checks': ['five required candidates and contract fields', 'all result gates remain uncertain',
                      'all calculation and evidence/assumption paths exist', 'CSV column counts and scenario counts',
                      'unfulfilled demand does not become a model pass'],
           'csv_rows': counts, 'source_sha256': {str(p.relative_to(ROUND)): digest(p) for p in sorted(source_paths)},
           'result_sha256': {n: digest(HERE / n) for n in RESULTS},
           'scope_limit': 'Checks integrity, reproducibility and declared scope; not bank reconciliation or factual proof of effects'}
    (HERE / 'artifact-validation.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'artifact_checks': 'pass', 'reproduced_identical_model_outputs': reproduced, 'candidates': 5}, ensure_ascii=False))


if __name__ == '__main__':
    main()
