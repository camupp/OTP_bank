#!/usr/bin/env python3
"""Independent published-rule reconstruction, never imports author evaluator.
Source-only reader allowed by assignment. All inputs are synthetic assumptions.
AST author functions are used ONLY in concrete adversarial probes at the end.
"""
import sys
sys.dont_write_bytecode=True
import ast,copy,csv,hashlib,importlib.util,json,math
from collections import defaultdict,Counter
from datetime import datetime,date,timedelta,timezone
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SUP=ROOT/'supporting'
OLD=SUP/'fixtures'
AD=SUP/'round002-stress'
KEYS=['CON-022@v1','CON-023@v1','CON-016@v2','BASELINE']
CONFIGS=json.loads((AD/'business-config.json').read_text())['configs']
def loadreader():
 sp=importlib.util.spec_from_file_location('public_source_reader',AD/'reader.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
reader=loadreader()
def h(x):return hashlib.sha256((json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
def dt(x,end=False):
 if not x:return None
 if len(x)==10:x+='T23:59:59+03:00' if end else 'T00:00:00+03:00'
 t=datetime.fromisoformat(x);return t if t.tzinfo else t.replace(tzinfo=timezone(timedelta(hours=3)))
def fr(x):return Fraction(str(x))
def uniq(rows,key):
 seen={}
 for r in rows:
  if r[key] in seen and r!=seen[r[key]]:raise ValueError('conflicting primitive PK '+key)
  seen[r[key]]=r
 return list(seen.values())
def by(rows,*keys):
 d=defaultdict(list)
 for r in rows:d[tuple(r.get(k) for k in keys)].append(r)
 return d
def union_hours(rows):
 spans=sorted((dt(x['start_at']),dt(x['end_at'])) for x in rows);sp=[]
 for a,b in spans:
  if sp and a<=sp[-1][1]:sp[-1][1]=max(b,sp[-1][1])
  else:sp.append([a,b])
 return sum((b-a).total_seconds()/3600 for a,b in sp)
def action_errors(a,forbidden,action,scope=None,close=None):
 if not a:return ['performed_action_missing']
 errs=[]
 if a.get('action')!=action:errs.append('wrong_action')
 try:
  t=dt(a.get('signed_at'))
  if not t:errs.append('signature_time_missing')
  elif close and t<close:errs.append('signature_precedes_quality_close')
 except (ValueError,TypeError):errs.append('signature_time_invalid')
 actors=[a.get(k) for k in ['input_editor_id','signer_id','operator_id']]
 if any(not isinstance(x,str) or not x.strip() for x in actors):errs.append('missing_actor')
 if len(set(actors))!=3:errs.append('roles_not_distinct')
 if any(x in forbidden for x in actors):errs.append('beneficiary_actor')
 for k,v in a.items():
  if k.endswith('_reporting_to') and any(x in forbidden for x in (v if isinstance(v,list) else [v]) if x):errs.append('reporting_conflict:'+k)
 if scope is not None and a.get('source_ref')!=scope:errs.append('wrong_scope')
 return errs

def read_metrics(d):
 """Primitive source facts, separate from the two prospective award policies."""
 ev=by(uniq(d['work_events'],'event_id'),'period_id','subject_id');qa=by(d['quality_acts'],'period_id','subject_id')
 caps={(r['period_id'],r['subject_id']):r for r in d['roster_capacity']}
 rules={(r['period_id'],r['family']):r for r in d['period_rules']}
 cls={r['type_id']:r for r in d['classifier']};members=by(d['team_members'],'period_id','team_id')
 manifests=defaultdict(list)
 for m in d['source_manifest']:
  rows=[r for r in d[m['table']] if r.get('period_id',m['period_id'])==m['period_id']]
  reason=m['availability'] if m['availability'] not in ('available','restored') else 'hash_count' if len(rows)!=m['received_count'] or m['received_count']!=m['expected_count'] or h(rows)!=m['received_sha256'] else None
  if reason:manifests[m['period_id']].append((m['table'],reason))
 facts=[]
 for reg in d['comparison_registry']:
  p,s=reg['period_id'],reg['subject_id'];cap=caps[p,s];f=cap['family'];r=rules[p,f];close=dt(r.get('quality_close_at') or r['quality_close'],True)
  ms=members[p,s];own={s}|{m['employee_id'] for m in ms};pending=[]
  rows=ev[p,s];roots=by(rows,'root_id');roots={k[0]:v for k,v in roots.items() if k[0]}
  if any(not e.get('root_id') for e in rows):pending.append('missing_root_link')
  if cap.get('assignment_history_status')!='complete' or any(e.get('assignment_history_status')!='complete' or not e.get('assigned_by') or e['assigned_by'] in own for e in rows):pending.append('assignment_missing_or_self')
  if dt(r['approved_at'])>=dt(r['start']) or r['standard_owner'] in own:pending.append('rule_not_prospective_independent')
  relevant={'period_rules','comparison_registry','roster_capacity','classifier','work_events','quality_acts',{'support':'support_outcomes','backoffice':'process_outcomes','project':'project_records'}[f]}
  if f=='project':relevant.add('team_members')
  pending += [a+':'+b for a,b in manifests[p] if a in relevant]
  corrections=[a for a in d['approvals_audit'] if a['period_id']==p and a['beneficiary_id'] in own and a.get('action')=='type_correction']
  if any(action_errors(a,own,'type_correction') for a in corrections):pending.append('unapproved_type_correction')
  valid=[];invalid=[]
  for q in qa[p,s]:
   ok=(q.get('evidence_status')=='present' and q.get('checker_id') and q['checker_id'] not in own and q.get('criterion')=='defect_penalty' and q.get('scale')=='0..100' and q.get('scale_version')=='penalty-v1' and q.get('scope')==('team' if f=='project' else 'personal') and q.get('sample_method')=='census_of_scenario_work_register' and q.get('inspection_id') and q.get('finalized_at') and dt(q['finalized_at'])<=close and q.get('observation_end') and q['observation_end'][:10]>=r['quality_close'] and all(q.get(k) is not None for k in ['minor','major','critical']))
   (valid if ok else invalid).append(q)
  inspections=by(valid,'inspection_id');scores=[min(max(0,100-2*q['minor']-10*q['major']-100*q['critical']) for q in qs) for qs in inspections.values()]
  qmean=Fraction(sum(scores),len(scores)) if scores else None
  covered=[];missing=[]
  caseacts={q['case_id'] for q in valid if q.get('coverage_object')=='one_distinct_case'}
  for root,es in roots.items():
   whole=any(q.get('coverage_object')=='same_deliverable_inspection' and (q.get('case_id') in {e['case_id'] for e in es} or q.get('deliverable_id')==root) for q in valid) if f=='project' else False
   absent=[e['case_id'] for e in es if e['case_id'] not in caseacts and not (f!='project' and any(e.get(k) in caseacts for k in ['duplicate_of','reopen_of','correction_of']))]
   if whole or not absent:covered.append(root)
   else:missing+=absent
  if missing or not scores:pending.append('incomplete_compatible_QA')
  numer=Fraction(0);accepted=timely=adverse=0;pertype=defaultdict(Fraction)
  outcomes={o['case_id']:o for o in d[{'support':'support_outcomes','backoffice':'process_outcomes','project':'project_records'}[f]] if o['period_id']==p and o['subject_id']==s}
  project=[];failproject=[]
  for root,es in roots.items():
   original=min(es,key=lambda e:(e['assigned_at'],e['case_id']));latest=max([e for e in es if e['case_id']==original['case_id']],key=lambda e:e['version'])
   if f=='project':
    ps=[x for x in d['project_records'] if x['period_id']==p and x['subject_id']==s and (x['deliverable_id']==root or x['parent_id']==root)]
    if not ps:pending.append('project_record_missing');continue
    x=ps[0];typ='analytical_business_decision_package' if x.get('usage_measure')=='distinct_business_decisions_using_deliverable' else 'workflow'
    conf=[c for c in CONFIGS if c['version']==1 and c['comparison_group_id']==reg['comparison_group_id'] and c['source_query']['period_id']==p and c['work_type']==typ]
    c=conf[0] if len(conf)==1 else None
    if not c:pending.append('business_config_missing')
    if x.get('criteria_ref','').startswith('CFG-') and c and x['criteria_ref']!=c['config_id']+'-v1':pending.append('conflicting_goal_version')
    needed=['criteria_ref','criteria_agreed_at','acceptance_at','acceptance_ref','acceptance_owner','release_at','release_ref','usage_observed_at','usage_ref','usage_owner','usage_coverage']
    unknown=any(not x.get(k) for k in needed) or x.get('usage_status')!='present' or x.get('usage_units') is None
    if unknown:pending.append('acceptance_or_use_missing')
    else:
     if x['acceptance_owner'] in own or x['usage_owner'] in own:pending.append('self_acceptance_use')
     if dt(x['criteria_agreed_at'])>=dt(r['start']):pending.append('criteria_not_prospective')
    deadline=dt(c['business_deadline']) if c else close
    actualok=not unknown and dt(x['acceptance_at'])<=deadline and dt(x['release_at'])<=deadline and dt(x['usage_observed_at'])<=close and dt(x['release_at'])<=dt(x['usage_observed_at']) and not x.get('rollback') and x['usage_units']>0
    if not unknown and not actualok:failproject.append('actual_late_unused_or_rollback')
    ready=bool(actualok and c and c.get('readiness_criterion') and dt(x['acceptance_at'])<=dt(c['readiness_criterion']['ready_by']) and dt(x['release_at'])<=dt(c['readiness_criterion']['ready_by']))
    project.append({'root':root,'type':typ,'usage':x.get('usage_units'),'config':c['config_id'] if c else None,'target':c['target_value'] if c else None,'actual_ok':actualok,'preread_ready':ready,'record_ref':x['record_id'],'acceptance_at':x.get('acceptance_at'),'release_at':x.get('release_at'),'usage_observed_at':x.get('usage_observed_at')})
    accepted+=actualok
    if actualok:
     # Literal legacy standard-work unit once per nonduplicated deliverable,
     # never once per cloned child record or per usage run.
     numer+=fr(cls[original['type_id']]['standard_units']);pertype[original['type_id']]+=fr(cls[original['type_id']]['standard_units'])
   else:
    o=outcomes.get(original['case_id']);bad=any(e.get('reopen_of') or e.get('correction_of') for e in es) or bool(o and (o.get('repeat_of') if f=='support' else o.get('returned')));adverse+=bool(bad)
    if not o:pending.append('outcome_missing');continue
    ok=bool(latest.get('accepted_at') and latest.get('accepted_by') and latest['accepted_by'] not in own and dt(latest['accepted_at'])<=dt(r['end'],True) and latest['status'] in ['Done','resolved'] and (o.get('resolved') if f=='support' else o.get('accepted')))
    accepted+=ok;deadline=o.get('sla_due_at') or original.get('due_at');timely+=bool(ok and deadline and dt(latest['accepted_at'])<=dt(deadline))
    c=cls.get(original['type_id'])
    if not c or c.get('employee_editable') or c['complexity_owner'] in own or dt(c['approved_at'])>=dt(r['start']):pending.append('unconfirmed_class')
    # Repeated root does not create accepted standard units in the result route.
    if ok and not bad and c:numer+=fr(c['standard_units']);pertype[c['type_id']]+=fr(c['standard_units'])
  intervals=[]
  for i in d['capacity_intervals']:
   if (i['period_id'],i['subject_id'])!=(p,s):continue
   if i.get('source_ref') and i.get('recorded_by') and i.get('approved_by') and i['recorded_by'] not in own and i['approved_by'] not in own:intervals.append(i)
   else:pending.append('unconfirmed_interval')
  removed=union_hours(intervals)
  available=(fr(cap['scheduled_hours'])-fr(cap['leave_hours'])-fr(cap['training_hours'])-fr(removed))*fr(cap['allocation_fraction'])
  denominator=available*sum(fr(a['capacity_share'])*fr(a['standard_units_per_hour']) for a in r['stratum_allocations'])
  ratio=numer/denominator if denominator>0 else None
  strata={a['type_id']:pertype[a['type_id']]/(available*fr(a['capacity_share'])*fr(a['standard_units_per_hour'])) if available>0 else None for a in r['stratum_allocations']}
  legacyQ=sum(fr(a['mix_weight'])*strata[a['type_id']] for a in r['stratum_allocations']) if available>0 else None
  facts.append({'period':p,'subject':s,'family':f,'group':reg['home_pool_id'],'window':reg['window_id'],'cohort':reg['cohort_id'],'roots':len(roots),'accepted':accepted,'acceptance_rate':accepted/len(roots) if roots else None,'sla':timely/len(roots) if roots else None,'adverse_rate':adverse/len(roots) if roots else None,'qa':float(qmean) if qmean is not None else None,'QA_complete':len(covered)==len(roots) and bool(scores),'inspections':len(scores),'critical':sum(q['critical'] for q in valid),'major':sum(q['major'] for q in valid),'pending':sorted(set(pending)),'failproject':failproject,'numerator':float(numer),'denominator':float(denominator),'ratio':float(ratio) if ratio is not None else None,'strata':{k:float(v) if v is not None else None for k,v in strata.items()},'legacyQ':float(legacyQ) if legacyQ is not None else None,'available_hours':float(available),'removed_hours':removed,'active_days':cap['active_days'],'event_days':len({e['event_at'][:10] for e in rows}),'project':project,'own':sorted(own),'members':ms,'close':close.isoformat(),'rule_ref':r['rule_id'],'capacity_ref':cap['capacity_id'],'event_refs':[e['event_id'] for e in rows[:2]],'QA_refs':[q['act_id'] for q in valid[:2]],'invalid_QA_refs':[q['act_id'] for q in invalid[:2]],'source_incidents':manifests[p]})
 return facts

def policy(key,x,d):
 p=[];fails=[];f=x['family'];q=x['qa'];n=x['roots'];common=list(x['pending']);strong=False;rank=None
 if key=='BASELINE':return 'not_computable',False,None,['source_fields_do_not_define_baseline_local_award_rules']
 if key=='CON-016@v2':
  # Literal original QA sample and thresholds; no new census or analytical card.
  rules=next(r for r in d['period_rules'] if r['rule_id']==x['rule_ref'])
  es=uniq([e for e in d['work_events'] if e['period_id']==x['period'] and e['subject_id']==x['subject']],'event_id');cases=sorted({e['case_id'] for e in es})
  benefit={z['case_id']:z.get('benefit_id') for z in d['project_records'] if z['period_id']==x['period'] and z['subject_id']==x['subject']}
  if not rules.get('sampling_seed'):common.append('original_sampling_seed_missing')
  sample=sorted(cases,key=lambda cid:hashlib.sha256((x['window']+'|'+str(benefit.get(cid) or cid)+'|'+cid+'|'+rules.get('sampling_seed','')).encode()).hexdigest())[:20]
  acts=[a for a in d['quality_acts'] if a['period_id']==x['period'] and a['subject_id']==x['subject'] and a['case_id'] in sample and a.get('evidence_status')=='present' and a.get('scale_version')=='penalty-v1' and a.get('minor') is not None and a.get('major') is not None and a.get('checker_id') not in x['own'] and dt(a['finalized_at'])<=dt(x['close'])]
  # QA all-register new coverage rule is not retrofitted to the original sample.
  common=[z for z in common if z not in ['incomplete_compatible_QA','business_config_missing','conflicting_goal_version']]
  if len({a['case_id'] for a in acts})!=len(sample):common.append('original_sample_unavailable')
  q=sum(max(0,100-2*a['minor']-10*a['major']) for a in acts)/len(acts) if acts else None
  x['historical_QA']=q;x['historical_sample_cases']=sample
  if f=='project':
   # One business deliverable is one result; child tickets cannot supply eight new benefits.
   fails.append('minimum_eight_nonduplicated_closures_not_met') if n<8 else None
  else:
   if n<20 or x['numerator']<(100 if f=='support' else 80):fails.append('original_minimum_volume')
  if x['active_days']<10:fails.append('original_exposure')
  if q is not None and q<(97 if f=='support' else 98):fails.append('original_QA')
  if x['critical']:fails.append('critical')
  if x['legacyQ'] is None:common.append('original_Q_not_computable')
  elif x['legacyQ']<1-1e-9:fails.append('Q_below_one')
  if x['adverse_rate'] is not None and x['adverse_rate']>(.05 if f in ('support','project') else .02):fails.append('original_adverse_rate')
  strong=x['legacyQ'] is not None and x['legacyQ']>=1.1-1e-9;rank=math.floor((x['legacyQ'] or 0)*100+.5)/100
 else:
  A=key=='CON-022@v1'
  # A's quality rank does not consume capacity exception claims.
  if A:common=[z for z in common if z!='unconfirmed_interval']
  if x['active_days']<(10 if A else 30) or n<(1 if f=='project' else 20):fails.append('insufficient_own_exposure')
  if q is not None and x['QA_complete'] and q<((97 if f=='support' else 98) if A else 95):fails.append('QA_below_absolute_threshold')
  if x['critical'] or (not A and x['major']):fails.append('observed_QA_defect_gate')
  if f!='project':
   if x['acceptance_rate'] is not None and x['acceptance_rate']<.95:fails.append('accepted_below_95pct')
   if f=='backoffice' and x['sla'] is not None and x['sla']<.95:fails.append('SLA_below_95pct')
   if A:
    if x['adverse_rate'] is not None and x['adverse_rate']>(.05 if f=='support' else .02):fails.append('adverse_rate')
    strong=q is not None and q>=99 and x['inspections']>=20 and x['event_days']>=10
    rank=q
   else:
    if x['ratio'] is not None and x['ratio']<1-1e-9:fails.append('result_below_prospective_capacity')
    if min((v for v in x['strata'].values() if v is not None),default=0)<.9-1e-9:fails.append('stratum_below_90pct')
    strong=x['ratio'] is not None and x['ratio']>=1.1-1e-9 and min((v for v in x['strata'].values() if v is not None),default=0)>=1-1e-9;rank=round(x['ratio'],4) if x['ratio'] is not None else None
  else:
   fails+=x['failproject']
   if not A:
    for z in x['project']:
     if z['target'] is not None and z['usage'] is not None and z['usage']<z['target']:fails.append('local_business_target')
    ratios=[z['usage']/z['target'] for z in x['project'] if z['target'] and z['usage'] is not None]
    analytic=bool(x['project']) and all(z['type']=='analytical_business_decision_package' for z in x['project'])
    strong=all(z['preread_ready'] for z in x['project']) if analytic else bool(ratios) and min(ratios)>=1.1-1e-9
    rank=1 if analytic else min(ratios) if ratios else None
   else:strong=q is not None and q>=99 and x['QA_complete'];rank=q
 if key=='CON-022@v1' and fails:state='not_earned'
 elif any('known_unusable_before_start' in z for z in common):state='not_computable'
 elif common:state='pending'
 elif fails:state='not_earned'
 else:state='earned'
 return state,strong and state=='earned',rank,sorted(set(common+fails))

def calc(key,facts,d):
 rows=[]
 for x0 in facts:
  x=copy.deepcopy(x0);state,strong,rank,reason=policy(key,x,d)
  x.update(candidate_key=key,state=state,strong=strong,rank_key=rank,rank=None,tie_size=0,unit_top_R=0,reason=reason)
  rows.append(x)
 for gp,group in by(rows,'period','group').items():
  npeople=len({m['employee_id'] for x in group for m in x['members']}) if group[0]['family']=='project' else len(group)
  pool=150*npeople
  if key=='BASELINE' or len(group)<2:continue
  if any(x['state'] in ['pending','not_computable'] for x in group):
   for x in group:x['top_status']='pending_group';x['group_reserve_R']=pool
   continue
  eligible=sorted([x for x in group if x['strong']],key=lambda x:x['rank_key'],reverse=True)
  clusters=[]
  for x in eligible:
   if not clusters or (clusters[-1][-1]['rank_key']-x['rank_key']>=1 if key=='CON-022@v1' else clusters[-1][-1]['rank_key']!=x['rank_key']):clusters.append([])
   clusters[-1].append(x)
  pos=0
  for tied in clusters:
   amount=sum([Fraction(2,5),Fraction(3,10),Fraction(1,5),Fraction(1,10)][pos:min(4,pos+len(tied))])*pool/len(tied)
   for x in tied:x.update(rank=pos+1,tie_size=len(tied),unit_top_R=float(amount))
   pos+=len(tied)
 people=[]
 for x in rows:
  p=x['period'];s=x['subject'];capdays=x['active_days'];min_days=30 if key=='CON-023@v1' else 10
  persons=[(m['employee_id'],m['contribution_share'],m['personal_active_days'],m['window_id'],m['cohort_id']) for m in x['members']] if x['family']=='project' else [(s,1,capdays,x['window'],x['cohort'])]
  for person,share,days,w,c in persons:
   forbidden=set(x['own']);aud=[a for a in d['approvals_audit'] if a['period_id']==p and a['beneficiary_id']==person];post=[a for a in aud if a.get('action')=='input_correction_and_posting_review'];a=max(post,key=lambda z:z.get('version',0)) if post else None
   auth=action_errors(a,forbidden,'input_correction_and_posting_review',p+':'+person,dt(x['close']))
   # New candidates require an exact materialised package, absent in every public fixture.
   if key in ['CON-022@v1','CON-023@v1']:auth.append('current_materialized_award_package_binding_not_in_source')
   if key=='BASELINE':auth.append('baseline_local_award_policy_unavailable')
   right=x['state'] if days>=min_days else 'not_earned';top=math.floor(x['unit_top_R']*share+1e-9) if right=='earned' else 0
   people.append({'candidate_key':key,'period':p,'subject':person,'unit':s,'window':w,'cohort':c,'calculated_state':right,'top_calculated_R':top,'top_authorized_U_R':top if not auth else 0,'authorization_errors':auth,'rank':x['rank'],'tie_size':x['tie_size'],'share':share,'original_right_date':x['close']})
 return rows,people

def calendar(d):
 result=[]
 for w in d.get('personal_windows',[]):
  rules=[r for r in d['period_rules'] if r['window_id']==w['window_id']]
  for r in rules:
   cap=next(c for c in d['roster_capacity'] if c['period_id']==r['period_id'] and c['subject_id']==w['subject_id'])
   lo=dt(r['start']);hi=dt(r['end'])+timedelta(days=1);close=dt(r['quality_close_at'])
   for e in d['work_events']:
    if e['subject_id']!=w['subject_id'] or not lo-timedelta(days=1)<=dt(e['event_at'])<=hi+timedelta(days=1):continue
    q=next(q for q in d['quality_acts'] if q['case_id']==e['case_id']);receipt=next(z for z in d['source_receipts'] if z['source_key']['act_id']==q['act_id'])
    inside=lo<=dt(e['event_at'])<hi;employed=(not cap.get('effective_from') or e['event_at'][:10]>=cap['effective_from']) and (not cap.get('effective_to') or e['event_at'][:10]<=cap['effective_to'])
    timely=bool(e.get('accepted_at') and dt(e['accepted_at'])<=close);fact=bool(q.get('evidence_status')=='present' and q.get('minor') is not None and dt(q['finalized_at'])<=close)
    delivered=receipt['delivery_status'] in ['received','restored'] and receipt.get('received_sha256')==h(q)
    state='outside_interval' if not inside else 'outside_effective_employment' if not employed else 'actual_acceptance_late' if not timely else 'timely_fact_received' if fact and delivered else 'evidence_restoration_pending'
    result.append({'window':w['window_id'],'period':r['period_id'],'source_partition':e['period_id'],'subject':w['subject_id'],'event':e['event_id'],'event_at':e['event_at'],'start':lo.isoformat(),'next_start_exclusive':hi.isoformat(),'close':close.isoformat(),'acceptance_at':e.get('accepted_at'),'QA_finalized_at':q['finalized_at'],'received_at':receipt['received_at'],'inside':inside,'employed':employed,'state':state,'original_window_reserve':inside and employed and timely and not(fact and delivered),'full_award':'not_computable_boundary_probe_only'})
 return result

def jsonout(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(path,rows):
 if not rows:return
 with path.open('w') as f:
  fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows])

def ast_namespace(path):
 """Only function definitions and harmless imports, for a concrete defect probe."""
 tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))];ns={'__file__':str(path),'PUBLIC_CONFIGS':CONFIGS};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns

def defects():
 # A single independent expected rule is used: unsigned/unbound policy changes cannot authorize U.
 d=reader.expand_scenario('R1.volume',OLD)
 p='P1';person='S31';src=next(a for a in d['approvals_audit'] if a['approval_id']==p+':'+person)
 a=copy.deepcopy(src);a.update(approval_id='AWARD:'+p+':'+person,action='input_correction_and_posting_review',signed_at='2026-04-28T12:30:00+03:00',version=2,source_ref=p+':'+person)
 d['approvals_audit'].append(a)
 for m in d['source_manifest']:
  if m['table']=='approvals_audit':
   rs=[r for r in d['approvals_audit'] if r['period_id']==m['period_id']];m.update(received_count=len(rs),expected_count=len(rs),received_sha256=h(rs))
 B=ast_namespace(ROOT/'branches/B/con-023/evaluator.py');spec=json.loads((ROOT/'branches/B/con-023/metrics-spec.json').read_text())
 u,ppl=B['evaluate'](d,spec,CONFIGS);row=next(x for x in ppl if x['period']=='P1' and x['subject']==person)
 changed=copy.deepcopy(spec);changed['top_R_per_person']=300
 u2,p2=B['evaluate'](d,changed,CONFIGS);row2=next(x for x in p2 if x['period']=='P1' and x['subject']==person)
 result={'test':'C3 exact package and policy binding','source':'R1.volume plus one controlled performed award-review; no package/rule/config/decision hashes provided','subject':person,'expected':'authorization held, U=0; a policy change requires new signed materialised package','observed_original':{k:row[k] for k in ['authorization','authorization_errors','top_earned_R','top_U_R']},'observed_changed_rule_same_signature':{k:row2[k] for k in ['authorization','authorization_errors','top_earned_R','top_U_R']},'source_mutation':'only in-memory; no source/author writes','author_code_execution':'AST function definitions only, no module-level exports or builders'}
 jsonout(OUT/'counterexamples.json',[result]);return result

def main():
 allunits=[];allpeople=[];summ=[];vectors={};cals=[]
 for ent in reader.scenario_index(OLD):
  name=ent['name'];d=reader.expand_scenario(name,OLD);facts=read_metrics(d)
  if d.get('personal_windows'):
   cals += [dict(scenario=name,**r) for r in calendar(d)]
  for key in KEYS:
   units,people=calc(key,facts,d)
   # Boundary panels do not constitute a complete work census for ANY variant.
   if d.get('personal_windows'):
    for x in units:x.update(state='not_computable',strong=False,unit_top_R=0,reason=sorted(set(x['reason']+['calendar_probe_not_complete_award_census'])))
    for x in people:x.update(calculated_state='not_computable',top_calculated_R=0,top_authorized_U_R=0)
   for x in units:x['scenario']=name
   for x in people:x['scenario']=name
   allunits+=units;allpeople+=people
   summ.append({'scenario':name,'candidate_key':key,'units':len(units),'persons':len(people),'unit_states':dict(Counter(x['state'] for x in units)),'strong_units':sum(x['strong'] for x in units),'calculated_top_personal_R':sum(x['top_calculated_R'] for x in people),'authorized_top_U_R':sum(x['top_authorized_U_R'] for x in people),'guarantee_note':'see personal-windows.csv; no all-N extrapolation'})
   if name.startswith('R') or name=='base':vectors[name+'|'+key]=[{k:x.get(k) for k in ['period','subject','family','roots','qa','ratio','project','state','strong','rank','tie_size','unit_top_R','reason']} for x in units if x['period'] in ['P1','C01Q1']]
 csvout(OUT/'independent-units.csv',allunits);csvout(OUT/'independent-persons.csv',allpeople);csvout(OUT/'scenario-summary.csv',summ);csvout(OUT/'calendar.csv',cals)
 windows=[]
 for keys,ps in by(allpeople,'scenario','candidate_key','subject','window').items():
  name,key,person,window=keys;rs=sorted(ps,key=lambda x:dt(x['original_right_date']))[:2]
  state='not_computable' if key=='BASELINE' or name.startswith('R4.') else 'pending' if len(rs)<2 or any(x['calculated_state'] in ['pending','not_computable'] for x in rs) else 'earned' if all(x['calculated_state']=='earned' for x in rs) else 'not_earned'
  G=2500 if state=='earned' else 0
  windows.append({'scenario':name,'candidate_key':key,'subject':person,'window':window,'periods':[x['period'] for x in rs],'state':state,'calculated_G_R':G,'G_authorized_U_R':G if G and all(not x['authorization_errors'] for x in rs) else 0,'original_right_date':rs[-1]['original_right_date'] if rs else None,'frequency':'one first-quarter pair of fixed window / 12 months; no rolling retry'})
 csvout(OUT/'personal-windows.csv',windows);jsonout(OUT/'vectors.json',vectors)
 defect=json.loads((OUT/'counterexamples.json').read_text())[0] if (OUT/'counterexamples.json').exists() else defects()
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OLD/'manifest.json',AD/'manifest.json',ROOT/'branches/A/con-022/metrics-spec.json',ROOT/'branches/B/con-023/metrics-spec.json']}
 jsonout(OUT/'verification.json',{'python':sys.version,'scenario_count':len(reader.scenario_index(OLD)),'candidate_keys':KEYS,'comparisons':len(summ),'unit_rows':len(allunits),'personal_rows':len(allpeople),'calendar_rows':len(cals),'window_rows':len(windows),'input_hashes':hashes,'counterexample':defect,'method':'own primitive to metric to level to rank to integer personal money; source-only reader; historical sampling uses original seed; no author evaluator used as oracle','limitations':['Historical project closure grain counted by nonduplicated business root, no extra closures synthesized from child tickets.','Boundary rows cannot establish complete award census.','No real ledger posting exists; no source signature is upgraded to actual posting.']})
 print(json.dumps({'comparisons':len(summ),'unit_rows':len(allunits),'counterexample':defect},ensure_ascii=False))
if __name__=='__main__':main()
