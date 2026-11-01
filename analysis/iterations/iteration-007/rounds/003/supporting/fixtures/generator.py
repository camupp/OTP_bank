#!/usr/bin/env python3
"""Synthetic source exports. No bank connection, recognition algorithm or oracle reads."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from source.reader import apply_ops, expand_scenario

ROOT = Path(__file__).resolve().parent
VERSION = 'OTP-SYN-007-v1'
STAMP = '2026-11-01T09:00:00+03:00'
KEYS = {
    'period_rules': ['rule_id'], 'classifier': ['class_id'],
    'roster_capacity': ['capacity_id'], 'team_members': ['membership_id'],
    'worklog': ['worklog_id'], 'capacity_intervals': ['interval_id'],
    'work_events': ['event_id'], 'support_outcomes': ['outcome_id'],
    'process_outcomes': ['outcome_id'], 'project_records': ['record_id'],
    'quality_acts': ['act_id'], 'approvals_audit': ['approval_id'],
    'comparison_registry': ['registry_id'], 'source_manifest': ['partition_id'],
    'resource_assumptions': ['activity_id'],
}
PERIODS = {'P1': ('2026-01-01', '2026-03-31', '2026-04-28'),
           'P2': ('2026-04-01', '2026-06-30', '2026-07-28')}
SUBJECTS = {'S01': 'support', 'S02': 'support', 'B01': 'backoffice',
            'B02': 'backoffice', 'T01': 'project', 'T02': 'project'}
COUNTS = {'S01': 36, 'S02': 40, 'B01': 20, 'B02': 24, 'T01': 1, 'T02': 8}

def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()

def sha(obj):
    return hashlib.sha256(encoded(obj)).hexdigest()

def date(p, n):
    # Twenty weekdays in February / May, spread >=10 days even for twenty cases.
    days = [2,3,4,5,6,9,10,11,12,13,16,17,18,19,20,23,24,25,26,27]
    return f'2026-{"02" if p == "P1" else "05"}-{days[(n-1)%20]:02}'

def event(p, s, i):
    f = SUBJECTS[s]
    case = f'{p}-{s}-{i:03}'
    root = f'{p}-{s}-BEN' if f == 'project' else case
    d = date(p, i)
    return dict(event_id=f'EV-{case}-1', source_record_id=case, version=1,
        period_id=p, case_id=case, root_id=root, parent_id=root if f == 'project' else None,
        duplicate_of=None, subject_id=s, family=f, source_system_class=f'{f}_work_register',
        event_at=d+'T16:00:00+03:00', assigned_at=d+'T09:00:00+03:00',
        assignment_history_status='complete', queue_id=f'{f}-queue-A', channel='internal' if f!='support' else 'voice',
        type_id=(('S-C2' if i<=COUNTS[s]//2 else 'S-C4') if f=='support' else (('B-C3' if i<=COUNTS[s]//2 else 'B-C5') if f=='backoffice' else 'IT-DEL')),
        assigned_by='DISPATCH-01', due_at=d+'T18:00:00+03:00', status='Done' if f=='project' else 'resolved',
        accepted_at=d+'T17:00:00+03:00', accepted_by=f'OWNER-{f}',
        reopen_of=None, correction_of=None, external_blocker_ref=None)

def manifest_for(data):
    rows=[]
    for table in KEYS:
        if table == 'source_manifest': continue
        for p in PERIODS:
            selected=[r for r in data[table] if r.get('period_id',p)==p]
            rows.append(dict(partition_id=f'{table}:{p}', table=table, period_id=p,
                source_version='export-1', generated_at=STAMP, expected_count=len(selected),
                received_count=len(selected), availability='available', expected_before_start=True,
                readiness_at='2025-12-15', partition_ref=f'source/base.json#{table}/{p}',
                received_sha256=sha(selected), missing_reason=None))
    rows.append(dict(partition_id='quality_acts:P0',table='quality_acts',period_id='P0',source_version='export-1',generated_at=STAMP,expected_count=0,received_count=0,availability='available',expected_before_start=True,readiness_at='2025-12-15',partition_ref='source/base.json#quality_acts/P0',received_sha256=sha([]),missing_reason=None))
    return rows

def base_data():
    d={k:[] for k in KEYS}
    d['classifier']=[dict(class_id=c, family=f, type_id=c, standard_units=u,
        engineering_minutes_per_standard_unit=60, unit='standard_work_unit',
        complexity_owner='ENG-OWNER-01', approved_at='2025-12-01', effective_from='2026-01-01',
        version='engineering-scenario-1', employee_editable=False)
        for c,f,u in [('S-C1','support',1),('S-C2','support',2),('S-C4','support',4),('B-C1','backoffice',1),('B-C3','backoffice',3),('B-C5','backoffice',5),('IT-DEL','project',1)]]
    for p,(start,end,close) in PERIODS.items():
        for f in ['support','backoffice','project']:
            d['period_rules'].append(dict(rule_id=f'{p}:{f}',period_id=p,family=f,start=start,end=end,
                quality_close=close, window_id='W2026-A', annual_window_start='2026-01-01', annual_window_end='2026-12-31',
                comparison_group_id=f'G-{f}', rule_version='source-rule-1', classifier_version='engineering-scenario-1',
                standard_version='engineering-scenario-1', standard_owner='ENG-OWNER-01', approved_at='2025-12-01',
                source_ref='scenario-engineering-register', timezone='Europe/Moscow',
                stratum_allocations=([dict(type_id='S-C2',capacity_share=1/3,mix_weight=1/3,standard_units_per_hour=1),dict(type_id='S-C4',capacity_share=2/3,mix_weight=2/3,standard_units_per_hour=1)] if f=='support' else ([dict(type_id='B-C3',capacity_share=3/8,mix_weight=3/8,standard_units_per_hour=1),dict(type_id='B-C5',capacity_share=5/8,mix_weight=5/8,standard_units_per_hour=1)] if f=='backoffice' else [dict(type_id='IT-DEL',capacity_share=1,mix_weight=1,standard_units_per_hour=1)])),
                outcome_followup_days=14, sampling_seed='fixture-seed-007',
                seed_published_at=('2026-04-02' if p=='P1' else '2026-07-02'),
                seed_publisher='QA-OWNER-01', registry_frozen_at=end+'T23:59:59+03:00',
                process_service_contract_share=0.95 if f=='backoffice' else None))
        for s,f in SUBJECTS.items():
            frac=0.225 if f=='support' else (1/6 if f=='backoffice' else 0.5)
            d['roster_capacity'].append(dict(capacity_id=f'{p}:{s}',period_id=p,subject_id=s,
                entity_type='team' if f=='project' else 'employee',family=f,
                role='hr_operations' if s=='B01' else f,hire_date='2024-01-01',transfer_date=None,
                fte=2 if f=='project' else 1,scheduled_hours=480*(2 if f=='project' else 1),
                leave_hours=0,training_hours=0,allocation_fraction=frac,
                schedule_version='roster-1',registered_at='2025-12-15',capacity_owner='ROSTER-OWNER-01',
                active_days=60, assignment_history_status='complete'))
            d['worklog'].append(dict(worklog_id=f'{p}:{s}:1',period_id=p,subject_id=s,version=1,
                hours=108 if f=='support' else (80 if f=='backoffice' else 480),
                completeness='declared_complete',editable_by=s,edited_at=end+'T17:00:00+03:00',previous_hours=None))
            d['comparison_registry'].append(dict(registry_id=f'{p}:{s}',period_id=p,subject_id=s,
                comparison_group_id=f'G-{f}',window_id='W2026-A',cohort_id='C01',
                registered_at='2025-12-15',home_pool_id=f'G-{f}',eligible_unit='team' if f=='project' else 'employee'))
            for i in range(1,COUNTS[s]+1):
                e=event(p,s,i); d['work_events'].append(e)
                case=e['case_id']; day=e['event_at'][:10]
                if f=='support':
                    # All contacts/invitations are rows; no customer identifiers.
                    response=i<=30
                    d['support_outcomes'].append(dict(outcome_id=f'SO-{case}',period_id=p,case_id=case,
                        subject_id=s,queue_id='support-queue-A',topic='account_access',shift='day',
                        disposition='resolved',resolved=True,transfer=False,repeat_of=None,
                        linkage_method='case_root',contact_minutes=12,invited=True,responded=response,
                        csat_score=(4 if i%5==0 else 5) if response else None,csat_scale='1..5',
                        csat_at=day+'T18:00:00+03:00' if response else None,observation_end=PERIODS[p][1]))
                elif f=='backoffice':
                    on_time = not (s=='B01' and i==20)
                    if not on_time: e['accepted_at']=day+'T19:00:00+03:00'
                    d['process_outcomes'].append(dict(outcome_id=f'BO-{case}',period_id=p,case_id=case,
                        subject_id=s,operation_type=e['type_id'],mode='standard',accepted=True,
                        accepted_at=day+('T19:00:00+03:00' if not on_time else 'T17:00:00+03:00'),
                        sla_due_at=day+'T18:00:00+03:00',returned=False,return_reason=None,
                        correction_of=None,external_wait_reason=None,observation_end=PERIODS[p][1]))
                else:
                    root_day='2026-'+('02' if p=='P1' else '05')+'-27'
                    e['accepted_at']=root_day+'T17:00:00+03:00'
                    d['project_records'].append(dict(record_id=f'PR-{case}',period_id=p,case_id=case,
                        subject_id=s,version=1,deliverable_id=e['root_id'],parent_id=e['root_id'],
                        benefit_id=e['root_id'],criteria_ref=f'CRITERIA-{e["root_id"]}',
                        criteria_agreed_at='2025-12-01',acceptance_owner='PROCESS-OWNER-IT',
                        acceptance_at=root_day+'T17:00:00+03:00',acceptance_ref=f'ACCEPT-{e["root_id"]}',
                        release_ref=f'RELEASE-{e["root_id"]}',release_at=root_day+'T18:00:00+03:00',
                        usage_status='present',usage_ref=f'USE-{e["root_id"]}',usage_observed_at=PERIODS[p][1],
                        usage_owner='PROCESS-OWNER-IT',usage_coverage='one_internal_process',
                        usage_units=120,usage_measure='distinct_workflow_runs_at_deliverable_grain',
                        defects_ref=None,rollback=False,story_points=13 if s=='T01' else 2))
                d['quality_acts'].append(dict(act_id=f'QA-{case}',inspection_id=f'INSP-{case}',
                    period_id=p,case_id=case,event_id=e['event_id'],subject_id=s,
                    scope='team' if f=='project' else 'personal',criterion='defect_penalty',
                    scale='0..100',scale_version='penalty-v1',minor=(1 if i%2==0 else 0),major=0,critical=0,score=(98 if i%2==0 else 100),
                    sample_method='census_of_scenario_work_register',coverage_object='one_distinct_case',
                    checked_at=PERIODS[p][1]+'T19:00:00+03:00',observation_start=day,
                    observation_end=PERIODS[p][2],checker_id='QA-INDEPENDENT-01',
                    evidence_status='present',finalized_at=PERIODS[p][2]+'T09:00:00+03:00',existing_activity=True,existing_minutes=3))
        for team, members in {'T01':[('P01',.6),('P02',.4)],'T02':[('P03',.5),('P04',.5)]}.items():
            for person,share in members:
                d['team_members'].append(dict(membership_id=f'{p}:{person}',period_id=p,team_id=team,
                    employee_id=person,fte=1,contribution_share=share,personal_active_days=60,
                    role='manager' if person=='P01' else 'engineer',window_id='W2026-A',cohort_id='C01',
                    effective_from=start,effective_to=end,approved_by='ROSTER-OWNER-01',approved_at='2025-12-15'))
        for s,typ in [('S01','worker'),('B01','hr'),('P01','manager')]:
            d['approvals_audit'].append(dict(approval_id=f'{p}:{s}',period_id=p,version=1,
                beneficiary_id=s,beneficiary_role=typ,beneficiary_team='T01' if s=='P01' else None,
                action='input_correction_and_posting_review',source_ref=f'{p}:{s}',
                initiator_id=s,input_editor_id='DATA-OP-01',signer_id='OWNER-INDEPENDENT-01',
                operator_id='HR-INDEPENDENT-01',signer_reporting_to=None,operator_reporting_to=None,
                alternate_signer_id='ALT-OWNER-01',alternate_operator_id='ALT-HR-01',
                appeal_owner_id='APPEAL-01',signed_at=PERIODS[p][2]+'T10:00:00+03:00',
                before='export-1',after='export-1-checked',reason='source_completeness_review'))
    d['resource_assumptions']=[dict(activity_id=a,role=r,minutes_per_unit=m,unit=u,
        frequency=f,existing_activity=existing,source='fixture_assumption_not_bank_capacity')
        for a,r,m,u,f,existing in [
            ('QA-existing','qa_owner',3,'case','per_existing_act',True),
            ('export-setup','analyst',120,'source_class','one_off',False),
            ('completeness','analyst',8,'partition','per_export',False),
            ('independent-sign','owner',4,'subject_period','per_decision',False),
            ('exception','owner',12,'exception','only_if_raised',False),
            ('source-recovery','data_operator',30,'lost_partition','only_if_incident',False),
            ('new-QA-if-missing','qa_owner',5,'new_reviewed_case','only_if_needed',False)]]
    d['source_manifest']=manifest_for(d)
    return d


def scenarios(base):
    result=[]
    def scenario(sid,title,variants):
        result.append(dict(scenario_id=sid,title=title,baseline='base',variants=variants))
    def update(t,k,val): return dict(table=t,grain=KEYS[t],op='update',key=k,set=val)
    def insert(t,row): return dict(table=t,grain=KEYS[t],op='insert',key={k:row[k] for k in KEYS[t]},row=row)
    def delete(t,row): return dict(table=t,grain=KEYS[t],op='delete',key={k:row[k] for k in KEYS[t]})
    def select(t,**kw):return [r for r in base[t] if all(r.get(k)==v for k,v in kw.items())]
    scenario('F01','Два квартала сопоставимого потока',{'observed':[]})
    scenario('F02','Редактируемый worklog',{
        'inflated':[update('worklog',{'worklog_id':'P1:S01:1'},dict(hours=216,version=2,previous_hours=108))],
        'incomplete':[update('worklog',{'worklog_id':'P1:S01:1'},dict(hours=54,version=2,previous_hours=108,completeness='partial'))]})
    scenario('F03','Done, приёмка и сроки подтверждения',{
        'done_only':[update('work_events',{'event_id':'EV-P1-T01-001-1'},dict(accepted_at=None,accepted_by=None)),
            update('project_records',{'record_id':'PR-P1-T01-001'},dict(acceptance_at=None,acceptance_ref=None,usage_status='missing',usage_ref=None,usage_observed_at=None,usage_units=None))],
        'late_acceptance':[update('work_events',{'event_id':'EV-P1-T01-001-1'},dict(accepted_at='2026-05-05T17:00:00+03:00')),
            update('project_records',{'record_id':'PR-P1-T01-001'},dict(acceptance_at='2026-05-05T17:00:00+03:00',usage_observed_at='2026-05-07'))]})
    ops=[]
    communication=copy.deepcopy(select('quality_acts',period_id='P1',subject_id='S01')[0])
    communication.update(act_id='QA-COMM-P1-S01',inspection_id='INSP-COMM-P1-S01',criterion='communication_rubric',scale='0..100',scale_version='communication-v2',score=97,minor=None,major=None,critical=None,sample_method='selected_voice_topic',coverage_object='one_selected_case')
    ops.append(insert('quality_acts',communication))
    for row in select('quality_acts',period_id='P1',subject_id='S02')[:6]:
        ops.append(update('quality_acts',{'act_id':row['act_id']},dict(criterion='process_team_check',scale='1..5',scale_version='team-rubric-v3',score=4,minor=None,major=None,critical=None,scope='process',sample_method='convenience_unknown',coverage_object='one_selected_case')))
    for row in select('quality_acts',period_id='P1',subject_id='S02')[6:]:ops.append(delete('quality_acts',row))
    old=copy.deepcopy(select('quality_acts',period_id='P1',subject_id='S02')[0]);old.update(act_id='QA-OLD-P0',inspection_id='INSP-OLD-P0',period_id='P0',checked_at='2025-12-20',observation_start='2025-12-01',observation_end='2025-12-31',case_id=None,event_id=None)
    ops.append(insert('quality_acts',old))
    for row in select('support_outcomes',period_id='P1',subject_id='S01'):
        answered=int(row['case_id'][-3:])<=3
        ops.append(update('support_outcomes',{'outcome_id':row['outcome_id']},dict(responded=answered,csat_score=5 if answered else None,csat_at=row['csat_at'] if answered else None)))
    noanswers=[update('support_outcomes',{'outcome_id':r['outcome_id']},dict(responded=False,csat_score=None,csat_at=None)) for r in select('support_outcomes',period_id='P1',subject_id='S01')]
    scenario('F04','Шкалы, scope, покрытие и ответы',{'mixed':ops,'no_responses':noanswers})
    e=copy.deepcopy(select('work_events',case_id='P1-S01-001')[0]);e.update(event_id='EV-P1-S01-REOPEN-2',version=2,status='reopened',reopen_of='P1-S01-001',event_at='2026-02-03T11:00:00+03:00')
    wrong=copy.deepcopy(e);wrong.update(event_id='EV-P1-S01-NEW-1',source_record_id='P1-S01-NEW',case_id='P1-S01-NEW',version=1,status='resolved',duplicate_of='P1-S01-001')
    ret=copy.deepcopy(select('process_outcomes',case_id='P1-B01-001')[0]);ret.update(outcome_id='BO-P1-B01-CORR',case_id='P1-B01-CORR',correction_of='P1-B01-001',returned=True,return_reason='same_original_correction')
    er=copy.deepcopy(select('work_events',case_id='P1-B01-001')[0]);er.update(event_id='EV-P1-B01-CORR-1',source_record_id='P1-B01-CORR',case_id='P1-B01-CORR',correction_of='P1-B01-001')
    scenario('F05','Дубли, reopen и переделка',{'linked':[
        dict(table='work_events',grain=KEYS['work_events'],op='append_export_copy',key={'event_id':'EV-P1-S01-001-1'}),
        insert('work_events',e),insert('work_events',wrong),insert('process_outcomes',ret),insert('work_events',er)],
        'unlinked_new_id':[insert('work_events',{**wrong,'root_id':None,'duplicate_of':None,'reopen_of':None})]})
    ops=[update('roster_capacity',{'capacity_id':'P1:S02'},dict(fte=.5,scheduled_hours=40,leave_hours=8,training_hours=8,hire_date='2026-03-02',active_days=10)),
         update('worklog',{'worklog_id':'P1:S02:1'},dict(hours=12,completeness='partial'))]
    # Newcomer output is limited to ten observed cases on ten March workdays.
    for t,field in [('work_events','subject_id'),('support_outcomes','subject_id'),('quality_acts','subject_id')]:
        for r in select(t,period_id='P1',**{field:'S02'}):
            n=int(r['case_id'][-3:])
            if n>10:ops.append(delete(t,r));continue
            dd=f'2026-03-{[2,3,4,5,6,9,10,11,12,13][n-1]:02}'
            if t=='work_events':
                ops.append(update(t,{k:r[k] for k in KEYS[t]},dict(type_id='S-C4',channel='written',queue_id='support-complex',assigned_at=None,assigned_by=None,assignment_history_status='missing',event_at=dd+'T16:00:00+03:00',due_at=dd+'T18:00:00+03:00',accepted_at=dd+'T17:00:00+03:00')))
            elif t=='support_outcomes':ops.append(update(t,{k:r[k] for k in KEYS[t]},dict(topic='complex_account_change',queue_id='support-complex',csat_at=dd+'T18:00:00+03:00' if r['responded'] else None)))
            else:ops.append(update(t,{k:r[k] for k in KEYS[t]},dict(observation_start=dd)))
    scenario('F06','Новичок, доля потока и классификатор',{'capacity_mix':ops,
        'self_reclassified':[update('work_events',{'event_id':'EV-P1-S01-001-1'},dict(type_id='S-C4')),
            insert('approvals_audit',dict(approval_id='TYPE-SELF',period_id='P1',version=2,beneficiary_id='S01',action='type_correction',source_ref='EV-P1-S01-001-1',initiator_id='S01',input_editor_id='S01',signer_id='S01',operator_id='S01',alternate_signer_id=None,alternate_operator_id=None,before='S-C2',after='S-C4',reason='claimed_complexity',signed_at='2026-04-10'))]})
    ops=[]
    old=select('work_events',case_id='P1-T01-001')[0]
    for i in range(2,9):
        case=f'P1-T01-{i:03}'
        child=copy.deepcopy(old);child.update(event_id=f'EV-{case}-1',source_record_id=case,case_id=case)
        ops.append(insert('work_events',child))
        pr=copy.deepcopy(select('project_records',case_id='P1-T01-001')[0]);pr.update(record_id=f'PR-{case}',case_id=case,story_points=2);ops.append(insert('project_records',pr))
        # Same inspection evidence re-exported for child; not seven invented independent audits.
        qa=copy.deepcopy(select('quality_acts',case_id='P1-T01-001')[0]);qa.update(act_id=f'QA-{case}',case_id=case,event_id=child['event_id'],coverage_object='same_deliverable_inspection');ops.append(insert('quality_acts',qa))
    scenario('F07','Один deliverable и восемь его частей',{'split':ops})
    intervals=[]
    for name,start,end,kind in [('BL','10:00','12:00','external_blocker'),('HELP','11:00','13:00','help_other_team')]:
        intervals.append(dict(interval_id=f'P1-S01-{name}',period_id='P1',subject_id='S01',kind=kind,
            start_at=f'2026-02-10T{start}:00+03:00',end_at=f'2026-02-10T{end}:00+03:00',
            requestor_id='S01',recorded_by='OTHER-PROCESS-OWNER',approved_by='ROSTER-OWNER-01',
            source_ref=f'INDEPENDENT-LOG-{name}',recipient_team_id='T02' if name=='HELP' else None))
    scenario('F08','Пересекающиеся blocker и помощь',{'documented':[insert('capacity_intervals',r) for r in intervals]+[update('work_events',{'event_id':'EV-P1-S01-007-1'},dict(external_blocker_ref='P1-S01-BL'))],
        'self_claimed':[insert('capacity_intervals',{**r,'recorded_by':'S01','approved_by':None,'source_ref':None}) for r in intervals]+[update('work_events',{'event_id':'EV-P1-S01-007-1'},dict(external_blocker_ref='P1-S01-BL'))]})
    scenario('F09','Конфликт подписей по трём ролям',{'conflicted':[
        update('approvals_audit',{'approval_id':f'P1:{s}'},dict(input_editor_id=s,signer_id=s,operator_id=s,
            alternate_signer_id=None if s=='P01' else 'ALT-OWNER-01',alternate_operator_id=None if s=='P01' else 'ALT-HR-01',
            signer_reporting_to=s,operator_reporting_to=s)) for s in ['S01','B01','P01']]})
    # Partition is whole QA/P1; remove every QA row in that partition, not just subject S01.
    lost=[delete('quality_acts',r) for r in select('quality_acts',period_id='P1')]
    incident=update('source_manifest',{'partition_id':'quality_acts:P1'},dict(availability='lost_partition',source_version='export-2',generated_at='2026-04-15T09:00:00+03:00',missing_reason='partition_not_received',expected_before_start=True))
    early=update('source_manifest',{'partition_id':'quality_acts:P1'},dict(availability='known_unusable_before_start',source_version='readiness-fail',generated_at='2025-12-15T09:00:00+03:00',readiness_at='2025-12-15',expected_before_start=False,missing_reason='schema_not_available'))
    restored=update('source_manifest',{'partition_id':'quality_acts:P1'},dict(source_version='export-restored-3',generated_at='2026-05-08T09:00:00+03:00',availability='restored',missing_reason=None))
    scenario('F10','Потеря, восстановление и ранний пробел',{'lost':lost+[incident],'restored':[restored],'known_gap':lost+[early]})
    scenario('F11','Долевой SLA вокруг95% и потолок100%',{
        'below':[update('process_outcomes',{'outcome_id':'BO-P1-B01-019'},dict(accepted_at='2026-02-26T19:00:00+03:00')),update('work_events',{'event_id':'EV-P1-B01-019-1'},dict(accepted_at='2026-02-26T19:00:00+03:00'))],
        'at_contract':[],
        'ceiling':[update('process_outcomes',{'outcome_id':'BO-P1-B01-020'},dict(accepted_at='2026-02-27T17:00:00+03:00')),update('work_events',{'event_id':'EV-P1-B01-020-1'},dict(accepted_at='2026-02-27T17:00:00+03:00'))]})
    # Matching support case count creates a tie without copying the whole dataset.
    tie=[]
    for t in ['work_events','support_outcomes','quality_acts']:
        for r in select(t,subject_id='S02'):
            if int(r['case_id'][-3:])>36:tie.append(delete(t,r))
    tie.extend([
        update('team_members',{'membership_id':'P2:P02'},dict(team_id='T02',fte=.5,contribution_share=.2,effective_from='2026-04-01')),
        update('team_members',{'membership_id':'P2:P01'},dict(contribution_share=.6)),
        update('team_members',{'membership_id':'P2:P03'},dict(contribution_share=.4)),
        update('team_members',{'membership_id':'P2:P04'},dict(contribution_share=.4)),
        update('roster_capacity',{'capacity_id':'P2:T01'},dict(fte=1,scheduled_hours=480)),
        update('roster_capacity',{'capacity_id':'P2:T02'},dict(fte=2.5,scheduled_hours=1200))])
    scenario('F12','Ничья двух участников, перевод и доли',{'tie_transfer':tie})
    # Include explicit count/hash changes in each patch, preserving incident expected counts.
    for sc in result:
        for name,ops in sc['variants'].items():
            expanded=apply_ops(base,ops)
            for m in expanded['source_manifest']:
                t,p=m['table'],m['period_id']
                rows=[r for r in expanded[t] if r.get('period_id',p)==p]
                changes=dict(received_count=len(rows),received_sha256=sha(rows))
                if m['availability'] in ['available','restored']:changes['expected_count']=len(rows)
                if any(m.get(k)!=v for k,v in changes.items()):ops.append(update('source_manifest',{'partition_id':m['partition_id']},changes))
    return result


def validate(data, allow_export_duplicate=False):
    errors=[]
    for t,keys in KEYS.items():
        seen={}
        for r in data[t]:
            key=tuple(r[k] for k in keys)
            if key in seen and not (allow_export_duplicate and seen[key]==r):errors.append(f'duplicate {t} {key}')
            seen[key]=r
    cases={e['case_id'] for e in data['work_events']}
    event_ids={e['event_id'] for e in data['work_events']}
    for t in ['support_outcomes','process_outcomes','project_records','quality_acts']:
        for r in data[t]:
            if r.get('case_id') and r['case_id'] not in cases:errors.append(f'orphan case {t} {r[KEYS[t][0]]}')
            if r.get('event_id') and r['event_id'] not in event_ids:errors.append(f'orphan event {t}')
    for e in data['work_events']:
        start,end,_=PERIODS[e['period_id']]
        if not start<=e['event_at'][:10]<=end:errors.append(f'outside period {e["event_id"]}')
        if e['type_id'] not in {c['class_id'] for c in data['classifier']}:errors.append('unknown classifier')
        for k in ['duplicate_of','reopen_of','correction_of']:
            if e.get(k) and e[k] not in cases:errors.append(f'broken {k}')
    for p in PERIODS:
        for team in ['T01','T02']:
            members=[x for x in data['team_members'] if x['team_id']==team and x['period_id']==p]
            if sum(x['contribution_share'] for x in members)>1.000000001:errors.append('team shares >1')
            if len({x['employee_id'] for x in members})!=len(members):errors.append('member repeated')
    for r in data['roster_capacity']:
        if r['fte']<0 or r['scheduled_hours']<0 or not 0<=r['allocation_fraction']<=1:errors.append('invalid capacity')
        if r['leave_hours']+r['training_hours']>r['scheduled_hours']:errors.append('absence exceeds schedule')
        if r['entity_type']=='team':
            member_fte=sum(x['fte'] for x in data['team_members'] if x['team_id']==r['subject_id'] and x['period_id']==r['period_id'])
            if abs(member_fte-r['fte'])>1e-9:errors.append('team roster/member FTE mismatch')
    for r in data['period_rules']:
        if not r['start']<=r['end']<r['quality_close']:errors.append('invalid period/quality close')
        for field in ['capacity_share','mix_weight']:
            if abs(sum(x[field] for x in r['stratum_allocations'])-1)>1e-9:errors.append('strata sum differs from one')
    for m in data['source_manifest']:
        rows=[r for r in data[m['table']] if r.get('period_id',m['period_id'])==m['period_id']]
        if len(rows)!=m['received_count'] or sha(rows)!=m['received_sha256']:errors.append(f'partition checksum {m["partition_id"]}')
        if m['availability'] in ['available','restored'] and len(rows)!=m['expected_count']:errors.append('unexpected coverage')
    return errors


def generate():
    base=base_data();scs=scenarios(base)
    (ROOT/'source/base.json').write_bytes(encoded(base))
    for sc in scs:(ROOT/'patches'/f'{sc["scenario_id"]}.json').write_bytes(encoded(sc))
    index=[dict(scenario_id=s['scenario_id'],title=s['title'],variants=list(s['variants']),patch_ref=f'patches/{s["scenario_id"]}.json',baseline='base') for s in scs]
    (ROOT/'source/scenario_index.json').write_bytes(encoded(index))
    return base,scs


def verify():
    base=json.loads((ROOT/'source/base.json').read_text());errors=validate(base)
    comparisons=[]
    for p in PERIODS:
        for s in SUBJECTS:
            rows=[r for r in base['work_events'] if r['subject_id']==s and r['period_id']==p]
            comparisons.append(dict(period_id=p,subject_id=s,source_cases=len(rows),
                distinct_roots=len({r['root_id'] for r in rows}),event_days=len({r['event_at'][:10] for r in rows}),
                independent_inspections=len({r['inspection_id'] for r in base['quality_acts'] if r['subject_id']==s and r['period_id']==p})))
    checked=[]
    for sc in json.loads((ROOT/'source/scenario_index.json').read_text()):
        for variant in sc['variants']:
            expanded=expand_scenario(sc['scenario_id'],variant)
            es=validate(expanded,allow_export_duplicate=sc['scenario_id']=='F05')
            errors.extend(f'{sc["scenario_id"]}.{variant}: {e}' for e in es)
            checked.append(sc['scenario_id']+'.'+variant)
    if encoded(base_data())!=(ROOT/'source/base.json').read_bytes():errors.append('base regeneration differs')
    for sc in scenarios(base_data()):
        if encoded(sc)!=(ROOT/'patches'/f'{sc["scenario_id"]}.json').read_bytes():errors.append('patch regeneration differs')
    if len(base['work_events'])!=258:errors.append('base size differs')
    for c in comparisons:
        if c['subject_id'][0] in 'SB' and (c['source_cases']<20 or c['event_days']<10):errors.append('stream exposure too small')
    # Test source reader independence from row order (no algorithm/ranking assertion).
    canonical=lambda rows:sorted((json.dumps(r,sort_keys=True) for r in rows))
    if any(canonical(rows)!=canonical(list(reversed(rows))) for rows in base.values()):errors.append('row-order structural failure')
    summary=dict(version=VERSION,status='pass' if not errors else 'fail',errors=errors,
        base_table_rows={k:len(v) for k,v in base.items()},observations=comparisons,
        checked_variants=checked,deterministic_regeneration=True,
        exclusions='No candidate/parent Q, QA sampling, rewards, cash or causal effects computed.')
    (ROOT/'validation.json').write_bytes(encoded(summary))
    if errors:raise SystemExit('\n'.join(errors))
    return summary


def write_manifest():
    paths=[p for p in ROOT.rglob('*') if p.is_file() and 'oracle' not in p.relative_to(ROOT).parts
           and '__pycache__' not in p.parts and p.name not in ['manifest.json','manifest.sha256']]
    manifest=dict(version=VERSION,generated_at=STAMP,synthetic_only=True,
        source_entrypoint='source/base.json',patch_entrypoint='source/scenario_index.json',
        oracle_excluded=True,files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)])
    raw=encoded(manifest);(ROOT/'manifest.json').write_bytes(raw)
    (ROOT/'manifest.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  manifest.json\n')
    return hashlib.sha256(raw).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if not args.verify:generate()
    report=verify();digest=write_manifest()
    print(json.dumps(dict(status=report['status'],base_events=258,variants=len(report['checked_variants']),manifest_sha256=digest)))
