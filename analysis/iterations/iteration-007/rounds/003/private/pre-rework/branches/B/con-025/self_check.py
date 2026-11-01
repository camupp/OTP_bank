#!/usr/bin/env python3
"""Targeted booking/metadata, QA-neighborhood and C3 checks. No full38 rerun."""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,ast,copy,importlib.util,math
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent;ROUND=HERE.parents[2];ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists() and (p/'project').exists());PARENT=ROOT/'analysis/iterations/iteration-007/rounds/002/branches/B/con-023'
def load(p):return json.loads(p.read_text())
def read(p):return list(csv.DictReader(p.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ev=mod('current',HERE/'evaluator.py');reader=mod('public_reader',ROUND/'supporting/round002-stress/reader.py');spec=load(HERE/'metrics-spec.json');configs=load(ROUND/'supporting/round002-stress/business-config.json')['configs'];checks=[]
def check(name,ok,detail=''):checks.append(dict(name=name,status='pass' if ok else 'fail',detail=detail))
check('recipe_SHA',sha(ROUND/'supporting/qa-neighborhood-recipe.json')=='b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12')
frozen=load(ROUND/'inputs/manifest.json')
check('frozen_common_inputs_and_source',frozen['fingerprint']==spec['input_fingerprint'] and all(sha(ROUND/'inputs'/p)==v for p,v in frozen['files'].items()) and sha(ROUND/'supporting/fixtures/manifest.json')=='2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc' and sha(ROUND/'supporting/round002-stress/manifest.json')=='206b8c7cc0e84021c01b3d2f544a07ac909536e5f7498766809eee127532210c' and sha(ROUND/'supporting/resource-menu.json')=='59132888a970e491d22870a790a864abd24ab4fc0816aa0dc88a9464efe39ac1')
parent_manifest=load(HERE/'parent-reuse.json')
check('pinned_parent_data_SHA',all(sha(ROOT/p)==v for p,v in parent_manifest['files'].items()))
def scoring_functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name!='main'}
check('scoring_and_C3_functions_identical',scoring_functions(HERE/'evaluator.py')==scoring_functions(PARENT/'evaluator.py'),'Parent parsed as text only, never executed. Only export label/main metadata differs.')
oldspec=load(PARENT/'metrics-spec.json');strip=lambda x:{k:v for k,v in x.items() if k not in ('candidate_key','version','parents')}
check('recognition_spec_identical',strip(spec)==strip(oldspec))
old=read(PARENT/'monthly-resource.csv');new=read(HERE/'monthly-resource.csv');keys=('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role','month');key=lambda r:tuple(r[k] for k in keys);om={key(r):r for r in old};nm={key(r):r for r in new}
check('booking_scope11232',set(om)==set(nm) and len(nm)==11232)
same_fields=['existing_activity_h','new_activity_h','demand_h','base_available_h','activity_cost_RUB','base_replacement25_cash_RUB','queue_start_h','queue_end_h','deadline','deadline_state','earliest_finish_month','qualification','ready_date','recusal']
same=True;cash=True;forecast=True;series=defaultdict(list)
rates=load(HERE/'finance-spec.json')['booking']['rates_RUB_h']
for k,r in nm.items():
 o=om[k]
 for col in same_fields:
  try:same &= abs(float(r[col])-float(o[col]))<1e-6
  except ValueError:same &= r[col]==o[col]
 rate=rates[r['role']];d=float(r['demand_h']);base=float(r['base_available_h']);b=float(r['booked_h']);used=min(b,max(0,d-base));idle=b-used
 cash &= abs(float(r['reservation_cash_RUB'])-b*rate)<1e-6 and abs(float(r['paid_idle_h'])-idle)<1e-6 and abs(float(r['full_cost_work_plus_idle_RUB'])-(d+idle)*rate)<1e-5 and float(r['new_operating_cash_RUB'])<=float(o['new_operating_cash_RUB'])+1e-6
 series[k[:-1]].append(r)
for k,rs in series.items():
 rs.sort(key=lambda r:int(r['month']));maximum=max(int(om[key(r)]['booked_blocks']) for r in rs);q=0
 for r in rs:
  expected=min(maximum,max(0,math.ceil((float(r['demand_h'])+q-float(r['base_available_h']))/20-1e-10)))
  forecast &= int(r['booked_blocks'])==expected
  q=max(0,q+float(r['demand_h'])-float(r['total_capacity_h']))
check('actual_work_minutes_qualification_deadlines_queues_unchanged',same)
check('all_bookings_paid_no_cash_increase',cash)
check('full_forecast_booking_equation',forecast,'Complete parent7200/E24 maximum-obligations forecast; no observed qualification/U input.')
profiles=defaultdict(list)
for r in new:profiles[tuple(r[k] for k in keys[:5])].append(r)
check('fixed96_x1_preserved',all(all(float(r['queue_end_h'])<1e-7 for r in rs) for k,rs in profiles.items() if k[1]=='96000000' and k[3]=='1'))
check('old_all_fail_pass_queue_profiles_preserved',all(abs(float(r['queue_end_h'])-float(om[key(r)]['queue_end_h']))<1e-7 for r in new))
def semantic(rows,ignore=()):return [{k:v for k,v in r.items() if k not in ignore} for r in rows]
for name in ('resource-stages.csv','setup-resource.csv','money-examples.csv','unit-decisions.csv','window-guarantee.csv','group-top-reserve.csv','calendar-traces.csv'):
 check('zero_delta_'+name,semantic(read(HERE/name),('candidate',))==semantic(read(PARENT/name),('candidate',)))
pd=read(PARENT/'decisions.csv');nd=read(HERE/'decisions.csv');check('38_business_decisions_identical',semantic(pd,('authorization_package','authorization_package_sha256'))==semantic(nd,('authorization_package','authorization_package_sha256')))
check('all_current_packages_versioned',all(loads['candidate_key']=='CON-025@v1' and loads['decision_version']==1 for loads in [json.loads(r['authorization_package']) for r in nd]))
# Only the four public QA-neighborhood copies plus precision are recomputed.
recipe=load(ROUND/'supporting/qa-neighborhood-recipe.json');qa=[];reference=None
def physical(d,table):
 for part in d['source_manifest']:
  if part['table']==table:
   rr=[r for r in d[table] if r.get('period_id',part['period_id'])==part['period_id']];part.update(expected_count=len(rr),received_count=len(rr),received_sha256=ev.digest(rr))
def recognition(us,ps):return ({(r['period'],r['subject']):(r['normal'],r['strong'],r['rank_key'],r['rank'],r['tie_size'],str(r['top_R'])) for r in us},{(r['period'],r['subject']):(r['calculated_state'],r['rank'],r['tie_size'],r['top_earned_R'],r['top_U_R']) for r in ps})
for control in recipe['controls']:
 d=reader.expand_scenario('R2.quality',ROUND/'supporting/fixtures')
 if 'act_id' in control:
  act=next(q for q in d['quality_acts'] if q['act_id']==control['act_id']);subject='S21' if control['id']=='Q100_down' else 'S11';count=44 if subject=='S21' else 40
  inspections={q['inspection_id'] for q in d['quality_acts'] if q['subject_id']==subject and q['period_id']=='P1' and q['criterion']=='defect_penalty' and q['scale_version']=='penalty-v1'}
  check('QA_precondition_'+control['id'],act['subject_id']==subject and act['period_id']=='P1' and len(inspections)==count and act['score']==(98 if control['id']=='Q99_up' else 100) and act['minor']==(1 if control['id']=='Q99_up' else 0) and act['major']==0 and act['critical']==0);act.update(control['set']);physical(d,'quality_acts')
 us,ps=ev.evaluate(d,spec,configs);sig=recognition(us,ps)
 if reference is None:reference=sig
 check('QA_result_rank_unchanged_'+control['id'],sig==reference)
 qa.append({'control':control['id'],'rows':[{'subject':u['subject'],'period':u['period'],'QA':u['quality']['score'],'normal':u['normal'],'strong':u['strong'],'rank_key':u['rank_key'],'rank':u['rank'],'tie_size':u['tie_size'],'calculated_R':str(u['top_R'])} for u in us if u['period']=='P1' and u['family']=='support'],'authorized_U_R':sum(x['top_U_R'] for x in ps),'reason':'QA remains eligible gate; result-based rank is unchanged'})
precision=reader.expand_scenario('R2.precision',ROUND/'supporting/fixtures');pu,pp=ev.evaluate(precision,spec,configs);check('R2_precision_result_rank_unchanged',recognition(pu,pp)==reference)
check('Q99_up_matches_precision_QA',next(q['QA'] for x in qa if x['control']=='Q99_up' for q in x['rows'] if q['subject']=='S11')==next(u['quality']['score'] for u in pu if u['subject']=='S11' and u['period']=='P1'))
# Current-metadata C3 positive and five inherited defects, all in-memory only.
d=reader.expand_scenario('R1.volume',ROUND/'supporting/fixtures')
for a in d['approvals_audit']:
 if a['period_id']=='P1' and a['action']==spec['source_action']:a['signed_at']='2026-04-29T00:00:00+03:00'
for b in d['batch_metadata']:
 if b['period_id']=='P1':b['signed_at']='2026-04-29T01:00:00+03:00'
physical(d,'approvals_audit')
def observed(data,s,subject='S31'):
 _,ps=ev.evaluate(data,s,configs);return next(x for x in ps if x['period']=='P1' and x['subject']==subject)
acts=[]
for subject in ('S31','P031'):
 x=observed(d,spec,subject);package=x['authorization_package'];a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['approval_id']=='P1:'+subject));a.update(approval_id='AWARD:P1:'+subject,action=spec['posting_action'],version=2,signed_at='2026-04-29T02:00:00+03:00',signed_package_sha256=ev.digest(package),package_version=package['package_version'],decision_version=package['decision_version'],amounts_R=package['amounts_R']);d['approvals_audit'].append(a);physical(d,'approvals_audit');acts.append(a)
positive={s:observed(d,spec,s) for s in ('S31','P031')};check('C3_current_positive',positive['S31']['top_U_R']==600 and positive['P031']['top_U_R']==420)
probes=[]
cases=[('stale_rule_amount','S31',None),('award_before_close','S31',('AWARD:P1:S31','signed_at','2025-11-01T10:00:00+03:00')),('wrong_source_ref','S31',('P1:S31','source_ref','P2:someone_else')),('source_before_close','S31',('P1:S31','signed_at','2025-11-01T10:00:00+03:00')),('team_conflict','P031',('P1:T07','signer_id','P032'))]
for name,subject,patch in cases:
 data=copy.deepcopy(d);s=copy.deepcopy(spec)
 if patch:next(a for a in data['approvals_audit'] if a['approval_id']==patch[0])[patch[1]]=patch[2]
 else:s['top_R_per_person']=300
 physical(data,'approvals_audit');x=observed(data,s,subject);check('C3_'+name,x['top_U_R']==0 and x['calculated_state']=='earned' and x['top_earned_R']>0 and x['window']==positive[subject]['window'] and x['right_date']==positive[subject]['right_date']);probes.append(dict(probe=name,U=x['top_U_R'],earned_R=x['top_earned_R'],errors=x['authorization_errors']+x['source_review_errors']))
replay=copy.deepcopy(d);replay['approvals_audit'].append(copy.deepcopy(acts[0]));physical(replay,'approvals_audit');rx=observed(replay,spec);check('C3_replay',rx['top_U_R']==600 and rx['authorization_package_sha256']==positive['S31']['authorization_package_sha256'])
oldact=load(PARENT/'c3-rework-examples.json')['positive_acts'][0];stale=copy.deepcopy(d);stale['approvals_audit']=[oldact if a['approval_id']=='AWARD:P1:S31' else a for a in stale['approvals_audit']];physical(stale,'approvals_audit');check('C3_parent_metadata_signature_held',observed(stale,spec)['top_U_R']==0)
out={'candidate_key':'CON-025@v1','classification':'targeted author checks only; no full38scoring rerun and no actual bank posting','checks':checks,'counts':dict(Counter(c['status'] for c in checks)),'resource_scope':{'rows':len(new),'profiles':len(profiles),'conditional_profiles':sum(all(float(r['queue_end_h'])<1e-7 for r in rs) for rs in profiles.values())},'QA_neighborhood':qa,'C3_current_positive':{s:{k:x[k] for k in ('top_earned_R','top_U_R','authorization_package_sha256')} for s,x in positive.items()},'C3_negative':probes,'limits':['people/funding/readiness and intra-month rehearsal remain conditions','30conditional monthly profiles/42fails unchanged','no reduction of work, promises, minutes, QA or fulfillment','real U/R transaction ledger absent; repeated outputs are states not new postings']}
(HERE/'self-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
provenance={'candidate_key':'CON-025@v1','parent':'CON-023@v2','input_fingerprint':spec['input_fingerprint'],'parent_files':parent_manifest['files'],'scope':'38snapshots/3524personal/2600unit/304traces/432calendar reused with business decisions identical; current candidate/version/rule hash metadata rebound without scoring; resources recalculated all11232keys; only QA-neighborhood+C3 examples evaluated','closed_code_execution':False}
(HERE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['counts']))
if any(c['status']=='fail' for c in checks):print(json.dumps([c for c in checks if c['status']=='fail']));sys.exit(1)
