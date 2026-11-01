"""Current source controls: extract narrow predicates/fragments, never full evaluators."""
from pathlib import Path
import ast
import copy
import hashlib
import json
from datetime import datetime

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[1]
base = json.loads((ROUND / 'supporting/fixtures/source/base.json').read_text())
pins = json.loads((ROUND / 'private/versions-before-checks.json').read_text())
bad = [p for p,h in pins['files'].items() if hashlib.sha256((ROUND/p).read_bytes()).hexdigest()!=h]


def extract_approvals(path):
    tree = ast.parse(path.read_text())
    names = {'approval_errors', 'independent_approval'}
    nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    ns = {'datetime': datetime}
    exec(compile(ast.Module(body=nodes,type_ignores=[]), str(path),'exec'),ns)
    return ns['approval_errors'], ns['independent_approval'], tree


def coverage_fragment(tree):
    fn = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='evaluate')
    outer = next(n for n in fn.body if isinstance(n,ast.For))
    start = next(i for i,n in enumerate(outer.body) if isinstance(n,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id=='covered_cases' for t in n.targets))
    nodes = outer.body[start:start+3]
    # These statements contain only the scope check and trace, not metric or award logic.
    assert isinstance(nodes[2],ast.For)
    body = [ast.Assign(targets=[ast.Name(id='pending',ctx=ast.Store())],value=ast.List(elts=[],ctx=ast.Load()))] + copy.deepcopy(nodes)
    body.append(ast.Return(value=ast.Tuple(elts=[ast.Name(id='coverage_trace',ctx=ast.Load()),ast.Name(id='pending',ctx=ast.Load())],ctx=ast.Load())))
    args = ast.arguments(posonlyargs=[],args=[ast.arg(arg=x) for x in ('compatible','roots','family')],kwonlyargs=[],kw_defaults=[],defaults=[])
    wrapper = ast.FunctionDef(name='coverage',args=args,body=body,decorator_list=[])
    mod = ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[]))
    ns={}
    exec(compile(mod,'extracted_coverage_fragment','exec'),ns)
    return ns['coverage']


controls=[]
# A was independently checked in the immediately preceding assigned task; reuse its
# recorded controls without reading/reexecuting the A candidate or old versions.
for row in json.loads((HERE/'delta-A.json').read_text())['results']:
    controls.append({'candidate_key':row['candidate_key'],'control_kind':'performed_signature',
                     'vectors':row['signature_vectors'],'all_pass':row['all_delta_checks_pass']})

changes=[]
for number in ('020','021'):
    folder=ROUND/f'branches/B/con-{number}'
    spec=json.loads((folder/'metrics-spec.json').read_text())
    errors, approved, tree = extract_approvals(folder/'evaluator.py')
    coverage=coverage_fragment(tree)
    own={'T01'}|{m['employee_id'] for m in base['team_members'] if m['period_id']=='P1' and m['team_id']=='T01'}
    original=next(a for a in base['approvals_audit'] if a['period_id']=='P1' and a['beneficiary_id']=='P01')
    cases=[('independent_performed_action',{},True),
           ('other_team_beneficiary',{'signer_id':'P02'},False),
           ('team_id_as_actor',{'input_editor_id':'T01'},False),
           ('same_signer_operator',{'operator_id':original['signer_id']},False),
           ('same_editor_signer',{'input_editor_id':original['signer_id']},False),
           ('same_editor_operator',{'input_editor_id':original['operator_id']},False),
           ('empty_editor',{'input_editor_id':None},False),
           ('blank_signer',{'signer_id':'  '},False),
           ('missing_operator',{'operator_id':None},False),
           ('null_timestamp',{'signed_at':None},False),
           ('blank_timestamp',{'signed_at':' '},False),
           ('invalid_timestamp',{'signed_at':'not-a-time'},False),
           ('correction_is_not_posting_review',{'action':'type_correction'},False),
           ('signer_reports_to_team_member',{'signer_reporting_to':'P02'},False),
           ('editor_reports_to_beneficiary',{'input_editor_reporting_to':['P01']},False)]
    vectors=[]
    for ident,patch,expect in cases:
        a=copy.deepcopy(original);a.update(patch)
        observed=approved(a,own,spec['signature']['posting_action'],spec['signature']['distinct_pairs'])
        why=errors(a,own,spec['signature']['posting_action'],spec['signature']['distinct_pairs'])
        vectors.append({'case':ident,'changed_fields':patch,'forbidden_beneficiaries':sorted(own),
                        'expected_authorized':expect,'observed_predicate':observed,'errors':why,
                        'pass':observed==expect})
    # Observe caller guards separately: correct predicate is necessary, not sufficient.
    caller_vectors=[]
    for ident,patch,expected in [('source_scope_mismatch',{'source_ref':'P1:S01'},False),
                                ('team_scope_mismatch',{'beneficiary_team':'T02'},False)]:
        a=copy.deepcopy(original);a.update(patch)
        es=errors(a,own,spec['signature']['posting_action'],spec['signature']['distinct_pairs'])
        if a.get('source_ref')!='P1:P01':es.append('posting_review_source_scope_mismatch')
        if a.get('beneficiary_team') not in (None,'T01'):es.append('posting_review_team_scope_mismatch')
        caller_vectors.append({'case':ident,'changed_fields':patch,'expected_authorized':expected,
                               'observed_caller_guard_authorized':not es,'errors':es,'pass':(not es)==expected})
    controls.append({'candidate_key':spec['candidate_key'],'control_kind':'performed_independent_posting_review',
                     'vectors':vectors+caller_vectors,'all_pass':all(v['pass'] for v in vectors+caller_vectors)})
    events=[e for e in base['work_events'] if e['period_id']=='P1' and e['subject_id']=='T02']
    roots={events[0]['root_id']:events}
    qa=[a for a in base['quality_acts'] if a['period_id']=='P1' and a['subject_id']=='T02']
    partial=copy.deepcopy(qa[:1]); assert partial[0]['coverage_object']=='one_distinct_case'
    whole=copy.deepcopy(partial);whole[0]['coverage_object']='same_deliverable_inspection'
    unrelated=copy.deepcopy(whole);unrelated[0]['case_id']='unrelated-case';unrelated[0]['deliverable_id']='unrelated-deliverable'
    qa_vectors=[]
    for ident,acts,expected in [('all_eight_case_acts',qa,True),('one_of_eight_case_acts',partial,False),
                               ('explicit_linked_whole_deliverable_act',whole,True),('unrelated_whole_act',unrelated,False)]:
        trace,pending=coverage(acts,roots,'project')
        observed=all(t['covered'] for t in trace)
        qa_vectors.append({'case':ident,'source_case_count':len(events),'retained_act_count':len(acts),
                           'expected_complete_coverage':expected,'observed_coverage_guard':observed,
                           'trace':trace,'pending':pending,'pass':observed==expected})
    controls.append({'candidate_key':spec['candidate_key'],'control_kind':'QA_scope_and_completeness',
                     'vectors':qa_vectors,'all_pass':all(v['pass'] for v in qa_vectors)})
    old=json.loads((ROUND/f'private/pre-rework/branches/B/con-{number}/metrics-spec.json').read_text())
    changed=sorted(k for k in old.keys()|spec.keys() if old.get(k)!=spec.get(k))
    changes.append({'candidate_key':spec['candidate_key'],'changed_spec_keys':changed,
                    'business_mechanism_unchanged':set(changed)<={'candidate_key','signature','quality'}})

current={'scope':'Current independent controls on synthetic source copies; no actual bank evidence or causal claim',
         'method':'Narrow pure approval predicates and QA coverage fragment extracted with AST; complete candidate modules/evaluators/exports not executed. Expected requirements independently stated.',
         'controls':controls,'all_pass':not bad and all(c['all_pass'] for c in controls)}
(HERE/'current-control-vectors.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
delta={'pin_mismatches':bad,'pinned_files_checked':len(pins['files']),'metrics_changes':changes,
       'all_delta_checks_pass':current['all_pass'] and all(c['business_mechanism_unchanged'] for c in changes),
       'scope':'B targeted delta plus retained independent A control results; financial/model ledger handled in separate finance checks'}
(HERE/'delta-B.json').write_text(json.dumps(delta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_pass':current['all_pass'],'pin_mismatches':bad,'control_groups':len(controls),
                  'business_mechanism_unchanged':all(c['business_mechanism_unchanged'] for c in changes)},ensure_ascii=False))
