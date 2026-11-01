#!/usr/bin/env python3
"""Author checks only; not independent reviewer admission. No fixture writes."""
import sys
sys.dont_write_bytecode=True
import copy,hashlib,importlib.util,json,random
from pathlib import Path
H=Path(__file__).resolve().parent
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ev=mod('own_eval',H/'evaluator.py');reader=mod('reader',ev.FIXTURE/'source/reader.py')
spec=json.loads((H/'metrics-spec.json').read_text())
def normalize(data):
 for m in data['source_manifest']:
  rows=[r for r in data[m['table']] if r.get('period_id',m['period_id'])==m['period_id']]
  m['received_count']=len(rows);m['expected_count']=len(rows)
  m['received_sha256']=hashlib.sha256((json.dumps(rows,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
def result(data):
 u,p=ev.evaluate(data,spec)
 return sorted([(r['period'],r['subject'],r['state'],r['stretch'],r['rank'],r['tie_size'],r['top_R'],r['top_state']) for r in p])
base=reader.expand_scenario('base');expected=result(base)
shuffled=copy.deepcopy(base)
for table,rows in shuffled.items():
 if table!='source_manifest':random.Random(2026).shuffle(rows)
normalize(shuffled)
dup=copy.deepcopy(base);dup['work_events'].append(copy.deepcopy(dup['work_events'][0]));normalize(dup)
checks={
 'row_order_awards_invariant':result(shuffled)==expected,
 'exact_duplicate_awards_invariant':result(dup)==expected,
 'worklog_inflated_invariant':result(reader.expand_scenario('F02.inflated'))==expected,
 'worklog_incomplete_invariant':result(reader.expand_scenario('F02.incomplete'))==expected,
 'deliverable_split_awards_invariant':result(reader.expand_scenario('F07.split'))==expected,
 'source_restore_original_result':result(reader.expand_scenario('F10.restored'))==expected,
}
def unit(scenario,subject):
 return next(r for r in ev.evaluate(reader.expand_scenario(scenario),spec)[0] if r['period']=='P1' and r['subject']==subject)
if spec['mode']=='role_conditions':
 checks.update(SLA90_fails=unit('F11.below','B01')['state']=='not_earned',
               SLA95_normal=unit('F11.at_contract','B01')['normal'],
               SLA100_stretch=unit('F11.ceiling','B01')['stretch'])
else:
 checks.update(flow_missing_use_is_pending=unit('base','S01')['state']=='pending',
               project_existing_accept_use_normal=unit('base','T01')['normal'],
               project_missing_stretch_date_pending=unit('base','T01')['stretch_state']=='pending')
checks.update(known_source_gap_not_computable=unit('F10.known_gap','S01')['state']=='not_computable',
 lost_QA_not_personal_fail=unit('F10.lost','S01')['state']=='pending',
 actual_late_acceptance_fails=unit('F03.late_acceptance','T01')['state']=='not_earned',
 done_without_evidence_pending=unit('F03.done_only','T01')['state']=='pending')
# Actual alternate names alone cannot turn a conflicted signature into a signed award.
_,persons=ev.evaluate(reader.expand_scenario('F09.conflicted'),spec)
checks['no_self_signed_person']=all(r['state']!='earned' and r['posting']!='signed' for r in persons if r['period']=='P1' and r['subject'] in ('S01','B01','P01'))
countertraces=[]
def altered_approval(case,changes,person='P01'):
 data=copy.deepcopy(base)
 a=next(x for x in data['approvals_audit'] if x['period_id']=='P1' and x['beneficiary_id']==person)
 a.update(changes);normalize(data)
 us,ps=ev.evaluate(data,spec)
 row=next(x for x in ps if x['period']=='P1' and x['subject']==person)
 countertraces.append({'case':case,'subject':person,'posting':row['posting'],'authorization':row['authorization'],
  'calculated_qualification_state':row['calculated_qualification_state'],'state':row['state'],'approval_trace':row['approval_trace'],
  'potential_top_R':row['potential_top_R'],'authorized_top_R':row['top_R'],'reserved_top_R':row['top_reserved_R']})
 return row
bad_approvals={
 'SIG-B-NO-TIME':{'signed_at':None},
 'SIG-B-EMPTY-TIME':{'signed_at':''},
 'SIG-B-TEAM-SIGNER':{'signer_id':'P02'},
 'SIG-B-TEAM-EDITOR':{'input_editor_id':'P02'},
 'SIG-B-TEAM-OPERATOR':{'operator_id':'P02'},
 'SIG-B-SAME-ACTOR':{'operator_id':'OWNER-INDEPENDENT-01'},
 'SIG-B-EDITOR-SIGNER-COLLISION':{'input_editor_id':'OWNER-INDEPENDENT-01'},
 'SIG-B-EDITOR-OPERATOR-COLLISION':{'input_editor_id':'HR-INDEPENDENT-01'},
 'SIG-B-EMPTY-EDITOR':{'input_editor_id':None},
 'SIG-B-EMPTY-SIGNER':{'signer_id':''},
 'SIG-B-EMPTY-OPERATOR':{'operator_id':''},
 'SIG-B-WRONG-ACTION':{'action':'type_correction'},
 'SIG-B-SIGNER-REPORTS-TEAM':{'signer_reporting_to':'P02'},
 'SIG-B-OPERATOR-REPORTS-TEAM':{'operator_reporting_to':'P02'},
 'SIG-B-EDITOR-REPORTS-TEAM':{'input_editor_reporting_to':'P02'},
 'SIG-B-WRONG-SOURCE':{'source_ref':'other-period:other-person'},
 'SIG-B-WRONG-TEAM-SCOPE':{'beneficiary_team':'T02'},
}
for name,changes in bad_approvals.items():
 row=altered_approval(name,changes)
 checks[name]=row['authorization']=='pending' and row['posting']!='posting_review_signed' and row['state']=='pending' and row['top_R']==0
 # Invalid posting does not erase computed eligibility or manufacture authorized U.
 checks[name+'-RIGHT-RETAINED']=row['calculated_normal'] and row['ledger_state']=='conditional_reserved_not_U'
 if spec['mode']=='role_conditions':checks[name+'-SHARE-HELD']=row['potential_top_R']==144 and row['top_reserved_R']==144
good=altered_approval('SIG-B-VALID-CONTROL',{})
checks['SIG-B-VALID-CONTROL']=good['authorization']=='authorized' and good['posting']=='posting_review_signed' and good['ledger_state']=='authorized_U_not_posted'
reapproved=copy.deepcopy(base)
old=next(x for x in reapproved['approvals_audit'] if x['approval_id']=='P1:P01')
replacement=copy.deepcopy(old);old['signer_id']='P01'
replacement.update(approval_id='REVIEW-NEW-VERSION',version=2,signed_at='2026-04-28T11:00:00+03:00')
reapproved['approvals_audit'].append(replacement);normalize(reapproved)
_,rps=ev.evaluate(reapproved,spec)
checks['SIG-B-ACTUAL-REAPPROVAL-RESTORES-U']=next(x for x in rps if x['period']=='P1' and x['subject']=='P01')['ledger_state']=='authorized_U_not_posted'
# A type correction can be valid in its own right, never the required posting review.
corrected=copy.deepcopy(next(x for x in base['approvals_audit'] if x['approval_id']=='P1:P01'));corrected['action']='type_correction'
checks['TYPE-CORRECTION-ACTION-SEPARATE']=ev.independent_approval(corrected,{'T01','P01','P02'},'type_correction',spec['signature']['distinct_pairs']) and not ev.independent_approval(corrected,{'T01','P01','P02'},spec['signature']['posting_action'],spec['signature']['distinct_pairs'])
partial=copy.deepcopy(base)
partial['quality_acts']=[a for a in partial['quality_acts'] if a['period_id']!='P1' or a['subject_id']!='T02' or a['act_id']=='QA-P1-T02-001']
normalize(partial)
us,ps=ev.evaluate(partial,spec)
q=next(x for x in us if x['period']=='P1' and x['subject']=='T02')
checks['QA-B-PART-COVERAGE']=q['state']=='pending' and any(len(x['missing_case_ids'])==7 and x['case_scoped_covered_count']==1 and not x['covered'] for x in q['qa_coverage'])
checks['QA-B-PART-NO-AUTHORIZED-GROUP-TOP']=all(x['top_R']==0 for x in ps if x['period']=='P1' and x['group']==q['group'])
countertraces.append({'case':'QA-B-PART-COVERAGE','subject':'T02','state':q['state'],'qa_inspections':q['qa_inspections'],'coverage':q['qa_coverage']})
split_u,_=ev.evaluate(reader.expand_scenario('F07.split'),spec)
split=next(x for x in split_u if x['period']=='P1' and x['subject']=='T01')
checks['QA-B-ACTUAL-WHOLE-DELIVERABLE-REUSE']=split['normal'] and any(x['whole_deliverable_act_ids'] and x['covered'] and x['required_case_count']==8 for x in split['qa_coverage'])
countertraces.append({'case':'QA-B-ACTUAL-WHOLE-DELIVERABLE-REUSE','subject':'T01','state':split['state'],'coverage':split['qa_coverage']})
# Third class: special/appeal/correction coverage and source-case QA resource reconciliation.
import csv
fin=json.loads((H/'finance-spec.json').read_text());resources=fin['workload']['readiness_scenarios']
checks['RES-QA-48720-4060-2030-0']=[r['new_missing_QA_h_month'] for r in resources]==[4060,2030,0]
checks['RES-EXISTING-QA-ONCE']=all(r['existing_business_QA_h_month']==2436 for r in resources)
c=fin['workload']['special_and_appeal_counters']
checks['RES-SPECIAL-200-32-FULL']=c['special_hours_month']=={'HR':16,'manager':36,'employee':20} and c['special_resource_RUB_year']==1080000
checks['RES-APPEALS-NOT-FREE']=c['appeals_month']==120 and c['appeal_HR12h_owner24h_already_in_base_exceptions'] and c['appeal_employee10h_new']
checks['RES-CORRECTIONS-NOT-FREE']=c['corrections_month']==72 and c['correction_new_hours_month']=={'HR':6,'manager':6,'employee':3.6}
stages=list(csv.DictReader((H/'resource-stages.csv').open()))
totals={role:sum(float(x['hours_month']) for x in stages if x['owner']==role and x['existing']=='False') for role in ('HR','manager','employee','IT')}
declared=resources[-1]['new_recognition_hours_month_by_role']
checks['RES-EVERY-ROLE-HOUR-HAS-STAGE']=all(abs(totals[k]-declared[k])<1e-9 for k in totals)
checks['RES-EACH-STAGE-COUNT-X-MINUTES']=all(abs(float(x['units_month'])*float(x['minutes_unit'])/60-float(x['hours_month']))<1e-9 for x in stages)
checks['RES-SPECIAL-COUNTERS-NO-REWARD-CHANGE']=fin['scenario_parameters']['24000000']['special_R_month']==140000 and fin['special']['personal_awards_year_max']==2
group_reserves=list(csv.DictReader((H/'group-top-reserve.csv').open()))
checks['MONEY-GROUP-RESERVE-ONE-ROW']=len({(x['scenario'],x['period'],x['group']) for x in group_reserves})==len(group_reserves)
checks['MONEY-GROUP-AUTHORIZED-RESERVE-UNISSUED-BALANCE']=all(int(x['authorized_U_R'])+int(x['conditional_reserved_R'])+int(x['unissued_R'])==int(x['pool_cap_R']) for x in group_reserves)
countertraces.append({'case':'RES-TRANSPARENT-SPECIAL-APPEAL-CORRECTION','counters':c,'role_hours_month':totals,'regular_resource_RUB_year':resources[-1]['new_resource_RUB_year']})
(H/'rework-counterexamples.json').write_text(json.dumps({'candidate_key':spec['candidate_key'],'type':'author regression cases, transient in-memory public-source copies only','cases':countertraces},ensure_ascii=False,indent=2,default=ev.serial)+'\n')
out={'candidate_key':spec['candidate_key'],'type':'author self-check; not independent admission','python':sys.version.split()[0],'checks':checks,'all_pass':all(checks.values())}
(H/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
if not out['all_pass']:raise SystemExit(1)
