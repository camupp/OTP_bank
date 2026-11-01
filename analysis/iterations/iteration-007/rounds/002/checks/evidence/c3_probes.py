import sys
sys.dont_write_bytecode=True
import importlib.util,copy,json
from pathlib import Path
P=Path(__file__).with_name('independent_check.py');sp=importlib.util.spec_from_file_location('own_check',P);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
B=m.ast_namespace(m.ROOT/'branches/B/con-023/evaluator.py');spec=json.loads((m.ROOT/'branches/B/con-023/metrics-spec.json').read_text())
def refresh(d):
 for part in d['source_manifest']:
  if part['table']=='approvals_audit':
   rows=[x for x in d['approvals_audit'] if x['period_id']==part['period_id']];part.update(expected_count=len(rows),received_count=len(rows),received_sha256=m.h(rows))
def run(name,change,person='S31'):
 d=m.reader.expand_scenario('R1.volume',m.OLD);a=copy.deepcopy(next(x for x in d['approvals_audit'] if x['approval_id']=='P1:'+person));a.update(approval_id='AWARD:P1:'+person,action='input_correction_and_posting_review',version=2,signed_at='2026-04-28T12:30:00+03:00');d['approvals_audit'].append(a)
 change(d,a);refresh(d);u,p=B['evaluate'](d,spec,m.CONFIGS);row=next(x for x in p if x['period']=='P1' and x['subject']==person)
 return {'probe':name,'expected':'hold U, preserve separately calculated qualification','observed':{k:row[k] for k in ['calculated_state','authorization','authorization_errors','source_review_errors','top_earned_R','top_U_R']}}
probes=[]
probes.append(run('posting signed before work and QA',lambda d,a:a.update(signed_at='2025-11-01T10:00:00+03:00')))
probes.append(run('source review has wrong source_ref',lambda d,a:next(x for x in d['approvals_audit'] if x['approval_id']=='P1:S31').update(source_ref='P2:someone_else')))
probes.append(run('source review time before work and QA',lambda d,a:next(x for x in d['approvals_audit'] if x['approval_id']=='P1:S31').update(signed_at='2025-11-01T10:00:00+03:00')))
probes.append(run('team source-review signed by beneficiary member',lambda d,a:next(x for x in d['approvals_audit'] if x['approval_id']=='P1:T07').update(signer_id='P032'),person='P031'))
a={'action':'input_correction_and_posting_review','signed_at':'2026-04-28T12:30:00+03:00','input_editor_id':'E','signer_id':'S','operator_id':'O'}
role_tests=[]
for name,patch in [('missing_editor',{'input_editor_id':''}),('editor_equals_signer',{'input_editor_id':'S'}),('operator_equals_signer',{'operator_id':'S'}),('team_member_signer',{'signer_id':'P002'}),('editor_reports_to_beneficiary',{'input_editor_reporting_to':'P001'}),('wrong_action_with_alternate',{'action':'type_correction','alternate_signer_id':'NEW'})]:
 row=dict(a,**patch);err=B['approval_errors'](row,{'T01','P001','P002'},'input_correction_and_posting_review');role_tests.append({'test':name,'observed_errors':err,'pass':bool(err)})
m.jsonout(m.OUT/'c3-probes.json',{'concrete_defects':probes,'role_controls':role_tests});print(json.dumps(probes,ensure_ascii=False,indent=2))
