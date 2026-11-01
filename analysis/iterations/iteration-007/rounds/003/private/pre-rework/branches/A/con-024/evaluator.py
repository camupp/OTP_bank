#!/usr/bin/env python3
"""Source-only recognition analysis; standard library, Python 3.12.

evaluate(data, spec) accepts expanded PUBLIC source tables, never an oracle.
Scenario names label outputs only. Missing acceptance is never manufactured.
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import importlib.util
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parents[2]
FIXTURE = ROUND / 'supporting/fixtures'
ADDENDUM = ROUND / 'supporting/round002-stress'
PUBLIC_CONFIGS = json.loads((ADDENDUM/'business-config.json').read_text())['configs']

def digest(rows):
    return hashlib.sha256((json.dumps(rows,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()

def quality_category(mean):
    """Recognition of observed penalties, never statistical superiority.

    Complete normal/stretch/exposure gates are applied separately. A zero
    observed-penalty portfolio is a prospective category, not a rounded score.
    """
    if mean is None:return 'unmeasured'
    if mean==100:return 'no_observed_penalty'
    if mean>=99:return 'qualified_with_observed_penalty'
    return 'below_stretch_quality'

def quality_rank_key(mean):
    return (2 if mean==100 else 1,)

def stamp(x, end=False):
    if not x:return None
    if len(x)==10:x += 'T23:59:59+03:00' if end else 'T00:00:00+03:00'
    try:v=datetime.fromisoformat(x)
    except (ValueError,TypeError):return None
    if v.tzinfo is None:v=v.replace(tzinfo=__import__('datetime').timezone(__import__('datetime').timedelta(hours=3)))
    return v

def package_source_digest(data, posting_action):
    """Bind all source facts without making the award signature sign itself.

    The physical approvals partition still passes validate_manifest. Its hash
    includes award signatures, so the signing digest instead binds the exact
    non-award audit rows; otherwise adding a signature creates a hash cycle.
    """
    source={k:v for k,v in data.items() if k not in ('approvals_audit','source_manifest')}
    source['source_manifest']=[m for m in data['source_manifest'] if m['table']!='approvals_audit']
    source['source_audit']=[a for a in data['approvals_audit'] if a.get('action')!=posting_action]
    return digest(source)

def batch_errors(data, period):
    bs=[b for b in data.get('batch_metadata',[]) if b['period_id']==period]
    if not bs:return []  # legacy individual path, never invent a batch signature
    errors=[]
    for b in bs:
        regs=[r for r in data['comparison_registry'] if r['period_id']==period]
        ms=[m for m in data['team_members'] if m['period_id']==period]
        if b.get('roster_sha256')!=digest(regs) or b.get('roster_count')!=len(regs):errors.append('signed_roster_changed')
        if b.get('team_members_sha256')!=digest(ms) or b.get('team_member_count')!=len(ms):errors.append('signed_members_changed')
        forbidden={r['subject_id'] for r in regs}|{m['employee_id'] for m in ms}
        copy=dict(b,action='source_batch_composition_review')
        errors+=approval_errors(copy,forbidden,'source_batch_composition_review')
        if not b.get('version') or not b.get('source_version'):errors.append('batch_version_missing')
        expected={r['period_id']+':'+r['subject_id'] for r in regs}|{m['period_id']+':'+m['employee_id'] for m in ms}
        if not expected <= set(b.get('approval_refs',[]))|set(b.get('exception_refs',[])):errors.append('batch_approval_roster_incomplete')
    return sorted(set(errors))

def day(x):
    return date.fromisoformat(x[:10]) if x else None

def fraction(a, b):
    return F(a, b) if b else None

def unique(rows, key):
    out = {}
    for row in rows:
        k = row[key]
        if k in out and row != out[k]:
            raise ValueError('Conflicting source key: ' + str(k))
        out[k] = row
    return list(out.values())

def validate_manifest(data):
    problems = defaultdict(list)
    for m in data['source_manifest']:
        table, period = m['table'], m['period_id']
        rows = [r for r in data[table] if r.get('period_id', period) == period]
        digest = hashlib.sha256((json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                indent=2) + '\n').encode()).hexdigest()
        if m['availability'] in ('lost_partition', 'known_unusable_before_start'):
            problems[period].append((table, m['availability']))
        elif m['availability']=='partial':
            problems[period].append((table,'partial_source'))
        elif len(rows) != m['received_count'] or digest != m['received_sha256']:
            problems[period].append((table, 'checksum_or_count'))
    return problems

def approval_errors(a, beneficiaries, required_action='input_correction_and_posting_review',
                    distinct_pairs=None):
    """Validate a performed action, not a roster of possible alternate people.

    All rewarded team members and team IDs are excluded. Missing editor/signer/
    operator never implies independence. Null reporting_to means no stated link
    in this synthetic register; a stated recipient link is always disqualifying.
    """
    errors=[]
    forbidden=set(beneficiaries)
    if a.get('action') != required_action: errors.append('wrong_action')
    try:
        datetime.fromisoformat(a.get('signed_at') or '')
    except (ValueError,TypeError):errors.append('performed_signature_time_missing_or_invalid')
    for field in ('input_editor_id','signer_id','operator_id'):
        actor=a.get(field)
        if not isinstance(actor,str) or not actor.strip():errors.append(field+':missing')
        elif actor in forbidden:errors.append(field+':beneficiary')
    # Check every explicitly provided reporting dependency, including editor.
    for field,value in a.items():
        if field.endswith('_reporting_to'):
            targets=value if isinstance(value,list) else [value]
            if any(target in forbidden for target in targets if target):
                errors.append(field+':reports_to_beneficiary')
    pairs=distinct_pairs or [('input_editor_id','signer_id'),('input_editor_id','operator_id'),('signer_id','operator_id')]
    for left,right in pairs:
        if a.get(left) and a.get(left)==a.get(right):errors.append('roles_not_distinct:'+left+'/'+right)
    return sorted(set(errors))

def independent_approval(a, beneficiaries, required_action='input_correction_and_posting_review',
                         distinct_pairs=None):
    if isinstance(beneficiaries,str):beneficiaries={beneficiaries}
    return not approval_errors(a,beneficiaries,required_action,distinct_pairs)

def evaluate(data, spec):
    """Return unit rows and personal rows, including all intermediate evidence."""
    source_errors = validate_manifest(data)
    data_hash=package_source_digest(data,spec['signature']['posting_action']);rule_hash=digest(spec)
    batch_by_period={p:batch_errors(data,p) for p in {r['period_id'] for r in data['comparison_registry']}}
    members = data['team_members']
    rules = {(r['period_id'], r['family']): r for r in data['period_rules']}
    caps = {(r['period_id'], r['subject_id']): r for r in data['roster_capacity']}
    units = []
    for reg in sorted(data['comparison_registry'], key=lambda x:(x['period_id'],x['subject_id'])):
        p, s = reg['period_id'], reg['subject_id']
        cap = caps[p, s]; family = cap['family']; rule = rules[p, family]
        cfg = spec['roles'][family]; close = day(rule['quality_close'])
        close_at=stamp(rule.get('quality_close_at') or rule['quality_close'],True)
        start_at=stamp(rule['start']); end_at=stamp(rule['end'],True)
        own = {s} | {m['employee_id'] for m in members if m['team_id']==s} | {m['team_id'] for m in members if m['employee_id']==s}
        rows = unique([e for e in data['work_events'] if e['period_id']==p and e['subject_id']==s], 'event_id')
        if data.get('personal_windows'):
            # All source partitions may surround a boundary. Preserve unfinished assigned obligations.
            rows=[e for e in rows if stamp(e['event_at'])>=start_at and (start_at<=stamp(e['assigned_at'])<=end_at or start_at<=stamp(e['due_at'])<=end_at)]
        reasons, pending, fail, insufficient = [], [], [], []
        relevant = {'period_rules','roster_capacity','work_events','quality_acts','classifier','comparison_registry'}
        relevant.add({'support':'support_outcomes','backoffice':'process_outcomes','project':'project_records'}[family])
        if family == 'project': relevant.add('team_members')
        for table, err in source_errors.get(p, []):
            if table in relevant: pending.append(table+':'+err)
        if day(rule['approved_at']) >= day(rule['start']) or rule['standard_owner'] in own:
            pending.append('rule_not_prospective_or_independent')
        if cap.get('assignment_history_status') != 'complete': pending.append('roster_assignment_missing')
        if cap['active_days'] < spec['exposure_days']: insufficient.append('active_days')
        by_case = defaultdict(list)
        for e in rows:
            by_case[e['case_id']].append(e)
            if not e.get('root_id'): pending.append('root_link_missing:'+e['case_id'])
            if e.get('assignment_history_status') != 'complete': pending.append('assignment_missing:'+e['case_id'])
            if not e.get('assigned_by') or e['assigned_by'] in own: pending.append('assignment_independence')
        # All assigned roots remain in denominator, including unfinished and repeated work.
        roots = defaultdict(list)
        for e in rows:
            if e.get('root_id'): roots[e['root_id']].append(e)
        n = len(roots)
        if n < cfg['minimum_roots']: insufficient.append('minimum_roots')
        corrections=defaultdict(list)
        for a in data['approvals_audit']:
            if a['period_id']==p and a['beneficiary_id'] in own and a.get('action')=='type_correction':
                corrections[(a['beneficiary_id'],a.get('source_ref'))].append(a)
        latest_corrections=[max(group,key=lambda a:(a.get('version',0),a.get('signed_at') or '',a['approval_id'])) for group in corrections.values()]
        if any(not independent_approval(a,own,'type_correction',spec['signature']['distinct_pairs']) for a in latest_corrections):
            pending.append('unapproved_classification_correction')
        # Existing QA only: correct period/rubric/scope, mature, independently checked.
        compatible=[]
        for a in data['quality_acts']:
            if a['period_id']!=p or a['subject_id']!=s: continue
            if (a.get('criterion')=='defect_penalty' and a.get('scale')=='0..100'
                and a.get('scale_version')=='penalty-v1' and a.get('scope')==('team' if family=='project' else 'personal')
                and a.get('evidence_status')=='present' and a.get('checker_id') not in own
                and a.get('checker_id') and a.get('sample_method')=='census_of_scenario_work_register'
                and stamp(a.get('finalized_at')) and stamp(a['finalized_at'])<=close_at
                and day(a.get('observation_end')) and day(a['observation_end'])>=close
                and all(a.get(k) is not None for k in ('minor','major','critical'))):
                compatible.append(a)
        # Copies sharing an inspection never create independent evidence or improve its score.
        inspections=defaultdict(list)
        for a in compatible: inspections[a['inspection_id']].append(a)
        scores=[min(max(0,100-2*a['minor']-10*a['major']-100*a['critical']) for a in group) for group in inspections.values()]
        qmean=F(sum(scores),len(scores)) if scores else None
        covered_cases={a['case_id'] for a in compatible if a.get('coverage_object')=='one_distinct_case'}
        coverage_trace=[]
        for root, es in roots.items():
            required_cases={e['case_id'] for e in es}
            whole=[a for a in compatible if family=='project' and a.get('coverage_object')=='same_deliverable_inspection'
                   and (a.get('case_id') in required_cases or a.get('deliverable_id')==root)]
            # A benefit is deduplicated once, but case-scoped QA cannot expand its scope.
            covered=bool(whole) or all(e['case_id'] in covered_cases or
                (family!='project' and (e.get('duplicate_of') in covered_cases or e.get('correction_of') in covered_cases))
                for e in es)
            coverage_trace.append({'root':root,'required_case_count':len(required_cases),
                'case_scoped_covered_count':len(required_cases & covered_cases),
                'whole_deliverable_act_ids':sorted({a['act_id'] for a in whole}),
                'whole_deliverable_inspection_ids':sorted({a['inspection_id'] for a in whole}),
                'covered':covered,'missing_case_ids':[] if whole else sorted(required_cases-covered_cases)})
            if not covered: pending.append('qa_coverage:'+root)
        if not scores: pending.append('qa_missing_or_incompatible')
        if qmean is not None and all(x['covered'] for x in coverage_trace) and qmean < cfg['quality_min']: fail.append('qa_below_normal')
        if any(a['critical'] for a in compatible): fail.append('critical_error')
        # Report observations, no CSAT gate and no imputation of a missing answer.
        outcomes=[o for o in data['support_outcomes'] if o['period_id']==p and o['subject_id']==s]
        responses=[o for o in outcomes if o.get('responded') and o.get('csat_scale')=='1..5' and o.get('csat_score') is not None]
        csat={'contacts':len(outcomes),'invited':sum(o['invited'] for o in outcomes),
              'responses':len(responses),'mean':float(F(sum(o['csat_score'] for o in responses),len(responses))) if responses else None}
        outcome_table='support_outcomes' if family=='support' else 'process_outcomes'
        omap={o['case_id']:o for o in data.get(outcome_table,[]) if o['period_id']==p and o['subject_id']==s}
        accepted=timely=adverse=0
        accepted_roots=[]
        for root, es in roots.items():
            if family=='project': continue
            original=sorted(es,key=lambda e:(e['assigned_at'],e['case_id']))[0]
            latest=max(by_case[original['case_id']],key=lambda e:(e['version'],e['event_at']))
            o=omap.get(original['case_id'])
            if o is None:
                pending.append('outcome_missing:'+root); continue
            if day(o.get('observation_end')) is None or day(o['observation_end'])<day(rule['end']):
                pending.append('outcome_not_mature:'+root)
            ok=(latest.get('accepted_at') and latest.get('accepted_by') and latest['accepted_by'] not in own
                and latest['status'] in ('resolved','Done') and stamp(latest['accepted_at'])<= (end_at if data.get('personal_windows') else close_at))
            ok=bool(ok and (o.get('resolved') if family=='support' else o.get('accepted')))
            bad=any(e.get('reopen_of') or e.get('correction_of') for e in es)
            bad=bool(bad or (o.get('repeat_of') if family=='support' else o.get('returned')))
            accepted+=ok; adverse+=bad
            deadline=o.get('sla_due_at') or original.get('due_at')
            timely+=bool(ok and deadline and latest['accepted_at']<=deadline)
            if ok: accepted_roots.append(root)
        pr=[x for x in data['project_records'] if x['period_id']==p and x['subject_id']==s]
        deliverables=defaultdict(list)
        for x in pr: deliverables[x['deliverable_id']].append(x)
        use_min=None; early_min=None; project_type=None; business_config=None; business_ready=None
        if family=='project':
            accepted=0; usages=[]; early=[]
            for root, es in roots.items():
                ps=[x for group in deliverables.values() for x in group if x['parent_id']==root or x['deliverable_id']==root]
                if not ps: pending.append('project_record_missing:'+root); continue
                values={(x.get('criteria_ref'),x.get('criteria_agreed_at'),x.get('acceptance_ref'),x.get('acceptance_at'),
                         x.get('acceptance_owner'),x.get('usage_ref'),x.get('usage_observed_at'),x.get('usage_units'),x.get('usage_owner')) for x in ps}
                if len(values)!=1: pending.append('inconsistent_deliverable_evidence:'+root); continue
                x=ps[0]
                project_type='analytical_business_decision_package' if x.get('usage_measure')=='distinct_business_decisions_using_deliverable' else 'workflow'
                configs=[c for c in PUBLIC_CONFIGS if c['comparison_group_id']==reg['comparison_group_id'] and c['source_query']['period_id']==p and c['work_type']==project_type and c['version']==1]
                if len(configs)!=1:pending.append('business_config_missing_or_ambiguous:'+root)
                else:
                    business_config=configs[0]
                    if stamp(business_config['approved_at'])>=start_at or business_config['owner'] in own:pending.append('business_config_not_prospective_independent')
                    # Legacy refs are left unchanged; addendum refs bind the prospective config version.
                    if x.get('criteria_ref','').startswith('CFG-') and x['criteria_ref']!=business_config['config_id']+'-v1':pending.append('conflicting_business_goal_version')
                if not x.get('criteria_ref') or not day(x.get('criteria_agreed_at')) or day(x['criteria_agreed_at'])>=day(rule['start']):
                    pending.append('prospective_criteria_missing:'+root)
                required=('acceptance_at','acceptance_ref','acceptance_owner','release_ref','release_at','usage_ref','usage_observed_at','usage_owner','usage_coverage')
                if any(not x.get(k) for k in required) or x.get('usage_status')!='present' or x.get('usage_units') is None:
                    pending.append('acceptance_or_use_missing:'+root); continue
                if x['acceptance_owner'] in own or x['usage_owner'] in own: pending.append('self_acceptance_or_use:'+root)
                deadline=stamp(business_config['business_deadline']) if business_config else close_at
                if stamp(x['acceptance_at'])>deadline or stamp(x['release_at'])>deadline or stamp(x['usage_observed_at'])>close_at:
                    fail.append('actual_acceptance_or_use_after_business_deadline:'+root); continue
                if x.get('rollback'): fail.append('rollback:'+root)
                if x['usage_units']<=0: fail.append('unused:'+root)
                # A recognizes complete, accepted and used work; planned use-volume is diagnostic, never quality rank.
                if business_config and business_config['direction']=='binary_completion' and x['usage_units']<1:fail.append('business_decision_not_used:'+root)
                if business_config and business_config.get('readiness_criterion'):
                    ready=stamp(business_config['readiness_criterion']['ready_by'])
                    business_ready=stamp(x['acceptance_at'])<=ready and stamp(x['release_at'])<=ready
                    # Early use only has meaning relative to the one named decision; no extra points for earlier timestamps.
                if day(x['release_at'])>day(x['usage_observed_at']): pending.append('use_before_release:'+root)
                if day(x['acceptance_at'])+timedelta(days=spec['followup_days'])>close:
                    pending.append('acceptance_followup_not_mature:'+root)
                accepted+=1; usages.append(x['usage_units']);accepted_roots.append(root)
                # No fictitious deliverable due-date inferred from child ticket due_at.
                if x.get('commitment_due_at'): early.append((day(x['commitment_due_at'])-day(x['acceptance_at'])).days)
            use_min=min(usages) if usages else None
            early_min=min(early) if len(early)==n and early else None
        rate=fraction(accepted,n); adverse_rate=fraction(adverse,n); sla=fraction(timely,n)
        stretch=False; rank_key=()
        if spec['mode']=='role_conditions':
            if family=='support':
                if rate is not None and rate<F(str(cfg['accepted_min'])):fail.append('resolution_rate')
                if adverse_rate is not None and adverse_rate>F(str(cfg['adverse_max'])):fail.append('repeat_rate')
                stretch=rate==1 and adverse==0 and qmean is not None and qmean>=cfg['stretch_quality']
                rank_key=(rate or F(0),-(adverse_rate or F(0)),qmean or F(0))
            elif family=='backoffice':
                if rate is not None and rate<F(str(cfg['accepted_min'])):fail.append('acceptance_rate')
                if sla is not None and sla<F(str(cfg['sla_min'])):fail.append('sla_below_contract')
                if adverse_rate is not None and adverse_rate>F(str(cfg['adverse_max'])):fail.append('return_rate')
                stretch=rate==1 and sla==1 and adverse==0 and qmean is not None and qmean>=cfg['stretch_quality']
                rank_key=(sla or F(0),rate or F(0),-(adverse_rate or F(0)),qmean or F(0))
            else:
                if accepted<n: reasons.append('not_all_result_evidence_available')
                stretch=accepted==n and qmean is not None and qmean>=cfg['stretch_quality']
                rank_key=(F(min(use_min or 0,cfg['stretch_usage'])),qmean or F(0))
        else:
            if family in ('support','backoffice'):
                # These fields are an explicit new owner check, absent in public fixture.
                contracts=[c for c in data.get('ordinary_commitments',[]) if c['period_id']==p and c['subject_id']==s]
                if len(contracts)!=1:pending.append('ordinary_plan_accept_use_confirmation_missing')
                else:
                    c=contracts[0]
                    required=('plan_ref','agreed_at','owner','scope_ref','acceptance_ref','acceptance_at','usage_ref','usage_at')
                    if any(not c.get(k) for k in required):pending.append('commitment_fields_missing')
                    elif c['owner'] in own or day(c['agreed_at'])>=day(rule['start']):pending.append('commitment_not_prospective_independent')
                    elif day(c['acceptance_at'])>close or day(c['usage_at'])>close:fail.append('commitment_actual_late')
                    elif c.get('accepted') is False or c.get('used') is False:fail.append('commitment_rejected_or_unused')
                    elif c.get('accepted') is not True or c.get('used') is not True:pending.append('commitment_result_unknown')
                    if set(c.get('root_ids',[]))!=set(roots):pending.append('commitment_scope_incomplete')
                    if c.get('accepted') and c.get('used'):
                        stretch=timely==n and n>0 and adverse==0
                # Whole normal service commitment: no residual forgotten work.
                if n and (accepted<n or adverse):fail.append('ordinary_commitment_not_completed')
                rank_key=()  # All eligible stretch commitments tie. No hidden impact score.
            else:
                if accepted<n and not pending:fail.append('planned_stage_not_completed')
                # Normal uses actual prospective stage criteria/accept/use already in record.
                # Stretch additionally requires a preagreed stage due date, not child deadlines.
                stretch=early_min is not None and early_min>=spec['stretch_early_days']
                if early_min is None:reasons.append('stretch_due_date_not_available_normal_unaffected')
                rank_key=()
        # Top is quality only, subject to robust sufficient exposure and normal business conditions.
        quality_exposure=(len(inspections)>=20 and len({e['event_at'][:10] for e in rows})>=10) if family!='project' else (n>=1 and bool(coverage_trace) and all(t['covered'] for t in coverage_trace))
        stretch=qmean is not None and qmean>=cfg['stretch_quality'] and quality_exposure
        rank_key=quality_rank_key(qmean) if stretch else ()
        if fail:state='not_earned';suff='sufficient'
        elif insufficient:state='not_earned';suff='insufficient'
        elif pending:state='not_computable' if any('known_unusable_before_start' in a for a in pending) else 'pending';suff='source_incident' if any('lost_partition' in a or 'checksum' in a for a in pending) else 'insufficient_evidence'
        else:state='earned';suff='sufficient'
        unit={'period':p,'subject':s,'family':family,'group':reg['comparison_group_id'],
              'window_id':reg['window_id'],'cohort_id':reg['cohort_id'],'state':state,'sufficiency':suff,
              'normal':state=='earned','stretch':stretch and state=='earned','rank_key':rank_key,
              'stretch_state':'pending' if spec['mode']=='ordinary_commitment' and family=='project' and early_min is None and state=='earned' else ('earned' if stretch and state=='earned' else state if state!='earned' else 'not_earned'),
              'rank':None,'tie_size':0,'unit_top_R':0,'top_state':'not_earned',
              'roots':n,'accepted_roots':accepted,'acceptance_rate':rate,'sla':sla,'adverse_rate':adverse_rate,
              'qa_inspections':len(inspections),'qa_compatible_acts':len(compatible),'qa_mean':qmean,'quality_category':quality_category(qmean),
              'qa_coverage':coverage_trace,
              'usage_min':use_min,'early_min_days':early_min,'project_type':project_type,'business_config':business_config['config_id'] if business_config else None,'business_ready_by_preread':business_ready,'top_exposure_sufficient':quality_exposure,'active_days':cap['active_days'],
              'scheduled_hours_already_FTE':cap['scheduled_hours'],
              'available_allocated_before_intervals_h':(cap['scheduled_hours']-cap['leave_hours']-cap['training_hours'])*cap['allocation_fraction'],
              'worklog_diagnostic_h':[w['hours'] for w in data['worklog'] if w['period_id']==p and w['subject_id']==s],
              'csat':csat,'reason':sorted(set(fail+insufficient+pending+reasons)),
              'source_refs':{'rule':rule['rule_id'],'registry':reg['registry_id'],'capacity':cap['capacity_id'],
                 'events':[e['event_id'] for e in rows[:3]],'inspection_ids':sorted(inspections)[:3],
                 'project_records':[x['record_id'] for x in pr[:2]]},
              'accepted_root_ids':sorted(accepted_roots)}
        units.append(unit)
    people=[]
    for u in units:
        p,s=u['period'],u['subject']
        ms=[m for m in members if m['period_id']==p and m['team_id']==s]
        if u['family']=='project' and sum(F(str(m['contribution_share'])) for m in ms)>1:raise ValueError('Team shares exceed one')
        persons=[(m['employee_id'],F(str(m['contribution_share'])),m['personal_active_days'],m['window_id'],m['cohort_id']) for m in ms] if u['family']=='project' else [(s,F(1),u['active_days'],u['window_id'],u['cohort_id'])]
        forbidden={s} | {person for person,_,_,_,_ in persons} | {m['employee_id'] for m in members if m['team_id']==s} | {m['team_id'] for m in members if m['employee_id'] in {person for person,_,_,_,_ in persons}}
        for person,share,days,window,cohort in persons:
            a=[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id']==person]
            source_reviews=[v for v in a if v.get('action')=='source_completeness_review']
            source_errors_person=[]
            if data.get('batch_metadata'):
                source_errors_person=list(batch_by_period[p])
                if not source_reviews:source_errors_person.append('source_review_missing')
                else:
                    source_review=max(source_reviews,key=lambda v:v.get('version',0))
                    source_errors_person+=approval_errors(source_review,forbidden,'source_completeness_review')
                    if source_review.get('source_ref')!=p+':'+person:source_errors_person.append('source_review_scope_mismatch')
                    if stamp(source_review.get('signed_at')) and stamp(source_review['signed_at'])<stamp(rules[p,u['family']].get('quality_close_at') or rules[p,u['family']]['quality_close']):source_errors_person.append('source_review_before_quality_close')
                if u['family']=='project':
                    team_reviews=[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id']==s and a.get('action')=='source_completeness_review']
                    if not team_reviews:source_errors_person.append('team_source_review_missing')
                    else:
                        ta=max(team_reviews,key=lambda v:v.get('version',0));source_errors_person+=approval_errors(ta,forbidden,'source_completeness_review')
                        if ta.get('source_ref')!=p+':'+s:source_errors_person.append('team_source_scope_mismatch')
            posting_reviews=[x for x in a if x.get('action')==spec['signature']['posting_action']]
            # Latest version of the required action; an older signature cannot approve a newer edit.
            latest=max(posting_reviews,key=lambda x:(x.get('version',0),x.get('signed_at') or '',x['approval_id'])) if posting_reviews else None
            errors=approval_errors(latest,forbidden,spec['signature']['posting_action'],spec['signature']['distinct_pairs']) if latest else ['performed_posting_review_missing']
            if latest and latest.get('source_ref')!=p+':'+person:errors.append('posting_review_source_scope_mismatch')
            if latest and stamp(latest.get('signed_at')) and stamp(latest['signed_at'])<stamp(rules[p,u['family']].get('quality_close_at') or rules[p,u['family']]['quality_close']):errors.append('authorization_before_quality_close')
            if latest and u['family']=='project' and latest.get('beneficiary_team') not in (None,s):errors.append('posting_review_team_scope_mismatch')
            if any(table=='approvals_audit' for table,_ in source_errors.get(p,[])):errors.append('approval_source_incident')
            errors+=source_errors_person
            # Exact data+policy binding includes every downstream decision deterministically.
            binding={'period':p,'person':person,'source_sha256':data_hash,'rule_sha256':rule_hash,'version':spec['candidate_key']}
            if latest:
                if latest.get('package_binding_sha256')!=digest(binding):errors.append('award_package_hash_or_rule_binding_missing_or_changed')
                if latest.get('source_version') is None:errors.append('award_source_version_missing')
            signed=not errors
            state=u['state'];why=[]
            if days<spec['exposure_days']:state='not_earned';why.append('personal_exposure_insufficient')
            elif not signed and state=='earned':state='pending';why.append('independent_authorization_pending')
            people.append({'period':p,'subject':person,'unit':s,'family':u['family'],'group':u['group'],
                 'window_id':window,'cohort_id':cohort,'share':share,'state':state,'normal':state=='earned',
                 'calculated_qualification_state':u['state'] if days>=spec['exposure_days'] else 'not_earned',
                 'calculated_normal':u['normal'] and days>=spec['exposure_days'],
                 'stretch':u['stretch'] and state=='earned','reason':u['reason']+why,'personal_active_days':days,
                 'posting':'posting_review_signed' if signed else 'new_independent_posting_signature_required',
                 'authorization':'authorized' if signed else 'pending',
                 'authorization_errors':sorted(set(errors)),'source_review_errors':sorted(set(source_errors_person)),
                 'approval_trace':{'required_action':spec['signature']['posting_action'],'selected_approval_id':latest['approval_id'] if latest else None,
                    'source_ref':latest.get('source_ref') if latest else None,'signed_at':latest.get('signed_at') if latest else None,
                    'editor':latest.get('input_editor_id') if latest else None,'signer':latest.get('signer_id') if latest else None,
                    'operator':latest.get('operator_id') if latest else None,'forbidden_beneficiaries':sorted(forbidden),
                    'observed_actions':sorted({str(x.get('action') or '') for x in a}),'errors':errors},
                 'ledger_state':'authorized_U_not_posted' if signed and state=='earned' else 'conditional_reserved_not_U' if state in ('pending','not_computable') else 'no_earned_right',
                 'top_R':0,'potential_top_R':0,'top_reserved_R':0,'top_U_R':0,'top_state':'not_earned','rank':None,'tie_size':0})
    for p,g in sorted({(u['period'],u['group']) for u in units}):
        group=[u for u in units if u['period']==p and u['group']==g]
        eligible=[u for u in group if u['stretch']]
        group_people=[x for x in people if x['period']==p and x['group']==g]
        pool=spec['top_R_per_person']*len({x['subject'] for x in group_people})
        # Unresolved competing results cannot be silently treated as rank losers.
        unsettled=any(u['state'] in ('pending','not_computable') or u['stretch_state']=='pending' for u in group)
        if len(group)<2:continue
        if unsettled:
            for u in group:u['top_state']='pending_group';u['top_reserved_max_R']=pool
            for x in group_people:x['top_state']='pending_group'
            continue
        # Fixed categories never depend on neighboring contestants. Inside a
        # category every eligible portfolio ties; decimal QA is diagnostic only.
        eligible.sort(key=lambda u:u['rank_key'],reverse=True)
        i=0
        while i<len(eligible):
            tied=[u for u in eligible if u['rank_key']==eligible[i]['rank_key']]
            j=i+len(tied)
            award=sum(F(str(spec['top_shares'][r]))*pool for r in range(i,min(j,4)))/len(tied)
            for u in tied:
                u.update(rank=i+1,tie_size=len(tied),unit_top_R=award,top_state='earned' if award else 'not_earned')
                for x in group_people:
                    if x['unit']==u['subject']:
                        x.update(rank=i+1,tie_size=len(tied))
                        x['potential_top_R']=int(award*x['share']) if x['calculated_normal'] else 0
                        if x['state']=='earned':
                            x['top_R']=int(award*x['share']);x['top_U_R']=x['top_R'];x['top_state']='authorized_U' if award else 'not_earned'
                        elif x['state'] in ('pending','not_computable'):
                            x['top_state']='pending_personal_authorization';x['top_reserved_R']=x['potential_top_R']
            i=j
    return units, people

def serial(x):
    if isinstance(x,F):return str(x)
    raise TypeError(type(x).__name__)

def write_csv(path, rows):
    if not rows:return
    candidate=json.loads((HERE/'metrics-spec.json').read_text())['candidate_key']
    rows=[dict(candidate_key=candidate,**row) for row in rows]
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False,default=serial) if isinstance(v,(dict,list,tuple)) else str(v) if isinstance(v,F) else v for k,v in r.items()})

def run():
    spec=json.loads((HERE/'metrics-spec.json').read_text())
    module=importlib.util.spec_from_file_location('public_reader',ADDENDUM/'reader.py')
    reader=importlib.util.module_from_spec(module);module.loader.exec_module(reader)
    decisions=[];unit_rows=[];windows=[];traces=[];groups=[];cal=[];summaries=[]
    for entry in reader.scenario_index(FIXTURE):
        scenario=entry['name'];data=reader.expand_scenario(scenario,FIXTURE);us,ps=evaluate(data,spec)
        states={}
        for u in us:
            states[u['state']]=states.get(u['state'],0)+1
            # All unit numbers remain reproducible without copying raw events.
            unit_rows.append(dict(scenario=scenario,**{k:v for k,v in u.items() if k not in ('qa_coverage','accepted_root_ids')}))
        seen=set()
        for u in us:
            signature=(u['family'],u['state'],u['stretch'],str(u['qa_mean']),tuple(u['reason']))
            if signature not in seen:
                seen.add(signature)
                traces.append({'scenario':scenario,'period':u['period'],'subject':u['subject'],'family':u['family'],'state':u['state'],'qa_mean':u['qa_mean'],'quality_category':u['quality_category'],'normal':u['normal'],'stretch':u['stretch'],'rank':u['rank'],'tie_size':u['tie_size'],'reasons':u['reason'],'refs':u['source_refs'],'coverage':u['qa_coverage'][:2], 'source_locator':entry.get('patch_ref') or entry.get('source_ref') or 'fixtures/source/base.json'})
        for x in ps:
            decisions.append(dict(scenario=scenario,**{k:v for k,v in x.items() if k!='approval_trace'}))
        for p,g in sorted({(u['period'],u['group']) for u in us}):
            gp=[x for x in ps if x['period']==p and x['group']==g];gu=[u for u in us if u['period']==p and u['group']==g]
            pool=150*len({x['subject'] for x in gp});unsettled=any(u['top_state']=='pending_group' for u in gu)
            calculated=sum(x['potential_top_R'] for x in gp);authorized=sum(x['top_U_R'] for x in gp)
            reserved=pool if unsettled else sum(x['top_reserved_R'] for x in gp)
            assert authorized+reserved<=pool
            groups.append(dict(scenario=scenario,period=p,group=g,pool_R=pool,calculated_R=calculated,authorized_U_R=authorized,reserved_R=reserved,unissued_R=pool-authorized-reserved))
        rulemap={(r['period_id'],r['family']):r for r in data['period_rules']}
        for person,window in sorted({(x['subject'],x['window_id']) for x in ps}):
            qs=sorted([x for x in ps if x['subject']==person and x['window_id']==window],key=lambda x:stamp(rulemap[x['period'],x['family']]['start']))
            # First TWO contiguous fixed quarters only: never pick the best two.
            qs=qs[:2];same=len(qs)==2
            if same:
                r0=rulemap[qs[0]['period'],qs[0]['family']];r1=rulemap[qs[1]['period'],qs[1]['family']]
                same=day(r1['start'])==day(r0['end'])+timedelta(days=1)
                pw=[w for w in data.get('personal_windows',[]) if w['subject_id']==person and w['window_id']==window]
                if pw:same=same and day(pw[0]['start'])==day(r0['start'])
            passed=same and all(x['calculated_normal'] for x in qs)
            invalid=any(x['calculated_qualification_state']=='not_earned' for x in qs)
            state='not_earned' if invalid else 'calculated_earned' if passed else 'pending'
            authorized=2500 if passed and all(x['authorization']=='authorized' for x in qs) else 0
            windows.append(dict(scenario=scenario,subject=person,window_id=window,quarters=','.join(x['period'] for x in qs),contiguous_fixed_quarters=same,calculated_state=state,calculated_G_R=2500 if passed else 0,authorized_U_R=authorized,reserved_R=0 if invalid else 2500-authorized,original_window_preserved=True,posted_R=0))
        for e in data['work_events'] if data.get('personal_windows') else []:
            rs=[r for r in data['period_rules'] if r['family']==e['family'] and r['comparison_group_id']==next(z['comparison_group_id'] for z in data['comparison_registry'] if z['subject_id']==e['subject_id'] and z['period_id']==e['period_id'])]
            actual=[r['period_id'] for r in rs if stamp(r['start'])<=stamp(e['event_at'])<=stamp(r['end'],True)]
            qas=[a for a in data['quality_acts'] if a.get('event_id')==e['event_id']]
            r=next(r for r in data['period_rules'] if r['period_id']==e['period_id'])
            cal.append(dict(scenario=scenario,event_id=e['event_id'],subject=e['subject_id'],partition_label=e['period_id'],event_at=e['event_at'],actual_periods=','.join(actual),inside_label=stamp(r['start'])<=stamp(e['event_at'])<=stamp(r['end'],True),quality_close_at=r['quality_close_at'],QA_timely=bool(qas) and all(stamp(a['finalized_at'])<=stamp(r['quality_close_at']) for a in qas),QA_available=bool(qas) and all(a['evidence_status']=='present' for a in qas)))
        summaries.append(dict(scenario=scenario,units=len(us),persons=len(ps),states=states,normal=sum(u['normal'] for u in us),strong=sum(u['stretch'] for u in us),authorized_U_R=sum(x['top_U_R'] for x in ps)))
    write_csv(HERE/'decisions.csv',decisions);write_csv(HERE/'unit-decisions.csv',unit_rows);write_csv(HERE/'window-guarantee.csv',windows);write_csv(HERE/'group-top-reserve.csv',groups);write_csv(HERE/'calendar-boundaries.csv',cal)
    (HERE/'traces.json').write_text(json.dumps({'candidate_key':spec['candidate_key'],'locator_base':'round002 supporting; legacy paths resolve under fixtures; use scenario+table PK to reconstruct through public reader','traces':traces},ensure_ascii=False,indent=2,default=serial)+'\n')
    (HERE/'scenario-summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scenarios':len(summaries),'decisions':len(decisions),'units':len(unit_rows),'compact_traces':len(traces)}))

if __name__=='__main__':run()
