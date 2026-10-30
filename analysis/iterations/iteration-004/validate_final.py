"""Targeted artifact integrity/coverage check; not a bank-effect validation."""
from pathlib import Path
import hashlib, json, re, urllib.parse
RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[2]
R=RUN/'rounds/001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
checks={};errors=[]
def check(k,v):
    checks[k]=bool(v)
    if not v:errors.append(k)
for p in R.rglob('*.json'):read(p)
check('all_round_json_parse',True)
manifest=read(R/'inputs/manifest.json')
check('five_frozen_inputs_unchanged',all(sha(R/'inputs'/p)==h for p,h in manifest['files'].items()) and len(manifest['files'])==5)
check('rubric_unchanged',sha(R/'inputs/rubric.json')==sha(ROOT/'.agents/skills/case-iteration/assets/rubric.json'))
c=read(RUN/'run-config.json');d=read(ROOT/'.agents/skills/case-iteration/assets/run-config.json')
check('limits_one_round_one_concept_two_branches',c['max_iterations']==1 and c['first_round_candidates_per_branch']==1 and c['parallel_branches']==2 and c['max_rework_per_round']==1)
check('global_defaults_preserved',d['max_iterations']==3 and d['first_round_candidates_per_branch']==2)
p=read(RUN/'provenance.json')
check('all_preparation_dependencies_unchanged',all(sha(ROOT/x)==h for x,h in p['preparation_hashes'].items()))
v=read(R/'private/versions-before-checks.json')
check('candidate_versions_unchanged',all(sha(ROOT/x)==h for x,h in v['files'].items()))
old=ROOT/'analysis/iterations/iteration-003/rounds/001/branches/B/concept.md'
check('incumbent_three_copies_byte_identical',old.read_bytes()==(RUN/'incumbent/concept.md').read_bytes()==(R/'supporting/incumbent/concept.md').read_bytes())
pm=read(R/'review-packet/manifest.json')
check('final_reviewer_packet_unchanged',all(sha(R/'review-packet'/p)==h for p,h in pm['files'].items()))
leaks=[]
for f in (R/'review-packet').rglob('*'):
    if f.is_file():
        for pattern in [r'CON-\d+',r'branches/[AB]',r'incumbent',r'\bB_',r'H-B2',r'lineage']:
            if re.search(pattern,f.read_text()):leaks.append((str(f.relative_to(R)),pattern))
check('no_identity_labels_in_final_packet',not leaks)
repair=read(R/'private/anonymity-repair.json')
check('first_review_and_packet_preserved',all((R/x).is_file() for x in repair['first_review_preserved']) and (R/repair['first_packet_preserved']).is_dir())
check('repair_only_technical_labels',repair['candidate_and_shared_bytes_unchanged'] and not repair['concept_mechanism_changes'] and not repair['financial_changes'] and not repair['rubric_changes'])
keys={'BASELINE','CON-006@v2','CON-009@v1','CON-010@v1'}
f=read(R/'checks/finance.json');e=read(R/'checks/evidence.json')
check('four_finance_and_evidence_results',{x['candidate_key'] for x in f['results']}==keys=={x['candidate_key'] for x in e['results']})
check('independent_finance_arithmetic',read(R/'checks/finance/verification.json')['status']=='pass')
review=read(R/'review.json');rub=read(R/'inputs/rubric.json');mapping=read(R/'private/review-map.json')['aliases']
check('four_final_reviewer_assessments',{x['alias'] for x in review['results']}==set(mapping))
check('complete_gates_and_criteria',all(set(x['gates'])==set(rub['gates']) and set(x['criteria'])==set(rub['criteria']) and all(type(n)==int and 0<=n<=3 for n in x['criteria'].values()) for x in review['results']))
selection=read(R/'selection.json')
check('updated_inputs_disclosed',selection['inputs_changed'] and manifest['fingerprint']!=read(R/'round.json')['previous_input_fingerprint'])
if selection['selected_alias']:
    a=selection['selected_alias'];rr=next(x for x in review['results'] if x['alias']==a);k=mapping[a]['candidate_key']
    check('selected_from_eligible_final_shortlist',a in review['shortlist'] and all(x=='pass' for x in rr['gates'].values()) and k==selection['champion'])
    check('selected_finance_evidence_consistent',all(x=='pass' for x in next(x for x in f['results'] if x['candidate_key']==k)['gates'].values()) and next(x for x in e['results'] if x['candidate_key']==k)['status']!='unsupported')
    if (R/'snapshot.json').exists():
        check('selected_copy_matches_reviewed_version',sha(R/'selected.md')==sha(R/'review-packet/candidates'/(a+'.md')))
else:check('null_selection_honest',selection['champion'] is None and not selection['material_improvement'])
links=[];planned=[]
paths=list(R.rglob('*.md'))+[RUN/'report.md',ROOT/'project/status.md',ROOT/'project/decisions.md',ROOT/'README.md',ROOT/'analysis/README.md',ROOT/'analysis/iterations/README.md',ROOT/'analysis/preparation/README.md',ROOT/'research/README.md']
for p in paths:
    if not p.is_file():errors.append('missing '+str(p));continue
    prose=re.sub(r'```.*?```','',p.read_text(),flags=re.S)
    prose=re.sub(r'`[^`]*`','',prose)
    for m in re.finditer(r'\[[^\]]+\]\((<[^>]+>|[^)]+)\)',prose):
        t=m[1].strip('<>')
        if t.startswith(('https://','http://','#','codex://')):continue
        target=urllib.parse.unquote(t.split('#')[0])
        if not (p.parent/target).exists():
            if (p.parent/target).resolve()==(R/'snapshot.json').resolve():planned.append((str(p.relative_to(ROOT)),t))
            else:links.append((str(p.relative_to(ROOT)),t))
check('local_markdown_links_resolve',not links)
check('round_rework_limit_respected',read(R/'round.json')['rework_count']<=1)
if (R/'snapshot.json').exists():
    state=read(RUN/'state.json')
    check('completed_single_round',state['status']=='completed' and state['completed_rounds']==1 and state['active_round'] is None and state['stop_reason']=='iteration_limit' and state['current_best']['candidate_key']==selection['champion'])
result={'status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'identity_leaks':leaks,'broken_links':links,'planned_snapshot_links_before_seal':planned,'finance_rows':read(R/'checks/finance/verification.json')['row_counts'],'scope':'Structure, source versions, flow/calculation check records, links and final-review eligibility; no measured effect or real bank rollout proof','closed_snapshot':'rounds/001/snapshot.json' if (R/'snapshot.json').exists() else None}
(RUN/'final-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
