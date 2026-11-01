import sys
sys.dont_write_bytecode=True
import copy,json,importlib.util
from pathlib import Path
from datetime import timedelta
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('own_primitive',HERE/'primitive_support.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
R=m.ROOT;A=m.ast_namespace(R/'branches/A/con-024/evaluator.py');SPEC=json.loads((R/'branches/A/con-024/metrics-spec.json').read_text())
def refresh(d):
 for z in d['source_manifest']:
  if z['availability'] in ['available','restored']:
   rs=[x for x in d[z['table']] if x.get('period_id',z['period_id'])==z['period_id']];z.update(expected_count=len(rs),received_count=len(rs),received_sha256=m.h(rs))
def positive():
 d=m.reader.expand_scenario('R1.volume',m.OLD)
 for a in d['approvals_audit']:a['signed_at']='2026-04-29T00:01:00+03:00' if a['period_id']=='P1' else '2026-07-29T00:01:00+03:00'
 for b in d['batch_metadata']:b['signed_at']='2026-04-29T00:02:00+03:00' if b['period_id']=='P1' else '2026-07-29T00:02:00+03:00'
 refresh(d);return d
def sign(d,person='P031'):
 source={k:v for k,v in d.items() if k not in ['approvals_audit','source_manifest']};source['source_manifest']=[z for z in d['source_manifest'] if z['table']!='approvals_audit'];source['source_audit']=[z for z in d['approvals_audit'] if z['action']!=SPEC['signature']['posting_action']]
 binding={'period':'P1','person':person,'source_sha256':m.h(source),'rule_sha256':m.h(SPEC),'version':SPEC['candidate_key']}
 a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['approval_id']=='P1:'+person));a.update(approval_id='AWARD:P1:'+person,action=SPEC['signature']['posting_action'],source_version='hypothetical-current',version=2,signed_at='2026-04-29T00:03:00+03:00',package_binding_sha256=m.h(binding));d['approvals_audit'].append(a);refresh(d)
def observe(d,configs=None):
 A['PUBLIC_CONFIGS']=m.CONFIGS if configs is None else configs;_,ps=A['evaluate'](d,SPEC);p=next(p for p in ps if p['period']=='P1' and p['subject']=='P031');return {k:p[k] for k in ['calculated_qualification_state','authorization','authorization_errors','source_review_errors','potential_top_R','top_U_R','window_id']}
d=positive();sign(d);positive_observed=observe(d)
early=positive();next(a for a in early['approvals_audit'] if a['approval_id']=='P1:T07')['signed_at']='2025-11-01T10:00:00+03:00';refresh(early);sign(early)
cfg=copy.deepcopy(m.CONFIGS);next(c for c in cfg if c['comparison_group_id']=='R2-G-project' and c['source_query']['period_id']=='P1' and c['work_type']=='workflow' and c['version']==1)['baseline_value']=0
result={'candidate_key':SPEC['candidate_key'],'method':'own documented package projection, AST observation only, in-memory source copies','positive':positive_observed,'team_source_before_effort':{'expected_U_R':0,'observed':observe(early)},'external_config_changed_same_signature':{'expected_U_R':0,'observed':observe(d,cfg)}}
m.jsonout(HERE/'a-c3-specific.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
