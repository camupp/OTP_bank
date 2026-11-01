#!/usr/bin/env python3
"""Frozen source reader: no generator, private data or decision calculations."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def apply_ops(data, ops):
    data = copy.deepcopy(data)
    for op in ops:
        rows = data[op['table']]
        if op['op'] == 'reorder':
            keyed = {r[op['grain']]: r for r in rows}
            if len(keyed) != len(rows) or set(keyed) != set(op['keys']):
                raise ValueError('reorder must list each primary key exactly once')
            data[op['table']] = [keyed[k] for k in op['keys']]
            continue
        matches = [i for i, r in enumerate(rows)
                   if all(r.get(k) == v for k, v in op['key'].items())]
        if op['op'] == 'insert':
            if matches:
                raise ValueError('insert existing key')
            rows.append(copy.deepcopy(op['row']))
        else:
            if len(matches) != 1:
                raise ValueError(f"expected one row: {op['table']} {op['key']}")
            i = matches[0]
            if op['op'] == 'update':
                rows[i].update(copy.deepcopy(op['set']))
            elif op['op'] == 'delete':
                rows.pop(i)
            elif op['op'] == 'append_export_copy':
                rows.append(copy.deepcopy(rows[i]))
            else:
                raise ValueError(op['op'])
    return data

def scenario_index(old_fixture_root):
    """Explicit old fixture directory is mandatory; returns 23 old + new names."""
    old = Path(old_fixture_root).resolve()
    items = [{'name': 'base', 'source': 'old', 'baseline': 'base'}]
    for row in json.loads((old/'source/scenario_index.json').read_text()):
        for variant in row['variants']:
            items.append({'name': row['scenario_id']+'.'+variant,
                          'source': 'old', 'baseline': 'base'})
    items.extend(json.loads((ROOT/'source/scenario_index.json').read_text()))
    return items

def business_configs(comparison_group_id, period_id, work_type=None, version=1):
    """Metadata lookup only. Empty list explicitly means no matching configuration.

    Defaults to prospective v1. Request version=2 explicitly to inspect a conflict;
    this function does not establish validity or compute any worker result.
    """
    rows = json.loads((ROOT/'business-config.json').read_text())['configs']
    return [r for r in rows if r['comparison_group_id'] == comparison_group_id
            and r['source_query']['period_id'] == period_id and r['version'] == version
            and (work_type is None or r['work_type'] == work_type)]

def expand_scenario(scenario_id, old_fixture_root, variant=None):
    """expand_scenario('R1.volume', '/explicit/path/to/old/fixtures').

    Old shorthand expand_scenario('F02', old_root, 'inflated') is also supported.
    Every call starts from an immutable source snapshot; patches never accumulate.
    """
    old = Path(old_fixture_root).resolve()
    if variant is not None:
        scenario_id += '.'+variant
    rows = json.loads((ROOT/'source/scenario_index.json').read_text())
    entry = next((r for r in rows if r['name'] == scenario_id), None)
    if entry:
        data = json.loads((ROOT/entry['source_ref']).read_text())
        if entry.get('patch_ref'):
            data = apply_ops(data, json.loads((ROOT/entry['patch_ref']).read_text())['operations'])
        return data
    data = json.loads((old/'source/base.json').read_text())
    if scenario_id == 'base':
        return data
    family, *part = scenario_id.split('.', 1)
    if family not in {f'F{i:02}' for i in range(1, 13)}:
        raise ValueError('Unknown scenario: '+scenario_id)
    variants = json.loads((old/'patches'/f'{family}.json').read_text())['variants']
    if not part:
        if len(variants) != 1:
            raise ValueError('Choose variant: '+', '.join(variants))
        part = [next(iter(variants))]
    return apply_ops(data, variants[part[0]])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario', nargs='?')
    parser.add_argument('--old-fixture-root', required=True)
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    result = scenario_index(args.old_fixture_root) if args.list else expand_scenario(args.scenario, args.old_fixture_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
