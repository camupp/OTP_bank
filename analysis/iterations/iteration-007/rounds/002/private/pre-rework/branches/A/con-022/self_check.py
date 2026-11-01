#!/usr/bin/env python3
"""Author self-check C1–C7; public sources only, no independent admission.

Run python3 -B self_check.py after evaluator.py and build_resources.py.
All writes stay beside this script. Synthetic authorization mutations are tests,
not performed bank actions. Closed snapshots are read, never executed.
"""
import sys
sys.dont_write_bytecode = True
import ast, copy, csv, hashlib, importlib.util, json, math
from collections import defaultdict
from datetime import timedelta
from fractions import Fraction as F
from pathlib import Path

P=Path(__file__).resolve().parent; R=P.parents[2]; ROOT=R.parents[4]
def load(path):return json.loads(path.read_text())
def rows(path):return list(csv.DictReader(path.open()))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def imp(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ev=imp('candidate_evaluator',P/'evaluator.py')
reader=imp('public_source_reader',R/'supporting/round002-stress/reader.py')
spec=load(P/'metrics-spec.json'); old=R/'supporting/fixtures'
checks=[]; detail={}
def check(gate,name,ok,locator,observed=None):
    checks.append(dict(check=gate,name=name,status='pass' if ok else 'fail',locator=locator,observed=observed))
def refresh(d,table):
    for m in d['source_manifest']:
        if m['table']==table:
            rr=[x for x in d[table] if x.get('period_id',m['period_id'])==m['period_id']]
            m.update(received_count=len(rr),expected_count=len(rr),received_sha256=ev.digest(rr),availability='available')
def result(d,period,subject,personal=False,sp=None):
    us,ps=ev.evaluate(d,sp or spec)
    return next(x for x in (ps if personal else us) if x['period']==period and x['subject']==subject)

# C1: only the explicitly public members, never generator/validation/oracle.
manifest=load(R/'inputs/manifest.json')
check('C1','frozen five inputs',all(sha(R/'inputs'/k)==v for k,v in manifest['files'].items()),'inputs/manifest.json',manifest['fingerprint'])
hashes=load(P/'finance-spec.json')['source_hashes']
check('C1','source and money SHA',all(sha(ROOT/k)==v for k,v in hashes.items()),'finance-spec.json#source_hashes',hashes)
pub=load(R/'supporting/round002-stress/manifest.json')
public_files=[(R/'supporting/round002-stress'/x['path'],x['sha256']) for x in pub['files']]
public_files += [(old/x['path'],x['sha256']) for x in pub['external_old_fixture']['files']]
check('C1','public manifests content',all(sha(p)==h for p,h in public_files),'supporting/round002-stress/manifest.json',len(public_files))
tree=ast.parse((P/'evaluator.py').read_text())
forbidden=('oracle','coordinator-only','/private/','generator.py','validation.json')
literal_paths=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and ('/' in n.value or '.py' in n.value) and '\n' not in n.value]
check('C1','no forbidden imports/reads',not any(f in v for f in forbidden for v in literal_paths),'evaluator.py AST literal paths/imports',literal_paths)
source={x['name']:reader.expand_scenario(x['name'],old) for x in reader.scenario_index(old)}
evaluated={k:ev.evaluate(d,spec) for k,d in source.items()}
check('C1','all 38 snapshots evaluate',len(evaluated)==38,'public reader scenario_index',len(evaluated))
configs=load(R/'supporting/round002-stress/business-config.json')['configs']
check('C1','prospective config v1',all(ev.stamp(c['approved_at'])<ev.stamp(c['valid_from']) for c in configs if c['version']==1),'business-config.json#configs[version=1]')

# C2: recover ordinary, strong, insufficient and pending per family from source.
base=source['R1.volume']; samples=[]
for family in spec['roles']:
    reg=next(x for x in base['comparison_registry'] if x['period_id']=='P1' and next(c for c in base['roster_capacity'] if c['period_id']=='P1' and c['subject_id']==x['subject_id'])['family']==family)
    subject=reg['subject_id']; p=reg['period_id']
    for label in ('ordinary','strong','insufficient','pending'):
        d=copy.deepcopy(base)
        for a in d['quality_acts']:
            if a['period_id']==p and a['subject_id']==subject:
                a.update(minor=1 if label=='ordinary' else 0,major=0,critical=0,score=98 if label=='ordinary' else 100)
                if label=='pending':a['evidence_status']='missing'
        if label=='insufficient':
            next(c for c in d['roster_capacity'] if c['period_id']==p and c['subject_id']==subject)['active_days']=9
        refresh(d,'quality_acts');refresh(d,'roster_capacity')
        u=result(d,p,subject)
        expected={'ordinary':u['normal'] and not u['stretch'] and u['qa_mean']==98,
                  'strong':u['normal'] and u['stretch'] and u['qa_mean']==100,
                  'insufficient':u['sufficiency']=='insufficient' and not u['normal'],
                  'pending':u['state']=='pending' and u['qa_mean'] is None}[label]
        check('C2',family+' '+label,expected,'R1.volume#quality_acts/roster_capacity:'+p+':'+subject)
        samples.append(dict(family=family,case=label,subject=subject,period=p,state=u['state'],qa=str(u['qa_mean']),roots=u['roots'],rank=u['rank']))
detail['hand_reconstructed_role_examples']=samples
u,p=evaluated['R1.volume']
check('C2','complete group quality ties despite volume',all(x['tie_size']==(8 if x['family']=='project' else 40) and x['rank']==1 for x in u),'R1.volume#all groups',{'units':len(u),'people':len(p)})
for fam in spec['roles']:
    q=[x for x in evaluated['R2.quality'][0] if x['family']==fam and x['period']=='P1']
    check('C2',fam+' 98/99/100 discriminate',all(x['normal'] and not x['stretch'] for x in q if x['qa_mean']==98) and all(x['rank']==1 for x in q if x['qa_mean']==100) and all(x['rank']>1 for x in q if x['qa_mean']==99),'R2.quality#'+fam)
q=result(source['R2.precision'],'P1','S11')
check('C2','0.05 change produces no new superiority',q['qa_mean']==F(1981,20) and q['rank']==1 and q['tie_size']>10,'R2.precision#S11; QA40 acts: one98→100',{'qa':str(q['qa_mean']),'tie_size':q['tie_size']})
check('C2','small CSAT and worklog do not rank',[(x['normal'],x['rank'],x['qa_mean']) for x in evaluated['R2.small_csat'][0]]==[(x['normal'],x['rank'],x['qa_mean']) for x in evaluated['R1.volume'][0]],'R2.small_csat vs R1.volume')
for name in ('F02.inflated','F02.incomplete','F08.documented','F08.self_claimed'):
    check('C2',name+' diagnostic only',[(x['normal'],x['qa_mean'],x['rank']) for x in evaluated[name][0]]==[(x['normal'],x['qa_mean'],x['rank']) for x in evaluated['base'][0]],name+' vs base')
check('C2','split is one deliverable/inspection',[(x['normal'],x['qa_mean'],x['roots'],x['unit_top_R']) for x in evaluated['F07.split'][0]]==[(x['normal'],x['qa_mean'],x['roots'],x['unit_top_R']) for x in evaluated['base'][0]],'F07.split vs base')
check('C2','second project type normal without100 uses',all(result(source['R3.analytical'],'P1','T0'+str(i))['normal'] for i in range(1,7)) and not result(source['R3.analytical'],'P1','T07')['normal'],'R3.analytical#T01..T07')
check('C2','missing/foreign/full root never QA0',result(source['R2.foreign_scale'],'P1','S01')['state']=='pending' and result(source['R2.incomplete_root'],'P1','T01')['state']=='pending','R2.foreign_scale/R2.incomplete_root')
check('C2','post-start goal cannot improve',[(x['normal'],x['rank']) for x in evaluated['R3.conflicting_goal'][0]]==[(x['normal'],x['rank']) for x in evaluated['R3.analytical'][0]],'R3.conflicting_goal vs R3.analytical')

# C3: positive performed authorization, then empty fields/conflicts/hash edits.
def authorized_fixture():
    d=copy.deepcopy(base);person='S01';period='P1'
    a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['period_id']==period and a['beneficiary_id']==person))
    a.update(approval_id='SELF-CHECK-PERFORMED',action=spec['signature']['posting_action'],source_ref=period+':'+person,
             input_editor_id='TEST-EDITOR',signer_id='TEST-SIGNER',operator_id='TEST-OPERATOR',signed_at='2026-04-29T10:00:00+03:00',
             signer_reporting_to=None,operator_reporting_to=None,source_version='TEST-SOURCE-V1',version=1)
    d['approvals_audit'].append(a)
    a['package_binding_sha256']=ev.digest(dict(period=period,person=person,source_sha256=ev.package_source_digest(d,spec['signature']['posting_action']),rule_sha256=ev.digest(spec),version=spec['candidate_key']))
    refresh(d,'approvals_audit');return d
positive=authorized_fixture(); good=result(positive,'P1','S01',True)
check('C3','positive action authorizes U not posting',good['authorization']=='authorized' and good['top_U_R']==150 and good['ledger_state']=='authorized_U_not_posted','in-memory R1.volume + explicit performed test action',good['approval_trace'])
def negative(field,value,label=None,person='S01'):
    d=copy.deepcopy(positive);a=next(a for a in d['approvals_audit'] if a['approval_id']=='SELF-CHECK-PERFORMED')
    if value=='__DELETE__':a.pop(field,None)
    else:a[field]=value
    refresh(d,'approvals_audit'); x=result(d,'P1',person,True)
    check('C3',label or field+'='+str(value),x['authorization']=='pending' and x['top_U_R']==0 and x['calculated_normal'] and x['potential_top_R']==150,'test performed action#'+field,x['authorization_errors'])
for field in ('signed_at','action','source_ref','input_editor_id','signer_id','operator_id'):
    for value in (None,'',' ','__DELETE__'):negative(field,value)
for field,value in [('signed_at','invalid'),('action','type_correction'),('source_ref','P2:S01'),('signed_at','2026-01-01T10:00:00+03:00'),('source_version',None),('package_binding_sha256','bad'),('signer_id','S01'),('operator_id','TEST-SIGNER'),('input_editor_id','TEST-SIGNER'),('signer_reporting_to','S01'),('operator_reporting_to',['S01'])]:negative(field,value)
for field in ('input_editor_id','signer_id','operator_id'):
    for beneficiary in ('T01','P001','P002'):
        a=dict(action='input_correction_and_posting_review',source_ref='P1:P001',signed_at='2026-04-29T10:00:00+03:00',input_editor_id='E',signer_id='S',operator_id='O');a[field]=beneficiary
        check('C3',field+' team beneficiary '+beneficiary,bool(ev.approval_errors(a,{'T01','P001','P002'},spec['signature']['posting_action'])),'approval_errors team-scope test')
for field in ('input_editor_reporting_to','signer_reporting_to','operator_reporting_to'):
    a=dict(action=spec['signature']['posting_action'],signed_at='2026-04-29T10:00:00+03:00',input_editor_id='E',signer_id='S',operator_id='O');a[field]=['P002']
    check('C3',field+' team reporting conflict',bool(ev.approval_errors(a,{'T01','P001','P002'},spec['signature']['posting_action'])),'approval_errors team-reporting test')
for name,person in [('R1.missing_signature','S01'),('R1.conflicted_signature','P001'),('R1.batch_changed','S01')]:
    x=result(source[name],'P1',person,True)
    check('C3',name+' source action blocked',x['calculated_normal'] and x['authorization']=='pending' and bool(x['source_review_errors']),name+'#'+person,x['source_review_errors'])
changed=copy.deepcopy(spec);changed['quality']['substantive_difference_points']=2
check('C3','rule edit invalidates signed package',result(positive,'P1','S01',True,changed)['authorization']=='pending','positive fixture + modified rule hash')
check('C3','repeat delivery deterministic and not ledger-posted',result(positive,'P1','S01',True)==good,'same immutable source replay; actual ledger not implemented')
check('C3','lost/restored original qualification',result(source['F10.lost'],'P1','S01')['state']=='pending' and result(source['F10.restored'],'P1','S01')['normal'],'F10.lost/F10.restored#P1:S01')
detail['authorization_note']='Positive mutations are explicit synthetic test actions, not actual source events. Production posting/replay journal is specified, not implemented or claimed executed.'

# C4: monthly arithmetic, annual aggregation, finite supply, queue and cash.
mrows=rows(P/'monthly-resource.csv');arows=rows(P/'annual-resource.csv')
keys=('redemption','fixed_C_year','QA_reuse','labor_multiplier','base_substitution','role')
groups=defaultdict(list)
for r in mrows:groups[tuple(r[k] for k in keys)].append(r)
check('C4','complete monthly panel',len(mrows)==11232 and len(groups)==288 and all({int(r['month']) for r in v}==set(range(1,40)) for v in groups.values()),'monthly-resource.csv',len(mrows))
eq=True; queues=True; supply=True
for k,rs in groups.items():
    queue=0
    for r in rs:
        n=lambda c:float(r[c]);d=n('demand_h');baseh=n('base_available_h');book=n('paid_booked_h');rate=n('rate_RUB_h')
        expected_used=min(book,max(0,d-baseh));expected_idle=book-expected_used
        eq &= all(abs(a-b)<1e-6 for a,b in [(n('paid_used_h'),expected_used),(n('paid_idle_h'),expected_idle),(n('full_resource_RUB'),(d+expected_idle)*rate),(n('new_cash_RUB'),book*rate+min(baseh,d)*rate*n('base_substitution'))])
        queue=max(0,queue+d-baseh-book);queues &= abs(queue-n('queue_carry_h'))<1e-6
        supply &= abs(book/20-round(book/20))<1e-6 and (book<=120 if r['role']=='HR' else book<=11240 if r['role']=='owner_QA' else book<=80)
check('C4','work/idle/cash no reserve double price',eq,'monthly-resource.csv#all rows')
check('C4','queues conserved',queues,'monthly-resource.csv#queue_carry_h')
check('C4','finite block supply',supply,'resource-supply.json + monthly-resource.csv')
annual_ok=True
periods={'Y1':(1,12),'Y2':(13,24),'Y3':(25,36),'tail':(37,39),'m1-39':(1,39)}
for a in arows:
    lo,hi=periods[a['period']];rs=[r for r in groups[tuple(a[k] for k in keys)] if lo<=int(r['month'])<=hi]
    for col in ('demand_h','full_resource_RUB','paid_booked_h','paid_used_h','paid_idle_h','new_cash_RUB','excess_h'):
        annual_ok &= abs(float(a[col])-sum(float(r[col]) for r in rs))<1e-5
    annual_ok &= abs(float(a['peak_h'])-max(float(r['demand_h']) for r in rs))<1e-6
check('C4','annual sums peaks from same months',annual_ok,'annual-resource.csv#all1440 rows')
x1=[r for r in mrows if r['labor_multiplier']=='1'];x2=[r for r in mrows if r['labor_multiplier']=='2']
check('C4','x1 funded capacity only scope',all(r['funded_capacity_pass']=='True' and float(r['queue_carry_h'])==0 for r in x1),'monthly-resource.csv#labor_multiplier=1')
check('C4','x2 HR fail disclosed',any(r['role']=='HR' and r['funded_capacity_pass']=='False' for r in x2),'monthly-resource.csv#labor_multiplier=2,role=HR')
hr=[r for r in x1 if r['role']=='HR' and float(r['source_person_checks'])>0]
bound=min((340-float(r['demand_h'])+.1*float(r['source_person_checks'])*2/60)/(float(r['source_person_checks'])*2/60) for r in hr)
detail['resource']={'funded_x1_all_roles':True,'x2_HR_failed_month_rows':sum(r['role']=='HR' and r['funded_capacity_pass']=='False' for r in x2),'min_HR_exception_boundary_fraction_all_months':bound,'HR_booked_cash_39months':4680000,'setup_cash_RUB':sum(float(r['cash_RUB']) for r in rows(P/'setup-resource.csv')),'year2_fixed96_QA100_expected':{r['role']:{k:r[k] for k in ('demand_h','full_resource_RUB','new_cash_RUB','peak_h')} for r in arows if r['redemption']=='EXPECTED' and r['fixed_C_year']=='96000000' and r['QA_reuse']=='1' and r['labor_multiplier']=='1' and r['base_substitution']=='0' and r['period']=='Y2'}}
check('C4','10percent exceptions under funded boundary',bound>=.1,'monthly-resource.csv derived HR boundary',bound)

# C5: fixed money, ledger conservation, actual dates and whole SKU examples.
fin=load(P/'finance-spec.json');f=fin['scenario_parameters']['24000000']
check('C5','E24 unchanged',f['guarantee_R_person']==2500 and f['guarantee_max_R_year']==18000000 and f['contest_R_year']==4320000 and f['special_R_year']==1680000 and sum(f[k] for k in ('guarantee_max_R_year','contest_R_year','special_R_year'))==24000000,'finance-spec.json#scenario_parameters.24000000')
grows=rows(P/'group-top-reserve.csv')
check('C5','top pool authorization+reserve+unissued',all(int(r['pool_R'])==int(r['authorized_U_R'])+int(r['reserved_R'])+int(r['unissued_R']) and int(r['calculated_R'])<=int(r['pool_R']) for r in grows),'group-top-reserve.csv#all252 groups')
check('C5','whole SKU and C/R paths',all(int(r['C_after_conversion'])==int(r['calculated_R'])+int(r['existing_C']) and int(r['whole_SKU500'])*int(r['SKU_price_C'])+int(r['remaining_C'])==int(r['C_after_conversion']) for r in rows(P/'money-examples.csv')),'money-examples.csv#12profiles')
check('C5','no source award presented posted',all(int(r['top_U_R'])==0 for r in rows(P/'decisions.csv')) and all(int(r['posted_R'])==0 for r in rows(P/'window-guarantee.csv')),'decisions.csv/window-guarantee.csv')
boundary=rows(P/'calendar-boundaries.csv')
check('C5','nine cohorts real period dates',len({r['subject'] for r in boundary})==9 and any(r['inside_label']=='False' for r in boundary) and {r['scenario'] for r in boundary}=={'R4.boundaries','R4.restored'},'calendar-boundaries.csv',len(boundary))
detail['R4_limitation']='All18 source units have fewer than20 roots and an actual late accepted root, so no G arises even after QA restoration. R4 proves date/receipt parsing, not a positive money entitlement. F10 lost/restored demonstrates the original-period qualification path; financial nine-cohort m1–39 dates remain the unchanged first-launch.csv.'

# C6/C7 cannot be independently completed by a concept author.
delegated=[{'check':'C6','status':'pending_independent','scope':'coordinator/finance compare BASELINE, immutable016,022,023 on common inputs; no control outputs edited'},
           {'check':'C7','status':'pending_independent','scope':'independent finance/evidence and fresh blinded review; author self-check is not a gate verdict'}]
out={'candidate_key':'CON-022@v1','status':'pass' if all(c['status']=='pass' for c in checks) else 'fail','scope':'author checks of C1–C5 and handoff only; no independent gates or measured bank effect','python':sys.version.split()[0],'checks':checks,'detail':detail,'uncompleted':delegated,'limits':['Real independent staffing and operating cash remain prospective prerequisites.','x2 HR is outside timely capacity scope; all rights remain reserved.','Monthly hours establish scenario capacity; intra-day export distribution and incidents require pilot timing validation.','Actual U/posting/merchant fulfillment absent from source are not asserted.','M05 budget/procurement failures and uncertain real bank readiness remain unchanged.']}
(P/'self-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({'status':out['status'],'checks':len(checks),'failed':[c['name'] for c in checks if c['status']=='fail'],'resource':detail['resource']},ensure_ascii=False))
if out['status']!='pass':raise SystemExit(1)
