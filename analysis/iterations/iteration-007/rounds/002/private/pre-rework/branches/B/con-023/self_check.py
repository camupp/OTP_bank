#!/usr/bin/env python3
"""Author checks only; no independent gate decision and no writes to inputs.
Run after evaluator.py/build_resources.py/make_money_examples.py with python3 -B.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,importlib.util,copy,math,re
from pathlib import Path
from collections import Counter,defaultdict
HERE=Path(__file__).resolve().parent
ROUND=HERE.parents[2]
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists() and (p/'project').exists())
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(name):return list(csv.DictReader((HERE/name).open()))
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
checks=[]
def check(name,ok,locator,detail=''):
 checks.append(dict(name=name,status='pass' if ok else 'fail',locator=locator,detail=detail))
ev=module('candidate',HERE/'evaluator.py')
reader=module('public_reader',ROUND/'supporting/round002-stress/reader.py')
old=ROUND/'supporting/fixtures';stress=ROUND/'supporting/round002-stress'
spec=load(HERE/'metrics-spec.json');finance=load(HERE/'finance-spec.json');configs=load(stress/'business-config.json')['configs']
provenance=[]
for root,expected in [(old,'2a8d8effe027296dd4a0b52a2717b2c8ac2dc75303af3f1bf56f8f8540ad3edc'),(stress,'206b8c7cc0e84021c01b3d2f544a07ac909536e5f7498766809eee127532210c')]:
 check('C1_manifest_'+root.name,sha(root/'manifest.json')==expected,str((root/'manifest.json').relative_to(ROOT)))
 for f in load(root/'manifest.json')['files']:
  rel=f['path']
  # These entries may be named in the old manifest but are not assigned inputs.
  if any(x in Path(rel).parts for x in ('oracle','private','coordinator-only')) or Path(rel).name in ('generator.py','validation.json'):continue
  p=root/rel;ok=sha(p)==f['sha256'];check('C1_public_file_hash',ok,str(p.relative_to(ROOT)))
  provenance.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
inp=load(ROUND/'inputs/manifest.json')
check('C1_fingerprint',inp['fingerprint']==spec['input_fingerprint'],'inputs/manifest.json#fingerprint')
for rel,expected in inp['files'].items():check('C1_frozen_input',sha(ROUND/'inputs'/rel)==expected,'inputs/'+rel)
for rel,expected in finance['money_core_reused_no_reexecution'].items():
 check('C5_money_reuse_SHA',sha(ROOT/rel)==expected,rel)
 provenance.append(dict(path=rel,sha256=sha(ROOT/rel)))
check('C1_business_v1_prospective',all(ev.day(c['approved_at'])<ev.day(c['valid_from']) for c in configs if c['version']==1),'supporting/round002-stress/business-config.json#configs[version=1]')
check('C1_source_only_no_panel_rule',all(s not in (HERE/'evaluator.py').read_text() for s in ("/'oracle'","/'private'","generator.py","if name==","if name ==","if s=='S","if s == 'S")),'evaluator.py#evaluate','Names are output labels; this textual check is supplemented by the published function signature/code review.')
u=rows('unit-decisions.csv');p=rows('decisions.csv');g=rows('group-top-reserve.csv');w=rows('window-guarantee.csv');calendar=rows('calendar-traces.csv')
check('C2_all38',len(set(r['scenario'] for r in u))==len(reader.scenario_index(old))==38,'unit-decisions.csv#scenario')
def sig(r):return tuple(r[k] for k in ('state','normal','strong','rank','tie_size','top_R'))
base={(r['period'],r['subject']):r for r in u if r['scenario']=='base'}
for scenario in ('F02.inflated','F02.incomplete','F07.split','F04.no_responses'):
 other={(r['period'],r['subject']):r for r in u if r['scenario']==scenario}
 check('C2_no_gain_'+scenario,all(sig(r)==sig(other[k]) for k,r in base.items()),'unit-decisions.csv#scenario='+scenario)
for fam in ('support','backoffice','project'):
 rs=[r for r in u if r['scenario']=='R1.volume' and r['family']==fam and r['period']=='P1']
 normal=[r for r in rs if r['normal']=='True' and r['strong']=='False'];strong=[r for r in rs if r['strong']=='True']
 check('C2_ordinary_strong_'+fam,bool(normal) and len(set(r['result'] for r in strong))>=2 and len(set(r['rank'] for r in strong))>=2,'unit-decisions.csv#R1.volume/P1/'+fam)
 check('C2_equal_quality_different_result_'+fam,len(set(json.loads(r['quality'])['score'] for r in rs))==1,'unit-decisions.csv#R1.volume/P1/'+fam)
 before={(r['period'],r['subject']):sig(r) for r in u if r['scenario']=='R1.volume' and r['family']==fam}
 for sc in ('R2.quality','R2.precision','R2.small_csat'):
  after={(r['period'],r['subject']):sig(r) for r in u if r['scenario']==sc and r['family']==fam}
  check('C2_QA_is_gate_'+fam+'_'+sc,before==after,'unit-decisions.csv#'+sc)
 # Explicit author probes use an unchanged complete source with just exposure reduced.
 d=reader.expand_scenario('base',old);s=next(x['subject_id'] for x in d['roster_capacity'] if x['family']==fam)
 for c in d['roster_capacity']:
  if c['subject_id']==s:c['active_days']=0
 for m in d['source_manifest']:
  if m['table']=='roster_capacity':
   rr=[x for x in d[m['table']] if x.get('period_id',m['period_id'])==m['period_id']];m['received_sha256']=ev.digest(rr)
 us,_=ev.evaluate(d,spec,configs)
 check('C2_insufficient_'+fam,all(x['state']=='insufficient' for x in us if x['subject']==s),'author in-memory base probe#roster_capacity.active_days=0; physical manifest recomputed','Probe only; shared source unchanged.')
 check('C2_pending_'+fam,any(r['state']=='pending' and r['family']==fam and r['scenario']=='F10.lost' for r in u),'unit-decisions.csv#F10.lost/'+fam)
analytical=[r for r in u if r['scenario']=='R3.analytical' and r['family']=='project' and r['period']=='P1']
check('C2_analytical_three_strong_tied',sum(r['strong']=='True' for r in analytical)==3 and all(r['rank']=='1' and r['tie_size']=='3' for r in analytical if r['strong']=='True'),'unit-decisions.csv#R3.analytical/P1/project')
check('C2_analytical_ordinary_path',sum(r['normal']=='True' and r['strong']=='False' for r in analytical)==3,'unit-decisions.csv#R3.analytical/P1/project')
check('C2_conflicting_goal_pending',any('conflicting_goal_version' in r['reason'] and r['state']=='pending' for r in u if r['scenario']=='R3.conflicting_goal'),'unit-decisions.csv#R3.conflicting_goal')
check('C3_partial_root_pending',any(r['family']=='project' and r['state']=='pending' for r in u if r['scenario']=='R2.incomplete_root'),'unit-decisions.csv#R2.incomplete_root')
a=dict(action=spec['posting_action'],signed_at='2026-04-28T10:00:00+03:00',input_editor_id='E',signer_id='S',operator_id='O')
check('C3_good_performed_action',not ev.approval_errors(a,{'BEN','MATE'},spec['posting_action']),'self_check.py#direct approval primitive')
for key,value,label in [('signed_at',None,'no_timestamp'),('signed_at','','empty_timestamp'),('signed_at','invalid','invalid_timestamp'),('action',spec['source_action'],'wrong_action'),('signer_id','BEN','self_signer'),('signer_id','MATE','whole_team_conflict'),('operator_id','S','same_signer_operator'),('input_editor_id','','empty_editor'),('signer_reporting_to','MATE','reporting_conflict'),('operator_reporting_to',['OTHER','BEN'],'list_reporting_conflict')]:
 z=copy.deepcopy(a);z[key]=value
 check('C3_'+label,bool(ev.approval_errors(z,{'BEN','MATE'},spec['posting_action'])),'self_check.py#direct approval primitive/'+label)
check('C3_missing_source_timestamp_detected',any('signed_at_missing_or_invalid' in r['source_review_errors'] for r in p if r['scenario']=='R1.missing_signature'),'decisions.csv#R1.missing_signature')
check('C3_conflicted_team_detected',any('beneficiary_actor' in r['source_review_errors'] or 'reporting_conflict' in r['source_review_errors'] for r in p if r['scenario']=='R1.conflicted_signature'),'decisions.csv#R1.conflicted_signature')
check('C3_batch_changed_detected',any('registry_changed_after_batch' in r['source_review_errors'] for r in p if r['scenario']=='R1.batch_changed'),'decisions.csv#R1.batch_changed')
check('C3_source_review_never_U',all(float(r['top_U_R'])==0 and r['authorization']=='held_no_authorization' for r in p if r['scenario'].startswith(('R1.','R2.','R3.','R4.'))),'decisions.csv#R1–R4','New public panels have source-review only; actual award authorization is absent.')
check('C5_group_conservation',all(abs(float(r['pool_R'])-float(r['earned_R'])-float(r['conditional_R'])-float(r['unissued_R']))<1e-7 and float(r['authorized_U_R'])<=float(r['earned_R']) for r in g),'group-top-reserve.csv#every row')
check('C5_G_conservation',all(float(r['G_earned_R'])==float(r['G_U_R'])+float(r['G_earned_held_R']) and not(float(r['G_earned_R']) and float(r['G_conditional_ceiling_R'])) for r in w),'window-guarantee.csv#every row')
check('C5_R4_original_window_and_boundaries',len({r['window'] for r in calendar})==9 and all(r['fixed_window_unchanged']=='True' for r in calendar) and any(r['calendar_result']=='outside_interval' for r in calendar),'calendar-traces.csv#9windows')
check('C5_R4_restoration',any(r['scenario']=='R4.boundaries' and r['calendar_result']=='evidence_restoration_pending' for r in calendar) and any(r['scenario']=='R4.restored' and r['calendar_result']=='timely_fact_received' for r in calendar),'calendar-traces.csv#R4.boundaries/R4.restored','Boundary probes do not compute complete award/census.')
monthly=rows('monthly-resource.csv');annual=rows('annual-resource.csv');rates=finance['booking']['rates_RUB_h'];series=defaultdict(list)
for r in monthly:series[tuple(r[k] for k in ('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role'))].append(r)
check('C4_calendar_shape',len(monthly)==11232 and len(annual)==1440 and all({int(r['month']) for r in rs}==set(range(1,40)) for rs in series.values()),'monthly-resource.csv/annual-resource.csv')
arithmetic=True;queue_ok=True
for key,rs in series.items():
 prev=0
 for r in sorted(rs,key=lambda r:int(r['month'])):
  f=lambda k:float(r[k]);rate=rates[r['role']]
  arithmetic &= abs(f('demand_h')-f('existing_activity_h')-f('new_activity_h'))<1e-7 and abs(f('total_capacity_h')-f('base_available_h')-f('booked_h'))<1e-7
  arithmetic &= abs(f('booked_h')-f('reserve_used_h')-f('paid_idle_h'))<1e-7 and abs(f('reservation_cash_RUB')-f('booked_h')*rate)<1e-7
  arithmetic &= abs(f('full_cost_work_plus_idle_RUB')-(f('demand_h')+f('paid_idle_h'))*rate)<1e-5
  arithmetic &= abs(f('new_operating_cash_RUB')-f('reservation_cash_RUB')-float(r['substitution'])*min(f('demand_h'),f('base_available_h'))*rate)<1e-5
  queue_ok &= abs(f('queue_start_h')-prev)<1e-7 and abs(f('queue_end_h')-max(0,prev+f('demand_h')-f('total_capacity_h')))<1e-7
  prev=f('queue_end_h')
check('C4_no_double_resource_cash',arithmetic,'monthly-resource.csv#all11232')
check('C4_queue_continuity',queue_ok,'monthly-resource.csv#all11232')
annual_ok=True
for r in annual:
 key=tuple(r[k] for k in ('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution','role'));lo,hi={'year1':(1,12),'year2':(13,24),'year3':(25,36),'tail':(37,39),'all39':(1,39)}[r['period']]
 xs=[x for x in series[key] if lo<=int(x['month'])<=hi]
 for target,source in [('demand_h','demand_h'),('booked_h','booked_h'),('reserve_cash_RUB','reservation_cash_RUB'),('actual_work_RUB','activity_cost_RUB'),('full_RUB','full_cost_work_plus_idle_RUB'),('new_operating_cash_RUB','new_operating_cash_RUB')]:annual_ok &= abs(float(r[target])-sum(float(x[source]) for x in xs))<1e-4
 annual_ok &= abs(float(r['peak_h'])-max(float(x['demand_h']) for x in xs))<1e-7
check('C4_annual_from_same_months',annual_ok,'annual-resource.csv#all1440')
profiles=defaultdict(list)
for r in monthly:profiles[tuple(r[k] for k in ('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution'))].append(r)
capacity=[]
for key,rs in profiles.items():
 failed=sorted({r['role'] for r in rs if float(r['queue_end_h'])>1e-7})
 capacity.append(dict(zip(('scenario','fixed_C_year','QA_reuse','labor_multiplier','substitution'),key))|dict(state='fail' if failed else 'conditional_monthly_capacity_only',failed_roles=failed,new_operating_cash_39_RUB=sum(float(r['new_operating_cash_RUB']) for r in rs),full_cost_39_RUB=sum(float(r['full_cost_work_plus_idle_RUB']) for r in rs)))
check('C4_HR220_not_silent_reserve',all(r['HR220_only_state']==('pass' if float(r['demand_h'])<=220 else 'fail') for r in monthly if r['role']=='HR'),'monthly-resource.csv#HR220_only_state')
check('C4_known_fails_retained',all(c['state']=='fail' for c in capacity if c['labor_multiplier']=='2') and all(c['state']=='fail' for c in capacity if c['scenario']=='JAN_OLD50' and c['fixed_C_year']=='144000000'),'monthly-resource.csv#x2/JAN_OLD50_fixed144')
check('C5_E24_unchanged',finance['unchanged']['G_ceiling_R_year']+finance['unchanged']['top_R_year']+finance['unchanged']['special_R_year']==finance['unchanged']['E_R_year']==24000000,'finance-spec.json#unchanged')
links=[]
for f in HERE.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
  if '://' in target or target.startswith('#'):continue
  if not (f.parent/target.split('#')[0]).exists():links.append(str(f.name)+':'+target)
check('documentation_local_links',not links,'*.md',str(links))
limitations=[
 'C2: full R4 award is not established by boundary-only source; calendar-audit only. Source systems, local targets and causal effects remain assumptions.',
 'C3: actual posting ledger, performed award authorization for the new panels, and full signed award-register hash are absent. No real payment or independent authorization acceptance claimed.',
 'C4: conditional arithmetic capacity is not confirmed people/funding or proof of submonth SLA. No person-level qualified roster or timed rehearsal has been performed. Finite role positions and readiness are design prerequisites; employee requests remain time of the actual applicants, not four substitute claimants.',
 'C4: x2 and JAN_OLD50/fixed144 fail. Above the12 incident/month envelope, assurance needs a new capacity decision; existing rights and original dates persist.',
 'C5: inherited money model was SHA-verified, not executed. Full currency/cash/stock grid and regional SKU adequacy require independent finance assessment. Existing narrow34m/fixed96 scope is not extended.',
 'C6: unchanged baseline/CON-016 and the other current branch were not evaluated by this author. Common comparison is coordinator/independent-check work.',
 'C7: independent finance/evidence/blinded review and selection are not done by this author. Self-check cannot grant gates.'
]
result=dict(candidate_key='CON-023@v1',classification='author self-check, not independent review or deployment approval',python_version=sys.version.split()[0],checks=checks,counts=dict(Counter(c['status'] for c in checks)),source_scenarios=38,decision_rows=len(p),unit_rows=len(u),calendar_rows=len(calendar),monthly_resource_rows=len(monthly),annual_resource_rows=len(annual),capacity_profiles=capacity,scope_counts=dict(Counter(c['state'] for c in capacity)),limitations=limitations)
(HERE/'self-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(HERE/'provenance.json').write_text(json.dumps(dict(candidate='CON-023@v1',input_fingerprint=spec['input_fingerprint'],files=provenance,scope='assigned public source and inherited money references only; no restricted files read'),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('counts','source_scenarios','decision_rows','unit_rows','calendar_rows','monthly_resource_rows','annual_resource_rows','scope_counts')}))
if any(c['status']=='fail' for c in checks):
 print(json.dumps([c for c in checks if c['status']=='fail'],ensure_ascii=False));sys.exit(1)
