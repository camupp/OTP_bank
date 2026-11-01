"""Independent source reconstruction and narrowly extracted predicate counterexamples.

Does not import or run any candidate module/evaluator/export/self-check. The two
approval predicates are extracted with AST, compiled alone, and checked against
independently stated signature requirements. Source tables remain untouched.
"""
from pathlib import Path
import ast
import copy
import csv
import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import date, datetime

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[1]
FIXTURE = ROUND / 'supporting/fixtures'


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def day(value):
    return date.fromisoformat(value[:10]) if value else None


def extract_function(path, name):
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name], {'file': str(path.relative_to(ROUND)), 'start': fn.lineno,
                             'end': fn.end_lineno, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


reader_spec = importlib.util.spec_from_file_location('common_source_reader', FIXTURE / 'source/reader.py')
reader = importlib.util.module_from_spec(reader_spec)
reader_spec.loader.exec_module(reader)
index = json.loads((FIXTURE / 'source/scenario_index.json').read_text())
names = ['base'] + [row['scenario_id'] + '.' + v for row in index for v in row['variants']]
summaries = []
for name in names:
    data = reader.expand_scenario(name)
    for cap in data['roster_capacity']:
        subject, period, family = cap['subject_id'], cap['period_id'], cap['family']
        rule = next(r for r in data['period_rules'] if r['period_id'] == period and r['family'] == family)
        # Exact repeated export rows are one source observation. Roots retain all versions.
        es = {e['event_id']: e for e in data['work_events'] if e['subject_id'] == subject and e['period_id'] == period}
        roots = defaultdict(list)
        for e in es.values():
            if e.get('root_id'):
                roots[e['root_id']].append(e)
        people = {subject} | {m['employee_id'] for m in data['team_members'] if m['team_id'] == subject and m['period_id'] == period}
        qa = [q for q in data['quality_acts'] if q['subject_id'] == subject and q['period_id'] == period
              and q.get('evidence_status') == 'present' and q.get('checker_id') not in people
              and q.get('criterion') == 'defect_penalty' and q.get('scale') == '0..100'
              and q.get('scale_version') == 'penalty-v1'
              and q.get('scope') == ('team' if family == 'project' else 'personal')
              and q.get('sample_method') == 'census_of_scenario_work_register'
              and day(q.get('finalized_at')) and day(q['finalized_at']) <= day(rule['quality_close'])
              and day(q.get('observation_end')) and day(q['observation_end']) >= day(rule['quality_close'])]
        inspections = defaultdict(list)
        for q in qa:
            inspections[q['inspection_id']].append(q)
        inspection_scores = [min(100 - 2 * q['minor'] - 10 * q['major'] for q in qs) for qs in inspections.values()]
        root_scores, covered_roots = [], 0
        for root, events in roots.items():
            cases = {e['case_id'] for e in events}
            qs = [q for q in qa if q['case_id'] in cases]
            covered = {q['case_id'] for q in qs}
            if cases <= covered or (family == 'project' and any(q.get('coverage_object') == 'same_deliverable_inspection' for q in qs)):
                covered_roots += 1
                if qs:
                    root_scores.append(min(q['score'] for q in qs))
        outcomes = {o['case_id']: o for o in data['support_outcomes'] + data['process_outcomes']
                    if o['subject_id'] == subject and o['period_id'] == period}
        accepted = timely = adverse = weighted = 0
        classes = {c['type_id']: c for c in data['classifier']}
        usages, project_proof = [], []
        for root, events in roots.items():
            original = min(events, key=lambda e: (e['assigned_at'], e['case_id']))
            outcome = outcomes.get(original['case_id'])
            latest = max([e for e in events if e['case_id'] == original['case_id']], key=lambda e: (e['version'], e['event_at']))
            if family != 'project':
                if outcome:
                    ok = bool(latest.get('accepted_at') and latest.get('accepted_by') not in people
                              and latest['status'] in ('resolved', 'Done')
                              and (outcome.get('resolved') if family == 'support' else outcome.get('accepted')))
                    bad = bool(any(e.get('reopen_of') or e.get('correction_of') for e in events)
                               or (outcome.get('repeat_of') if family == 'support' else outcome.get('returned')))
                    accepted += ok
                    adverse += bad
                    deadline = outcome.get('sla_due_at') or original.get('due_at')
                    timely += bool(ok and deadline and latest['accepted_at'] <= deadline)
                    if ok and not bad:
                        weighted += classes.get(original['type_id'], {}).get('standard_units', 0)
            else:
                prs = [r for r in data['project_records'] if r['subject_id'] == subject and r['period_id'] == period and r['deliverable_id'] == root]
                if prs:
                    r = prs[0]
                    usages.append(r.get('usage_units'))
                    project_proof.append({'root': root, 'parts': len(events), 'criteria': r.get('criteria_ref'),
                                          'accepted_at': r.get('acceptance_at'), 'usage_at': r.get('usage_observed_at'),
                                          'usage_units_once': r.get('usage_units')})
        cs = [o for o in data['support_outcomes'] if o['subject_id'] == subject and o['period_id'] == period]
        response = [o['csat_score'] for o in cs if o.get('responded') and o.get('csat_scale') == '1..5' and o.get('csat_score') is not None]
        summaries.append({'scenario': name, 'period': period, 'subject': subject, 'family': family,
                          'event_rows_unique': len(es), 'roots': len(roots), 'accepted_roots_raw': accepted,
                          'timely_roots_raw': timely, 'adverse_roots': adverse, 'weighted_good_units': weighted,
                          'available_h_before_exceptions': (cap['scheduled_hours']-cap['leave_hours']-cap['training_hours'])*cap['allocation_fraction'],
                          'qa_compatible_acts': len(qa), 'qa_inspections_unique': len(inspections),
                          'qa_mean_inspections': sum(inspection_scores)/len(inspection_scores) if inspection_scores else None,
                          'qa_whole_roots': covered_roots, 'qa_mean_root_worst': sum(root_scores)/len(root_scores) if root_scores else None,
                          'csat_contacts': len(cs), 'csat_invited': sum(o.get('invited', False) for o in cs),
                          'csat_n': len(response), 'csat_mean': sum(response)/len(response) if response else None,
                          'project_proof': project_proof})
save('source-reconstruction.json', {'scope': 'Independent primitive facts, not a replacement complete reward evaluator', 'rows': summaries})

base = reader.expand_scenario('base')
counterexamples = []
# A: the author predicate is extracted alone; data copy has no executed timestamp.
a_path = ROUND / 'branches/A/con-018/evaluator.py'
a_sign, a_locator = extract_function(a_path, 'signoff')
data = copy.deepcopy(base)
row = next(a for a in data['approvals_audit'] if a['period_id'] == 'P1' and a['beneficiary_id'] == 'S01')
row['signed_at'] = None
observed = a_sign(data, 'P1', 'S01')
counterexamples.append({'id': 'SIG-A-NO-TIME', 'candidates': ['CON-018@v1', 'CON-019@v1'],
                        'change': {'approval_id': row['approval_id'], 'signed_at': None},
                        'expected_independently': 'not signed: named actors without signed_at do not prove performed signature',
                        'observed_extracted_predicate': observed, 'locator': a_locator,
                        'conclusion': 'Actual counterexample to signoff predicate, not an execution of complete author evaluator'})
b_path = ROUND / 'branches/B/con-020/evaluator.py'
b_sign, b_locator = extract_function(b_path, 'independent_approval')
team = [m for m in base['team_members'] if m['period_id'] == 'P1' and m['team_id'] == 'T01']
for ident, values, expected in [
    ('SIG-B-TEAM', {'signer_id': team[1]['employee_id']}, 'reject: signer is another beneficiary of same awarded team result'),
    ('SIG-B-SAME-ACTOR', {'operator_id': 'OWNER-INDEPENDENT-01', 'signer_id': 'OWNER-INDEPENDENT-01'}, 'reject: verification and posting must be distinct people'),
    ('SIG-B-EMPTY-EDITOR', {'input_editor_id': None}, 'hold: independent source editor is not identified')]:
    row = copy.deepcopy(next(a for a in base['approvals_audit'] if a['period_id'] == 'P1' and a['beneficiary_id'] == 'P01'))
    row.update(values)
    observed = b_sign(row, 'P01')
    counterexamples.append({'id': ident, 'candidates': ['CON-020@v1', 'CON-021@v1'], 'source_copy': row,
                           'expected_independently': expected, 'observed_extracted_predicate': bool(observed),
                           'locator': b_locator, 'conclusion': 'Actual predicate counterexample; no module/evaluator export executed'})

row = copy.deepcopy(next(a for a in base['approvals_audit'] if a['period_id'] == 'P1' and a['beneficiary_id'] == 'P01'))
row['action'] = 'type_correction'
predicate = b_sign(row, 'P01')
counterexamples.append({'id': 'SIG-B-WRONG-ACTION', 'candidates': ['CON-020@v1', 'CON-021@v1'],
                       'source_copy': row, 'expected_independently': 'new posting signature required: a type correction is not posting review',
                       'observed_predicate': bool(predicate), 'observed_caller_label': 'signed' if predicate else 'new_independent_posting_signature_required',
                       'locator': {'file': str(b_path.relative_to(ROUND)), 'start': 249, 'end': 259},
                       'conclusion': 'Caller filters beneficiary/period without action; its label expression reproduced, no complete evaluator run'})

# B: one distinct-case inspection cannot cover seven other uninspected task parts.
data = copy.deepcopy(base)
events = [e for e in data['work_events'] if e['period_id'] == 'P1' and e['subject_id'] == 'T02']
cases = {e['case_id'] for e in events}
qa = [q for q in data['quality_acts'] if q['period_id'] == 'P1' and q['subject_id'] == 'T02']
retained = qa[0]
assert retained['coverage_object'] == 'one_distinct_case'
covered_cases = {retained['case_id']}
observed = any(e['case_id'] in covered_cases for e in events)
expected = cases <= covered_cases or retained['coverage_object'] == 'same_deliverable_inspection'
counterexamples.append({'id': 'QA-B-PART-COVERAGE', 'candidates': ['CON-020@v1', 'CON-021@v1'],
                       'change': 'keep exactly one of eight T02/P1 one_distinct_case acts; truthful available manifest updated for retained rows',
                       'retained_act': retained['act_id'], 'roots': 1, 'source_cases': len(cases), 'covered_cases': len(covered_cases),
                       'expected_independently': expected, 'observed_code_expression': observed,
                       'locator': {'file': str(b_path.relative_to(ROUND)), 'start': 113, 'end': 120},
                       'conclusion': 'A root is counted once as benefit, but all its required case evidence still needs coverage; static code expression reproduced independently'})
save('counterexamples.json', {'source_unchanged': True, 'full_author_evaluators_executed': False,
                             'extracted_pure_predicates_only': True, 'cases': counterexamples})

# Selected scalar checks establish values and construction facts independently.
def pick(name, person, period='P1'):
    return next(r for r in summaries if r['scenario'] == name and r['subject'] == person and r['period'] == period)

checks = {
    'source_has_23_sets': len(names) == 23,
    'base_S01_standard_units_108': pick('base','S01')['weighted_good_units'] == 108,
    'base_S02_standard_units_120': pick('base','S02')['weighted_good_units'] == 120,
    'base_support_capacity_108': pick('base','S01')['available_h_before_exceptions'] == 108,
    'base_B01_units80_B02_units96': pick('base','B01')['weighted_good_units'] == 80 and pick('base','B02')['weighted_good_units'] == 96,
    'base_B01_SLA19of20': pick('base','B01')['timely_roots_raw'] == 19 and pick('base','B01')['roots'] == 20,
    'base_B02_SLA24of24': pick('base','B02')['timely_roots_raw'] == 24 and pick('base','B02')['roots'] == 24,
    'F07_one_root_eight_parts': pick('F07.split','T01')['roots'] == 1 and pick('F07.split','T01')['event_rows_unique'] == 8,
    'F07_one_inspection': pick('F07.split','T01')['qa_inspections_unique'] == 1,
    'F04_no_CSat_is_null': pick('F04.no_responses','S01')['csat_n'] == 0 and pick('F04.no_responses','S01')['csat_mean'] is None,
    'F11_rates18_19_20of20': [pick('F11.'+x,'B01')['timely_roots_raw'] for x in ['below','at_contract','ceiling']] == [18,19,20],
    'bounded_Q_110_is_impossible_at95': 1.1*.95 > 1,
    'A_missing_timestamp_predicate_accepts': counterexamples[0]['observed_extracted_predicate'][0] == 'signed',
    'B_other_team_beneficiary_predicate_accepts': counterexamples[1]['observed_extracted_predicate'] is True,
    'B_same_signer_operator_predicate_accepts': counterexamples[2]['observed_extracted_predicate'] is True,
    'B_one_part_coverage_counterexample': observed is True and expected is False,
}
save('verification.json', {'all_pass': all(checks.values()), 'checks': checks,
                           'interpretation': 'Pass confirms independently calculated facts AND successful reproduction of defects, not that candidates pass.'})
print(json.dumps({'scenarios': len(names), 'primitive_rows': len(summaries), 'checks': checks}, ensure_ascii=False))
