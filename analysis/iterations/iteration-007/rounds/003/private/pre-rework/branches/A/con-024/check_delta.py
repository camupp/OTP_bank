#!/usr/bin/env python3
"""Targeted scorer/QA-neighborhood checks; never execute a closed artifact."""
import sys
sys.dont_write_bytecode=True
import ast,copy,csv,hashlib,importlib.util,json
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];ROOT=R.parents[4]
OLD=R.parent/'002/branches/A/con-022';S=R/'supporting'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def rows(p):return list(csv.DictReader(p.open()))
def module(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ev=module('candidate_024',P/'evaluator.py');reader=module('public_reader_003',S/'round002-stress/reader.py')
spec=load(P/'metrics-spec.json');checks=[]
def check(name,ok,observed=None):checks.append(dict(name=name,status='pass' if ok else 'fail',observed=observed))
recipe=load(S/'qa-neighborhood-recipe.json')
check('frozen recipe SHA',sha(S/'qa-neighborhood-recipe.json')=='b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12')
inputs=load(R/'inputs/manifest.json')
check('five inputs unchanged',all(sha(R/'inputs'/k)==v for k,v in inputs['files'].items()),inputs['fingerprint'])
refs=load(P/'resource-reference.json')
check('all resource basis SHA unchanged',all(sha(ROOT/v['project_path'])==v['sha256'] for v in refs['files'].values()))
oldspec=load(OLD/'metrics-spec.json')
check('normal thresholds/exposure/currency/signatures unchanged',all(spec[k]==oldspec[k] for k in ('roles','exposure_days','followup_days','guarantee_R','top_R_per_person','top_shares','input_contract','missing','signature','normal','mode','batch_protocol','project_business_config')))
oldcode=(OLD/'evaluator.py').read_text();newcode=(P/'evaluator.py').read_text()
sections=[('normal_source_core','def evaluate(data, spec):','# Top is quality only'),('authorization_core','    people=[]','    for p,g in sorted'),('fixed_window_core','        rulemap=','        for e in data[')]
section_proof={}
for label,start,end in sections:
    a=oldcode[oldcode.index(start):oldcode.index(end,oldcode.index(start))];b=newcode[newcode.index(start):newcode.index(end,newcode.index(start))]
    section_proof[label]={'unchanged':a==b,'sha256':hashlib.sha256(a.encode()).hexdigest()}
    check(label+' literal unchanged',a==b)
for name in ('package_source_digest','stamp','batch_errors','approval_errors','independent_approval','validate_manifest'):
    def fn(code):return ast.dump(next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
    check('C3 helper '+name+' AST unchanged',fn(oldcode)==fn(newcode))

# Every original snapshot is recalculated in this candidate directory.
oldunits={(r['scenario'],r['period'],r['subject']):r for r in rows(OLD/'unit-decisions.csv')}
newunits={(r['scenario'],r['period'],r['subject']):r for r in rows(P/'unit-decisions.csv')}
stable=('state','sufficiency','normal','stretch','stretch_state','roots','accepted_roots','acceptance_rate','sla','adverse_rate','qa_inspections','qa_compatible_acts','qa_mean','usage_min','early_min_days','active_days','scheduled_hours_already_FTE','available_allocated_before_intervals_h','top_exposure_sufficient','project_type','business_config','business_ready_by_preread')
differences=[{'key':k,'field':f,'before':oldunits[k][f],'after':newunits[k][f]} for k in newunits for f in stable if oldunits[k][f]!=newunits[k][f]]
check('38 snapshot normal/stretch/source metrics regression',oldunits.keys()==newunits.keys() and not differences,{'unit_rows':len(newunits),'differences':differences})
oldg=rows(OLD/'window-guarantee.csv');newg=rows(P/'window-guarantee.csv')
check('fixed windows G rights unchanged', [{k:v for k,v in r.items() if k!='candidate_key'} for r in oldg]==[{k:v for k,v in r.items() if k!='candidate_key'} for r in newg],len(newg))

def refresh(d,table):
    for m in d['source_manifest']:
        if m['table']==table:
            rr=[x for x in d[table] if x.get('period_id',m['period_id'])==m['period_id']]
            m.update(expected_count=len(rr),received_count=len(rr),received_sha256=ev.digest(rr))
    # A receipt, when present, carries the same physical partition checksum.
    for rc in d.get('source_receipts',[]):
        for m in d['source_manifest']:
            if rc.get('partition_id')==m['partition_id']:
                for key in ('received_count','received_sha256'):
                    if key in rc:rc[key]=m[key]
base=reader.expand_scenario('R2.quality',S/'fixtures')
expected={'Q0':F(99),'Q99_down':F(1979,20),'Q99_up':F(1981,20),'Q100_down':F(2199,22)}
probe_rows=[];ties=[];observations={};copies={}
for control in recipe['controls']:
    cid=control['id'];d=copy.deepcopy(base);target='S21' if cid=='Q100_down' else 'S11'
    if 'act_id' in control:
        acts=[a for a in d['quality_acts'] if a['act_id']==control['act_id']]
        assert len(acts)==1,'recipe act not unique'
        a=acts[0];pre={'Q99_down':(40,0,100),'Q99_up':(40,1,98),'Q100_down':(44,0,100)}[cid]
        same=[x for x in d['quality_acts'] if x['period_id']=='P1' and x['subject_id']==target]
        check(cid+' recipe precondition',len({x['inspection_id'] for x in same})==pre[0] and a['minor']==pre[1] and a['score']==pre[2] and a['major']==a['critical']==0 and a['period_id']=='P1' and a['subject_id']==target)
        a.update(control['set']);refresh(d,'quality_acts')
        changed=[(x['act_id'],f) for x,y in zip(d['quality_acts'],base['quality_acts']) for f in x if x[f]!=y[f]]
        check(cid+' only recipe fields changed',set(changed)=={(control['act_id'],'minor'),(control['act_id'],'score')})
        check(cid+' other tables fixed',all(d[k]==base[k] for k in d if k not in ('quality_acts','source_manifest','source_receipts')))
    copies[cid]=d;us,ps=ev.evaluate(d,spec)
    t=next(u for u in us if u['period']=='P1' and u['subject']==target)
    person=next(x for x in ps if x['period']=='P1' and x['subject']==target)
    check(cid+' exact primitive QA',t['qa_mean']==expected[cid],str(t['qa_mean']))
    check(cid+' U absent without new performed award',all(x['top_U_R']==0 for x in ps))
    observations[cid]={'target':target,'qa_exact':str(t['qa_mean']),'normal':t['normal'],'stretch':t['stretch'],'category':t['quality_category'],'rank':t['rank'],'tie_size':t['tie_size'],'calculated_R':person['potential_top_R'],'authorized_U_R':person['top_U_R']}
    for u in us:
        people=[x for x in ps if x['period']==u['period'] and x['unit']==u['subject']]
        probe_rows.append({'probe':cid,'period':u['period'],'subject':u['subject'],'family':u['family'],'group':u['group'],'qa_exact':str(u['qa_mean']),'inspections':u['qa_inspections'],'normal':u['normal'],'stretch':u['stretch'],'category':u['quality_category'],'rank_key':u['rank_key'],'rank':u['rank'],'tie_size':u['tie_size'],'unit_calculated_R':u['unit_top_R'],'personal_calculated_R_sum':sum(x['potential_top_R'] for x in people),'authorized_U_R':sum(x['top_U_R'] for x in people)})
    for p,g,cat in sorted({(u['period'],u['group'],u['quality_category']) for u in us if u['stretch']}):
        cohort=[u for u in us if u['period']==p and u['group']==g and u['quality_category']==cat and u['stretch']]
        ties.append({'probe':cid,'period':p,'group':g,'category':cat,'member_subjects':sorted(u['subject'] for u in cohort),'qa_min_exact':str(min(u['qa_mean'] for u in cohort)),'qa_max_exact':str(max(u['qa_mean'] for u in cohort)),'rank':cohort[0]['rank'],'unit_R_exact':str(cohort[0]['unit_top_R'])})
up=reader.expand_scenario('R2.precision',S/'fixtures')
check('Q99_up coincides with R2.precision primitive acts',copies['Q99_up']['quality_acts']==up['quality_acts'])
check('99.05 bridge does not merge99 and100',observations['Q99_up']['category']=='qualified_with_observed_penalty' and observations['Q99_up']['rank']>1 and observations['Q99_up']['calculated_R']==0,observations['Q99_up'])
check('98.95 keeps exact stretch99 boundary',observations['Q99_down']['normal'] and not observations['Q99_down']['stretch'] and observations['Q99_down']['rank'] is None)
check('100 one minor enters qualified penalty category',observations['Q100_down']['normal'] and observations['Q100_down']['stretch'] and observations['Q100_down']['category']=='qualified_with_observed_penalty' and observations['Q100_down']['calculated_R']==0,observations['Q100_down'])
sequence=[F(98),F(1979,20),F(99),F(1981,20),F(2199,22),F(100)]
keys=[0 if q<99 else ev.quality_rank_key(q)[0] for q in sequence]
check('categories monotone independent of other members',keys==sorted(keys) and keys==[0,0,1,1,1,2],keys)
check('98/99/100 meaningful admission/category differences',ev.quality_category(F(98))=='below_stretch_quality' and ev.quality_category(F(99))=='qualified_with_observed_penalty' and ev.quality_category(F(100))=='no_observed_penalty')

# New rule hash must invalidate an old act; explicitly matching new test act can authorize.
d=reader.expand_scenario('R1.volume',S/'fixtures')
a=copy.deepcopy(next(a for a in d['approvals_audit'] if a['period_id']=='P1' and a['beneficiary_id']=='S01'))
a.update(approval_id='QA003-HYPOTHETICAL-AWARD',action=spec['signature']['posting_action'],source_ref='P1:S01',input_editor_id='TEST-EDITOR',signer_id='TEST-SIGNER',operator_id='TEST-OPS',signer_reporting_to=None,operator_reporting_to=None,signed_at='2026-04-29T10:00:00+03:00',source_version='QA003-TEST-V1',version=1)
d['approvals_audit'].append(a)
def binding(sp):return ev.digest({'period':'P1','person':'S01','source_sha256':ev.package_source_digest(d,spec['signature']['posting_action']),'rule_sha256':ev.digest(sp),'version':sp['candidate_key']})
a['package_binding_sha256']=binding(oldspec);refresh(d,'approvals_audit')
u,pp=ev.evaluate(d,spec);t=next(x for x in pp if x['period']=='P1' and x['subject']=='S01')
check('old rule/candidate signature invalid for024',t['authorization']=='pending' and t['top_U_R']==0 and t['calculated_normal'])
a['package_binding_sha256']=binding(spec);refresh(d,'approvals_audit')
u,pp=ev.evaluate(d,spec);t=next(x for x in pp if x['period']=='P1' and x['subject']=='S01')
check('explicit matching new act authorizes U only',t['authorization']=='authorized' and t['top_U_R']==150 and t['ledger_state']=='authorized_U_not_posted')

ev.write_csv(P/'qa-neighborhood.csv',probe_rows)
(P/'qa-ties.json').write_text(json.dumps({'candidate_key':spec['candidate_key'],'recipe_sha256':sha(S/'qa-neighborhood-recipe.json'),'ties':ties},ensure_ascii=False,indent=2)+'\n')
rank_changes=[]
for k,n in newunits.items():
    o=oldunits[k]
    if any(n[f]!=o[f] for f in ('rank','tie_size','unit_top_R')):rank_changes.append({'scenario':k[0],'period':k[1],'subject':k[2],'old_rank':o['rank'],'new_rank':n['rank'],'old_tie':o['tie_size'],'new_tie':n['tie_size'],'old_unit_R':o['unit_top_R'],'new_unit_R':n['unit_top_R']})
with (P/'rank-delta.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rank_changes[0]) if rank_changes else ['scenario','period','subject']);w.writeheader();w.writerows(rank_changes)
result={'candidate_key':spec['candidate_key'],'status':'pass' if all(c['status']=='pass' for c in checks) else 'fail','scope':'Author targeted scorer/recipe regression assertions only; inherited full checks pinned, no independent admission','checks':checks,'observations':observations,'rank_delta_rows':len(rank_changes),'unchanged_code_sections':section_proof,'resource_delta':'zero across resource-reference.json entire scope; existing setup/monthly controls already include rule implementation; no new QA/source/human operation','limitations':['One confirmed minor at100 changes zero-observed-penalty category and may sharply change cash. This is not full robustness to0.05.','Categories recognize observed complete work; no statistical confidence or future-quality superiority is claimed.','99 threshold remains exact and discontinuous by frozen stretch contract.','C3 inherited helpers/authorization core are unchanged; only new/old rule hash positive/negative checks repeated. Production ledger fulfillment is not implemented.','Parent x2 HR/M05 failures and actual staffing/cash/SKU unknowns remain; no expanded admission.','Independent finance/evidence/C6/C7 and selection are coordinator work.']}
(P/'self-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[c['name'] for c in checks if c['status']=='fail'],'observations':observations,'rank_delta_rows':len(rank_changes)},ensure_ascii=False))
if result['status']!='pass':raise SystemExit(1)
