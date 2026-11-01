#!/usr/bin/env python3
"""Author checks only; not independent reviewer admission. No fixture writes."""
import sys
sys.dont_write_bytecode=True
import copy,hashlib,importlib.util,json,random
from pathlib import Path
H=Path(__file__).resolve().parent
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ev=mod('own_eval',H/'evaluator.py');reader=mod('reader',ev.FIXTURE/'source/reader.py')
spec=json.loads((H/'metrics-spec.json').read_text())
def normalize(data):
 for m in data['source_manifest']:
  rows=[r for r in data[m['table']] if r.get('period_id',m['period_id'])==m['period_id']]
  m['received_count']=len(rows);m['expected_count']=len(rows)
  m['received_sha256']=hashlib.sha256((json.dumps(rows,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
def result(data):
 u,p=ev.evaluate(data,spec)
 return sorted([(r['period'],r['subject'],r['state'],r['stretch'],r['rank'],r['tie_size'],r['top_R'],r['top_state']) for r in p])
base=reader.expand_scenario('base');expected=result(base)
shuffled=copy.deepcopy(base)
for table,rows in shuffled.items():
 if table!='source_manifest':random.Random(2026).shuffle(rows)
normalize(shuffled)
dup=copy.deepcopy(base);dup['work_events'].append(copy.deepcopy(dup['work_events'][0]));normalize(dup)
checks={
 'row_order_awards_invariant':result(shuffled)==expected,
 'exact_duplicate_awards_invariant':result(dup)==expected,
 'worklog_inflated_invariant':result(reader.expand_scenario('F02.inflated'))==expected,
 'worklog_incomplete_invariant':result(reader.expand_scenario('F02.incomplete'))==expected,
 'deliverable_split_awards_invariant':result(reader.expand_scenario('F07.split'))==expected,
 'source_restore_original_result':result(reader.expand_scenario('F10.restored'))==expected,
}
def unit(scenario,subject):
 return next(r for r in ev.evaluate(reader.expand_scenario(scenario),spec)[0] if r['period']=='P1' and r['subject']==subject)
if spec['mode']=='role_conditions':
 checks.update(SLA90_fails=unit('F11.below','B01')['state']=='not_earned',
               SLA95_normal=unit('F11.at_contract','B01')['normal'],
               SLA100_stretch=unit('F11.ceiling','B01')['stretch'])
else:
 checks.update(flow_missing_use_is_pending=unit('base','S01')['state']=='pending',
               project_existing_accept_use_normal=unit('base','T01')['normal'],
               project_missing_stretch_date_pending=unit('base','T01')['stretch_state']=='pending')
checks.update(known_source_gap_not_computable=unit('F10.known_gap','S01')['state']=='not_computable',
 lost_QA_not_personal_fail=unit('F10.lost','S01')['state']=='pending',
 actual_late_acceptance_fails=unit('F03.late_acceptance','T01')['state']=='not_earned',
 done_without_evidence_pending=unit('F03.done_only','T01')['state']=='pending')
# Actual alternate names alone cannot turn a conflicted signature into a signed award.
_,persons=ev.evaluate(reader.expand_scenario('F09.conflicted'),spec)
checks['no_self_signed_person']=all(r['state']!='earned' and r['posting']!='signed' for r in persons if r['period']=='P1' and r['subject'] in ('S01','B01','P01'))
out={'type':'author self-check; not independent admission','python':sys.version.split()[0],'checks':checks,'all_pass':all(checks.values())}
(H/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
if not out['all_pass']:raise SystemExit(1)
