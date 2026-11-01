import sys
sys.dont_write_bytecode=True
import ast,copy,csv,json,hashlib,importlib.util,math
from fractions import Fraction as F
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('own_primitive',HERE/'primitive_support.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
R=m.ROOT
rawU=list(csv.DictReader((HERE/'primitive-units-base.csv').open()));rawP=list(csv.DictReader((HERE/'primitive-persons-base.csv').open()))

def own_rank(rows,persons):
 for u in rows:u.update(rank=None,tie_size=0,unit_top_R=0,quality_class='unavailable' if u.get('qa') in [None,''] else 'zero_observed_penalty' if F(str(u['qa']))==100 else 'qualified_with_penalty' if F(str(u['qa']))>=99 else 'below_stretch_quality')
 for gp,group in m.by(rows,'scenario','period','group').items():
  ps=[p for p in persons if p['scenario']==gp[0] and p['period']==gp[1] and p['unit'] in {u['subject'] for u in group}]
  pool=150*len({p['subject'] for p in ps})
  if len(group)<2:continue
  if any(u['state'] in ['pending','not_computable'] for u in group):
   for u in group:u['top_status']='pending_group';u['group_reserve_R']=pool
   continue
  eligible=[u for u in group if u['strong'] in [True,'True']]
  eligible.sort(key=lambda u:2 if u['quality_class']=='zero_observed_penalty' else 1,reverse=True)
  pos=0
  for category in ['zero_observed_penalty','qualified_with_penalty']:
   tied=[u for u in eligible if u['quality_class']==category]
   if not tied:continue
   amount=sum([F(2,5),F(3,10),F(1,5),F(1,10)][pos:min(pos+len(tied),4)])*pool/len(tied)
   for u in tied:u.update(rank=pos+1,tie_size=len(tied),unit_top_R=str(amount))
   pos+=len(tied)
 for p in persons:
  u=next(u for u in rows if (u['scenario'],u['period'],u['subject'])==(p['scenario'],p['period'],p['unit']))
  p['rank']=u['rank'];p['tie_size']=u['tie_size'];p['top_calculated_R']=math.floor(F(str(u['unit_top_R']))*F(str(p['share']))) if p['calculated_state']=='earned' else 0;p['top_authorized_U_R']=0
 return rows,persons

Aunits=[copy.deepcopy(u) for u in rawU if u['candidate_key']=='CON-022@v1'];Apersons=[copy.deepcopy(p) for p in rawP if p['candidate_key']=='CON-022@v1']
Aunits,Apersons=own_rank(Aunits,Apersons)
for u in Aunits:u['candidate_key']='CON-024@v1'
for p in Apersons:p['candidate_key']='CON-024@v1'
allU=list(Aunits);allP=list(Apersons)
for key in ['CON-025@v1','CON-023@v2','BASELINE']:
 origin='CON-023@v2' if key!='BASELINE' else 'BASELINE'
 for r in rawU:
  if r['candidate_key']==origin:x=copy.deepcopy(r);x['candidate_key']=key;allU.append(x)
 for r in rawP:
  if r['candidate_key']==origin:x=copy.deepcopy(r);x['candidate_key']=key;allP.append(x)
m.csvout(HERE/'independent-units.csv',allU);m.csvout(HERE/'independent-persons.csv',allP)

# New recipe applies only specified defects/score on independent source copies.
recipe=json.loads((R/'supporting/qa-neighborhood-recipe.json').read_text());assert hashlib.sha256((R/'supporting/qa-neighborhood-recipe.json').read_bytes()).hexdigest()=='b5ce8d3d8b0442879526be9916e657371b1929f5d1f469cab1751ed334192a12'
probes=[];ties=[]
for entry in recipe['controls']+[{'id':'R2.precision','change':'existing source'}]:
 name=entry['id'];d=m.reader.expand_scenario('R2.precision' if name=='R2.precision' else 'R2.quality',m.OLD)
 if 'act_id' in entry:
  q=next(q for q in d['quality_acts'] if q['act_id']==entry['act_id']);subject='S21' if name=='Q100_down' else 'S11';expected_n=44 if name=='Q100_down' else 40
  qs=[q for q in d['quality_acts'] if q['subject_id']==subject and q['period_id']=='P1'];assert len({q['inspection_id'] for q in qs})==expected_n
  assert q['minor']==(1 if name=='Q99_up' else 0) and q['major']==0 and q['critical']==0 and q['score']==(98 if name=='Q99_up' else 100)
  q.update(entry['set'])
  for receipt in d.get('source_receipts',[]):
   if receipt['source_key'].get('act_id')==entry['act_id']:receipt['received_sha256']=m.h(q)
  for z in d['source_manifest']:
   if z['table']=='quality_acts' and z['period_id']=='P1':
    rs=[x for x in d['quality_acts'] if x['period_id']=='P1'];z.update(received_sha256=m.h(rs),expected_count=len(rs),received_count=len(rs))
 facts=m.read_metrics(d)
 for key in ['CON-024@v1','CON-025@v1','CON-023@v2','BASELINE']:
  basekey='CON-022@v1' if key=='CON-024@v1' else 'CON-023@v1' if key!='BASELINE' else 'BASELINE'
  u,p=m.calc(basekey,facts,d)
  for row in u:row.update(scenario=name,candidate_key=key)
  for row in p:row.update(scenario=name,candidate_key=key)
  if key=='CON-024@v1':u,p=own_rank(u,p)
  for subject in ['S01','S11','S21','S31','B11','T03','T05']:
   x=next(x for x in u if x['subject']==subject and x['period']=='P1');person=next(xp for xp in p if xp['unit']==subject and xp['period']=='P1');qaacts=[q for q in d['quality_acts'] if q['subject_id']==subject and q['period_id']=='P1' and q['scale_version']=='penalty-v1'];exact=F(sum(100-2*q['minor']-10*q['major']-100*q['critical'] for q in qaacts),len(qaacts))
   probes.append({'control':name,'candidate_key':key,'subject':subject,'QA_exact':str(exact),'QA_display':float(exact),'inspections':len(qaacts),'normal':x['state']=='earned','state':x['state'],'stretch':x['strong'],'quality_class':x.get('quality_class'),'rank':x['rank'],'tie_size':x['tie_size'],'unit_top_R':str(x['unit_top_R']),'personal_top_R':person['top_calculated_R'],'authorized_U_R':0,'original_window':person['window']})
  if key=='CON-024@v1':
   for category in ['zero_observed_penalty','qualified_with_penalty']:
    group=[x for x in u if x['period']=='P1' and x['family']=='support' and x.get('quality_class')==category and x['strong']]
    ties.append({'control':name,'candidate_key':key,'category':category,'members':[x['subject'] for x in group],'n':len(group),'QA_range':[min(x['qa'] for x in group),max(x['qa'] for x in group)] if group else None,'rank':group[0]['rank'] if group else None,'personal_R':[xp['top_calculated_R'] for xp in p if xp['period']=='P1' and xp['unit'] in {x['subject'] for x in group}],'authorized_U_R':0})
m.csvout(HERE/'qa-neighborhood.csv',probes);m.jsonout(HERE/'qa-ties.json',ties)

# Direct structural proof permits reusing old primitive/normal/QA data.
def funcs(p):return {x.name:x for x in ast.parse(p.read_text()).body if isinstance(x,ast.FunctionDef)}
oldA=funcs(R.parent/'002/branches/A/con-022/evaluator.py');newA=funcs(R/'branches/A/con-024/evaluator.py');oldB=funcs(R/'supporting/previous-best/evaluator.py');newB=funcs(R/'branches/B/con-025/evaluator.py')
class NormalizeRank(ast.NodeTransformer):
 def visit_Assign(self,node):
  node=self.generic_visit(node)
  if any(isinstance(t,ast.Name) and t.id=='rank_key' for t in node.targets) and any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='quality_rank_key' for n in ast.walk(node.value)):node.value=ast.parse('(qmean or F(0),)',mode='eval').body
  return node
 def visit_Dict(self,node):
  node=self.generic_visit(node);keep=[i for i,k in enumerate(node.keys) if not(isinstance(k,ast.Constant) and k.value=='quality_category')];node.keys=[node.keys[i] for i in keep];node.values=[node.values[i] for i in keep];return node
oldloop=next(x for x in oldA['evaluate'].body if isinstance(x,ast.For));newloop=next(x for x in newA['evaluate'].body if isinstance(x,ast.For));normalized=NormalizeRank().visit(copy.deepcopy(newloop))
invariance={'A_primitive_normal_QA_loop_except_explicit_rank_fields':ast.dump(oldloop,include_attributes=False)==ast.dump(normalized,include_attributes=False),'A_helpers':all(ast.dump(oldA[k],include_attributes=False)==ast.dump(newA[k],include_attributes=False) for k in oldA if k not in ['evaluate','run']),'B_all_analytical_functions':all(ast.dump(oldB[k],include_attributes=False)==ast.dump(newB[k],include_attributes=False) for k in oldB if k!='main')}
assert all(invariance.values()),invariance
# Compare the NEW independent category outputs against frozen saved output rows.
lookup={(u['scenario'],u['period'],u['subject']):u for u in Aunits};diff=[]
for a in csv.DictReader((R/'branches/A/con-024/unit-decisions.csv').open()):
 b=lookup[a['scenario'],a['period'],a['subject']]
 observed=F(a['unit_top_R'] or '0');expected=F(str(b['unit_top_R']))
 if observed!=expected or (a['rank'] or '')!=('' if b['rank'] is None else str(b['rank'])) or a['stretch']!=b['strong']:diff.append({'scenario':a['scenario'],'period':a['period'],'subject':a['subject'],'observed_top':str(observed),'expected_top':str(expected)})
m.jsonout(HERE/'metric-invariance.json',{'invariance':invariance,'A_new_rank_compared_unit_rows':len(Aunits),'A_new_rank_differences':diff,'basis_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'primitive-units-base.csv',HERE/'primitive-persons-base.csv',HERE/'primitive-windows-base.csv']},'recipe_sha256':hashlib.sha256((R/'supporting/qa-neighborhood-recipe.json').read_bytes()).hexdigest()})
print(json.dumps({'invariance':invariance,'A_rank_difference_count':len(diff),'Q_summary':[x for x in probes if x['candidate_key']=='CON-024@v1' and (x['subject']=='S21' if x['control']=='Q100_down' else x['subject']=='S11')]},ensure_ascii=False,indent=2))
