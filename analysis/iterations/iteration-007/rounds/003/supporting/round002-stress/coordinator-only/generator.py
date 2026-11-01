#!/usr/bin/env python3
"""Preparation only. Deterministic primitive fixtures; no recognition calculations."""
import argparse
import calendar
import copy
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
STAMP = '2026-11-01T12:00:00+03:00'
VERSION = 'OTP-SYN-007-R002-v1'
PK = {'period_rules':'rule_id','roster_capacity':'capacity_id','comparison_registry':'registry_id',
      'team_members':'membership_id','classifier':'class_id','work_events':'event_id',
      'support_outcomes':'outcome_id','process_outcomes':'outcome_id','project_records':'record_id',
      'quality_acts':'act_id','worklog':'worklog_id','approvals_audit':'approval_id',
      'capacity_intervals':'interval_id','resource_assumptions':'activity_id',
      'batch_metadata':'batch_id','source_receipts':'receipt_id','personal_windows':'window_id'}

def encoded(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

def sha(x):
    return hashlib.sha256(encoded(x)).hexdigest()

def ts(day, clock='12:00:00'):
    return str(day)+'T'+clock+'+03:00'

def month(day, n):
    y, m = divmod(day.year*12+day.month-1+n, 12)
    return date(y,m+1,min(day.day,calendar.monthrange(y,m+1)[1]))

def row_for(old,table,**keys):
    return copy.deepcopy(next(r for r in old[table] if all(r.get(k)==v for k,v in keys.items())))

def manifests(data, locator):
    rows=[]
    periods=[r['period_id'] for r in data['period_rules']]
    periods=list(dict.fromkeys(periods))
    for table, values in data.items():
        if table=='source_manifest': continue
        has_period=any('period_id' in r for r in values)
        for period in periods:
            part=[r for r in values if r.get('period_id')==period] if has_period else values
            rows.append(dict(partition_id=f'{table}:{period}',table=table,period_id=period,
                partition_ref=f'{locator}#{table}/{period}',source_version=VERSION,
                generated_at=STAMP,expected_count=len(part),received_count=len(part),
                received_sha256=sha(part),availability='available',expected_before_start=True,
                readiness_at='2025-12-15',missing_reason=None))
    data['source_manifest']=rows

def audit(subject,period,team=None,role='worker',signed='2026-04-28'):
    return dict(approval_id=f'{period}:{subject}',period_id=period,beneficiary_id=subject,
        beneficiary_role=role,beneficiary_team=team,initiator_id=subject,
        input_editor_id='DATA-EDITOR-R2',signer_id='SOURCE-SIGNER-R2',operator_id='OPS-R2',
        signer_reporting_to=None,operator_reporting_to=None,
        alternate_signer_id='ALT-SIGNER-R2',alternate_operator_id='ALT-OPS-R2',
        appeal_owner_id='APPEAL-R2',signed_at=ts(signed,'10:00:00'),
        action='source_completeness_review',source_ref=f'{period}:{subject}',
        before=VERSION,after=VERSION,reason='source_register_review',version=1)

def batch(data,period,close):
    roster=[r for r in data['comparison_registry'] if r['period_id']==period]
    members=[r for r in data['team_members'] if r['period_id']==period]
    refs=[r['approval_id'] for r in data['approvals_audit'] if r['period_id']==period]
    return dict(batch_id=f'BATCH:{period}',period_id=period,source_version=VERSION,
        roster_ref=f'comparison_registry#{period}',team_members_ref=f'team_members#{period}',
        roster_sha256=sha(roster),team_members_sha256=sha(members),
        roster_count=len(roster),team_member_count=len(members),approval_refs=refs,
        exception_refs=[],input_editor_id='BATCH-EDITOR-R2',signer_id='BATCH-SIGNER-R2',
        operator_id='BATCH-OPS-R2',signed_at=ts(close,'11:00:00'),version=1,
        source_ref=f'synthetic-signed-composition/{period}')

def empty(old):
    return {k:[] for k in old if k!='source_manifest'} | {'batch_metadata':[], 'source_receipts':[], 'personal_windows':[]}

def build_full(old,equal=False):
    d=empty(old)
    d['classifier']=copy.deepcopy(old['classifier'])
    d['resource_assumptions']=copy.deepcopy(old['resource_assumptions'])
    for p,start,end,close in [('P1','2026-01-01','2026-03-31','2026-04-28'),('P2','2026-04-01','2026-06-30','2026-07-28')]:
        for family in ['support','backoffice','project']:
            r=row_for(old,'period_rules',period_id=p,family=family)
            r.update(rule_version='source-rule-R2-1',comparison_group_id='R2-G-'+family,
                     registry_frozen_at='2025-12-15T18:00:00+03:00',source_ref='synthetic-prospective-capacity-plan-v1')
            if family=='backoffice':
                r['stratum_allocations']=[dict(type_id='B-C3',capacity_share=3/8,mix_weight=3/8,standard_units_per_hour=1),
                                           dict(type_id='B-C5',capacity_share=5/8,mix_weight=5/8,standard_units_per_hour=1)]
            d['period_rules'].append(r)
        for family,prefix,n in [('support','S',40),('backoffice','B',40),('project','T',8)]:
            for i in range(1,n+1):
                subject=f'{prefix}{i:02}'
                group=(i-1)//(10 if n==40 else 2)
                count=20 if equal else [18,20,22,24][group]
                base_subject=prefix+'01'
                cap=row_for(old,'roster_capacity',period_id=p,subject_id=base_subject)
                cap.update(capacity_id=f'{p}:{subject}',subject_id=subject,
                           scheduled_hours=2400 if family=='project' else 480,
                           fte=5 if family=='project' else 1,
                           allocation_fraction={'support':.25,'backoffice':1/3,'project':.5}[family],
                           schedule_version='roster-R2-1',registered_at='2025-12-15')
                d['roster_capacity'].append(cap)
                reg=row_for(old,'comparison_registry',period_id=p,subject_id=base_subject)
                reg.update(registry_id=f'{p}:{subject}',subject_id=subject,
                           comparison_group_id='R2-G-'+family,home_pool_id='R2-G-'+family)
                d['comparison_registry'].append(reg)
                d['approvals_audit'].append(audit(subject,p,subject if family=='project' else None,
                                                  'team' if family=='project' else 'worker',close))
                log=row_for(old,'worklog',period_id=p,subject_id=base_subject)
                log.update(worklog_id=f'{p}:{subject}:1',subject_id=subject,
                           hours={'support':120,'backoffice':160,'project':1200}[family])
                d['worklog'].append(log)
                if family=='project':
                    for j in range(1,6):
                        employee=f'P{(i-1)*5+j:03}'
                        tm=row_for(old,'team_members',period_id=p,employee_id='P01')
                        tm.update(membership_id=f'{p}:{employee}',employee_id=employee,team_id=subject,
                                  fte=1,contribution_share=.2,role='manager' if j==1 else 'engineer')
                        d['team_members'].append(tm)
                        d['approvals_audit'].append(audit(employee,p,subject,tm['role'],close))
                    n_events=2
                else: n_events=count*2
                for j in range(1,n_events+1):
                    case=f'{p}-{subject}-{j:03}'
                    day=date.fromisoformat(start)+timedelta(days=20+j)
                    if family=='project': day=date.fromisoformat(end)-timedelta(days=10)
                    event=row_for(old,'work_events',period_id=p,subject_id=base_subject)
                    root=f'{p}-{subject}-ROOT' if family=='project' else case
                    type_id=('IT-DEL' if family=='project' else
                             ('S-C2' if j%2 else 'S-C4') if family=='support' else
                             ('B-C3' if j%2 else 'B-C5'))
                    event.update(event_id=f'EV-{case}-1',case_id=case,source_record_id=case,
                        subject_id=subject,root_id=root,parent_id=root if family=='project' else None,
                        type_id=type_id,event_at=ts(day,'16:00:00'),accepted_at=ts(day,'17:00:00'),
                        assigned_at=ts(date.fromisoformat(start),'09:00:00'),due_at=ts(day,'18:00:00'))
                    d['work_events'].append(event)
                    qa=row_for(old,'quality_acts',period_id=p,subject_id=base_subject)
                    qa.update(act_id='QA-'+case,inspection_id='INSP-'+case,case_id=case,
                        event_id=event['event_id'],subject_id=subject,score=98 if j%2 else 100,
                        minor=1 if j%2 else 0,major=0,critical=0,observation_start=str(day))
                    if family=='project': qa.update(scope='team',coverage_object='one_distinct_case')
                    d['quality_acts'].append(qa)
                    if family=='support':
                        r=row_for(old,'support_outcomes',period_id=p,subject_id=base_subject)
                        r.update(outcome_id='SO-'+case,subject_id=subject,case_id=case,csat_at=ts(day,'18:00:00'))
                        d['support_outcomes'].append(r)
                    elif family=='backoffice':
                        r=row_for(old,'process_outcomes',period_id=p,subject_id=base_subject)
                        r.update(outcome_id='BO-'+case,subject_id=subject,case_id=case,
                                 accepted_at=event['accepted_at'],sla_due_at=event['due_at'])
                        d['process_outcomes'].append(r)
                    else:
                        r=row_for(old,'project_records',period_id=p,subject_id=base_subject)
                        r.update(record_id='PR-'+case,case_id=case,subject_id=subject,
                                 deliverable_id=root,parent_id=root,benefit_id=root,
                                 criteria_ref=f'CFG-WORKFLOW-{p}-v1',criteria_agreed_at='2025-12-01',
                                 acceptance_at=ts(day,'17:00:00'),acceptance_owner='ACCEPT-OWNER-R2',
                                 acceptance_ref='ACCEPT-'+root,release_at=ts(day,'18:00:00'),
                                 release_ref='RELEASE-'+root,usage_units=100 if equal else [80,100,120,180][group],
                                 usage_owner='USE-OWNER-R2',usage_ref='USE-'+root,usage_observed_at=ts(end,'18:00:00'))
                        d['project_records'].append(r)
        d['batch_metadata'].append(batch(d,p,close))
    manifests(d,'source/R1.json')
    return d

def configs():
    rows=[]
    for p,start,end in [('P1','2026-01-01','2026-03-31'),('P2','2026-04-01','2026-06-30')]:
        for family,target,unit in [('support',120,'standard_work_unit'),('backoffice',160,'standard_work_unit'),('project',100,'distinct_workflow_runs_at_deliverable_grain')]:
            project=family=='project'
            rows.append(dict(config_id=f'CFG-WORKFLOW-{p}' if project else f'CFG-{family.upper()}-{p}',
                version=1,comparison_group_id='R2-G-'+family,root_scope='all_assigned_roots_in_period',
                valid_from=start,valid_to=end,work_type='workflow' if project else family,
                unit=unit,target_value=target,baseline_value=None,direction='higher',
                target_basis='prospective_process_plan_requires_100_distinct_runs' if project else 'prospective_capacity_and_stratum_engineering_plan',
                owner='BUSINESS-OWNER-R2',approved_at='2025-12-01T10:00:00+03:00',
                acceptance_criteria=['independent_acceptance_ref','all_assigned_obligations_in_scope'],
                use_criteria=['independent_usage_ref_at_root_grain'] if project else ['accepted_unique_cases'],
                business_deadline=ts(end,'18:00:00'),maturity_end=str(date.fromisoformat(end)+timedelta(days=28)),
                source_query=dict(tables=['work_events','project_records'] if project else ['work_events','roster_capacity','classifier'],
                                  period_id=p,join=['subject_id','period_id','root_id'],scope='all_assignments_not_self_selected'),
                comparison_rule='same_family_period_engineering_mix_and_prospective_capacity',
                qa=dict(criterion='defect_penalty',scale='0..100',scale_version='penalty-v1',precision_points=1,
                        substantive_difference_points=1,unit='quality_points',minor_penalty=2,major_penalty=10,critical_penalty=100)))
        deadline=date.fromisoformat(end)-timedelta(days=4)
        prep=date.fromisoformat(end)-timedelta(days=11)
        rows.append(dict(config_id=f'CFG-ANALYTICAL-{p}',version=1,comparison_group_id='R2-G-project',
            root_scope='one_analytical_package_for_one_named_business_decision_per_team',
            valid_from=start,valid_to=end,work_type='analytical_business_decision_package',
            unit='distinct_business_decisions_using_deliverable',target_value=1,baseline_value=0,direction='binary_completion',
            target_basis='one_pre_scheduled_committee_decision_requires_a_checked_analytical_package',
            owner='BUSINESS-OWNER-R2',approved_at='2025-12-01T10:00:00+03:00',
            acceptance_criteria=['independent_acceptance_ref','reconciled_assumptions_and_sensitivity_in_package'],
            use_criteria=['independent_minutes_of_one_named_decision_using_package'],
            business_deadline=ts(deadline,'12:00:00'),maturity_end=str(date.fromisoformat(end)+timedelta(days=28)),
            readiness_criterion=dict(ready_by=ts(prep,'12:00:00'),
                rationale='committee_pre_read_and_one_scheduled_validation_cycle_before_decision',
                further_earliness_benefit='none_assumed',source_fields=['acceptance_at','release_at','usage_observed_at']),
            source_query=dict(tables=['work_events','project_records','quality_acts'],period_id=p,
                              join=['subject_id','period_id','case_id','deliverable_id'],scope='all_assigned_roots'),
            comparison_rule='analytical_type_only_same_decision_pre_read_calendar_and_team_capacity',
            qa=copy.deepcopy(rows[-1]['qa'])))
        conflict=copy.deepcopy(rows[-1]); conflict.update(version=2,approved_at=ts(date.fromisoformat(start)+timedelta(days=20)),
            business_deadline=ts(date.fromisoformat(end)+timedelta(days=5),'12:00:00'),
            change_reason='deadline_relaxed_after_period_start',supersedes_version=1)
        rows.append(conflict)
    # Addendum requirements can also be queried against old, unchanged source groups.
    # These are prospective synthetic assumptions for this comparison, not amendments
    # to the historical rules of an incumbent concept.
    for row in list(rows):
        if row['work_type'] not in ['support','backoffice','workflow']:continue
        legacy=copy.deepcopy(row)
        legacy.update(config_id=row['config_id'].replace('CFG-','CFG-LEGACY-',1),
                      comparison_group_id=row['comparison_group_id'].replace('R2-G-','G-'),
                      application_scope='round002_prospective_common_assumption_only',
                      does_not_amend_legacy_source_rule=True)
        if row['work_type']=='support':legacy['target_value']=108
        if row['work_type']=='backoffice':legacy['target_value']=80
        rows.append(legacy)
    return dict(version=VERSION,synthetic_only=True,generated_at=STAMP,configs=rows)

def analytical(d,config):
    out=copy.deepcopy(d)
    for r in out['project_records']:
        p=r['period_id']; i=int(r['subject_id'][1:]); c=next(c for c in config['configs'] if c['config_id']==f'CFG-ANALYTICAL-{p}' and c['version']==1)
        prep=datetime.fromisoformat(c['readiness_criterion']['ready_by'])
        offset=[-1,0,0,1,2,3,13,14][i-1]
        ready=prep+timedelta(days=offset)
        r.update(criteria_ref=c['config_id']+'-v1',acceptance_at=ready.isoformat(),
                 release_at=ready.isoformat(),usage_measure='distinct_business_decisions_using_deliverable',
                 usage_units=0 if i==8 else 1,usage_coverage='one_named_business_decision',
                 usage_observed_at=(max(datetime.fromisoformat(c['business_deadline']),ready)+timedelta(minutes=30)).isoformat(),
                 acceptance_ref='AN-ACCEPT-'+r['deliverable_id'],usage_ref='DECISION-MINUTES-'+r['deliverable_id'])
        event=next(e for e in out['work_events'] if e['case_id']==r['case_id'])
        event.update(accepted_at=r['acceptance_at'],event_at=r['release_at'],due_at=c['business_deadline'])
        qa=next(q for q in out['quality_acts'] if q['case_id']==r['case_id'])
        qa.update(observation_start=r['acceptance_at'][:10],checked_at=r['acceptance_at'])
    return out

def build_windows(old):
    d=empty(old); d['classifier']=copy.deepcopy(old['classifier']); d['resource_assumptions']=copy.deepcopy(old['resource_assumptions'])
    for i in range(1,10):
        subject=f'CW{i:02}'; first=date(2026,i,15); annual_end=month(first,12)-timedelta(days=1)
        window=f'W-C{i:02}-2026'; cohort=f'C{i:02}'
        d['personal_windows'].append(dict(window_id=window,cohort_id=cohort,subject_id=subject,start=str(first),
            end=str(annual_end),quarter_start_month_offsets=[0,3,6,9],boundary_rule='start_inclusive_next_start_exclusive',
            approved_at='2025-12-01T10:00:00+03:00',owner='CALENDAR-OWNER-R2',timezone='Europe/Moscow'))
        hire=first+timedelta(days=10) if i==8 else date(2024,1,1)
        transfer=month(first,3)+timedelta(days=10) if i==9 else None
        for q in [1,2]:
            start=month(first,3*(q-1)); next_start=month(start,3); end=next_start-timedelta(days=1); close=end+timedelta(days=28)
            p=f'C{i:02}Q{q}'
            rule=row_for(old,'period_rules',period_id='P1',family='support')
            rule.update(rule_id=p+':support',period_id=p,start=str(start),end=str(end),quality_close=str(close),quality_close_at=ts(close,'12:00:00'),
                annual_window_start=str(first),annual_window_end=str(annual_end),window_id=window,
                comparison_group_id='R4-'+cohort,registry_frozen_at='2025-12-15T18:00:00+03:00',
                rule_version='personal-source-R2-1',source_ref='synthetic-personal-calendar-v1')
            d['period_rules'].append(rule)
            cap=row_for(old,'roster_capacity',period_id='P1',subject_id='S01')
            cap.update(capacity_id=p+':'+subject,period_id=p,subject_id=subject,hire_date=str(hire),
                       transfer_date=str(transfer) if transfer else None,allocation_fraction=.25,
                       effective_from=str(max(start,hire,transfer if q==2 and transfer else start)),
                       effective_to=str(end),schedule_version='personal-roster-R2-1')
            if i==8 and q==1: cap.update(scheduled_hours=400,active_days=50)
            if i==9 and q==2: cap.update(scheduled_hours=400,active_days=50)
            d['roster_capacity'].append(cap)
            reg=row_for(old,'comparison_registry',period_id='P1',subject_id='S01')
            reg.update(registry_id=p+':'+subject,period_id=p,subject_id=subject,cohort_id=cohort,
                       window_id=window,comparison_group_id='R4-'+cohort,home_pool_id='R4-support')
            d['comparison_registry'].append(reg)
            d['approvals_audit'].append(audit(subject,p,signed=str(close+timedelta(days=2))))
            # Edge records retain exact event timestamps; an extract partition is not an interval verdict.
            stamps=[ts(start-timedelta(days=1),'23:59:59'),ts(start,'00:00:00'),ts(start,'00:00:01'),
                    ts(end,'23:59:59'),ts(next_start,'00:00:00'),ts(next_start,'00:00:01'),
                    ts(end-timedelta(days=3),'12:00:00'),ts(end-timedelta(days=2),'12:00:00'),ts(end-timedelta(days=1),'12:00:00')]
            for j,event_at in enumerate(stamps,1):
                case=f'{p}-{subject}-{j:03}'; instant=datetime.fromisoformat(event_at)
                ev=row_for(old,'work_events',period_id='P1',subject_id='S01')
                accepted=instant
                if j>=7: accepted=datetime.fromisoformat(ts(close,'12:00:00'))+timedelta(seconds=j-8)
                ev.update(period_id=p,subject_id=subject,event_id='EV-'+case,case_id=case,root_id=case,source_record_id=case,
                    event_at=event_at,accepted_at=accepted.isoformat(),assigned_at=ts(start-timedelta(days=10),'09:00:00'),
                    due_at=ts(end,'23:59:59'),type_id='S-C2')
                d['work_events'].append(ev)
                so=row_for(old,'support_outcomes',period_id='P1',subject_id='S01')
                so.update(period_id=p,subject_id=subject,outcome_id='SO-'+case,case_id=case,
                          csat_at=accepted.isoformat(),observation_end=str(close))
                d['support_outcomes'].append(so)
                qa=row_for(old,'quality_acts',period_id='P1',subject_id='S01')
                finalized=datetime.fromisoformat(ts(close,'12:00:00'))
                if j>=7: finalized+=timedelta(seconds=j-8)
                qa.update(period_id=p,subject_id=subject,act_id='QA-'+case,inspection_id='INSP-'+case,
                    case_id=case,event_id=ev['event_id'],score=100,minor=0,
                    checked_at=accepted.isoformat(),finalized_at=finalized.isoformat(),
                    observation_start=event_at[:10],observation_end=str(close))
                if j==7:
                    qa.update(evidence_status='unavailable_in_received_extract',score=None,minor=None,major=None,critical=None)
                d['quality_acts'].append(qa)
                received=finalized+timedelta(minutes=5)
                # Timely act delivered after close vs an act genuinely finalized after close.
                if j==7: received=finalized+timedelta(days=2)
                d['source_receipts'].append(dict(receipt_id='RECEIPT-'+case,period_id=p,subject_id=subject,
                    source_table='quality_acts',source_key={'act_id':qa['act_id']},source_version=1,
                    original_finalized_at=qa['finalized_at'],received_at=received.isoformat(),
                    delivery_status='lost_in_transit' if j==7 else 'received',
                    received_sha256=None if j==7 else sha(qa),source_ref='signed-QA/'+qa['act_id']))
            d['batch_metadata'].append(batch(d,p,str(close+timedelta(days=2))))
    manifests(d,'source/R4.json')
    return d

def diff(a,b):
    ops=[];orders=[]
    for table in a:
        pk='partition_id' if table=='source_manifest' else PK[table]
        left={r[pk]:r for r in a[table]}; right={r[pk]:r for r in b[table]}
        for key in left.keys()-right.keys(): ops.append(dict(table=table,grain=pk,key={pk:key},op='delete'))
        for key,row in right.items():
            if key not in left: ops.append(dict(table=table,grain=pk,key={pk:key},op='insert',row=row))
            elif row!=left[key]:
                ops.append(dict(table=table,grain=pk,key={pk:key},op='update',set={k:v for k,v in row.items() if left[key].get(k)!=v}))
        if list(left)!=list(right):orders.append(dict(table=table,grain=pk,key={},op='reorder',keys=list(right)))
    return sorted(ops,key=lambda x:(x['table'],str(x['key']),x['op']))+orders

def prepare(old):
    files={}; full=build_full(old); window=build_windows(old); config=configs()
    files['source/R1.json']=full; files['source/R4.json']=window; files['business-config.json']=config
    index=[]
    def add(name,data,base=full,source='source/R1.json',direct=False):
        entry=dict(name=name,source='addendum',source_ref=source,baseline='R1.volume' if source.endswith('R1.json') else 'R4.boundaries',
                   alternative_snapshot=True)
        if not direct:
            manifests(data,source)
            if name=='R2.incomplete_root':
                partition=next(r for r in data['source_manifest'] if r['partition_id']=='quality_acts:P1')
                partition.update(expected_count=partition['received_count']+1,availability='partial',missing_reason='one_expected_case_act_absent')
            entry['patch_ref']='patches/'+name+'.json'
            files[entry['patch_ref']]=dict(name=name,operations=diff(base,data))
        index.append(entry)
    add('R1.volume',full,direct=True)
    add('R1.truly_equal',build_full(old,True))
    # All underlying volume/capacity in R2 remains that of R1.volume.
    quality=copy.deepcopy(full)
    for r in quality['quality_acts']:
        i=int(r['subject_id'][1:]); group=(i-1)//(10 if r['subject_id'][0]!='T' else 2)
        if group==0: r.update(score=98,minor=1)
        elif group>=2: r.update(score=100,minor=0)
    add('R2.quality',quality)
    precision=copy.deepcopy(quality)
    next(r for r in precision['quality_acts'] if r['act_id']=='QA-P1-S11-001').update(score=100,minor=0)
    add('R2.precision',precision)
    foreign=copy.deepcopy(full)
    for r in foreign['quality_acts']:
        if r['subject_id']=='S01': r.update(criterion='communication',scale_version='communication-v2',score=97,minor=None,major=None,critical=None)
    add('R2.foreign_scale',foreign)
    csat=copy.deepcopy(full)
    n=Counter()
    for r in csat['support_outcomes']:
        if r['subject_id']=='S01':
            k=r['period_id'];n[k]+=1
            if n[k]>3:r.update(responded=False,csat_score=None,csat_at=None)
    add('R2.small_csat',csat)
    incomplete=copy.deepcopy(full)
    incomplete['quality_acts']=[r for r in incomplete['quality_acts'] if r['act_id']!='QA-P1-T01-002']
    add('R2.incomplete_root',incomplete)
    analytical_data=analytical(full,config)
    add('R3.analytical',analytical_data)
    unconfirmed=copy.deepcopy(analytical_data)
    for r in unconfirmed['project_records']:
        if r['subject_id']=='T01':r.update(acceptance_ref=None,acceptance_at=None,usage_ref=None,usage_status='missing',usage_observed_at=None)
    for r in unconfirmed['work_events']:
        if r['subject_id']=='T01':r.update(accepted_at=None,accepted_by=None)
    add('R3.unconfirmed',unconfirmed)
    conflict=copy.deepcopy(analytical_data)
    for r in conflict['project_records']:
        if r['subject_id']=='T07':r.update(criteria_ref=f"CFG-ANALYTICAL-{r['period_id']}-v2",criteria_agreed_at='2026-01-21' if r['period_id']=='P1' else '2026-04-21')
    add('R3.conflicting_goal',conflict)
    missing=copy.deepcopy(full);missing['approvals_audit'][0]['signed_at']=None
    add('R1.missing_signature',missing)
    conflicting=copy.deepcopy(full)
    next(r for r in conflicting['approvals_audit'] if r['beneficiary_id']=='P001').update(signer_id='P002',signer_reporting_to='P001')
    add('R1.conflicted_signature',conflicting)
    tampered=copy.deepcopy(full);tampered['comparison_registry'][0]['home_pool_id']='R2-G-backoffice'
    edit=audit('S01','P1',signed='2026-04-28')
    edit.update(approval_id='REGISTRY-EDIT:P1:S01',action='registry_input_change',
                signed_at='2026-04-28T12:00:00+03:00',source_ref='comparison_registry#P1:S01',
                before='home_pool_id=R2-G-support',after='home_pool_id=R2-G-backoffice',
                reason='source_change_after_batch_signed_at_11:00',version=2)
    tampered['approvals_audit'].append(edit)
    add('R1.batch_changed',tampered)
    add('R4.boundaries',window,base=window,source='source/R4.json',direct=True)
    restored=copy.deepcopy(window)
    for r in restored['source_receipts']:
        if r['delivery_status']=='lost_in_transit':
            qa=next(q for q in restored['quality_acts'] if q['act_id']==r['source_key']['act_id'])
            qa.update(evidence_status='present',score=100,minor=0,major=0,critical=0)
            r.update(delivery_status='restored',received_sha256=sha(qa))
    add('R4.restored',restored,base=window,source='source/R4.json')
    files['source/scenario_index.json']=index
    return files

def validate(full,name):
    # Structural assertions; selected destructive variants intentionally differ.
    for table,pk in PK.items():
        vals=[r[pk] for r in full[table]]
        assert len(vals)==len(set(vals)),(name,table,'duplicate')
    events={r['case_id']:r for r in full['work_events']}
    for table in ['quality_acts','support_outcomes','process_outcomes','project_records']:
        for r in full[table]:
            assert r['case_id'] in events,(name,table,'case')
            assert r['subject_id']==events[r['case_id']]['subject_id']
    for q in full['quality_acts']:
        assert q['event_id']==events[q['case_id']]['event_id']
        if q['scale_version']=='penalty-v1' and q['evidence_status']=='present':assert q['score']==max(0,100-2*q['minor']-10*q['major']-100*q['critical'])
    for r in full['source_manifest']:
        rows=full[r['table']]
        has_period=any('period_id' in z for z in rows)
        part=[z for z in rows if z.get('period_id')==r['period_id']] if has_period else rows
        assert r['received_count']==len(part) and r['expected_count']>=len(part)
        if r['availability']=='available':assert r['expected_count']==len(part)
        assert r['received_sha256']==sha(part),(name,r['partition_id'])
    return dict(name=name,counts={k:len(v) for k,v in full.items()},pk_unique=True,case_refs_valid=True,partition_hashes_valid=True,compatible_penalties_consistent=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--old-fixture-root',required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    oldroot=Path(a.old_fixture_root).resolve();old=json.loads((oldroot/'source/base.json').read_text())
    result=prepare(old);again=prepare(old)
    assert encoded(result)==encoded(again),'nondeterministic generation'
    for path,value in result.items():
        dest=ROOT/path
        if a.verify: assert dest.read_bytes()==encoded(value),str(dest)
        else: dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(encoded(value))
    spec=importlib.util.spec_from_file_location('public_reader',ROOT/'reader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    reports=[]
    for entry in result['source/scenario_index.json']:
        reports.append(validate(m.expand_scenario(entry['name'],oldroot),entry['name']))
    full=result['source/R1.json']
    assert len(full['comparison_registry'])==176 and len(full['team_members'])==80
    beneficiaries={r['subject_id'] for r in full['comparison_registry']}|{r['employee_id'] for r in full['team_members']}
    for r in full['approvals_audit']:
        assert r['signed_at'] and len({r['input_editor_id'],r['signer_id'],r['operator_id']})==3
        assert not ({r['input_editor_id'],r['signer_id'],r['operator_id']}&beneficiaries)
    for p in ['P1','P2']:
        people={r['subject_id'] for r in full['comparison_registry'] if r['period_id']==p}|{r['employee_id'] for r in full['team_members'] if r['period_id']==p}
        assert people=={r['beneficiary_id'] for r in full['approvals_audit'] if r['period_id']==p}
        for i in range(1,9):
            members=[r for r in full['team_members'] if r['period_id']==p and r['team_id']==f'T{i:02}']
            assert len(members)==5 and sum(r['contribution_share'] for r in members)==1
        for family in ['support','backoffice','project']:
            capacities=[r for r in full['roster_capacity'] if r['period_id']==p and r['family']==family]
            assert len({(r['scheduled_hours'],r['allocation_fraction'],r['fte'],r['leave_hours'],r['training_hours']) for r in capacities})==1
    for root in {r['deliverable_id'] for r in full['project_records']}:
        records=[r for r in full['project_records'] if r['deliverable_id']==root]
        assert len(records)==2 and len({r['acceptance_ref'] for r in records})==1 and len({r['usage_ref'] for r in records})==1
        assert len({q['inspection_id'] for q in full['quality_acts'] if q['case_id'] in {r['case_id'] for r in records}})==2
    assert len(result['source/R4.json']['personal_windows'])==9 and len(result['source/R4.json']['period_rules'])==18
    assert len(m.business_configs('G-support','P1','support'))==1
    assert len(m.business_configs('G-project','P1','workflow'))==1
    assert m.business_configs('G-project','P1','analytical_business_decision_package')==[]
    assert m.business_configs('R4-C01','C01Q1')==[]
    classes={r['type_id']:r['standard_units'] for r in full['classifier']}
    amounts=defaultdict(float);quality=defaultdict(list)
    for e in full['work_events']:
        if e['family']!='project':amounts[(e['period_id'],e['subject_id'])]+=classes[e['type_id']]
    for q in full['quality_acts']:quality[(q['period_id'],q['subject_id'])].append(q['score'])
    assert all(sum(v)/len(v)==99 for v in quality.values())
    assert sorted({v/120 for (p,s),v in amounts.items() if s.startswith('S')})==[.9,1,1.1,1.2]
    assert sorted({v/160 for (p,s),v in amounts.items() if s.startswith('B')})==[.9,1,1.1,1.2]
    assert sorted({r['usage_units'] for r in full['project_records']})==[80,100,120,180]
    groups=Counter((r['period_id'],r['subject_id']) for r in full['work_events'] if r['family']!='project')
    assert min(groups.values())>=20
    for cfg in result['business-config.json']['configs']:
        if cfg['version']==1: assert cfg['approved_at'][:10]<cfg['valid_from']
    baseline_names=m.scenario_index(oldroot)
    assert len([r for r in baseline_names if r['source']=='old'])==23
    # Expand old regressions without transforming or consulting private results.
    for entry in baseline_names:
        if entry['source']=='old':m.expand_scenario(entry['name'],oldroot)
    oldmanifest=hashlib.sha256((oldroot/'manifest.json').read_bytes()).hexdigest()
    assert oldmanifest=='2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc'
    validation=dict(version=VERSION,synthetic_only=True,deterministic_repeat=True,
        old_manifest_sha256=oldmanifest,old_regression_expanded=23,new_panels=len(reports),
        r1_ranges_verified=True,r1_qa_mean=99,minimum_flow_cases_per_subject_period=min(groups.values()),
        prospective_v1_config=True,qa_precision_points=1,
        full_panels_independent_signed_roster=True,team_size=5,project_root_parts=2,
        r4_cohorts=9,r4_personal_quarters=18,
        metadata_lookups=dict(legacy_support=1,legacy_workflow=1,legacy_analytical=0,r4_business_target=0),
        primitive_trace=dict(r1_flow_volume_ratios=[.9,1,1.1,1.2],r1_workflow_uses=[80,100,120,180],
            r2_precision_pair_aggregate_delta_points=2/40,r3_analytical_usage_values=[0,1],
            r3_ready_day_offsets_from_pre_read=[-1,0,0,1,2,3,13,14],
            r4_events_per_person_quarter=9,r4_delivery_recoveries=18),
        note='Only source structure and primitive ranges; no candidate behavior or money checked.',panels=reports)
    vpath=ROOT/'coordinator-only/validation.json'
    if a.verify:assert vpath.read_bytes()==encoded(validation)
    else:vpath.write_bytes(encoded(validation))
    public=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or 'coordinator-only' in path.parts or '__pycache__' in path.parts:continue
        if path.name in ['manifest.json','manifest.sha256']:continue
        payload=path.read_bytes()
        public.append(dict(path=str(path.relative_to(ROOT)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
    dependencies=[]
    original={r['path']:r for r in json.loads((oldroot/'manifest.json').read_text())['files']}
    for relative in ['README.md','dictionary.md','assumptions.csv','source/base.json','source/scenario_index.json','source/reader.py']+[f'patches/F{i:02}.json' for i in range(1,13)]:
        payload=(oldroot/relative).read_bytes()
        dependency=dict(path=relative,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
        assert dependency==original[relative],('old source changed',relative)
        dependencies.append(dependency)
    manifest=dict(version=VERSION,synthetic_only=True,frozen=True,generated_at=STAMP,
        files=public,external_old_fixture=dict(path_required_explicitly=True,manifest_sha256=oldmanifest,files=dependencies),
        entrypoint='reader.py',index='source/scenario_index.json',coordinator_only_excluded=True)
    manifest_bytes=encoded(manifest);manifest_hash=hashlib.sha256(manifest_bytes).hexdigest()
    private=dict(public_manifest_sha256=manifest_hash,files=[dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in [ROOT/'coordinator-only/generator.py',vpath]])
    for dest,payload in [(ROOT/'manifest.json',manifest_bytes),(ROOT/'manifest.sha256',(manifest_hash+'\n').encode()),
                         (ROOT/'coordinator-only/manifest.json',encoded(private))]:
        if a.verify:assert dest.read_bytes()==payload,str(dest)
        else:dest.write_bytes(payload)
    print(json.dumps({k:v for k,v in validation.items() if k!='panels'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
