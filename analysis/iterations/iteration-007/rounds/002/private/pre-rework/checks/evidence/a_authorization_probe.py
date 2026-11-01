import sys
sys.dont_write_bytecode=True
import importlib.util,json,copy
from pathlib import Path
p=Path(__file__).with_name('independent_check.py');sp=importlib.util.spec_from_file_location('check',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
d=m.reader.expand_scenario('R1.volume',m.OLD);spec=json.loads((m.ROOT/'branches/A/con-022/metrics-spec.json').read_text());A=m.ast_namespace(m.ROOT/'branches/A/con-022/evaluator.py')
# Independently implement the documented canonical non-circular signing projection.
source={k:v for k,v in d.items() if k not in ['approvals_audit','source_manifest']};source['source_manifest']=[z for z in d['source_manifest'] if z['table']!='approvals_audit'];source['source_audit']=[z for z in d['approvals_audit'] if z.get('action')!='input_correction_and_posting_review']
binding={'period':'P1','person':'S31','source_sha256':m.h(source),'rule_sha256':m.h(spec),'version':'CON-022@v1'}
a=copy.deepcopy(next(x for x in d['approvals_audit'] if x['approval_id']=='P1:S31'));a.update(approval_id='AWARD:P1:S31',action='input_correction_and_posting_review',signed_at='2026-04-28T12:30:00+03:00',source_version='OTP-SYN-007-R002-v1',version=2,package_binding_sha256=m.h(binding));d['approvals_audit'].append(a)
for z in d['source_manifest']:
 if z['table']=='approvals_audit':
  rs=[x for x in d['approvals_audit'] if x['period_id']==z['period_id']];z.update(expected_count=len(rs),received_count=len(rs),received_sha256=m.h(rs))
_,ps=A['evaluate'](d,spec);good=next(x for x in ps if x['period']=='P1' and x['subject']=='S31')
spec2=copy.deepcopy(spec);spec2['top_R_per_person']=300;_,ps=A['evaluate'](d,spec2);bad=next(x for x in ps if x['period']=='P1' and x['subject']=='S31')
result={'method':'independent expected binding; AST functions only to reproduce exact signing control, no export or posting','valid_performed_bound_review':{k:good[k] for k in ['authorization','authorization_errors','potential_top_R','top_U_R']},'same_signature_changed_rule':{k:bad[k] for k in ['authorization','authorization_errors','potential_top_R','top_U_R']},'expected_pass':good['top_U_R']==150 and bad['top_U_R']==0}
m.jsonout(m.OUT/'a-authorization-probe.json',result);print(json.dumps(result,ensure_ascii=False))
