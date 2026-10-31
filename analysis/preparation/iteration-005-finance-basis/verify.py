"""Independent CSV arithmetic and an import-with-no-writes check; writes here only."""
from pathlib import Path
import csv
import hashlib
import json
import runpy
import sys

P = Path(__file__).resolve().parent


def main():
    before = {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in P.rglob('*') if x.is_file()}
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    runpy.run_path(str(P / 'model.py'), run_name='read_only_import_test')
    sys.dont_write_bytecode = previous
    after = {str(x): hashlib.sha256(x.read_bytes()).hexdigest() for x in P.rglob('*') if x.is_file()}
    assert before == after, 'Import changed files'
    rows = list(csv.DictReader((P / 'annual-three-year.csv').open()))
    def num(row, key):
        return float(row[key])
    for row in rows:
        n = lambda key: num(row, key)
        assert abs(n('C_open') + n('fixed_C_issued') + n('R_to_C') - n('physical_C_required') - n('C_close')) < 1e-5
        assert abs(n('R_open') + n('R_posted') - n('R_to_C') - n('R_close')) < 1e-5
        assert abs(n('F_open') + n('F_granted') - n('F_posted') - n('F_unissued_expired') - n('F_close')) < 1e-5
        assert abs(n('total_cash_required_rub') - n('consumed_landed_rub') - n('inventory_close_landed_rub') + n('inventory_open_landed_rub')) < 1e-5
        expected = max(0, n('post_start_rights_exposure_rub') - n('inventory_close_landed_rub'))
        assert abs(expected - n('reserve_target_close_rub')) < 1e-5
        assert abs(n('cash_plus_signed_reserve_delta_rub') - n('total_cash_required_rub') - n('reserve_target_close_rub') + n('reserve_target_open_rub')) < 1e-5
    # Hand formulas independent of the model's functions.
    selected = [r for r in rows if r['scenario'] == 'FULL_NEW' and r['year'] == '1']
    for r in selected:
        assert abs(num(r, 'consumed_landed_rub') - (40000000 + num(r, 'fixed_C_year') + num(r, 'envelope_R_year')) * .194) < 1e-5
    expected96 = next(r for r in rows if r['scenario'] == 'EXPECTED' and r['year'] == '1' and r['fixed_C_year'] == '96000000' and r['envelope_R_year'] == '24000000')
    assert abs(num(expected96, 'post_start_rights_close_C_R') - 38400000) < 1e-5
    assert abs(num(expected96, 'cash_plus_reserve_delta_plus_buffer_rub') - 31540000) < 1e-5
    limits = json.loads((P / 'limits.json').read_text())
    tier = next(r for r in limits['universal_tiers'] if r['envelope_R_year'] == 24000000 and r['cycles_year'] == 4 and r['lower_award_R'] == 500)
    assert tier['all_eligible_R_required'] == 14400000
    assert tier['remaining_for_contest_and_special_R'] == 9600000
    assert len(rows) == 360
    report = dict(status='pass', rows=len(rows), checks=['Import leaves owned files byte-identical',
        'Independent C/R/F ledgers', 'Independent cash-consumption-inventory identity',
        'Future cash reserve nets paid stock once', 'Signed reserve delta reconciles',
        'Full-new costs reproduce hand formula at .194 RUB/C',
        'Expected fixed96/E24 reserves all 38.4m retained new rights',
        'Universal quarterly 500 R all7200 leaves 9.6m inside24m'])
    (P / 'independent-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
