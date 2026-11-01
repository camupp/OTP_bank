#!/usr/bin/env python3
"""Only CON-024v2 C3 rework checks; no closed export or38/40-test rerun."""
import sys
sys.dont_write_bytecode=True
import ast,copy,csv,hashlib,importlib.util,json
from pathlib import Path
from datetime import datetime,timedelta
P=Path(__file__).resolve().parent;R=P.parents[2];S=R/'supporting'
def h(x):return hashlib.sha256((json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
A=module('candidate024v2',P/'evaluator.py');reader=module('public_source',S/'round002-stress/reader.py');SPEC=load(P/'metrics-spec.json');CONFIGS=load(S/'round002-stress/business-config.json')['configs'];pro=load(P/'provenance.json')
checks=[];observations={}
def check(name,condition,observed=None):checks.append({'name':name,'status':'pass' if condition else 'fail','observed':observed})
def refresh(d):
 for z in d['source_manifest']:
  if z['table']=='approvals_audit' and z['availability'] in ('available','restored'):
   rs=[x for x in d[z['table']] if x.get('period_id',z['period_id'])==z['period_id']]
   z.update(expected_count=len(rs),received_count=len(rs),received_sha256=h(rs))
def positive_source():
 d=reader.expand_scenario('R1.volume',S/'fixtures')
 for a in d['approvals_audit']:a['signed_at']='2026-04-29T00:01:00+03:00' if a['period_id']=='P1' else '2026-07-29T00:01:00+03:00'
 for b in d['batch_metadata']:b['signed_at']='2026-04-29T00:02:00+03:00' if b['period_id']=='P1' else '2026-07-29T00:02:00+03:00'
 refresh(d);return d
# Reference signing projection is constructed here independently; it does not
# call package_source_digest or digest from the implementation under test.
def projection(d,configs):
 source={k:v for k,v in d.items() if k not in ('approvals_audit','source_manifest')}
 source['source_manifest']=[z for z in d['source_manifest'] if z['table']!='approvals_audit']
 source['source_audit']=[z for z in d['approvals_audit'] if z.get('action')!=SPEC['signature']['posting_action']]
 source['public_business_configs']=copy.deepcopy(configs)
 return source

def sign(d,configs=CONFIGS):
 before=h(projection(d,configs))
 a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['approval_id']=='P1:P031'))
 binding={'period':'P1','person':'P031','source_sha256':before,'rule_sha256':h(SPEC),'version':SPEC['candidate_key']}
 a.update(approval_id='HYPOTHETICAL-AWARD:P1:P031',action=SPEC['signature']['posting_action'],source_version='hypothetical-current-v2',version=2,signed_at='2026-04-29T00:03:00+03:00',package_binding_sha256=h(binding))
 d['approvals_audit'].append(a);refresh(d)
 return before==h(projection(d,configs))
def observe(d,configs=CONFIGS):
 A.PUBLIC_CONFIGS=copy.deepcopy(configs)
 _,people=A.evaluate(d,SPEC)
 p=next(x for x in people if x['period']=='P1' and x['subject']=='P031')
 return {k:p[k] for k in ('calculated_qualification_state','calculated_normal','authorization','authorization_errors','source_review_errors','potential_top_R','top_U_R','top_reserved_R','window_id','cohort_id','period','ledger_state')}
def held(x):return x['calculated_normal'] and x['calculated_qualification_state']=='earned' and x['potential_top_R']==150 and x['authorization']=='pending' and x['top_U_R']==0 and x['top_reserved_R']==150 and (x['window_id'],x['period'])==('W2026-A','P1')

code=(P/'evaluator.py').read_text();tree=ast.parse(code)
for name,pin in pro['rework']['unchanged_AST_functions'].items():
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 check('unchanged AST '+name,hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest()==pin)
for name,start,end in [('normal_stretch_units','def evaluate(data, spec):','    people=[]'),('rank_money','    for p,g in sorted','    return units, people'),('fixed_G','        rulemap=','        for e in data[')]:
 a=code.index(start);b=code.index(end,a)
 check('unchanged code '+name,hashlib.sha256(code[a:b].encode()).hexdigest()==pro['rework']['unchanged_code_slices'][name])
for name,pin in pro['rework']['reused_csv_semantic_pins'].items():
 rr=list(csv.DictReader((P/name).open()));now=[{k:v for k,v in r.items() if k!='candidate_key'} for r in rr]
 check('reused numerical output '+name,len(rr)==pin['rows'] and h(now)==pin['semantic_sha256_excluding_candidate_key'])

d=positive_source();check('independent projection has no own-award cycle',sign(d));positive=observe(d);observations['positive_current_package']=positive
check('positive matching current package authorizes150U only',positive['authorization']=='authorized' and positive['top_U_R']==150 and positive['potential_top_R']==150 and positive['ledger_state']=='authorized_U_not_posted',positive)
for label,value in [('early_team','2025-11-01T10:00:00+03:00'),('empty_team_time',''),('missing_team_time',None),('invalid_team_time','invalid-date')]:
 early=positive_source();next(a for a in early['approvals_audit'] if a['approval_id']=='P1:T07')['signed_at']=value;refresh(early);sign(early)
 x=observe(early);observations[label]=x
 check(label+' holds computed right/reserve/window withU0',held(x) and bool(x['source_review_errors']),x)
# Exact inclusive lower bound uses the same published local-day rule as personal.
bound=positive_source();rule=next(q for q in bound['period_rules'] if q['period_id']=='P1' and q['family']=='project');close=rule.get('quality_close_at') or rule['quality_close']
if len(close)==10:close+='T00:00:00+03:00'
next(a for a in bound['approvals_audit'] if a['approval_id']=='P1:T07')['signed_at']=close;refresh(bound);sign(bound)
x=observe(bound);observations['team_at_inclusive_close']=x
check('team close lower bound inclusive like personal',x['authorization']=='authorized' and x['top_U_R']==150,x)
changed=copy.deepcopy(CONFIGS);target=next(c for c in changed if c['comparison_group_id']=='R2-G-project' and c['source_query']['period_id']=='P1' and c['work_type']=='workflow' and c['version']==1)
check('assigned matching config precondition baseline null',target['baseline_value'] is None)
target['baseline_value']=0
x=observe(d,changed);observations['external_config_changed_same_signature']=x
check('external config full content change invalidates same signature',held(x) and 'award_package_hash_or_rule_binding_missing_or_changed' in x['authorization_errors'],x)
check('actual configs exactly independent reference projection',A.package_source_digest(d,SPEC['signature']['posting_action'])==h(projection(d,changed)))
replay=observe(d);observations['replay_same_current_package']=replay
check('replay returns same single authorized right not a second posting',replay==positive and replay['top_U_R']==150 and replay['ledger_state']=='authorized_U_not_posted',replay)
A.PUBLIC_CONFIGS=CONFIGS
result={'candidate_key':'CON-024@v2','parents':['CON-024@v1'],'status':'pass' if all(c['status']=='pass' for c in checks) else 'fail','scope':'Single targeted rework, two C3 defects only; no full scorer/source/resource regeneration and no independent admission','checks':checks,'observations':observations,'projection_definition':'CanonicalSHA(source tables excluding approvals_audit/source_manifest; source_manifest excluding approvals_audit partition; non-award source_audit; public_business_configs=complete actual PUBLIC_CONFIGS with versions/all fields). Award binding adds period/person/full spec SHA/candidate version. Physical audit count/SHA checked independently.','limitations':['Synthetic performed test signatures, not actual bank U or posting. Replay here proves deterministic authorization of one right; production ledger is specified separately.','Scorer, normal/stretch, G and resource/money are reused under semantic SHA/unchanged AST; prior38/40 are not rerun.','Original personal window and source dates are preserved by unchanged code/output pins; invalid authorization holds150R conditional reserve.','Independent evidence/finance will verify this narrow delta; no expansion of previous capacity/budget scope.']}
(P/'self-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'assertions':len(checks),'failed':[c['name'] for c in checks if c['status']=='fail'],'positive_U':positive['top_U_R'],'early_team_U':observations['early_team']['top_U_R'],'changed_config_U':observations['external_config_changed_same_signature']['top_U_R'],'replay_U':replay['top_U_R']},ensure_ascii=False))
if result['status']!='pass':raise SystemExit(1)
