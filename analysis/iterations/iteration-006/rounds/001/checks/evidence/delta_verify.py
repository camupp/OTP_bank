"""Independent v2 delta, fixed-date windows, open-right tails and freshness checks."""
from pathlib import Path
import csv,hashlib,itertools,json
R=Path(__file__).resolve().parents[2]; OUT=R/'checks/evidence';ROOT=R.parents[4]
OLD=R/'private/before-targeted-rework/branches/A';NEW=R/'branches/A'
old=json.loads((OLD/'finance-spec.json').read_text());new=json.loads((NEW/'finance-spec.json').read_text())
checks=[]
def chk(name,actual,expected):
 ok=abs(actual-expected)<1e-7 if isinstance(actual,(int,float)) and isinstance(expected,(int,float)) else actual==expected
 checks.append({'check':name,'pass':ok,'actual':actual,'expected':expected})
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def data(p):
 with p.open() as f:return list(csv.DictReader(f))
chk('newcandidatekey',new['candidate_key'],'CON-016@v2')
chk('parentconceptSHA',new['version_provenance']['archive_concept_sha256'],sh(OLD/'concept-016.md'))
for section in ['N_eligible','scenario_parameters','special','stacking']:
 chk('unchanged '+section,new[section],old[section])
for section,drop in [('contests','team_rule'),('workload','IT_initial_schedule')]:
 a={k:v for k,v in new[section].items() if k!=drop};b={k:v for k,v in old[section].items() if k!=drop}
 chk('unchanged numeric '+section,a,b)
for field in ['initial_cohorts','cohort_size','cohort_starts_months','first_all_good_post_months','subsequent_all_good_post_months']:
 chk('unchanged guarantee '+field,new['guarantee'][field],old['guarantee'][field])
chk('team rule150/225',all(x in new['contests']['team_rule'] for x in ['150*n','225*n']),True)
chk('no stale pool250','250*n' not in new['contests']['team_rule'],True)

calendar=data(NEW/'first-launch.csv')
for e in [24000000,36000000]:
 G=2500 if e==24000000 else 3750;unit=150 if e==24000000 else 225
 gs=[c+12*k for c in range(1,10) for k in range(3) if c+12*k<=36]
 ts=[s for c in range(1,10) for s in range(c,37,3)]
 sub=[r for r in calendar if int(r['E_R_year'])==e]
 chk(f'E{e} months',[int(r['month']) for r in sub],list(range(1,40)))
 for row in sub:
  m=int(row['month'])
  openg=sum(800*G for s in gs if s<=m<s+6)
  grossg=sum(800*G for s in gs if s<=m<=s+6)
  opent=sum(800*unit for s in ts if s<=m<s+3)
  postg=sum(800*G for s in gs if m==s+6)
  chk(f'E{e} m{m} G allowed',int(row['guarantee_post_allowed_upper_R']),postg)
  chk(f'E{e} m{m} openG',int(row['guarantee_conditional_open_endmonth_R']),openg)
  chk(f'E{e} m{m} grossG',int(row['guarantee_gross_open_before_quality_close_R']),grossg)
  chk(f'E{e} m{m} openTop',int(row['top_conditional_open_endmonth_R']),opent)
  chk(f'E{e} m{m} allOpen',int(row['total_conditional_open_endmonth_R']),openg+opent)
  chk(f'E{e} m{m} G no qualification shift',postg<=800*G,True)
 m12=next(x for x in sub if int(x['month'])==12)
 m36=next(x for x in sub if int(x['month'])==36)
 m39=next(x for x in sub if int(x['month'])==39)
 posted=sum(int(x['R_post_all_success_max']) for x in sub if int(x['month'])<=12)
 chk(f'E{e} posted12',posted,15840000*(e/24000000))
 chk(f'E{e} conditional12',int(m12['total_conditional_open_endmonth_R']),7080000*(e/24000000))
 unopened=e-posted-int(m12['total_conditional_open_endmonth_R'])
 chk(f'E{e} unopened12',unopened,1080000*(e/24000000))
 chk(f'E{e} conditional36',int(m36['total_conditional_open_endmonth_R']),7080000*(e/24000000))
 chk(f'E{e} conditional39',int(m39['total_conditional_open_endmonth_R']),0)
 chk(f'E{e} final guarantee39',max(s+6 for s in gs),39)
 chk(f'E{e} final top39',max(s+3 for s in ts),39)
 chk(f'E{e} m13 onlycohort7',[c for c in range(1,10) if any(c+12*k+6==13 for k in range(3))],[7])

# Failure of either fixed quarter cannot create an award at a different quarter date.
patterns=[]
for bits in itertools.product([False,True],repeat=4):
 earned=[]
 # next-year pair deliberately qualified; current first pair decides m7.
 if bits[0] and bits[1]:earned.append(7)
 earned.append(19)
 chk('C1 pattern'+str(bits)+' never m13',13 in earned,False)
 chk('C1 pattern'+str(bits)+' fail0G',7 in earned,bits[0] and bits[1])
 patterns.append({'four_quarters':bits,'first_window_G':2500 if 7 in earned else 0,'next_year_both_pass_date':19,'m13_G':0})
chk('newhire C1m4 firstwindow no own firstquarter',False and True,False)
chk('newhire C1m4 next qualifieddate',1+12+6,19)
chk('newhire C1m4 waitmonths',19-4,15)

# Historical burst, current corrected bound; M05 baskets/HR are illustrative arithmetic.
capacity=[]
for label,oldannual,newmonth,expectedB,expectedH in [('historical_v1_year2',32000000,6500000,3433.3333333333335,235.55555555555554),('fixed_v2_year2',32000000,2500000,2633.3333333333335,214.22222222222223),('fixed_v2_year1',40000000,2500000,2766.6666666666665,217.77777777777777),('fixed_v2_E36_year1',40000000,3750000,3016.6666666666665,224.44444444444446)]:
 baskets=(96000000/12+oldannual/12+newmonth)/5000
 hours=80+baskets*.02+baskets*.2/30+64
 chk(label+' baskets',baskets,expectedB);chk(label+' HR',hours,expectedH)
 capacity.append({'scenario':label,'baskets':baskets,'HR_hours_total':hours,'pass_baskets3000':baskets<=3000,'pass_HR220':hours<=220,'scope':'Independent arithmetic only; full dated budget/stock/cash assigned finance.'})

# Nothing else in the frozen source/other candidates may silently change.
prior=json.loads((OUT/'initial/final-v1-verification.json').read_text())['input_hashes']
for path,expected in prior.items():
 if '/branches/A/' not in path:
  chk('unchanged non-A '+path,sh(ROOT/path),expected)
current=json.loads((OUT/'verification.json').read_text())
for path,expected in current['input_hashes'].items():chk('current check fresh '+path,sh(ROOT/path),expected)
report={'classification':'Independent delta; no authorcalculator imported/executed, no new external evidence. All current scenario pass statements limited to named arithmetic; actual bank readiness unknown.','checks_count':len(checks),'failed':[x for x in checks if not x['pass']],'checks':checks,'fixed_window_patterns':patterns,'capacity_examples':capacity,'current_input_hashes':current['input_hashes'],'archive_source_sha':sh(OLD/'concept-016.md'),'new_concept_sha':sh(NEW/'concept-016.md'),'main_verification_count':current['count'],'main_verification_failed':current['failed']}
(OUT/'delta-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'failed':report['failed']},ensure_ascii=False))
