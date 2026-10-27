#!/usr/bin/env python3
"""Local artifact storage. No model calls, network requests or raw ingestion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

PACK = ('context.md', 'evidence.md', 'diagnosis.md', 'baseline.md', 'rubric.json')
CORE_GATES = {'case_scope', 'budget', 'currency_balances', 'three_user_groups', 'evidence_integrity'}
CONFIG_KEYS = {'schema_version', 'max_iterations', 'parallel_branches',
               'first_round_candidates_per_branch', 'later_candidates_per_branch',
               'max_stagnant_rounds', 'max_rework_per_round', 'max_wall_minutes'}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_file(base, value, boundary=None):
    require(isinstance(value, str) and value and not Path(value).is_absolute(), 'Expected relative file path')
    path = (base / value).resolve()
    boundary = (boundary or base).resolve()
    require(boundary in path.parents and path.is_file(), 'Missing file or path escapes boundary: ' + value)
    require(path.stat().st_size > 0, 'Empty artifact: ' + value)
    return path


def validate_config(config):
    require(set(config) == CONFIG_KEYS and config['schema_version'] == 1, 'Invalid run configuration')
    require(config['parallel_branches'] == 2, 'This workflow supports exactly two branches')
    for field in ('max_iterations', 'first_round_candidates_per_branch',
                  'later_candidates_per_branch', 'max_stagnant_rounds'):
        require(type(config[field]) is int and config[field] > 0, 'Invalid limit: ' + field)
    require(type(config['max_rework_per_round']) is int and config['max_rework_per_round'] >= 0,
            'Invalid rework limit')
    minutes = config['max_wall_minutes']
    require(minutes is None or (type(minutes) in (int, float) and minutes > 0), 'Invalid wall-time limit')


def hash_files(folder, exclude=()):
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            require(not path.is_symlink(), 'Snapshot cannot contain symlinks: ' + str(path))
            name = str(path.relative_to(folder))
            if name not in exclude:
                result[name] = sha(path)
    return result


def verify_snapshot(folder):
    record = read(folder / 'snapshot.json')
    actual = hash_files(folder, ('snapshot.json',))
    require(actual == record['files'], 'Sealed snapshot changed: ' + str(folder))
    return record


def input_manifest(folder):
    files = {name: sha(folder / name) for name in PACK}
    fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'schema_version': 1, 'files': files, 'fingerprint': fingerprint}


def check_inputs(folder):
    expected = read(folder / 'manifest.json')
    actual = input_manifest(folder)
    require(expected == actual, 'Frozen input packet changed')
    return actual['fingerprint']


def wall_exhausted(state, config):
    limit = config['max_wall_minutes']
    if limit is None:
        return False
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(state['created_at'])).total_seconds()
    return elapsed >= limit * 60


def validate_round(run, folder, config):
    meta = read(folder / 'round.json')
    fingerprint = check_inputs(folder / 'inputs')
    require(meta['input_fingerprint'] == fingerprint, 'Round input fingerprint mismatch')
    require(type(meta['rework_count']) is int and 0 <= meta['rework_count'] <= config['max_rework_per_round'],
            'Rework limit exceeded')
    rubric = read(folder / 'inputs/rubric.json')
    gates, criteria = rubric['gates'], rubric['criteria']
    require(CORE_GATES.issubset(set(gates)) and criteria and len(gates) == len(set(gates)) and len(criteria) == len(set(criteria)),
            'Invalid rubric keys')
    plan = read(folder / 'plan.json')
    require(plan.get('round_goal') and plan.get('novelty_rationale'), 'Plan needs goal and novelty rationale')
    specs = plan['branches']
    require(len(specs) == 2 and {x['branch_id'] for x in specs} == {'A', 'B'}, 'Plan must assign A and B')
    count = config['first_round_candidates_per_branch'] if meta['round'] == 1 else config['later_candidates_per_branch']
    generated = {}
    for spec in specs:
        branch = spec['branch_id']
        require(spec.get('output_dir') == 'branches/' + branch and spec.get('candidate_count') == count,
                'Branch output/count differs from run contract')
        require(all(spec.get(k) for k in ('mode', 'question', 'approach', 'distinction',
                                         'success_condition', 'rejection_condition')), 'Incomplete branch assignment')
        result = read(folder / 'branches' / branch / 'branch.json')
        require(result['branch_id'] == branch and result['status'] in ('complete', 'failed'), 'Invalid branch status')
        candidates = result['candidates']
        if result['status'] == 'failed':
            require(not candidates and result.get('failure_reason'), 'Failed branch needs reason and no claimed candidates')
        else:
            require(len(candidates) == count, 'Completed branch has wrong candidate count')
        for candidate in candidates:
            key = candidate['candidate_key']
            require(re.fullmatch(r'CON-\d+@v[1-9]\d*', key or '') and key not in generated, 'Invalid/duplicate candidate key')
            require(isinstance(candidate.get('parents'), list) and candidate.get('mechanism'), 'Candidate needs lineage and mechanism')
            path = relative_file(folder, candidate['path'])
            require((folder / 'branches' / branch).resolve() in path.parents, 'Candidate writes outside its branch')
            generated[key] = path
    mapping = read(folder / 'private/review-map.json')['aliases']
    require(mapping and all(re.fullmatch(r'V\d+', x) for x in mapping), 'Invalid review aliases')
    keys = [x['candidate_key'] for x in mapping.values()]
    require(len(keys) == len(set(keys)), 'One candidate version mapped more than once')
    prior = meta['prior_best']
    expected_keys = set(generated) | {'BASELINE'}
    if prior:
        expected_keys.add(prior['candidate_key'])
        require(prior['candidate_key'] not in generated, 'Unchanged incumbent cannot be a newly generated version')
    require(set(keys) == expected_keys, 'Review must include all generated candidates, baseline and incumbent')
    for alias, item in mapping.items():
        key, kind = item['candidate_key'], item['kind']
        origin = relative_file(folder, item['origin_path'], run)
        if key == 'BASELINE':
            require(kind == 'baseline' and origin == (folder / 'inputs/baseline.md').resolve(), 'Wrong baseline mapping')
        elif prior and key == prior['candidate_key']:
            require(kind == 'incumbent' and origin == relative_file(run, prior['artifact_path']), 'Wrong incumbent mapping')
        else:
            require(kind == 'candidate' and origin == generated[key], 'Wrong candidate mapping')
        relative_file(folder, 'review-packet/candidates/' + alias + '.md')
    relative_file(folder, 'review-packet/checks.json')
    finance_rows = read(folder / 'checks/finance.json')['results']
    evidence_rows = read(folder / 'checks/evidence.json')['results']
    finance = {x['candidate_key']: x for x in finance_rows}
    evidence = {x['candidate_key']: x for x in evidence_rows}
    require(len(finance) == len(finance_rows) and set(finance) == expected_keys, 'Finance coverage incomplete/duplicate')
    require(len(evidence) == len(evidence_rows) and set(evidence) == expected_keys, 'Evidence coverage incomplete/duplicate')
    for key in expected_keys:
        entry = finance[key]
        require(entry.get('scenario_scope') and set(entry['gates']) == {'budget', 'currency_balances'}, 'Invalid finance scenario/gates')
        require(all(x in ('pass', 'fail', 'uncertain') for x in entry['gates'].values()), 'Invalid finance gate status')
        for value in entry.get('calculation_paths', []):
            relative_file(folder, value)
        require(evidence[key]['status'] in ('supported', 'partial', 'unsupported'), 'Invalid evidence status')
    review = read(folder / 'review.json')
    results = {x['alias']: x for x in review['results']}
    require(len(results) == len(review['results']) and set(results) == set(mapping), 'Review coverage incomplete/duplicate')
    shortlist = review['shortlist']
    require(isinstance(shortlist, list) and len(shortlist) == len(set(shortlist)), 'Invalid shortlist')
    for alias, result in results.items():
        require(set(result['gates']) == set(gates), 'Missing review gates')
        require(all(x in ('pass', 'fail', 'uncertain') for x in result['gates'].values()), 'Invalid review gate')
        require(set(result['criteria']) == set(criteria), 'Missing review criteria')
        require(all(type(x) is int and 0 <= x <= 3 for x in result['criteria'].values()), 'Invalid criterion score')
        require(isinstance(result.get('findings'), list) and result.get('confidence'), 'Review needs findings and confidence grounds')
        key = mapping[alias]['candidate_key']
        for gate in ('budget', 'currency_balances'):
            if result['gates'].get(gate) == 'pass':
                require(finance[key]['gates'][gate] == 'pass', 'Reviewer gate contradicts finance check')
        if result['gates'].get('evidence_integrity') == 'pass':
            require(evidence[key]['status'] != 'unsupported', 'Reviewer gate contradicts evidence check')
    for alias in shortlist:
        require(alias in results and mapping[alias]['kind'] != 'baseline', 'Unknown/baseline shortlist entry')
        require(all(x == 'pass' for x in results[alias]['gates'].values()), 'Ineligible shortlist candidate')
    selection = read(folder / 'selection.json')
    require(selection.get('rationale') and type(selection.get('material_improvement')) is bool, 'Missing selection rationale/improvement')
    require(type(selection.get('inputs_changed')) is bool, 'Missing inputs_changed flag')
    expected_change = bool(meta.get('previous_input_fingerprint') and fingerprint != meta['previous_input_fingerprint'])
    require(selection['inputs_changed'] == expected_change, 'Input comparability flag is incorrect')
    chosen = selection['selected_alias']
    if chosen is None:
        require(selection['champion'] is None and not selection['material_improvement'], 'Null selection cannot claim a champion/improvement')
    else:
        require(chosen in shortlist and selection['champion'] == mapping[chosen]['candidate_key'], 'Selection disagrees with shortlist/map')
        if prior and selection['champion'] == prior['candidate_key'] and not expected_change:
            require(not selection['material_improvement'], 'Unchanged incumbent on unchanged inputs is not an improvement')
    if selection['material_improvement']:
        require(bool(selection.get('improvement_basis')), 'Improvement needs concrete supporting grounds')
    require(selection.get('stop_reason') in (None, 'no_useful_check', 'missing_data', 'resource_limit'), 'Unknown stop reason')
    for name in ('review.md', 'delta.md'):
        relative_file(folder, name)
    return meta, selection, mapping


def advance(run, folder, config):
    state = read(run / 'state.json')
    meta, selection = read(folder / 'round.json'), read(folder / 'selection.json')
    if state['completed_rounds'] >= meta['round']:
        return state
    require(state['completed_rounds'] == meta['round'] - 1, 'Cannot commit rounds out of order')
    best = None
    if selection['champion']:
        best = {'candidate_key': selection['champion'], 'round': meta['round'],
                'artifact_path': str((folder / 'selected.md').relative_to(run)),
                'input_fingerprint': meta['input_fingerprint']}
    save(run / 'best.json', {'champion': best})
    state.update(completed_rounds=meta['round'], active_round=None, current_best=best,
                 previous_input_fingerprint=meta['input_fingerprint'])
    state['stagnant_rounds'] = 0 if selection['material_improvement'] else state['stagnant_rounds'] + 1
    reason = selection.get('stop_reason')
    if not reason and wall_exhausted(state, config):
        reason = 'resource_limit'
    if not reason and state['completed_rounds'] >= config['max_iterations']:
        reason = 'iteration_limit'
    if not reason and state['stagnant_rounds'] >= config['max_stagnant_rounds']:
        reason = 'stagnation_limit'
    state['status'] = 'needs_inputs' if reason == 'missing_data' else ('completed' if reason else 'ready_for_next')
    state['stop_reason'] = reason
    save(run / 'state.json', state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('create', 'begin', 'validate', 'seal', 'compare', 'status', 'stop', 'resume'))
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--input-pack', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--round', type=int)
    parser.add_argument('--reason', default='user_request')
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.run_id), 'Invalid run ID')
    root = args.project_root.resolve()
    run = root / 'analysis/iterations' / args.run_id
    require(root in run.resolve().parents, 'Run path escapes project')
    if args.command == 'create':
        require(not run.exists(), 'Run already exists; do not reset history')
        default = Path(__file__).resolve().parent.parent / 'assets/run-config.json'
        config = read(args.config or default)
        validate_config(config)
        run.mkdir(parents=True)
        save(run / 'run-config.json', config)
        state = {'schema_version': 1, 'run_id': args.run_id, 'created_at': now(), 'status': 'ready',
                 'config_sha256': sha(run / 'run-config.json'),
                 'completed_rounds': 0, 'active_round': None, 'current_best': None,
                 'stagnant_rounds': 0, 'previous_input_fingerprint': None, 'stop_reason': None}
        save(run / 'state.json', state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return
    require((run / 'state.json').is_file(), 'Unknown run')
    config, state = read(run / 'run-config.json'), read(run / 'state.json')
    validate_config(config)
    require(sha(run / 'run-config.json') == state['config_sha256'], 'Run limits changed; do not reset agreed limits silently')
    if args.command == 'status':
        print(json.dumps(state, ensure_ascii=False, indent=2)); return
    if args.command == 'stop':
        require(state['status'] not in ('completed', 'needs_inputs'), 'Run already ended')
        state.update(status='stopped', stop_reason=args.reason)
        save(run / 'state.json', state)
        print('Stopped; unfinished artifacts retained.'); return
    if args.command == 'resume':
        require(state['status'] == 'stopped', 'Only explicitly stopped runs can resume')
        state.update(status='working' if state['active_round'] else 'ready_for_next', stop_reason=None)
        save(run / 'state.json', state)
        print('Resumed without resetting iteration/resource limits.'); return
    if args.command == 'begin':
        require(state['status'] in ('ready', 'ready_for_next'), 'Run not ready; inspect status/unfinished round')
        require(not wall_exhausted(state, config), 'Wall-time budget exhausted')
        require(state['completed_rounds'] < config['max_iterations'], 'Iteration limit reached')
        require(args.input_pack and args.input_pack.is_dir(), 'Prepared input pack required')
        for number in range(1, state['completed_rounds'] + 1):
            verify_snapshot(run / 'rounds' / ('%03d' % number))
        for name in PACK:
            path = args.input_pack / name
            require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0, 'Missing/empty input or symlink: ' + name)
        rubric = read(args.input_pack / 'rubric.json')
        require(rubric.get('gates') and rubric.get('criteria'), 'Input rubric missing')
        number = state['completed_rounds'] + 1
        folder = run / 'rounds' / ('%03d' % number)
        require(not folder.exists(), 'Unfinished round exists; inspect it instead of overwriting')
        for name in ('inputs', 'branches/A', 'branches/B', 'checks', 'private', 'review-packet/candidates'):
            (folder / name).mkdir(parents=True, exist_ok=True)
        for name in PACK:
            shutil.copyfile(args.input_pack / name, folder / 'inputs' / name)
        manifest = input_manifest(folder / 'inputs')
        save(folder / 'inputs/manifest.json', manifest)
        save(folder / 'round.json', {'schema_version': 1, 'round': number, 'status': 'working', 'created_at': now(),
                                   'input_fingerprint': manifest['fingerprint'], 'prior_best': state['current_best'],
                                   'previous_input_fingerprint': state['previous_input_fingerprint'], 'rework_count': 0})
        state.update(status='working', active_round=number)
        save(run / 'state.json', state)
        print(str(folder)); return
    number = args.round or state['active_round'] or state['completed_rounds']
    require(type(number) is int and number > 0, 'Round number required')
    folder = run / 'rounds' / ('%03d' % number)
    require(folder.is_dir(), 'Unknown round')
    if args.command == 'compare':
        verify_snapshot(folder)
        meta, selection = read(folder / 'round.json'), read(folder / 'selection.json')
        print(json.dumps({'round': number, 'previous_best': meta['prior_best'], 'champion': selection['champion'],
                          'inputs_changed': selection['inputs_changed'],
                          'declared_material_improvement': selection['material_improvement'],
                          'declared_grounds': selection.get('improvement_basis', []),
                          'semantic_comparison': str(folder / 'delta.md')}, ensure_ascii=False, indent=2)); return
    if (folder / 'snapshot.json').exists():
        verify_snapshot(folder)
        if args.command == 'seal':
            print(json.dumps(advance(run, folder, config), ensure_ascii=False, indent=2))
        else:
            print('Sealed snapshot hashes valid; no factual verification performed.')
        return
    meta, selection, mapping = validate_round(run, folder, config)
    if args.command == 'validate':
        print('Working round structure valid; no factual verification performed.'); return
    require(args.command == 'seal' and state['active_round'] == number, 'Only active round can be sealed')
    chosen = selection['selected_alias']
    if chosen:
        source = folder / 'review-packet/candidates' / (chosen + '.md')
        target = folder / 'selected.md'
        require(not target.exists() or sha(target) == sha(source), 'Existing selected.md differs from reviewed candidate')
        if not target.exists():
            shutil.copyfile(source, target)
    else:
        require(not (folder / 'selected.md').exists(), 'Null winner must not retain selected.md')
    meta.update(status='sealed', sealed_at=now())
    save(folder / 'round.json', meta)
    save(folder / 'snapshot.json', {'schema_version': 1, 'sealed_at': now(),
                                   'files': hash_files(folder, ('snapshot.json',))})
    print(json.dumps(advance(run, folder, config), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
