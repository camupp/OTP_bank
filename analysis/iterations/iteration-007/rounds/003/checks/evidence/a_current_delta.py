import sys
sys.dont_write_bytecode=True
import ast,copy,csv,json,hashlib,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('own_primitive',HERE/'primitive_support.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
R=m.ROOT;A=m.ast_namespace(R/'branches/A/con-024/evaluator.py');SPEC=json.loads((R/'branches/A/con-024/metrics-spec.json').read_text());CONFIGS=copy.deepcopy(m.CONFIGS)
assert SPEC['candidate_key']=='CON-024@v2'
def refresh(d):
 for z in d['source_manifest']:
  if z['availability'] in ['available','restored']:
   rs=[x for x in d[z['table']] if x.get('period_id',z['period_id'])==z['period_id']];z.update(expected_count=len(rs),received_count=len(rs),received_sha256=m.h(rs))
def positive():
 d=m.reader.expand_scenario('R1.volume',m.OLD)
 for a in d['approvals_audit']:a['signed_at']='2026-04-29T00:01:00+03:00' if a['period_id']=='P1' else '2026-07-29T00:01:00+03:00'
 for b in d['batch_metadata']:b['signed_at']='2026-04-29T00:02:00+03:00' if b['period_id']=='P1' else '2026-07-29T00:02:00+03:00'
 refresh(d);return d
def sign(d,person='P031',configs=CONFIGS):
 # Own canonical projection of all actual external records and source facts.
 source={k:v for k,v in d.items() if k not in ['approvals_audit','source_manifest']};source['source_manifest']=[z for z in d['source_manifest'] if z['table']!='approvals_audit'];source['source_audit']=[z for z in d['approvals_audit'] if z['action']!=SPEC['signature']['posting_action']];source['public_business_configs']=configs
 binding={'period':'P1','person':person,'source_sha256':m.h(source),'rule_sha256':m.h(SPEC),'version':SPEC['candidate_key']}
 a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['approval_id']=='P1:'+person));a.update(approval_id='AWARD:P1:'+person,action=SPEC['signature']['posting_action'],source_version='hypothetical-current',version=2,signed_at='2026-04-29T00:03:00+03:00',package_binding_sha256=m.h(binding));d['approvals_audit'].append(a);refresh(d);return binding,a
controls=[]
def observe(d,configs=CONFIGS,person='P031'):
 A['PUBLIC_CONFIGS']=configs;units,ps=A['evaluate'](d,SPEC);p=next(p for p in ps if p['period']=='P1' and p['subject']==person)
 return {k:p[k] for k in ['calculated_qualification_state','authorization','authorization_errors','source_review_errors','potential_top_R','top_reserved_R','top_U_R','window_id','cohort_id','ledger_state']},ps

def record(name,d,expected_U,configs=CONFIGS,person='P031'):
 obs,ps=observe(d,configs,person);ok=obs['top_U_R']==expected_U and obs['potential_top_R']==150 and obs['calculated_qualification_state']=='earned' and obs['window_id']=='W2026-A' and obs['cohort_id']=='C01'
 if expected_U==0:ok=ok and obs['top_reserved_R']==150
 controls.append({'candidate_key':SPEC['candidate_key'],'control':name,'expected':{'U_R':expected_U,'calculated_right_R':150,'calculated_qualification':'earned','original_window':'W2026-A','cohort':'C01','held_reserve_R':150 if expected_U==0 else 0},'observed':obs,'status':'pass' if ok else 'fail'});return obs,ps

# Positive packages for personal and team, assembled without author materializer.
for person in ['S31','P031']:
 d=positive();sign(d,person);record('positive_personal' if person=='S31' else 'positive_team_member',d,150,person=person)
# Each negative is independently signed over its current source, ensuring the
# actual performed team action/time is tested rather than just an old hash.
for label,timestamp in [('team_source_before_effort','2025-11-01T10:00:00+03:00'),('team_source_empty_time',''),('team_source_invalid_time','invalid-time')]:
 d=positive();next(a for a in d['approvals_audit'] if a['approval_id']=='P1:T07')['signed_at']=timestamp;refresh(d);sign(d);record(label,d,0)
# Explicit timestamp boundary belongs to this synthetic project quarter.
for label,timestamp,expected in [('team_source_at_exact_close','2026-04-28T12:00:00+03:00',150),('team_source_one_second_before_close','2026-04-28T11:59:59+03:00',0)]:
 d=positive();next(r for r in d['period_rules'] if r['period_id']=='P1' and r['family']=='project')['quality_close_at']='2026-04-28T12:00:00+03:00';next(a for a in d['approvals_audit'] if a['approval_id']=='P1:T07')['signed_at']=timestamp;refresh(d);sign(d);record(label,d,expected)
# Exact external config identity is required even if this field leaves scoring unchanged.
d=positive();sign(d);changed=copy.deepcopy(CONFIGS);next(c for c in changed if c['comparison_group_id']=='R2-G-project' and c['source_query']['period_id']=='P1' and c['work_type']=='workflow' and c['version']==1)['baseline_value']=0;record('external_config_changed_same_signature',d,0,configs=changed)
d=positive();sign(d,configs=changed);record('positive_current_changed_config',d,150,configs=changed)
# Missing award preserves independently established right and its reserve.
d=positive();record('missing_award_preserves_right_window_reserve',d,0)
# Replay observes one logical state; it does not execute a real ledger transaction.
d=positive();_,a=sign(d);x,ps=observe(d);x2,p2=observe(d);d['approvals_audit'].append(copy.deepcopy(a));refresh(d);x3,p3=observe(d)
controls.append({'candidate_key':SPEC['candidate_key'],'control':'replay_and_exact_duplicate_award_delivery','expected':{'U_states_R':[150,150,150],'unique_logical_rows':[1,1,1],'real_ledger_posting':'absent'},'observed':{'U_states_R':[v['top_U_R'] for v in [x,x2,x3]],'unique_logical_rows':[sum(p['subject']=='P031' and p['period']=='P1' for p in rows) for rows in [ps,p2,p3]],'windows':[v['window_id'] for v in [x,x2,x3]]},'status':'pass' if all(v['top_U_R']==150 for v in [x,x2,x3]) and all(sum(p['subject']=='P031' and p['period']=='P1' for p in rows)==1 for rows in [ps,p2,p3]) else 'fail'})
# No metric/quality/category/ranking changes: structural and data invariance.
old=R/'private/pre-rework/branches/A/con-024';cur=R/'branches/A/con-024'
def fs(p):return {n.name:n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
of=fs(old/'evaluator.py');nf=fs(cur/'evaluator.py')
checks={name:ast.dump(of[name],include_attributes=False)==ast.dump(nf[name],include_attributes=False) for name in ['quality_category','quality_rank_key']}
oldloops=[n for n in of['evaluate'].body if isinstance(n,ast.For)];newloops=[n for n in nf['evaluate'].body if isinstance(n,ast.For)];checks['primitive_normal_QA_loop']=ast.dump(oldloops[0],include_attributes=False)==ast.dump(newloops[0],include_attributes=False);checks['categorical_rank_money_loop']=ast.dump(oldloops[-1],include_attributes=False)==ast.dump(newloops[-1],include_attributes=False)
os=json.loads((old/'metrics-spec.json').read_text());ignored={'candidate_key','signature','batch_protocol'};checks['normal_quality_rank_policy_parameters']={k:v for k,v in os.items() if k not in ignored}=={k:v for k,v in SPEC.items() if k not in ignored}
# Compare exact nonmetadata numeric output bytes as parsed rows, not author tests.
csv_invariance={}
for name in ['unit-decisions.csv','decisions.csv','qa-neighborhood.csv','window-guarantee.csv']:
 def rows(path):return [{k:v for k,v in r.items() if k!='candidate_key'} for r in csv.DictReader(path.open())]
 csv_invariance[name]=rows(old/name)==rows(cur/name)
pins=json.loads((R/'private/versions-before-checks.json').read_text())['files'];bad=[p for p,v in pins.items() if hashlib.sha256((R/p).read_bytes()).hexdigest()!=v]
result={'candidate_key':SPEC['candidate_key'],'scope':'exact external configuration binding and performed team source time, positives, reserve/window and replay','method':'independent canonical source/config/rule projection; own expected150R from prior independent categorical calculation; current pure AST functions only observed; no author assertions/materializer as oracle','controls':controls,'summary':{'pass':sum(c['status']=='pass' for c in controls),'fail':sum(c['status']=='fail' for c in controls)},'limits':['Hypothetical in-memory actions only; public source unchanged.','For date-only quality_close the published A rule uses the start of its local day; explicit timestamps are tested inclusively.','U is an authorization state; no actual transactional ledger or API tested.']}
m.jsonout(HERE/'a-current-controls.json',result);m.jsonout(HERE/'current-delta-verification.json',{'candidate_key':SPEC['candidate_key'],'current_C3_summary':result['summary'],'semantic_invariance':checks,'numeric_CSV_invariance':csv_invariance,'final_pin_count':len(pins),'final_pin_mismatches':bad,'large_sweep_repeated':False,'QA_probes_repeated':False})
print(json.dumps({'C3':result['summary'],'semantic_invariance':checks,'CSV_invariance':csv_invariance,'pin_mismatches':bad,'failed_controls':[c for c in controls if c['status']=='fail']},ensure_ascii=False,indent=2))
