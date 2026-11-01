"""Independent narrow recheck of A only; no B reads or candidate module execution."""
from pathlib import Path
import ast
import copy
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[1]


def function(path, name):
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
    return ns[name]


def rows(path):
    return list(csv.DictReader(path.open()))


def normalized(data):
    return [{k: v for k, v in r.items() if k not in ('candidate_key', 'rule_version')} for r in data]


pin = json.loads((ROUND / 'private/repaired-A-pins.json').read_text())
bad = [p for p, h in pin['files'].items() if hashlib.sha256((ROUND / p).read_bytes()).hexdigest() != h]
base = json.loads((ROUND / 'supporting/fixtures/source/base.json').read_text())
results = []
for number in ('018', '019'):
    current = ROUND / f'branches/A/con-{number}'
    previous = ROUND / f'private/pre-rework/branches/A/con-{number}'
    signoff = function(current / 'evaluator.py', 'signoff')
    vectors = []
    for name, value in [('null', None), ('empty', ''), ('whitespace', ' \t '), ('absent', None), ('performed', '2026-04-28T10:00:00+03:00')]:
        data = copy.deepcopy(base)
        approval = next(x for x in data['approvals_audit'] if x['approval_id'] == 'P1:S01')
        if name == 'absent':
            approval.pop('signed_at', None)
        else:
            approval['signed_at'] = value
        status, ref = signoff(data, 'P1', 'S01')
        # Independent reconstruction of unchanged ledger conditions: calculated
        # eligibility remains true; current-quarter top requires ready posting;
        # G requires both quarter signatures and remains attached to original window.
        period1 = {'normal': True, 'signoff_status': status, 'top_R': 105, 'top_pending': False,
                   'window_id': 'W2026-A', 'right_date': '2026-04-28'}
        period2 = {'normal': True, 'signoff_status': 'signed', 'window_id': 'W2026-A',
                   'right_date': '2026-07-28'}
        posting = 'ready' if status == 'signed' and period1['normal'] else 'held'
        approved_top = period1['top_R'] if posting == 'ready' and not period1['top_pending'] else 0
        qualified_G = 2500
        approved_G = qualified_G if all(r['signoff_status'] == 'signed' for r in (period1, period2)) else 0
        expected_signed = name == 'performed'
        vectors.append({'case': name, 'observed_pure_signoff': status, 'approval_ref': ref,
                        'expected_signed': expected_signed, 'calculated_normal_preserved': True,
                        'calculated_G_R': qualified_G, 'posting': posting,
                        'approved_P1_top_R_from_unchanged_ledger_condition': approved_top,
                        'approved_G_R_from_unchanged_ledger_condition': approved_G,
                        'window': period2['window_id'], 'original_G_example_date': period2['right_date'],
                        'pass': (status == 'signed') == expected_signed and
                                (expected_signed or (approved_top == 0 and approved_G == 0))})
    decision_old, decision_new = rows(previous / 'decisions.csv'), rows(current / 'decisions.csv')
    money_old, money_new = rows(previous / 'money-examples.csv'), rows(current / 'money-examples.csv')
    spec_old = json.loads((previous / 'metrics-spec.json').read_text())
    spec_new = json.loads((current / 'metrics-spec.json').read_text())
    changed_spec = sorted(k for k in spec_old.keys() | spec_new.keys() if spec_old.get(k) != spec_new.get(k))
    resource_equal = all((previous / name).read_bytes() == (current / name).read_bytes()
                         for name in ('resource-sensitivity.csv', 'peak-resource.csv'))
    result = {'candidate_key': f'CON-{number}@v2', 'signature_vectors': vectors,
              'ordinary_scenarios': len({r['scenario'] for r in decision_new}),
              'ordinary_personal_rows': len(decision_new),
              'ordinary_decisions_equal_except_metadata': normalized(decision_old) == normalized(decision_new),
              'ordinary_money_equal_except_metadata': normalized(money_old) == normalized(money_new),
              'metrics_spec_changed_keys': changed_spec,
              'metrics_mechanism_unchanged': set(changed_spec) <= {'candidate_key', 'rule_version', 'signing'},
              'resource_tables_byte_equal': resource_equal}
    result['all_delta_checks_pass'] = (all(x['pass'] for x in vectors)
                                        and result['ordinary_scenarios'] == 23
                                        and result['ordinary_personal_rows'] == 368
                                        and result['ordinary_decisions_equal_except_metadata']
                                        and result['ordinary_money_equal_except_metadata']
                                        and result['metrics_mechanism_unchanged'] and resource_equal)
    results.append(result)
output = {'scope': 'A delta only; author signoff function extracted alone, no full evaluator/module/build/verify execution; ledger consequences independently derived from unchanged code conditions',
          'pin_mismatches': bad, 'results': results,
          'all_pass': not bad and all(r['all_delta_checks_pass'] for r in results),
          'remaining_limits': ['018 project root-capacity norm still absent', '019 outcome saturation/portfolio comparability unchanged',
                               'nonempty signed_at checked; real audit provenance and timestamp schema remain production input validation']}
(HERE / 'delta-A.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'all_pass': output['all_pass'], 'pin_mismatches': bad,
                  'candidate_pass': {r['candidate_key']: r['all_delta_checks_pass'] for r in results}}, ensure_ascii=False))
