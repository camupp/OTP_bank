#!/usr/bin/env python3
"""Source-only reader. Reads base.json and ../patches; never imports generator or oracle."""
import copy
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def apply_ops(data, ops):
    out=copy.deepcopy(data)
    for op in ops:
        table=op['table']; key=op['key']; rows=out[table]
        matches=[i for i,row in enumerate(rows) if all(row.get(k)==v for k,v in key.items())]
        if op['op']=='insert':
            if matches: raise ValueError(f'insert existing key {table} {key}')
            rows.append(copy.deepcopy(op['row']))
        elif op['op']=='update':
            if len(matches)!=1: raise ValueError(f'update expected single key {table} {key}')
            rows[matches[0]].update(copy.deepcopy(op['set']))
        elif op['op']=='delete':
            if len(matches)!=1: raise ValueError(f'delete expected single key {table} {key}')
            rows.pop(matches[0])
        elif op['op']=='append_export_copy':
            if len(matches)!=1: raise ValueError('copy must select one row')
            rows.append(copy.deepcopy(rows[matches[0]]))
        else: raise ValueError(op['op'])
    return out


def expand_scenario(scenario_id, variant=None):
    """Read only source/base.json and one public patch; no recognition calculation.

    expand_scenario('F02.inflated') or expand_scenario('F02','inflated').
    F01 defaults to observed; multi-variant cases require an explicit variant.
    """
    data=json.loads((ROOT/'source/base.json').read_text())
    if scenario_id=='base':return data
    if '.' in scenario_id:
        scenario_id,variant=scenario_id.split('.',1)
    sc=json.loads((ROOT/'patches'/f'{scenario_id}.json').read_text())
    if variant is None:
        if len(sc['variants'])!=1:raise ValueError(f'Choose variant: {list(sc["variants"])}')
        variant=next(iter(sc['variants']))
    return apply_ops(data,sc['variants'][variant])


if __name__ == '__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: reader.py base|Fxx.variant')
    print(json.dumps(expand_scenario(sys.argv[1]),ensure_ascii=False,sort_keys=True,indent=2))
