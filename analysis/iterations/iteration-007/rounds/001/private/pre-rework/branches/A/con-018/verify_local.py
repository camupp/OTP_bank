#!/usr/bin/env python3
"""Own reproducibility/property checks only, not independent admission."""
import copy,csv,hashlib,importlib.util,json,random,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BRANCH=HERE.parent
ROUND=HERE.parents[2]
RUN=ROUND.parents[1]
REPO=RUN.parents[2]
F=ROUND/'supporting/fixtures'
checks={}
def load_module(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reader=load_module('allowed_reader',F/'source/reader.py')
parent=json.loads((RUN/'incumbent/finance-spec.json').read_text())
for num in [18,19]:
 folder=BRANCH/f'con-{num:03d}';module=load_module('candidate'+str(num),folder/'evaluator.py');spec=json.loads((folder/'metrics-spec.json').read_text())
 def run(name):return module.evaluate(reader.expand_scenario(name),spec)
 baseline=run('base');rs={}
 b=reader.expand_scenario('base');shuffled=copy.deepcopy(b)
 rng=random.Random(4217)
 for rows in shuffled.values():rng.shuffle(rows)
 rs['row_permutation_invariant']=baseline[:2]==module.evaluate(shuffled,spec)[:2]
 doubled={k:v+copy.deepcopy(v) for k,v in b.items()}
 rs['repeated_entire_export_idempotent']=baseline[:2]==module.evaluate(doubled,spec)[:2]
 rs['worklog_inflation_invariant']=baseline[:2]==run('F02.inflated')[:2]
 rs['worklog_incomplete_invariant']=baseline[:2]==run('F02.incomplete')[:2]
 def selected(rows,unit,period='P1'):return [x for x in rows if x['unit_id']==unit and x['period_id']==period]
 def comparable(rows):return [{k:v for k,v in x.items() if k not in ['source_refs','reason','approval_ref']} for x in rows]
 rs['split_same_root_same_decision_money']=comparable(selected(baseline[0],'T01'))==comparable(selected(run('F07.split')[0],'T01'))
 rs['self_claimed_exceptions_no_benefit']=comparable(selected(baseline[0],'S01'))==comparable(selected(run('F08.self_claimed')[0],'S01'))
 ds=selected(run('F08.documented')[2] if False else run('F08.documented')[0],'S01')
 trace=[x for x in run('F08.documented')[2] if x['subject_id']=='S01' and x['period_id']=='P1'][0]
 rs['overlapping_exceptions_union3h']=trace['union_exception_hours']==3
 rs['source_loss_pending_not_failed']=all(x['eligibility']=='pending' and x['data_status']=='source_incident' for x in run('F10.lost')[0] if x['period_id']=='P1')
 rs['source_restored_original_qualification']=baseline[:2]==run('F10.restored')[:2]
 rs['known_prestart_gap_not_computable']=all(x['eligibility']=='not_computable' for x in run('F10.known_gap')[0] if x['period_id']=='P1')
 conflicted=run('F09.conflicted')
 rs['conflicts_never_self_post']=all(x['posting_status']=='held' for x in conflicted[0] if x['period_id']=='P1' and x['subject_id'] in ['S01','B01','P01'])
 rs['named_alternate_not_fabricated_signature']=all(x['signoff_status']!='signed' for x in conflicted[0] if x['period_id']=='P1' and x['subject_id'] in ['S01','B01','P01'])
 rs['no_response_not_quality_zero']=comparable(selected(baseline[0],'S01'))==comparable(selected(run('F04.no_responses')[0],'S01'))
 rs['flow_SLA_boundaries']=not selected(run('F11.below')[0],'B01')[0]['normal'] and selected(run('F11.at_contract')[0],'B01')[0]['normal'] and selected(run('F11.ceiling')[0],'B01')[0]['normal']
 if num==19:
  rs['stretch_100pct_attainable']=selected(run('F11.ceiling')[0],'B01')[0]['stretch']
  rs['late_actual_acceptance_fails_original_period']=all(x['eligibility']=='not_earned' for x in selected(run('F03.late_acceptance')[0],'T01'))
  rs['done_without_evidence_pending']=all(x['eligibility']=='pending' for x in selected(run('F03.done_only')[0],'T01'))
 else:
  rs['project_root_norm_gap_visible']=all(x['eligibility']=='not_computable' and x['denominator'] is None for x in baseline[0] if x['family']=='project')
 finance=json.loads((folder/'finance-spec.json').read_text());keys=finance['reward_core']['keys_unchanged']
 normalized=copy.deepcopy(finance)
 for path,value in finance['metric_text_overrides'].items():
  section,key=path.split('.');normalized[section][key]=parent[section][key]
 rs['frozen_reward_money_equal_except_explicit_metric_text_and_path']=all(normalized[k]==parent[k] for k in keys)
 rs['embedded_inherited_policy_exact']=all(finance['inherited_reward_policy'][k]==parent[k] for k in keys)
 rs['calendar_source_recoverable']=(folder/finance['calendar']['source']).resolve().is_file()
 resources=list(csv.DictReader((folder/'resource-sensitivity.csv').open()))
 rs['QA_resource_priced_per_source_inspection']=all(abs(float(x['new_QA_hours_month'])-4060*(1-float(x['QA_reuse']))*float(x['labor_multiplier']))<1e-8 for x in resources)
 rs['frozen_core_file_hashes']=all(sha(REPO/x['path'])==x['sha256'] for x in finance['reward_core']['monetary_core_file_refs'])
 rs['fixture_manifest_hash']=sha(F/'manifest.json')==spec['source_manifest_sha256']
 allrows=list(csv.DictReader((folder/'decisions.csv').open()));money=list(csv.DictReader((folder/'money-examples.csv').open()))
 rs['base_plus22_scenarios_368_person_periods']=len({x['scenario'] for x in allrows})==23 and len(allrows)==368
 rs['one_person_period_per_scenario']=len({(x['scenario'],x['period_id'],x['subject_id']) for x in allrows})==len(allrows)
 rs['one_G_in_window']=all(sum(int(x['guarantee_R']) for x in money if x['scenario']==s and x['subject_id']==p)<=2500 for s,p in {(x['scenario'],x['subject_id']) for x in money})
 rs['top_person_pool_bounded']=all(sum(int(x['top_R']) for x in money if x['scenario']==s and x['period_id']==p and x['family']==fam)<=150*len([x for x in money if x['scenario']==s and x['period_id']==p and x['family']==fam]) for s,p,fam in {(x['scenario'],x['period_id'],x['family']) for x in money})
 rs['no_approved_U_without_signed']=all((x['signature']=='signed' or (int(x['approved_top_U_R'])==0 and int(x['approved_G_U_R'])==0)) for x in money)
 required=['concept.md','cards.md','metrics-spec.json','evaluator.py','decisions.csv','traces.json','money-examples.csv','employee-card.md','source-to-award.md','finance-spec.json','assumptions.csv','changes.md','resource-sensitivity.csv','peak-resource.csv']
 rs['required_files']=all((folder/x).is_file() for x in required)
 import re
 links=[]
 for name in ['concept.md','cards.md','employee-card.md','source-to-award.md']:
  for link in re.findall(r'\]\(([^)]+)\)',(folder/name).read_text()):
   if '://' not in link and not link.startswith('#'):links.append((folder/link.split('#')[0]).exists())
 rs['local_markdown_links_resolve']=all(links)
 rs['eight_concept_sections']=sum(line.startswith('## ') for line in (folder/'concept.md').read_text().splitlines())==8
 result={'candidate_key':spec['candidate_key'],'classification':'author self-check only; no independent finance/evidence/reviewer admission','runtime':sys.version,'checks':rs,'all_own_checks_pass':all(rs.values()),'remaining':['Real source/API/capacity/catalog/employee value unverified','Qualification examples use synthetic calendar quarters, not actual personal15th-day windows; production export exact window needed','Missing independent signatures deliberately held; named alternate not executed approval','CON-018 project root-capacity norm absent, project coverage not established' if num==18 else 'Assigned-root cohort completeness and stage scope prospective;1root causes coarse ties, not universal project value'],'artifacts_sha256':{x:sha(folder/x) for x in required}}
 (folder/'self-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(spec['candidate_key'],json.dumps(rs,ensure_ascii=False))
 checks[str(num)]=result['all_own_checks_pass']
if not all(checks.values()):raise SystemExit(1)
