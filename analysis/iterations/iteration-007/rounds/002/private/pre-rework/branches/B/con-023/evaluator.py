#!/usr/bin/env python3
"""CON-023@v1 analytical calculator. Python3 stdlib; verified on3.14.8.
No posting API. Names label output only; evaluate receives no scenario identifier.
"""
import sys
sys.dont_write_bytecode=True
import csv, json, hashlib, importlib.util, math
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, date, timedelta, timezone
from fractions import Fraction as F
HERE=Path(__file__).resolve().parent
ROUND=HERE.parents[2]
FIXTURE=ROUND/'supporting/fixtures'
STRESS=ROUND/'supporting/round002-stress'
def dt(x):
 if not x:return None
 v=datetime.fromisoformat(x)
 return v if v.tzinfo else v.replace(tzinfo=timezone(timedelta(hours=3)))
def day(x):return date.fromisoformat(x[:10]) if x else None
def digest(x):return hashlib.sha256((json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
def unique(rows,key):
 out={}
 for r in rows:
  if r[key] in out and out[r[key]]!=r:raise ValueError('conflicting key '+str(r[key]))
  out[r[key]]=r
 return list(out.values())
def approval_errors(a, forbidden, action):
 if not a:return ['performed_action_missing']
 e=[]
 if a.get('action')!=action:e.append('wrong_action')
 try:
  if not isinstance(a.get('signed_at'),str) or not a['signed_at'].strip() or dt(a['signed_at']) is None:e.append('signed_at_missing_or_invalid')
 except (ValueError,TypeError):e.append('signed_at_missing_or_invalid')
 actors=[a.get(k) for k in ('input_editor_id','signer_id','operator_id')]
 if any(not isinstance(x,str) or not x.strip() for x in actors):e.append('actor_missing')
 if len(set(actors))!=3:e.append('editor_signer_operator_not_distinct')
 if any(x in forbidden for x in actors):e.append('beneficiary_actor')
 for k,v in a.items():
  if k.endswith('_reporting_to') and any(x in forbidden for x in (v if isinstance(v,list) else [v]) if x):e.append('reporting_conflict:'+k)
 return sorted(set(e))
def manifest_errors(d):
 out=defaultdict(list)
 for m in d['source_manifest']:
  rows=[r for r in d[m['table']] if r.get('period_id',m['period_id'])==m['period_id']]
  if m['availability'] not in ('available','restored'):out[m['period_id']].append(m['table']+':'+m['availability'])
  elif len(rows)!=m['received_count'] or m['expected_count']!=m['received_count'] or digest(rows)!=m['received_sha256']:out[m['period_id']].append(m['table']+':hash_count')
 return out
def union_hours(rows):
 spans=sorted((dt(x['start_at']),dt(x['end_at'])) for x in rows); merged=[]
 for a,b in spans:
  if b<=a:raise ValueError('nonpositive interval')
  if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 return sum((b-a).total_seconds()/3600 for a,b in merged)
def quality(d, roots, s,p,f,rule,own):
 close=dt(rule['quality_close_at']) if rule.get('quality_close_at') else dt(rule['quality_close']+'T23:59:59+03:00')
 valid=[]; reject=[]
 for q in d['quality_acts']:
  if q['subject_id']!=s or q['period_id']!=p:continue
  ok=(q.get('evidence_status')=='present' and q.get('checker_id') and q['checker_id'] not in own and q.get('inspection_id')
      and q.get('scope')==('team' if f=='project' else 'personal') and q.get('criterion')=='defect_penalty'
      and q.get('scale')=='0..100' and q.get('scale_version')=='penalty-v1'
      and q.get('sample_method')=='census_of_scenario_work_register'
      and q.get('finalized_at') and dt(q['finalized_at'])<=close
      and q.get('observation_end') and day(q['observation_end'])>=day(rule['quality_close'])
      and q.get('observation_start') and day(q['observation_start'])>=day(rule['start'])
      and all(q.get(k) is not None for k in ('minor','major','critical')))
  if ok:valid.append(q)
  else:reject.append(q['act_id'])
 covered=set();used=[]
 for root,es in roots.items():
  cases={x['case_id'] for x in es}
  acts=[q for q in valid if q.get('case_id') in cases or q.get('deliverable_id')==root]
  whole=[q for q in acts if f=='project' and q.get('coverage_object')=='same_deliverable_inspection']
  part={q.get('case_id') for q in acts if q.get('coverage_object')=='one_distinct_case'}
  # Linked repeat/correction can reuse original case act; cannot create benefit.
  ok=bool(whole) or all(x['case_id'] in part or (f!='project' and any(x.get(k) in part for k in ('duplicate_of','reopen_of','correction_of'))) for x in es)
  if ok:covered.add(root)
  used+=acts
 byins=defaultdict(list)
 for q in used:byins[q['inspection_id']].append(q)
 scores=[];critical=major=0
 for qs in byins.values():
  vals={(q['minor'],q['major'],q['critical']) for q in qs}
  if len(vals)!=1:return {'state':'pending','score':None,'covered':len(covered),'required':len(roots),'inspections':len(byins),'refs':[],'rejected':reject,'reason':'conflicting_inspection'}
  minor,ma,cr=next(iter(vals));scores.append(max(0,100-2*minor-10*ma-100*cr));critical+=cr;major+=ma
 score=sum(scores)/len(scores) if scores else None
 state='pass' if roots and len(covered)==len(roots) else 'pending'
 if critical or major or (score is not None and score<95):state='fail'
 return {'state':state,'score':score,'covered':len(covered),'required':len(roots),'inspections':len(byins),'refs':sorted({q['act_id'] for q in used})[:3],'rejected':reject[:3],'reason':'all_parts_or_actual_whole_act'}
def calendar_audit(d):
 """Actual personal intervals, independent from export partition labels.
 Boundary rows test time logic, not a complete production/capacity census.
 """
 out=[]
 for w in d.get('personal_windows',[]):
  rules=sorted([r for r in d['period_rules'] if r['window_id']==w['window_id']],key=lambda r:r['start'])
  events=unique([e for e in d['work_events'] if e['subject_id']==w['subject_id']],'event_id')
  for r in rules:
   start=dt(r['start']+'T00:00:00+03:00');end=dt((day(r['end'])+timedelta(days=1)).isoformat()+'T00:00:00+03:00');close=dt(r['quality_close_at'])
   for e in events:
    # One row per source case and candidate personal interval. No period-ID membership shortcut.
    if not(start-timedelta(days=1)<=dt(e['event_at'])<=end+timedelta(days=1)):continue
    qa=[q for q in d['quality_acts'] if q.get('case_id')==e['case_id']]
    receipts=[x for x in d.get('source_receipts',[]) if x['source_key'].get('act_id') in {q['act_id'] for q in qa}]
    actual_qa=any(q.get('evidence_status')=='present' and q.get('finalized_at') and dt(q['finalized_at'])<=close for q in qa)
    delivered=any(x['delivery_status'] in ('received','restored') and x.get('received_at') and x.get('received_sha256')==digest(next(q for q in qa if q['act_id']==x['source_key']['act_id'])) for x in receipts)
    in_work=start<=dt(e['event_at'])<end
    cap=next(c for c in d['roster_capacity'] if c['subject_id']==w['subject_id'] and c['period_id']==r['period_id'])
    employed=(not cap.get('effective_from') or day(e['event_at'])>=day(cap['effective_from'])) and (not cap.get('effective_to') or day(e['event_at'])<=day(cap['effective_to']))
    accepted_by_close=bool(e.get('accepted_at') and dt(e['accepted_at'])<=close)
    out.append({'subject':w['subject_id'],'window':w['window_id'],'period':r['period_id'],'source_partition':e['period_id'],'event_id':e['event_id'],'case_id':e['case_id'],'event_at':e['event_at'],'accepted_at':e.get('accepted_at'),'interval_start':start.isoformat(),'next_start_exclusive':end.isoformat(),'quality_close_at':close.isoformat(),'work_in_interval':in_work,'in_effective_employment_interval':employed,'effective_from':cap.get('effective_from'),'effective_to':cap.get('effective_to'),'scheduled_hours_already_FTE_and_absence':cap['scheduled_hours'],'fixed_window_unchanged':True,'acceptance_by_close':accepted_by_close,'QA_fact_by_close':actual_qa,'QA_received_now':delivered,'calendar_result':'outside_interval' if not in_work else 'outside_effective_employment' if not employed else 'actual_acceptance_late' if not accepted_by_close else 'evidence_restoration_pending' if not(actual_qa and delivered) else 'timely_fact_received','receipt_refs':','.join(x['receipt_id'] for x in receipts),'reserved_original_window':in_work and employed and accepted_by_close and not(actual_qa and delivered),'award':'calendar_probe_only_no_business_config_or_full_census'})
 return out

def evaluate(d,spec,configs):
 errs=manifest_errors(d); units=[];classes={x['type_id']:x for x in d['classifier']};members=d['team_members']
 rules={(r['period_id'],r['family']):r for r in d['period_rules']}
 events=unique(d['work_events'],'event_id')
 for reg in sorted(d['comparison_registry'],key=lambda r:(r['period_id'],r['subject_id'])):
  p,s=reg['period_id'],reg['subject_id']; cap=next(c for c in d['roster_capacity'] if (c['period_id'],c['subject_id'])==(p,s));f=cap['family'];rule=rules[p,f]
  ms=[m for m in members if m['period_id']==p and m['team_id']==s];own={s}|{m['employee_id'] for m in ms}
  # R4 slices are calendar probes. Cross-partition source events handled in calendar_audit;
  # incomplete 9-case boundary probes never substitute a full source census.
  es=[e for e in events if e['period_id']==p and e['subject_id']==s]
  pending=[];fail=[];ins=[];roots=defaultdict(list)
  for e in es:
   if not e.get('root_id'):pending.append('root_link_missing:'+e['event_id']);continue
   roots[e['root_id']].append(e)
   if e.get('assignment_history_status')!='complete' or not e.get('assigned_by') or e['assigned_by'] in own:pending.append('assignment_history_independence')
  if cap.get('assignment_history_status')!='complete':pending.append('roster_assignment_history')
  if cap['active_days']<spec['min_active_days'] or len(roots)<(1 if f=='project' else spec['min_flow_roots']):ins.append('insufficient_exposure')
  relevant={'period_rules','comparison_registry','roster_capacity','work_events','quality_acts','classifier','capacity_intervals',{'support':'support_outcomes','backoffice':'process_outcomes','project':'project_records'}[f]}
  if f=='project':relevant.add('team_members')
  pending += [x for x in errs.get(p,[]) if x.split(':')[0] in relevant]
  if day(rule['approved_at'])>=day(rule['start']) or rule['standard_owner'] in own:pending.append('rule_not_independent_prospective')
  if day(cap['registered_at'])>=day(rule['start']) or cap['capacity_owner'] in own:pending.append('capacity_not_independent_prospective')
  for a in d['approvals_audit']:
   if a['period_id']==p and a['beneficiary_id'] in own and a['action']=='type_correction' and approval_errors(a,own,'type_correction'):pending.append('unapproved_type_correction:'+a['approval_id'])
  q=quality(d,roots,s,p,f,rule,own)
  if q['state']=='pending':pending.append('QA_incomplete')
  if q['state']=='fail':fail.append('QA_failed')
  prs=[x for x in d['project_records'] if x['period_id']==p and x['subject_id']==s]
  measures={x.get('usage_measure') for x in prs}
  worktype=f if f!='project' else ('analytical_business_decision_package' if measures=={'distinct_business_decisions_using_deliverable'} else 'workflow' if measures=={'distinct_workflow_runs_at_deliverable_grain'} else None)
  cs=[c for c in configs if c['version']==1 and c['comparison_group_id']==reg['comparison_group_id'] and c['source_query']['period_id']==p and c['work_type']==worktype]
  c=cs[0] if len(cs)==1 else None
  if not c:pending.append('prospective_business_config_missing_or_ambiguous')
  elif day(c['approved_at'])>=day(rule['start']) or c['owner'] in own:pending.append('config_not_independent_prospective')
  intervals=[]
  for x in d['capacity_intervals']:
   if x['period_id']!=p or x['subject_id']!=s:continue
   if x.get('source_ref') and x.get('recorded_by') and x.get('approved_by') and x['recorded_by'] not in own and x['approved_by'] not in own:intervals.append(x)
   else:pending.append('unconfirmed_capacity_interval:'+x['interval_id'])
  removed=union_hours(intervals)
  if removed and (cap['leave_hours'] or cap['training_hours']):pending.append('exception_absence_overlap_unknown')
  available=(cap['scheduled_hours']-cap['leave_hours']-cap['training_hours']-removed)*cap['allocation_fraction']
  good={};timely={};units_by_root={};pertype=defaultdict(float);project_values=[];ready_flags=[];project_refs=[]
  omap={o['case_id']:o for o in d[{'support':'support_outcomes','backoffice':'process_outcomes','project':'project_records'}[f]] if o['period_id']==p and o['subject_id']==s}
  for root,rs in sorted(roots.items()):
   original=min(rs,key=lambda e:(e.get('assigned_at') or '9999',e['case_id']));latest=max([e for e in rs if e['case_id']==original['case_id']],key=lambda e:(e['version'],e['event_at']))
   if f!='project':
    o=omap.get(original['case_id']);cl=classes.get(original['type_id']);units_by_root[root]=cl['standard_units'] if cl else 0
    if not cl or cl.get('employee_editable') or cl['complexity_owner'] in own or day(cl['approved_at'])>=day(rule['start']):pending.append('unconfirmed_class:'+root)
    if not o:pending.append('outcome_missing:'+root);good[root]=False;timely[root]=False;continue
    if not o.get('observation_end') or day(o['observation_end'])<day(latest['event_at'])+timedelta(days=rule['outcome_followup_days']):pending.append('outcome_immature:'+root)
    if not original.get('due_at'):pending.append('missing_due:'+root)
    bad=any(e.get('reopen_of') or e.get('correction_of') or e.get('status')=='reopened' for e in rs)
    ok=bool(latest.get('accepted_at') and latest.get('accepted_by') and latest['accepted_by'] not in own and day(latest['accepted_at'])<=day(rule['end']) and latest['status'] in ('Done','resolved'))
    ok=ok and bool(o.get('resolved') and not o.get('transfer') and not o.get('repeat_of') if f=='support' else o.get('accepted') and not o.get('returned')) and not bad
    good[root]=ok;timely[root]=bool(ok and (o.get('sla_due_at') or original.get('due_at')) and dt(latest['accepted_at'])<=dt(o.get('sla_due_at') or original['due_at']))
    if ok:pertype[original['type_id']]+=units_by_root[root]
   else:
    ps=[x for x in prs if x['deliverable_id']==root or x['parent_id']==root]
    if not ps:pending.append('project_record_missing:'+root);good[root]=False;continue
    fields=('benefit_id','criteria_ref','criteria_agreed_at','acceptance_at','acceptance_owner','acceptance_ref','release_at','release_ref','usage_ref','usage_observed_at','usage_owner','usage_status','usage_units','usage_measure','usage_coverage','rollback')
    if len({tuple(x.get(k) for k in fields) for x in ps})!=1:pending.append('inconsistent_project_evidence:'+root)
    x=ps[0];project_refs.append(x['record_id']);required=('criteria_ref','criteria_agreed_at','acceptance_at','acceptance_owner','acceptance_ref','release_at','release_ref','usage_ref','usage_observed_at','usage_owner','usage_coverage')
    if any(not x.get(k) for k in required) or x.get('usage_status')!='present' or x.get('usage_units') is None:pending.append('acceptance_or_use_missing:'+root);good[root]=False;continue
    if day(x['criteria_agreed_at'])>=day(rule['start']):pending.append('criteria_not_prospective:'+root)
    # Legacy criteria refs predate this prospective addendum; new refs name exact config version.
    if x['criteria_ref'].startswith('CFG-') and c and x['criteria_ref']!=c['config_id']+'-v1':pending.append('conflicting_goal_version:'+root)
    if x['acceptance_owner'] in own or x['usage_owner'] in own:pending.append('self_acceptance_use:'+root)
    if len({z['deliverable_id'] for z in d['project_records'] if z['period_id']==p and z.get('benefit_id')==x['benefit_id']})>1:pending.append('same_benefit_multiple_roots')
    target=c['target_value'] if c else None
    deadline=dt(c['business_deadline']) if c else None;close=dt(rule['quality_close']+'T23:59:59+03:00')
    ok=bool(c and dt(x['acceptance_at'])<=deadline and dt(x['release_at'])<=deadline and dt(x['usage_observed_at'])<=close and dt(x['release_at'])<=dt(x['usage_observed_at']) and not x['rollback'] and x['usage_units']>=target)
    if worktype=='analytical_business_decision_package':ok=bool(ok and x['usage_coverage']=='one_named_business_decision' and x['usage_units']==1)
    elif worktype=='workflow':ok=bool(ok and x['usage_coverage']=='one_internal_process')
    good[root]=ok;project_values.append(x['usage_units']/target if target else None)
    ready_flags.append(bool(c and c.get('readiness_criterion') and dt(x['acceptance_at'])<=dt(c['readiness_criterion']['ready_by']) and dt(x['release_at'])<=dt(c['readiness_criterion']['ready_by'])))
  n=len(roots);rate=sum(good.values())/n if n else None;sla=sum(timely.values())/n if n and f!='project' else None
  stratum={};numerator=sum(units_by_root.get(r,0) for r,v in good.items() if v);denominator=available*sum(a['capacity_share']*a['standard_units_per_hour'] for a in rule['stratum_allocations']) if f!='project' else None
  result=numerator/denominator if denominator and denominator>0 else None
  if f!='project':
   for a in rule['stratum_allocations']:
    den=available*a['capacity_share']*a['standard_units_per_hour'];stratum[a['type_id']]=pertype[a['type_id']]/den if den>0 else 0
   if set(pertype)-{a['type_id'] for a in rule['stratum_allocations']}:pending.append('unallocated_stratum')
   if denominator is None or denominator<=0:pending.append('nonpositive_capacity')
   if rate is not None and rate<spec['flow_acceptance_normal']:fail.append('full_assigned_acceptance_below_0.95')
   if result is not None and result<spec['flow_result_normal']-1e-9:fail.append('result_below_1.00')
   if min(stratum.values(),default=0)<spec['stratum_floor']-1e-9:fail.append('stratum_below_0.90')
   if f=='backoffice' and sla is not None and sla<spec['SLA_normal']-1e-9:fail.append('SLA_below_0.95')
   strong=bool(result is not None and result>=spec['flow_result_strong']-1e-9 and min(stratum.values(),default=0)>=1-1e-9 and rate is not None and rate>=.95)
   rank_key=(round(result,4),) if result is not None else ()
  else:
   if n and not all(good.values()) and not pending:fail.append('local_business_target_not_met')
   result=min(v for v in project_values if v is not None) if any(v is not None for v in project_values) else None
   strong=bool(all(good.values()) and n and (all(ready_flags) if worktype=='analytical_business_decision_package' else result is not None and result>=spec['workflow_strong']-1e-9))
   rank_key=(1,) if strong and worktype=='analytical_business_decision_package' else (round(result,4),) if result is not None else ()
  # Incomplete evidence dominates derived failures; confirmed critical QA or complete observed fail remains fail.
  state='not_earned' if q['state']=='fail' else 'not_computable' if any('known_unusable_before_start' in z for z in pending) else 'pending' if pending else 'insufficient' if ins else 'not_earned' if fail else 'earned'
  u={'period':p,'subject':s,'family':f,'work_type':worktype,'group':reg['home_pool_id'],'window':reg['window_id'],'cohort':reg['cohort_id'],'state':state,'normal':state=='earned','strong':strong and state=='earned','rank_key':rank_key,'rank':None,'tie_size':0,'top_R':F(0),'top_state':'not_earned','roots':n,'accepted':sum(good.values()),'acceptance_rate':rate,'sla':sla,'result':result,'numerator':numerator,'denominator':denominator,'available_hours':available,'removed_hours':removed,'stratum':stratum,'quality':q,'business_config':c['config_id']+'-v1' if c else None,'project_readiness':ready_flags,'reason':sorted(set(pending+ins+fail)),'refs':{'capacity':cap['capacity_id'],'registry':reg['registry_id'],'rule':rule['rule_id'],'events':[e['event_id'] for e in es[:2]],'project_records':project_refs[:2]},'active_days':cap['active_days'],'right_date':rule.get('quality_close_at',rule['quality_close'])}
  units.append(u)
 # Never compare different project types using bare usage counts. Separate preregistered local subpool.
 people=[]
 for u in units:
  ms=[m for m in members if m['period_id']==u['period'] and m['team_id']==u['subject']]
  if ms and sum(m['contribution_share'] for m in ms)>1+1e-9:raise ValueError('team shares exceed1')
  persons=[(m['employee_id'],F(str(m['contribution_share'])),m['personal_active_days'],m['window_id'],m['cohort_id'],m) for m in ms] if u['family']=='project' else [(u['subject'],F(1),u['active_days'],u['window'],u['cohort'],None)]
  forbidden={u['subject']}|{x[0] for x in persons}
  for person,share,days,window,cohort,m in persons:
   audits=[a for a in d['approvals_audit'] if a['period_id']==u['period'] and a['beneficiary_id']==person]
   reviews=[a for a in audits if a['action']==spec['posting_action']];a=max(reviews,key=lambda a:(a['version'],a.get('signed_at') or '')) if reviews else None
   ae=approval_errors(a,forbidden,spec['posting_action'])
   if a and a.get('source_ref')!=u['period']+':'+person:ae.append('wrong_source_scope')
   if a and u['family']=='project' and a.get('beneficiary_team') not in (None,u['subject']):ae.append('wrong_team_scope')
   # Source completeness actions are checked separately; never turn into authorization.
   sr=[z for z in audits if z['action']=='source_completeness_review'];src=max(sr,key=lambda z:(z['version'],z.get('signed_at') or '')) if sr else None
   se=approval_errors(src,forbidden,'source_completeness_review') if src else []
   batch=[b for b in d.get('batch_metadata',[]) if b['period_id']==u['period']]
   if batch:
    b=max(batch,key=lambda z:z['version'])
    roster=[z for z in d['comparison_registry'] if z['period_id']==u['period']];tms=[z for z in members if z['period_id']==u['period']]
    if digest(roster)!=b['roster_sha256'] or digest(tms)!=b['team_members_sha256'] or b.get('roster_count')!=len(roster) or b.get('team_member_count')!=len(tms):se.append('batch_composition_changed')
    if not src or src['approval_id'] not in b.get('approval_refs',[]):se.append('batch_person_review_not_covered')
    if src and src.get('signed_at') and dt(src['signed_at'])>dt(b['signed_at']):se.append('review_after_batch_version')
    if any(z['period_id']==u['period'] and z.get('action')=='registry_input_change' and z.get('signed_at') and dt(z['signed_at'])>dt(b['signed_at']) for z in d['approvals_audit']):se.append('registry_changed_after_batch')
    se+=approval_errors(dict(b,action='source_completeness_review'),forbidden,'source_completeness_review')
   if any(z.startswith('approvals_audit:') for z in errs.get(u['period'],[])):ae.append('approval_source_incident')
   personal=days>=spec['min_active_days']
   if m and (not m.get('approved_by') or m['approved_by'] in forbidden or day(m['approved_at'])>=day(rules[u['period'],'project']['start'])):personal=False
   calculated=u['state'] if personal else 'insufficient'
   if se and calculated=='earned':calculated='pending'
   state='pending' if calculated=='earned' and ae else calculated
   people.append({'period':u['period'],'subject':person,'unit':u['subject'],'family':u['family'],'work_type':u['work_type'],'group':u['group'],'window':window,'cohort':cohort,'share':share,'calculated_state':calculated,'calculated_normal':calculated=='earned','state':state,'strong':u['strong'] and personal and not se,'authorization':'signed_U_not_posted' if not ae else 'held_no_authorization','approval_ref':a.get('approval_id') if a else None,'source_review_ref':src.get('approval_id') if src else None,'source_review_errors':se,'authorization_errors':ae,'rank':None,'tie_size':0,'top_earned_R':0,'top_U_R':0,'top_conditional_R':0,'top_state':'not_earned','right_date':u['right_date'],'reason':u['reason']})
 for key in sorted({(u['period'],u['group'],u['work_type']) for u in units}):
  group=[u for u in units if (u['period'],u['group'],u['work_type'])==key];ps=[x for x in people if (x['period'],x['group'],x['work_type'])==key]
  pool=spec['top_R_per_person']*len({x['subject'] for x in ps})
  if len(group)<2:continue # unchanged small-group rule: one registered unit has no top
  # Missing authorization alone does not change observed rank; missing source review may.
  unsettled=any(u['state'] in ('pending','not_computable') for u in group) or any(x['source_review_errors'] for x in ps)
  if unsettled:
   for x in ps:x['top_state']='pending_group';x['top_conditional_R']=pool # repeated ceiling, do not sum
   continue
  qs=sorted([u for u in group if u['strong']],key=lambda u:u['rank_key'],reverse=True);i=0
  while i<len(qs):
   tied=[u for u in qs if u['rank_key']==qs[i]['rank_key']];j=i+len(tied)
   award=sum(F(str(spec['top_shares'][k]))*pool for k in range(i,min(j,4)))/len(tied)
   for u in tied:
    u.update(rank=i+1,tie_size=len(tied),top_R=award,top_state='earned' if award else 'not_earned')
    for x in ps:
     if x['unit']!=u['subject']:continue
     x.update(rank=i+1,tie_size=len(tied))
     if x['calculated_normal']:
      x['top_earned_R']=int(award*x['share']);x['top_U_R']=x['top_earned_R'] if not x['authorization_errors'] else 0
      x['top_state']='earned_held' if x['authorization_errors'] and award else 'authorized_U' if award else 'not_earned'
   i=j
 return units,people

def write_csv(path,rows):
 if not rows:return
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,default=str) if isinstance(v,(list,dict,tuple)) else str(v) if isinstance(v,F) else v for k,v in r.items()})
def main():
 module=importlib.util.spec_from_file_location('public_reader',STRESS/'reader.py');reader=importlib.util.module_from_spec(module);module.loader.exec_module(reader)
 configs=json.loads((STRESS/'business-config.json').read_text())['configs'];spec=json.loads((HERE/'metrics-spec.json').read_text())
 decisions=[];unitrows=[];windows=[];traces=[];calendar=[];groups=[]
 for entry in reader.scenario_index(FIXTURE):
  name=entry['name'];d=reader.expand_scenario(name,FIXTURE);us,ps=evaluate(d,spec,configs)
  decisions += [dict(scenario=name,**x) for x in ps];unitrows += [dict(scenario=name,**u) for u in us]
  calendar += [dict(scenario=name,**x) for x in calendar_audit(d)]
  # One representative of each distinct rule outcome; exact keys reconstruct from public reader.
  seen=set()
  for u in us:
   k=(u['family'],u['work_type'],u['state'],round(u['result'],4) if u['result'] is not None else None,u['strong'],tuple(u['reason']))
   if k not in seen:traces.append(dict(scenario=name,**u));seen.add(k)
  for person,window in sorted({(x['subject'],x['window']) for x in ps}):
   rows=sorted([x for x in ps if x['subject']==person and x['window']==window],key=lambda x:next(r['start'] for r in d['period_rules'] if r['period_id']==x['period'] and r['family']==x['family']))
   # First two fixed quarters only, even if a complete annual dataset has four.
   anchor=next(r['annual_window_start'] for r in d['period_rules'] if r['period_id']==rows[0]['period'] and r['family']==rows[0]['family'])
   a=day(anchor); month_index=a.year*12+a.month-1+3; second=date(month_index//12,month_index%12+1,a.day).isoformat()
   first_starts={anchor,second}
   rows=[x for x in rows if next(r['start'] for r in d['period_rules'] if r['period_id']==x['period'] and r['family']==x['family']) in first_starts]
   if not rows:continue
   states=[x['calculated_state'] for x in rows]
   calculated=len(rows)==2 and all(x=='earned' for x in states)
   st='earned' if calculated else 'not_earned' if any(x in ('not_earned','insufficient') for x in states) else 'not_computable' if 'not_computable' in states else 'pending'
   authorized=calculated and all(not x['authorization_errors'] for x in rows)
   windows.append({'scenario':name,'subject':person,'window':window,'cohort':rows[0]['cohort'],'periods':','.join(x['period'] for x in rows),'calculated_state':st,'G_earned_R':2500 if calculated else 0,'G_U_R':2500 if authorized else 0,'G_earned_held_R':2500 if calculated and not authorized else 0,'G_conditional_ceiling_R':2500 if st in ('pending','not_computable') else 0,'original_right_date':rows[-1]['right_date'],'rule':'first_two_quarters_same_fixed_window; once_per12months; no real posting; legacy calendar demonstration'})
  for p,g,t in sorted({(x['period'],x['group'],x['work_type']) for x in ps}):
   xs=[x for x in ps if (x['period'],x['group'],x['work_type'])==(p,g,t)];pool=150*len({x['subject'] for x in xs});unknown=any(x['top_state']=='pending_group' for x in xs)
   groups.append({'scenario':name,'period':p,'group':g,'work_type':t,'pool_R':pool,'earned_R':sum(x['top_earned_R'] for x in xs),'authorized_U_R':sum(x['top_U_R'] for x in xs),'conditional_R':pool if unknown else 0,'unissued_R':0 if unknown else pool-sum(x['top_earned_R'] for x in xs)})
 write_csv(HERE/'decisions.csv',decisions);write_csv(HERE/'unit-decisions.csv',unitrows);write_csv(HERE/'window-guarantee.csv',windows);write_csv(HERE/'group-top-reserve.csv',groups);write_csv(HERE/'calendar-traces.csv',calendar)
 (HERE/'traces.json').write_text(json.dumps({'candidate':'CON-023@v1','locators_base':'rounds/002/supporting; scenario via public reader; #table.primary_key','traces':traces},ensure_ascii=False,indent=2,default=str)+'\n')
 (HERE/'evaluation-summary.json').write_text(json.dumps({'candidate':'CON-023@v1','scenarios':len(reader.scenario_index(FIXTURE)),'decisions':len(decisions),'unit_states':dict(Counter(x['state'] for x in unitrows)),'posting_observed':False},indent=2)+'\n')
 print(json.dumps({'scenarios':len(reader.scenario_index(FIXTURE)),'decisions':len(decisions),'unit_rows':len(unitrows),'compact_traces':len(traces),'calendar_rows':len(calendar)}))
if __name__=='__main__':main()
