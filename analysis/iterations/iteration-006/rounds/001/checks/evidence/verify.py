"""Independent desk check; reads artifacts, never imports/runs author calculators."""
from pathlib import Path
from fractions import Fraction
import csv,hashlib,json
R=Path(__file__).resolve().parents[2]
ROOT=R.parents[4]
OUT=R/'checks/evidence'
checks=[]
def check(name,actual,expected):
 ok=abs(actual-expected)<1e-7 if isinstance(actual,(float,int)) and isinstance(expected,(float,int)) else actual==expected
 checks.append({'check':name,'pass':ok,'actual':actual,'expected':expected})
def rows(path):
 with path.open() as f:return list(csv.DictReader(f))
def fixed(m,novice):
 y=(m-1)//12;mm=(m-1)%12+1
 return ({1:350,2:50,3:600,6:50} if novice and y==0 else {1:150,2:50,6:50,12:1000}).get(mm,0)
def trajectory(kind,e,profile,events):
 novice=profile=='novice'
 if kind=='A':
  G=2500 if e==24000000 else 3750
  top=(2400 if e==24000000 else 3600) if profile=='strong_repeat_winner' else (480 if e==24000000 else 720) if profile=='team_member_winner' else 0
  lower=0
 elif kind=='B':
  G=0;lower=0
  top=(10000 if e==24000000 else 15000) if profile=='strong_repeat_winner' else (2000 if e==24000000 else 3000) if profile=='team_member' else 0
 else:
  G=0;lower=500
  top=4000 if profile=='strong_repeat_winner' else 800 if profile=='team_member' else 0
 balance=0; targets={1500:None,2500:None,5000:None};post12=0
 for m in range(1,121):
  reward=(lower+top if m>=4 and (m-4)%3==0 else 0)+(G if G and m>=7 and (m-7)%12==0 else 0)
  if m<=12:post12+=reward
  balance+=reward+(fixed(m,novice) if events else 0)
  for target in targets:
   if targets[target] is None and balance>=target:targets[target]=m
 return G,top,post12,targets

# Both complete concepts must exist.
for b,key in [('A','CON-016@v2'),('B','CON-017@v1')]:
 check(b+' complete concept exists',(R/f'branches/{b}/concept-{key[4:7]}.md').is_file(),True)

# Exact incumbent import, including the unaltered spec and every recorded artifact.
prov=json.loads((R.parents[1]/'incumbent/provenance.json').read_text())
for f in prov['files']:
 src=ROOT/f['source']; copy=ROOT/f['copy']
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 check('incumbent '+copy.name+' SHA',h(copy),f['sha256'])
 check('incumbent '+copy.name+' byte identity',src.read_bytes(),copy.read_bytes())
 # avoid embedding bytes in output
 checks[-1]['actual']='byte identical' if checks[-1]['pass'] else 'different';checks[-1]['expected']='byte identical'

A=json.loads((R/'branches/A/finance-spec.json').read_text())
B=json.loads((R/'branches/B/finance-spec.json').read_text())
for e in (24000000,36000000):
 a=A['scenario_parameters'][str(e)];b=B['scenarios'][str(e)]
 G=e*Fraction(3,4)/7200
 check(f'A{e} G',a['guarantee_R_person'],int(G))
 check(f'A{e} guarantee full N',a['guarantee_max_R_year'],7200*G)
 check(f'A{e} top',a['contest_R_year'],e*Fraction(18,100))
 check(f'A{e} special',a['special_R_year'],e*Fraction(7,100))
 check(f'A{e} envelope',a['guarantee_max_R_year']+a['contest_R_year']+a['special_R_year'],e)
 check(f'A{e} finite special',sum(x['award_R']*x['slots'] for x in a['special_slots_month'])*12,a['special_R_year'])
 unit=e*Fraction(18,100)/(7200*4)
 check(f'A{e} n40 pool',a['group40_pool_R_cycle'],unit*40)
 check(f'A{e} n40 slot1',a['group40_top_R'][0],int(unit*40*Fraction(4,10)))
 check(f'A{e} team1/5',a['group40_first_member_team5_R_cycle'],int(unit*40*Fraction(4,10)/5))
 check(f'A{e} guarantee actual certificate cash',a['guarantee_certificate_cash_all_N_RUB'],7200*G/5)
 check(f'B{e} envelope',b['contests']['annual_max_R']+b['special']['annual_max_R'],e)
 check(f'B{e} finite special',sum(x['award_R']*x['slots'] for x in b['special']['monthly_levels'])*12,b['special']['annual_max_R'])
 check(f'B{e} no guarantee',b['lower_tier']['award_R'],0)
 unit=e*Fraction(3,4)/(7200*4)
 check(f'B{e} n40 slots',b['contests']['n40_top_R'],[int(unit*40*s) for s in (Fraction(4,10),Fraction(3,10),Fraction(2,10),Fraction(1,10))])
 check(f'B{e} team slots',b['contests']['n40_eight_teams_five_member_R'],[int(unit*40*s/5) for s in (Fraction(4,10),Fraction(3,10),Fraction(2,10),Fraction(1,10))])
 check(f'B{e} cert cash',b['sku_sensitivity']['new_R_all_certificate_procurement_RUB'],e/5)
 check(f'B{e} cert uplift',b['sku_sensitivity']['all_new_certificate_cost_uplift_vs_mixed_RUB'],e*0.006)

# All supplied individual rows, each threshold is a separate save-only path.
for branch in 'AB':
 data=rows(R/f'branches/{branch}/employee-profiles.csv')
 for i,row in enumerate(data,2):
  e=int(row['E_R_year'] if branch=='A' else row['envelope_R_year'])
  p=row['profile']; events=row['fixed_case']=='specified_actual_events' if branch=='A' else row['corporate_events_case']=='True'
  G,top,post12,targets=trajectory(branch,e,p,events)
  check(f'{branch} profiles row{i} top',int(row['top_R_per_3month_cycle'] if branch=='A' else row['R_each_top_cycle']),top)
  check(f'{branch} profiles row{i} annual',int(row['R_earned_per_12observation_months'] if branch=='A' else row['R_four_completed_cycles']),G+4*top)
  check(f'{branch} profiles row{i} calendar12',int(row['R_post_calendar_months1_12_C1'] if branch=='A' else row['R_calendar_first_year_m1_m12']),post12)
  check(f'{branch} profiles row{i} fixed',int(row['fixed_C_first_year'] if branch=='A' else row['C_corporate_first_year']),(1050 if p=='novice' else 1250) if events else 0)
  for target in targets:
   field=f'first_{target}C_target_month_C1_save_only' if branch=='A' else f'first_{target}C_{ {1500:300,2500:500,5000:1000}[target]}RUB_month'
   check(f'{branch} profiles row{i} first{target}',int(row[field]) if row[field] else None,targets[target])

# B independently reconstructed finite-slot/tie examples (including rounding).
for i,row in enumerate(rows(R/'branches/B/edge-cases.csv'),2):
 e=int(row['envelope_R_year']); unit=Fraction(e*3,4)/(7200*4); pool=Fraction(row['pool_R']); case=row['case']
 values=json.loads(row['personal_payouts_R'])
 check(f'B edge row{i} sum',sum(values.values()),int(row['total_posted_R']))
 check(f'B edge row{i} conservation',float(pool)-sum(values.values()),float(row['unissued_R']))
 if 'all_tie' in case:check(f'B edge row{i} tie',list(set(values.values())),[int(pool/40)])
 if 'one_qualified' in case:check(f'B edge row{i} one qualified',list(values.values()),[int(pool*Fraction(4,10))])

# Reconstruct monthly prospective schedules without executing branch scripts.
for row in rows(R/'branches/A/first-launch.csv'):
 e=int(row['E_R_year']);m=int(row['month']);G=2500 if e==24000000 else 3750;u=150 if e==24000000 else 225
 g=sum(800*G for s in range(1,10) for start in range(s,37,12) if m==start+6)
 t=sum(800*u for s in range(1,10) for start in range(s,37,3) if m==start+3)
 sp=(140000 if e==24000000 else 210000) if m<=36 else 0
 check(f'A calendar{e} m{m} guarantee',int(row['guarantee_post_all_success_R']),g)
 check(f'A calendar{e} m{m} top',int(row['top_full_all_success_R']),t)
 check(f'A calendar{e} m{m} special',int(row['special_full_R']),sp)
 check(f'A calendar{e} m{m} sum',int(row['R_post_all_success_max']),g+t+sp)
for row in rows(R/'branches/B/calendar.csv'):
 e=int(row['envelope_R_year']);m=int(row['month']);t=e*Fraction(3,4)/12;s=e*Fraction(1,4)/12
 check(f'B calendar{e} m{m} posted',float(row['posted_total_R']),(t if 4<=m<=39 else 0)+(s if 2<=m<=37 else 0))

# Historical sliding-retry fixture is retained in retry-burst-independent.json and initial/.
# Current fixed dates are independently checked in delta_verify.py.

# Current immutable comparator paths (E36 does not scale its E24 mechanics).
comparison=[]
for p in ['ordinary_no_top','strong_repeat_winner','novice','team_member','part_time','restricted_region']:
 for events in (False,True):
  _,top,posted,targets=trajectory('I',24000000,p,events)
  comparison.append({'candidate_key':'CON-015@v1','profile':p,'corporate_events':events,'R_quarter':500+top,'R_four_cycles':4*(500+top),'R_post_calendar12_C1':posted,'C_corporate_first_year':(1050 if p=='novice' else 1250) if events else 0,**{f'first_{k}C_save_only_month_C1':v for k,v in targets.items()},'receipt_limit':'Balance threshold only; actual catalog/address/stock and unknown certificate<=3 reset must be checked.'})
with (OUT/'incumbent-profiles-independent.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
# Text discrepancy is reported, never silently repaired by checker.
check('A team pool agrees with scenario rates','250*n_unique_people' not in A['contests']['team_rule'],True)

files=[R/'inputs'/n for n in ['context.md','evidence.md','diagnosis.md','baseline.md','rubric.json']]+[R/f'branches/{b}/{n}' for b in 'AB' for n in ['finance-spec.json','employee-profiles.csv','concept-016.md' if b=='A' else 'concept-017.md']]+[R/'supporting/reward-basis.md',R/'supporting/reward-sources.json',R/'supporting/employee-profiles.md']
report={'independence':'No imports/execution of author calculators, source hashes/immutable import independently checked. Synthetic desk arithmetic is not bank evidence.','checks':checks,'failed':[x for x in checks if not x['pass']],'count':len(checks),'input_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
# Fractions only occur as numerically exact expected results.
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda v:float(v) if isinstance(v,Fraction) else str(v))+'\n')
print(json.dumps({'checks':len(checks),'failed':report['failed']},ensure_ascii=False))
