#!/usr/bin/env python3
"""Narrow independent C3 checks of current frozen policy. No author exporter.
Expected metrics/money come from the independent primitive reconstruction;
expected signing bytes are reconstructed here, not by author materializer.
"""
import sys
sys.dont_write_bytecode=True
import ast,copy,csv,hashlib,importlib.util,json
from pathlib import Path
from fractions import Fraction
from datetime import timedelta
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('independent_source_check',HERE/'independent_check.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
R=m.ROOT;BPATH=R/'branches/B/con-023';SPEC=json.loads((BPATH/'metrics-spec.json').read_text());CFG=copy.deepcopy(m.CONFIGS)
assert SPEC['candidate_key']=='CON-023@v2'
B=m.ast_namespace(BPATH/'evaluator.py')
# Own independently computed metric and award expectations from the frozen source sweep.
units={(x['scenario'],x['period'],x['subject']):x for x in csv.DictReader((HERE/'independent-units.csv').open()) if x['candidate_key'] in ('CON-023@v1','CON-023@v2')}
people=[x for x in csv.DictReader((HERE/'independent-persons.csv').open()) if x['candidate_key'] in ('CON-023@v1','CON-023@v2') and x['scenario']=='R1.volume']
def refresh(d):
 for z in d['source_manifest']:
  if z['availability'] in ('available','restored'):
   rs=[x for x in d[z['table']] if x.get('period_id',z['period_id'])==z['period_id']];z.update(received_count=len(rs),expected_count=len(rs),received_sha256=m.h(rs))
def positive_source():
 d=m.reader.expand_scenario('R1.volume',m.OLD)
 rules={(x['period_id'],x['family']):x for x in d['period_rules']}
 # An explicitly hypothetical completed source review, not an edit to public input.
 for a in d['approvals_audit']:
  if a['action']=='source_completeness_review':
   family=next(c['family'] for c in d['roster_capacity'] if c['period_id']==a['period_id'] and (c['subject_id']==a['beneficiary_id'] or c['subject_id']==a.get('beneficiary_team')))
   r=rules[a['period_id'],family];a['signed_at']=(m.dt(r.get('quality_close_at') or r['quality_close'],True)+timedelta(minutes=1)).isoformat()
 for b in d['batch_metadata']:
  close=max(m.dt(r.get('quality_close_at') or r['quality_close'],True) for r in d['period_rules'] if r['period_id']==b['period_id']);b['signed_at']=(close+timedelta(minutes=2)).isoformat()
 refresh(d);return d

def decision_rows(spec):
 result=[];factor=Fraction(str(spec['top_R_per_person']))/150
 for p in people:
  u=units['R1.volume',p['period'],p['unit']];project=json.loads(u['project']);typ=project[0]['type'] if project else u['family']
  result.append({'period':p['period'],'subject':p['subject'],'unit':p['unit'],'family':u['family'],'work_type':typ,'group':u['group'],'window':p['window'],'cohort':p['cohort'],'calculated_state':p['calculated_state'],'strong':u['strong']=='True','rank':int(p['rank']) if p['rank'] else None,'tie_size':int(p['tie_size']),'top_earned_R':int(Fraction(p['top_calculated_R'])*factor),'top_conditional_R':0,'right_date':p['original_right_date'][:10],'share':str(Fraction(p['share']))})
 return result

def own_package(d,spec,configs,period,person):
 rs=decision_rows(spec);current=next(x for x in rs if x['period']==period and x['subject']==person)
 group=sorted([x for x in rs if (x['period'],x['group'],x['work_type'])==(current['period'],current['group'],current['work_type'])],key=lambda x:x['subject'])
 select=lambda data:[x for x in data if not isinstance(x,dict) or x.get('period_id',period)==period]
 tables={k:select(v) if isinstance(v,list) else v for k,v in d.items() if k not in ['approvals_audit','source_manifest']}
 manifests=[x for x in d['source_manifest'] if x['period_id']==period and x['table']!='approvals_audit']
 reviews=m.uniq([a for a in d['approvals_audit'] if a['period_id']==period and a['action']==spec['source_action']],'approval_id')
 hashes={'source_sha256':m.h({'tables':tables,'source_manifests':manifests,'performed_source_reviews':reviews}),'registry_sha256':m.h(select(d['comparison_registry'])),'members_sha256':m.h(select(d['team_members'])),'config_sha256':m.h([x for x in configs if x['source_query']['period_id']==period]),'rule_sha256':m.h({'policy':spec,'period_rules':select(d['period_rules'])})}
 return {'package_version':1,'candidate_key':spec['candidate_key'],'decision_version':spec['version'],'period':period,'beneficiary':person,'unit':current['unit'],'window':current['window'],'binding_hashes':hashes,'decision_sha256':m.h({'current':current,'comparison_group':group}),'amounts_R':{'quarter_top_R':current['top_earned_R'],'quarter_top_conditional_R':0,'fixed_window_G_ceiling_R':2500 if current['calculated_state'] in ['earned','pending','not_computable'] else 0},'idempotency_keys':{'top':person+':'+period+':top','G':person+':'+current['window']+':G'},'G_release':'both first fixed quarters calculated and independently authorized; once/12months; ceiling is not a second grant'}

def sign(d,person,period='P1',spec=SPEC,configs=CFG,package_patch=None,act_patch=None):
 pkg=own_package(d,spec,configs,period,person)
 if package_patch:package_patch(pkg)
 src=next((x for x in d['approvals_audit'] if x['period_id']==period and x['beneficiary_id']==person),next(x for x in d['approvals_audit'] if x['period_id']==period))
 a=copy.deepcopy(src);r=next(r for r in d['period_rules'] if r['period_id']==period)
 a.update(approval_id='AWARD:'+period+':'+person,action=spec['posting_action'],version=2,signed_at=(m.dt(r.get('quality_close_at') or r['quality_close'],True)+timedelta(minutes=3)).isoformat(),signed_package_sha256=m.h(pkg),package_version=pkg['package_version'],decision_version=pkg['decision_version'],amounts_R=pkg['amounts_R'])
 a.update(period_id=period,beneficiary_id=person,source_ref=period+':'+person,beneficiary_team=pkg['unit'] if person.startswith('P0') else None)
 if act_patch:act_patch(a)
 d['approvals_audit'].append(a);refresh(d);return pkg,a

def observed(d,person='S31',period='P1',spec=SPEC,configs=CFG):
 u,ps=B['evaluate'](d,spec,configs);x=next(x for x in ps if x['subject']==person and x['period']==period)
 return x,ps
controls=[]
def record(name,x,expected_U,expected_state='earned',expected_top=None,package_equal=None):
 exp={'calculated_state':expected_state,'authorized_top_U_R':expected_U,'window':'W2026-A','original_right_date':'2026-04-28'}
 if expected_top is not None:exp['calculated_top_R']=expected_top
 obs={k:x[k] for k in ['calculated_state','window','right_date','top_earned_R','top_conditional_R','top_U_R','authorization_errors','source_review_errors','authorization_package_sha256']}
 ok=x['calculated_state']==expected_state and x['top_U_R']==expected_U and x['window']=='W2026-A' and x['right_date']=='2026-04-28'
 if expected_top is not None:ok=ok and x['top_earned_R']==expected_top
 if package_equal is not None:ok=ok and package_equal
 controls.append({'control':name,'candidate_key':'CON-023@v2','expected':exp,'observed':obs,'independent_package_equals_observed':package_equal,'status':'pass' if ok else 'fail'})

# Positive personal and team actions, both quarters, independently materialized package.
d=positive_source();packages={}
for person in ['S31','P031']:
 for period in ['P1','P2']:packages[period,person],_=sign(d,person,period)
for person,amount in [('S31',600),('P031',420)]:
 x,ps=observed(d,person);record('positive_'+('personal' if person=='S31' else 'team_member'),x,amount,expected_top=amount,package_equal=x['authorization_package']==packages['P1',person])
 p2=next(z for z in ps if z['subject']==person and z['period']=='P2');both=all(z['calculated_state']=='earned' and not z['authorization_errors'] and not z['source_review_errors'] for z in [x,p2]);controls.append({'control':'two_quarter_fixed_window_G_'+person,'candidate_key':'CON-023@v2','expected':{'one_annual_G_R':2500,'quarter_G_is_ceiling_only':True,'same_fixed_window':True},'observed':{'both_quarters_authorized':both,'windows':[x['window'],p2['window']],'G_keys':[x['authorization_package']['idempotency_keys']['G'],p2['authorization_package']['idempotency_keys']['G']]},'status':'pass' if both and x['window']==p2['window'] and x['authorization_package']['idempotency_keys']['G']==p2['authorization_package']['idempotency_keys']['G'] else 'fail'})

# Repeat same state, then exact duplicate delivery of the performed award act.
x,ps=observed(d);x2,ps2=observed(d);ddup=copy.deepcopy(d);ddup['approvals_audit'].append(copy.deepcopy(next(a for a in ddup['approvals_audit'] if a['approval_id']=='AWARD:P1:S31')));refresh(ddup);x3,p3=observed(ddup)
controls.append({'control':'same_package_and_duplicate_delivery_replay','candidate_key':'CON-023@v2','expected':{'unique_person_period_U_R':600,'one_logical_authorization':True,'ledger_posting':'not present'},'observed':{'U_states':[x['top_U_R'],x2['top_U_R'],x3['top_U_R']],'logical_rows':[sum(z['subject']=='S31' and z['period']=='P1' for z in rows) for rows in [ps,ps2,p3]],'top_keys':[z['authorization_package']['idempotency_keys']['top'] for z in [x,x2,x3]]},'status':'pass' if all(z['top_U_R']==600 for z in [x,x2,x3]) and all(sum(z['subject']=='S31' and z['period']=='P1' for z in rows)==1 for rows in [ps,ps2,p3]) else 'fail'})

# Five required negative controls. The scope/time/team tests carry a correct
# independently signed CURRENT package, so a stale hash cannot mask the reason.
def neg(name,mut=None,person='S31',act_patch=None,package_patch=None):
 data=positive_source()
 if mut:mut(data)
 refresh(data);pkg,act=sign(data,person,package_patch=package_patch,act_patch=act_patch);row,_=observed(data,person);record(name,row,0,expected_top=420 if person=='P031' else 600,package_equal=None);return data,row,act
neg('missing_exact_signed_package',act_patch=lambda a:a.pop('signed_package_sha256'))
neg('award_action_before_quality_close',act_patch=lambda a:a.update(signed_at='2025-11-01T10:00:00+03:00'))
neg('personal_source_wrong_scope',mut=lambda z:next(a for a in z['approvals_audit'] if a['approval_id']=='P1:S31').update(source_ref='P2:someone_else'))
neg('personal_source_before_quality_close',mut=lambda z:next(a for a in z['approvals_audit'] if a['approval_id']=='P1:S31').update(signed_at='2025-11-01T10:00:00+03:00'))
neg('team_source_beneficiary_actor',mut=lambda z:next(a for a in z['approvals_audit'] if a['approval_id']=='P1:T07').update(signer_id='P032'),person='P031')
# Source-action/scope/time requirements and identity cannot be inferred from alternates.
neg('missing_personal_source_action',mut=lambda z:z['approvals_audit'].remove(next(a for a in z['approvals_audit'] if a['approval_id']=='P1:S31')))
neg('missing_team_source_action',mut=lambda z:z['approvals_audit'].remove(next(a for a in z['approvals_audit'] if a['approval_id']=='P1:T07')),person='P031')
neg('wrong_award_action_with_named_alternate',act_patch=lambda a:a.update(action='type_correction',alternate_signer_id='NAMED-ONLY'))
neg('award_source_scope_mismatch',act_patch=lambda a:a.update(source_ref='P2:S31'))
neg('signed_amount_mismatch',act_patch=lambda a:a.update(amounts_R={'quarter_top_R':999,'quarter_top_conditional_R':0,'fixed_window_G_ceiling_R':2500}))
neg('signed_package_version_mismatch',act_patch=lambda a:a.update(package_version=999))
neg('signed_decision_version_mismatch',act_patch=lambda a:a.update(decision_version=999))
neg('different_decision_hash_signed',package_patch=lambda p:p.update(decision_sha256='0'*64))

# Stale exact signatures after changes to every mandated component.
def stale(name,mutation,person='S31',spec_mut=None,config_mut=None,expected_top=600):
 data=positive_source();_,a=sign(data,person);ss=copy.deepcopy(SPEC);cc=copy.deepcopy(CFG)
 if mutation:mutation(data)
 if spec_mut:spec_mut(ss)
 if config_mut:config_mut(cc)
 refresh(data);row,_=observed(data,person,spec=ss,configs=cc);record(name,row,0,expected_top=expected_top)
stale('source_hash_changed',lambda z:z['worklog'][0].update(hours=z['worklog'][0]['hours']+1))
stale('registry_hash_changed',lambda z:z['comparison_registry'][0].update(registered_at='2025-12-14'))
stale('member_hash_changed',lambda z:z['team_members'][0].update(approved_at='2025-12-14'),person='P031',expected_top=420)
stale('config_hash_changed',None,config_mut=lambda c:next(x for x in c if x['source_query']['period_id']=='P1').update(baseline_value=0))
stale('rule_and_amount_changed',None,spec_mut=lambda s:s.update(top_R_per_person=300),expected_top=1200)
stale('decision_version_changed',None,spec_mut=lambda s:s.update(version=3))

# Missing award preserves qualification; missing actual source preserves original
# conditional ceiling/window, with no imputed earned result or movement.
data=positive_source();x,_=observed(data);record('missing_award_preserves_calculated_right',x,0,expected_top=600)
lost=copy.deepcopy(data)
for z in lost['source_manifest']:
 if z['period_id']=='P1' and z['table']=='quality_acts':z['availability']='lost_partition'
x,_=observed(lost);record('source_incident_preserves_original_window_ceiling',x,0,expected_state='pending',expected_top=0)
controls[-1]['expected']['group_conditional_ceiling_R']=6000;controls[-1]['status']='pass' if controls[-1]['status']=='pass' and x['top_conditional_R']==6000 else 'fail'

# Semantic invariance of prior metric work; no new 38-snapshot evaluator sweep.
oldpath=R/'private/pre-rework/branches/B/con-023/evaluator.py';oldtree=ast.parse(oldpath.read_text());newtree=ast.parse((BPATH/'evaluator.py').read_text())
def fn(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
invariants={name:ast.dump(fn(oldtree,name),include_attributes=False)==ast.dump(fn(newtree,name),include_attributes=False) for name in ['quality','calendar_audit','manifest_errors','union_hours']}
oldloop=next(n for n in fn(oldtree,'evaluate').body if isinstance(n,ast.For));newloop=next(n for n in fn(newtree,'evaluate').body if isinstance(n,ast.For));invariants['primitive_to_unit_metric_loop']=ast.dump(oldloop,include_attributes=False)==ast.dump(newloop,include_attributes=False)
oldspec=json.loads((R/'private/pre-rework/branches/B/con-023/metrics-spec.json').read_text());ignored={'candidate_key','version','authorization','parents','authorization_contract'};invariants['metric_policy_parameters']= {k:v for k,v in oldspec.items() if k not in ignored}=={k:v for k,v in SPEC.items() if k not in ignored}
assert all(invariants.values()),invariants
frozen=json.loads((R/'private/versions-before-checks.json').read_text())['files'];mismatches=[p for p,v in frozen.items() if hashlib.sha256((R/p).read_bytes()).hexdigest()!=v]
assert not mismatches,mismatches
result={'candidate_key':'CON-023@v2','scope':'current C3 authorization controls; metrics retained after independent source calculations and semantic invariance','method':'own expected amounts from primitive sweep; independent canonical package reconstruction; AST functions of actual frozen evaluator solely to observe specific C3 cases; no author materializer or self-test as oracle','inputs':'R1.volume with explicitly hypothetical completed source/award actions in memory; public source unchanged','controls':controls,'summary':{'pass':sum(x['status']=='pass' for x in controls),'fail':sum(x['status']=='fail' for x in controls)},'limits':['Current U is a state; real transactional ledger posting is absent.','Both quarter G fields are ceilings for one fixed-window entitlement, never two grants.','Synthetic current controls do not establish bank permissions, API or independent staff readiness.']}
m.jsonout(HERE/'current-controls.json',result);m.jsonout(HERE/'delta-verification.json',{'python':sys.version,'current_candidate_keys':['CON-022@v1','CON-023@v2','CON-016@v2','BASELINE'],'semantic_invariance':invariants,'freeze_files_checked':len(frozen),'freeze_mismatches':mismatches,'current_control_summary':result['summary'],'no_full_resweep':True,'own_package_match_for_positive_personal_team':all(x['independent_package_equals_observed'] is True for x in controls if x['control'] in ['positive_personal','positive_team_member'])})
print(json.dumps({'summary':result['summary'],'failed_controls':[x for x in controls if x['status']=='fail'],'invariance':invariants},ensure_ascii=False,indent=2))
