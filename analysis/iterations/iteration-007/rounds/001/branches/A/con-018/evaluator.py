#!/usr/bin/env python3
"""Source-only recognition analysis; Python3.12 stdlib. No fixture/oracle/generator imports.
Run: python3 evaluator.py [--scenario base|Fxx.variant] [--out-dir PATH]
The optional fixture reader ONLY materializes public source tables. evaluate(data, spec)
contains no scenario/subject-specific decisions. All money is an illustrative E24 right,
not an API posting. Missing signatures never become completed approvals.
"""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from collections import defaultdict, Counter
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]
FIXTURE = ROUND / 'supporting/fixtures'

def dt(v):
    return datetime.fromisoformat(v) if v else None

def day(v):
    return date.fromisoformat(v[:10]) if v else None

def unique(rows, key):
    """Exact duplicate export is idempotent; ambiguous same-key record is rejected."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    out = []
    for k, group in sorted(grouped.items()):
        versions = {json.dumps(x, sort_keys=True) for x in group}
        if len(versions) != 1:
            raise ValueError('conflicting source key: '+key+'='+str(k))
        out.append(group[0])
    return out

def union_hours(intervals):
    spans = sorted((dt(x['start_at']), dt(x['end_at'])) for x in intervals)
    merged = []
    for start, end in spans:
        if end <= start:
            raise ValueError('nonpositive interval')
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start,end])
    return sum((b-a).total_seconds()/3600 for a,b in merged)

def manifest_state(data, period, tables):
    issues=[]
    for table in tables:
        parts=[x for x in data['source_manifest'] if x['table']==table and x['period_id']==period]
        if not parts:
            issues.append(('missing_partition_manifest',table))
            continue
        for part in parts:
            if part['availability']=='known_unusable_before_start':
                issues.append(('known_gap',table))
            elif part['availability'] not in ('available','restored'):
                issues.append(('lost_partition',table))
            elif part['expected_count']!=part['received_count']:
                issues.append(('count_mismatch',table))
    return issues

def signoff(data, period, person, members=()):
    rows=[x for x in data['approvals_audit'] if x['period_id']==period
          and x['beneficiary_id']==person and x['action']=='input_correction_and_posting_review']
    if not rows:
        return 'missing_signature', None
    a=max(rows,key=lambda x:x['version'])
    excluded=set(members)|{person,a.get('beneficiary_team')}
    excluded.discard(None)
    required=['input_editor_id','signer_id','operator_id','appeal_owner_id']
    if any(not a.get(k) or a[k] in excluded for k in required) or any(
        a.get(k) in excluded for k in ('signer_reporting_to','operator_reporting_to')) or a['operator_id']==a['signer_id']:
        return ('conflict_route_alternate' if a.get('alternate_signer_id') and a.get('alternate_operator_id') else 'conflict_escalate'),a['approval_id']
    signed_at=a.get('signed_at')
    if not isinstance(signed_at,str) or not signed_at.strip():
        return 'missing_signature_time',a['approval_id']
    return 'signed',a['approval_id']

def quality(data, events, roots, period, subject, family, rule, excluded):
    bycase={x['case_id']:root for root,group in roots.items() for x in group}
    valid=[]; rejected=[]
    for q in data['quality_acts']:
        if q.get('subject_id')!=subject or q.get('period_id')!=period:
            continue
        valid_act=(q.get('case_id') in bycase and q.get('evidence_status')=='present'
          and q.get('scope')==('team' if family=='project' else 'personal')
          and q.get('criterion')=='defect_penalty' and q.get('scale')=='0..100'
          and q.get('scale_version')=='penalty-v1' and q.get('sample_method')=='census_of_scenario_work_register'
          and q.get('coverage_object') in ('one_distinct_case','same_deliverable_inspection')
          and q.get('inspection_id') and q.get('checker_id') and q['checker_id'] not in excluded
          and q.get('critical') is not None and q.get('major') is not None and q.get('minor') is not None
          and q.get('observation_end') and day(q['observation_end'])>=day(rule['quality_close'])
          and q.get('finalized_at') and day(q['finalized_at'])<=day(rule['quality_close'])
          and q.get('checked_at') and day(q['checked_at'])>=day(rule['start'])
          and q.get('observation_start') and day(q['observation_start'])>=day(rule['start']))
        if valid_act: valid.append(q)
        else: rejected.append(q['act_id'])
    # Same inspection copied across task records remains one inspection.
    inspections={}
    for q in sorted(valid,key=lambda x:x['act_id']):
        key=(bycase[q['case_id']],q['inspection_id'])
        if key in inspections:
            if any(inspections[key][f]!=q[f] for f in ('score','minor','major','critical')):
                return {'status':'missing','coverage':0,'required':len(roots),'score':None,'critical':None,
                        'act_refs':[],'rejected':rejected,'reason':'conflicting_inspection'}
        else: inspections[key]=q
    root_scores={}
    for root in roots:
        acts=[q for (r,_),q in inspections.items() if r==root]
        if acts:
            coverage_acts=[q for q in valid if bycase[q['case_id']]==root]
            covered={q['case_id'] for q in coverage_acts}
            required_cases={x['case_id'] for x in roots[root]}
            whole_root=any(q.get('coverage_object')=='same_deliverable_inspection' for q in coverage_acts)
            if required_cases<=covered or (family=='project' and whole_root):
                root_scores[root]=min(q['score'] for q in acts)
    critical=sum(q['critical'] for q in inspections.values())
    major=sum(q['major'] for q in inspections.values())
    score=sum(root_scores.values())/len(root_scores) if root_scores else None
    status='pass' if len(root_scores)==len(roots) and roots else 'missing'
    if critical>0 or major>0 or (score is not None and score<95):status='fail'
    return {'status':status,'coverage':len(root_scores),'required':len(roots),'score':score,
            'critical':critical,'major':major,'act_refs':[q['act_id'] for q in inspections.values()],
            'rejected':rejected,'coverage_refs':[q['act_id'] for q in valid if q['coverage_object']=='same_deliverable_inspection'],'reason':'root_census_reused; no sampling inference'}

def evaluate(data, spec):
    """Pure rules over accessible expanded tables; no scenario name accepted here."""
    keys={'approvals_audit':'approval_id','capacity_intervals':'interval_id','classifier':'class_id','comparison_registry':'registry_id','period_rules':'rule_id','process_outcomes':'outcome_id','project_records':'record_id','quality_acts':'act_id','roster_capacity':'capacity_id','source_manifest':'partition_id','support_outcomes':'outcome_id','team_members':'membership_id','work_events':'event_id','worklog':'worklog_id','resource_assumptions':'activity_id'}
    data={k:unique(v,keys[k]) for k,v in data.items()}
    out=[]; detail=[]
    classes={x['type_id']:x for x in data['classifier']}
    events=unique(data['work_events'],'event_id')
    root_owners=defaultdict(set)
    for event in events:
        if event.get('root_id'):root_owners[(event['period_id'],event['root_id'])].add(event['subject_id'])
    benefit_roots=defaultdict(set)
    for record in data['project_records']:
        if record.get('benefit_id'):benefit_roots[(record['period_id'],record['benefit_id'])].add(record.get('deliverable_id'))
    outcomes={x['case_id']:x for x in data['support_outcomes']+data['process_outcomes']}
    for capacity in sorted(data['roster_capacity'],key=lambda x:(x['period_id'],x['subject_id'])):
        s=capacity['subject_id']; p=capacity['period_id']; family=capacity['family']
        rules=[x for x in data['period_rules'] if x['period_id']==p and x['family']==family]
        if len(rules)!=1:raise ValueError('missing/ambiguous rule')
        rule=rules[0]; members=[m for m in data['team_members'] if m['period_id']==p and m['team_id']==s]
        excluded={s}|{m['employee_id'] for m in members}
        e=[x for x in events if x['subject_id']==s and x['period_id']==p]
        bycase={x['case_id']:x for x in e}
        roots=defaultdict(list); reasons=[]; missing=[]
        for x in e:
            root=x.get('root_id')
            links=[x.get(f) for f in ('duplicate_of','reopen_of','correction_of') if x.get(f)]
            if not root and links:
                target=bycase.get(links[0],{})
                root=target.get('root_id')
            if not root:
                missing.append('unlinked_root:'+x['event_id']);continue
            roots[root].append(x)
            if len(root_owners[(p,root)])>1:missing.append('ambiguous_root_home_owner:'+root)
            if not x.get('assigned_at') or not x.get('assigned_by') or x['assigned_by'] in excluded or x.get('assignment_history_status')!='complete':
                missing.append('assignment_history:'+x['event_id'])
        required=['period_rules','roster_capacity','work_events','quality_acts','comparison_registry']
        required+=['project_records','team_members'] if family=='project' else [family=='support' and 'support_outcomes' or 'process_outcomes']
        if spec['mechanism']=='capacity':required+=['classifier','capacity_intervals']
        mi=manifest_state(data,p,required)
        q=quality(data,e,roots,p,s,family,rule,excluded)
        normal=False;stretch=False;numerator=0;denominator=0;value=None
        exposure=capacity['active_days']>=spec['min_active_days']
        if capacity.get('assignment_history_status')!='complete':missing.append('roster_assignment_history')
        if not e:missing.append('empty_work_register_no_proven_zero')
        # A beneficiary may initiate a request, but cannot approve correction/class/source.
        for a in data['approvals_audit']:
            if a['period_id']==p and a['beneficiary_id'] in excluded and a['action']=='type_correction':
                if any(a.get(k) in excluded or not a.get(k) for k in ('input_editor_id','signer_id','operator_id')):
                    missing.append('unapproved_type_correction:'+a['approval_id'])
        good={};ontime={};units={};per_type=defaultdict(float);project_units=[]
        for root,group in sorted(roots.items()):
            # Original assigned object anchors class/cohort; later status is not a new object.
            original=min(group,key=lambda x:(x.get('assigned_at') or '9999',x.get('version',1),x['event_id']))
            if family=='project':
                prs=[x for x in data['project_records'] if x['subject_id']==s and x['period_id']==p and x.get('deliverable_id')==root]
                if not prs:
                    missing.append('missing_project_record:'+root);good[root]=False;ontime[root]=False;continue
                fields=('benefit_id','criteria_ref','criteria_agreed_at','acceptance_at','acceptance_owner','acceptance_ref',
                        'release_at','release_ref','usage_ref','usage_status','usage_observed_at','usage_owner','usage_coverage','usage_units','usage_measure','rollback')
                if any(len({json.dumps(x.get(f),sort_keys=True) for x in prs})>1 for f in fields):
                    missing.append('conflicting_root_evidence:'+root)
                pr=sorted(prs,key=lambda x:x['record_id'])[0]
                if len(benefit_roots[(p,pr.get('benefit_id'))])>1:missing.append('benefit_split_across_roots:'+str(pr.get('benefit_id')))
                if not pr.get('criteria_ref') or not pr.get('criteria_agreed_at') or day(pr['criteria_agreed_at'])>=day(rule['start']):
                    missing.append('prospective_root_criteria:'+root)
                for f in ('acceptance_at','acceptance_owner','acceptance_ref','release_at','release_ref','usage_ref','usage_observed_at','usage_owner'):
                    if not pr.get(f):missing.append('unconfirmed_'+f+':'+root)
                if pr.get('usage_status')!='present' or pr.get('usage_units') is None:
                    missing.append('unconfirmed_usage:'+root)
                if pr.get('acceptance_owner') in excluded or pr.get('usage_owner') in excluded:
                    missing.append('self_acceptance_or_usage:'+root)
                late=any(pr.get(f) and day(pr[f])>day(rule['end']) for f in ('acceptance_at','release_at'))
                mature=pr.get('usage_observed_at') and pr.get('release_at') and (day(pr['usage_observed_at'])-day(pr['release_at'])).days>=rule['outcome_followup_days']
                usage_ok=(pr.get('usage_measure')=='distinct_workflow_runs_at_deliverable_grain' and pr.get('usage_coverage')=='one_internal_process'
                          and pr.get('usage_units') is not None and pr['usage_units']>=spec['project_min_usage'])
                if not mature and not late:missing.append('project_followup_unconfirmed:'+root)
                if late:reasons.append('actual_acceptance_or_release_after_period:'+root)
                if pr.get('usage_observed_at') and day(pr['usage_observed_at'])>day(rule['quality_close']):
                    reasons.append('late_actual_usage_excluded:'+root);usage_ok=False
                good[root]=bool(pr.get('acceptance_at') and pr.get('release_at') and not late and mature and usage_ok and not pr.get('rollback'))
                ontime[root]=good[root]
                project_units.append(pr.get('usage_units'))
                units[root]=1
            else:
                eligible=(original.get('assigned_at') and day(original['assigned_at'])<=day(rule['end'])
                          and original.get('due_at') and day(original['due_at'])<=day(rule['end']))
                if not original.get('due_at'):missing.append('missing_due:'+root)
                if not eligible:
                    # Unknown assignment is retained in cohort pending; a known future due is deferred.
                    if original.get('assigned_at') and original.get('due_at'):continue
                os=[outcomes[x['case_id']] for x in group if x['case_id'] in outcomes]
                if not os:
                    missing.append('missing_outcome:'+root);good[root]=False;ontime[root]=False;continue
                if any(not x.get('observation_end') or day(x['observation_end'])<(day(original['event_at'])+timedelta(days=rule['outcome_followup_days'])) for x in os):
                    missing.append('immature_outcome:'+root)
                if any(x.get('accepted_by') in excluded for x in group):missing.append('self_acceptance:'+root)
                if family=='support':
                    good[root]=(all(x.get('resolved') and not x.get('transfer') and not x.get('repeat_of') for x in os)
                                and not any(x.get('reopen_of') or x.get('status')=='reopened' for x in group)
                                and any(x.get('accepted_at') and x.get('accepted_by') and day(x['accepted_at'])<=day(rule['end']) for x in group))
                else:
                    good[root]=all(x.get('accepted') and x.get('accepted_at') and day(x['accepted_at'])<=day(rule['end']) and not x.get('returned') for x in os)
                ontime[root]=good[root] and any(x.get('accepted_at') and original.get('due_at') and dt(x['accepted_at'])<=dt(original['due_at']) for x in os if x.get('accepted_at')) if family=='backoffice' else good[root]
                typ=original.get('type_id');cl=classes.get(typ)
                if not cl or cl['employee_editable'] or cl['complexity_owner'] in excluded or day(cl['approved_at'])>=day(rule['start']):
                    missing.append('unconfirmed_class:'+root);units[root]=0
                else:units[root]=cl['standard_units']
                if good[root]:per_type[typ]+=units[root]
        cohort_n=len(good)
        if family!='project' and cohort_n<spec['min_flow_roots']:exposure=False
        if family=='project' and cohort_n<1:exposure=False
        if q['status']=='missing':missing.append('incomplete_compatible_QA_root_census')
        quality_pass=q['status']=='pass'
        flow_sla=sum(ontime.values())/cohort_n if cohort_n else None
        if family=='backoffice' and flow_sla is not None and flow_sla<spec['backoffice_SLA_normal']:
            quality_pass=False;reasons.append('SLA_below_absolute_0.95')
        independent_intervals=[];unconfirmed_intervals=[]
        for x in data['capacity_intervals']:
            if x['subject_id']==s and x['period_id']==p:
                if x.get('source_ref') and x.get('recorded_by') not in excluded and x.get('approved_by') and x['approved_by'] not in excluded:
                    independent_intervals.append(x)
                else:unconfirmed_intervals.append(x['interval_id'])
        removed=union_hours(independent_intervals)
        if removed and (capacity['leave_hours'] or capacity['training_hours']):missing.append('exception_overlap_with_absence_dates_unknown')
        available=(capacity['scheduled_hours']-capacity['leave_hours']-capacity['training_hours']-removed)*capacity['allocation_fraction']
        if capacity.get('capacity_owner') in excluded or day(capacity['registered_at'])>=day(rule['start']):missing.append('capacity_not_independent_prospective')
        stratum_ratios={}
        if spec['mechanism']=='capacity':
            numerator=sum(units.get(root,0) for root,v in good.items() if v)
            denominator=available*sum(x['capacity_share']*x['standard_units_per_hour'] for x in rule['stratum_allocations'])
            if denominator<=0:missing.append('no_independent_positive_capacity')
            if family=='project':
                numerator=sum(good.values());denominator=None
                missing.append('root_scope_capacity_standard_absent_IT_DEL_is_task_class')
            else:
                allocated={x['type_id'] for x in rule['stratum_allocations']}
                if set(per_type)-allocated:missing.append('unallocated_stratum')
                for a in rule['stratum_allocations']:
                    den=available*a['capacity_share']*a['standard_units_per_hour']
                    stratum_ratios[a['type_id']]=per_type.get(a['type_id'],0)/den if den>0 else 0
                value=numerator/denominator if denominator and denominator>0 else None
                normal=value is not None and value>=spec['normal'] and min(stratum_ratios.values(),default=0)>=spec['stratum_normal_floor']
                stretch=value is not None and value>=spec['stretch'] and min(stratum_ratios.values(),default=0)>=1
            units_name='accepted_standard_work_units / expected_standard_work_units'
        else:
            numerator=sum(ontime.values()) if family=='backoffice' else sum(good.values())
            denominator=cohort_n
            value=numerator/denominator if denominator else None
            normal=value is not None and value>=spec['normal']
            stretch=value is not None and value>=spec['stretch']
            units_name='successful_unique_root_obligations / all_due_assigned_unique_root_obligations'
        data_status='sufficient';reward='earned';metric_state='normal'
        if not exposure:
            data_status='insufficient';reward='not_earned';metric_state='insufficient_exposure'
        elif any(kind=='known_gap' for kind,_ in mi):
            data_status='insufficient';reward='not_computable';metric_state='known_source_gap'
        elif mi:
            data_status='source_incident';reward='pending';metric_state='source_incident'
        elif missing:
            data_status='insufficient';reward='not_computable' if any('root_scope_capacity_standard_absent' in x for x in missing) else 'pending';metric_state='unconfirmed_source'
        elif not quality_pass:
            reward='not_earned';metric_state='quality_fail'
        elif not normal:
            reward='not_earned';metric_state='below_normal'
        normal=bool(normal and exposure and quality_pass and data_status=='sufficient')
        stretch=bool(stretch and normal)
        rank_value=float(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)) if value is not None else None
        regs=[x for x in data['comparison_registry'] if x['period_id']==p and x['subject_id']==s]
        if len(regs)!=1:raise ValueError('registry is not unique')
        reg=regs[0]
        r={'rule_version':spec['rule_version'],'family':family,'subject_id':s,'period_id':p,
           'group_id':reg['home_pool_id'],'window_id':reg['window_id'],'cohort_id':reg['cohort_id'],
           'numerator':numerator,'denominator':denominator,'units':units_name,'value':value,'rank_value':rank_value,
           'quality_scope':'team' if family=='project' else 'personal','quality_coverage':q['coverage'],
           'quality_required':q['required'],'quality_score':q['score'],'quality_status':q['status'],
           'active_days':capacity['active_days'],'exposure_pass':exposure,'data_status':data_status,
           'metric_state':metric_state,'normal':normal,'stretch':stretch,'reward_status':reward,
           'top_unit_R':0,'eligible_unit_people':len(members) if family=='project' else 1,
           'rank':None,'reason':';'.join(sorted(set(reasons+missing+[a+':'+b for a,b in mi]))),
           'signoff_status':'personal_ledger_check_required','approval_ref':'',
           'added_HR_minutes':0.5,'added_manager_minutes':1.5,'added_employee_minutes':0,
           'source_refs':f'roster_capacity#{capacity["capacity_id"]};period_rules#{rule["rule_id"]};work_events#{s}/{p};quality_acts#{s}/{p}',
           'right_date':rule['quality_close'],'date_basis':'synthetic calendar-quarter qualification example; personal15th-day window not observed'}
        out.append(r)
        cs=[x for x in data['support_outcomes'] if x['period_id']==p and x['subject_id']==s]
        detail.append({'subject_id':s,'period_id':p,'source_refs':r['source_refs'],
            'source_samples':e[:1], 'capacity_fields':capacity,'approval_evidence':[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id'] in excluded],'union_exception_hours':removed,
            'available_hours':available,'stratum_units':dict(per_type),'stratum_ratios':stratum_ratios,
            'cohort_roots':len(roots),'successful_roots':sum(good.values()),'ontime_roots':sum(ontime.values()),
            'unconfirmed_exception_requests':unconfirmed_intervals,'quality':q,
            'CSAT_diagnostic':{'eligible':len(cs),'invited':sum(x['invited'] for x in cs),
                              'responded':sum(x['responded'] for x in cs),'used_for_rank':False},
            'project_usage_once_per_root':project_units,'result':{k:r[k] for k in ('numerator','denominator','value','normal','stretch','metric_state')}})
    # Rank within predeclared comparable pools; never cross families. Slots stay fixed.
    groups=defaultdict(list)
    for r in out:groups[(r['period_id'],r['group_id'])].append(r)
    for group in groups.values():
        n=sum(x['eligible_unit_people'] for x in group)
        for r in group:r['top_pending']=any(x['exposure_pass'] and x['reward_status'] in ('pending','not_computable') for x in group)
        qualified=sorted([r for r in group if r['stretch']],key=lambda x:(-x['rank_value'],x['subject_id']))
        if len(group)<2:continue
        pos=0
        while pos<len(qualified):
            ties=[x for x in qualified[pos:] if x['rank_value']==qualified[pos]['rank_value']]
            slots=spec['top_shares'][pos:pos+len(ties)]
            shared=Decimal(str(spec['top_R_per_person']*n))*sum((Decimal(str(x)) for x in slots),Decimal(0))/len(ties)
            for r in ties:r['top_unit_R']=float(shared);r['rank']=pos+1
            pos+=len(ties)
    # Project outcome is copied into personal eligibility, but team money is divided once.
    persons=[]
    for r in out:
        if r['family']=='project':
            memberships=[m for m in data['team_members'] if m['period_id']==r['period_id'] and m['team_id']==r['subject_id']]
            if sum(m['contribution_share'] for m in memberships)>1+1e-12:raise ValueError('team contribution exceeds 1')
            for m in memberships:
                a=copy.deepcopy(r);a['unit_id']=r['subject_id'];a['subject_id']=m['employee_id'];a['share']=m['contribution_share']
                a['window_id']=m['window_id'];a['cohort_id']=m['cohort_id']
                personal_ok=(m['personal_active_days']>=spec['min_active_days'] and m['approved_by'] not in {m['employee_id'],m['team_id']}
                             and day(m['approved_at'])<day(next(x['start'] for x in data['period_rules'] if x['period_id']==r['period_id'] and x['family']=='project')))
                if not personal_ok:
                    a['exposure_pass']=False;a['normal']=False;a['stretch']=False;a['data_status']='insufficient';a['reward_status']='not_earned';a['metric_state']='insufficient_personal_exposure'
                state,ref=signoff(data,r['period_id'],m['employee_id'],[x['employee_id'] for x in memberships])
                a['signoff_status']=state;a['approval_ref']=ref or '';a['top_R']=int((Decimal(str(r['top_unit_R']))*Decimal(str(m['contribution_share']))).to_integral_value(rounding=ROUND_FLOOR)) if personal_ok else 0
                persons.append(a)
        else:
            a=copy.deepcopy(r);a['unit_id']=r['subject_id'];a['share']=1
            state,ref=signoff(data,r['period_id'],r['subject_id']);a['signoff_status']=state;a['approval_ref']=ref or ''
            a['top_R']=int(Decimal(str(r['top_unit_R'])).to_integral_value(rounding=ROUND_FLOOR));persons.append(a)
    if len({(a['period_id'],a['subject_id']) for a in persons})!=len(persons):
        raise ValueError('person registered in multiple home pools in one period')
    # Fixed two-quarter personal window, no floating retry on transfer.
    windows=defaultdict(list)
    for a in persons:windows[(a['subject_id'],a['window_id'])].append(a)
    money=[]
    for (person,window),rows in sorted(windows.items()):
        rows.sort(key=lambda x:x['period_id'])
        if len({x['cohort_id'] for x in rows})!=1:raise ValueError('personal cohort changed')
        passed=len(rows)==2 and len({x['period_id'] for x in rows})==2 and all(x['normal'] for x in rows)
        blocked=any(x['reward_status'] in ('pending','not_computable') for x in rows)
        # Guaranteed actual failure/exposure dominates an unresolved other quarter.
        failed=any(x['reward_status']=='not_earned' for x in rows)
        window_status='earned' if passed else ('not_earned' if failed else ('not_computable' if any(x['reward_status']=='not_computable' for x in rows) else 'pending'))
        g=spec['guarantee_R'] if passed else 0
        for a in rows:
            a['window_guarantee_status']=window_status;a['window_guarantee_R']=g
            a['eligibility']=a['reward_status']
            if a['normal'] and a['signoff_status']!='signed':a['reward_status']='pending'
            a['posting_status']='ready' if a['signoff_status']=='signed' and a['normal'] else 'held'
            money.append({'subject_id':person,'family':a['family'],'period_id':a['period_id'],'window_id':window,
                'cohort_id':a['cohort_id'],'unit_id':a['unit_id'],'share':a['share'],'rank':a['rank'],
                'top_unit_R':a['top_unit_R'],'top_R':a['top_R'],'top_status':'pending_group_evidence' if a['top_pending'] else ('earned' if a['top_R'] else 'not_earned'),'guarantee_R':g if a is rows[-1] else 0,
                'right_date':a['right_date'],'date_basis':a['date_basis'],'guarantee_right_date':rows[-1]['right_date'],
                'window_status':window_status,'posting_status':a['posting_status'],
                'approved_top_U_R':a['top_R'] if a['posting_status']=='ready' and not a['top_pending'] else 0,
                'approved_G_U_R':g if a is rows[-1] and all(x['signoff_status']=='signed' for x in rows) else 0,
                'signature':a['signoff_status'],'pending_amount_R':(a['top_R'] if a['posting_status']!='ready' or a['top_pending'] else 0)+(g if a is rows[-1] and not all(x['signoff_status']=='signed' for x in rows) else 0),
                'certificate_nominal_RUB_from_G':g/5,'R_to_C':1,'double_redemption':False})
    return sorted(persons,key=lambda x:(x['period_id'],x['family'],x['subject_id'])),money,detail

def read_scenarios():
    module_spec=importlib.util.spec_from_file_location('public_fixture_reader',FIXTURE/'source/reader.py')
    reader=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(reader)
    index=json.loads((FIXTURE/'source/scenario_index.json').read_text())
    names=['base']+[x['scenario_id']+'.'+v for x in index for v in x['variants']]
    return reader,names

def write_csv(path, rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scenario');ap.add_argument('--out-dir',type=Path,default=HERE)
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    spec=json.loads((HERE/'metrics-spec.json').read_text());reader,names=read_scenarios()
    if args.scenario:names=[args.scenario]
    decisions=[];money=[];traces=[]
    for name in names:
        data=reader.expand_scenario(name)
        rows,m,details=evaluate(data,spec)
        decisions += [dict(candidate_key=spec['candidate_key'],scenario=name,**r) for r in rows]
        money += [dict(candidate_key=spec['candidate_key'],scenario=name,**r) for r in m]
        # Full intermediate scalar summaries but only one example event per unit.
        traces += [dict(candidate_key=spec['candidate_key'],scenario=name,**d) for d in details if name=='base' or d['period_id']==min(x['period_id'] for x in details)]
    write_csv(args.out_dir/'decisions.csv',decisions);write_csv(args.out_dir/'money-examples.csv',money)
    (args.out_dir/'traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'candidate':spec['candidate_key'],'scenarios':len(names),'decisions':len(decisions),
                      'states':dict(Counter(x['reward_status'] for x in decisions))},ensure_ascii=False))
if __name__=='__main__':main()
