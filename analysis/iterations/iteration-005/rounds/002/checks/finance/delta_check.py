#!/usr/bin/env python3.12
"""Targeted post-rework delta verification only. No new scenarios or core formulas."""
import json,csv,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;OLD=R/'private/before-targeted-rework'
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
oldpins=json.loads((OLD/'versions-before-checks.json').read_text());newpins=json.loads((R/'private/versions-after-rework.json').read_text())
assert newpins==json.loads((R/'private/versions-before-checks.json').read_text())
for path,h in oldpins.items():assert sha((OLD/path).read_bytes())==h,path
for path,h in newpins.items():assert sha((R/path).read_bytes())==h,path
files=[]
for path,h in newpins.items():
 prior=sha((OLD/path).read_bytes()) if (OLD/path).exists() else None
 files.append({'path':path,'before_sha256':prior,'after_sha256':h,'changed':prior!=h})
# Monetary/workload mechanics and currency maximum remain exactly as pinned.
invariants=[]
for path in ['branches/A/finance-spec-013.json','branches/B/finance-spec-011.json']:
 b=json.loads((OLD/path).read_text());a=json.loads((R/path).read_text())
 for field in ['N_eligible','lower_tier','contests','special','stacking','annual_total_R','monthly_calendar_R','workload']:
  assert a[field]==b[field],(path,field)
  invariants.append({'path':path,'field':field,'before_sha256':sha(canonical(b[field])),'after_sha256':sha(canonical(a[field])),'unchanged':True})
 d=a['dated_prefunding'];assert d['promise_day']==14 and d['effort_start_day']==15
 assert d['ordinary_gross_peak_R_from_month4']==7200000 and d['special_unconfirmed_max_R']==200000
 assert d['ordinary_month_close_R']==5400000
for path in ['branches/A/first-launch.csv','branches/A/launch-years.csv','branches/A/stationary-m05.csv','branches/A/money-examples.csv']:
 assert (OLD/path).read_bytes()==(R/path).read_bytes(),path
 invariants.append({'path':path,'before_sha256':sha((OLD/path).read_bytes()),'after_sha256':sha((R/path).read_bytes()),'unchanged':True})
path='branches/B/first-launch.csv'
def normal_raw(q):return b''.join(line for line in q.read_bytes().splitlines(keepends=True) if line.startswith((b'EXPECTED,',b'FULL_NEW,')))
b=normal_raw(OLD/path);a=normal_raw(R/path);assert a==b and len(a.splitlines())==30
invariants.append({'path':path,'scope':'30 EXPECTED/FULL_NEW CSV rows raw bytes','before_sha256':sha(b),'after_sha256':sha(a),'unchanged':True})
path='branches/B/first-launch.json';b=json.loads((OLD/path).read_text());a=json.loads((R/path).read_text())
for scenario in ['EXPECTED','FULL_NEW']:
 assert a['scenarios'][scenario]==b['scenarios'][scenario]
 invariants.append({'path':path,'scope':scenario+' complete scenario object','before_sha256':sha(canonical(b['scenarios'][scenario])),'after_sha256':sha(canonical(a['scenarios'][scenario])),'unchanged':True})
# Every formerly mismatching numeric field now matches its same independent value.
rows=lambda p:list(csv.DictReader(p.open()))
oldcmp=rows(OLD/'checks/finance/source-monthly-comparison.csv');newcmp=rows(P/'source-monthly-comparison.csv')
index={(x['candidate_key'],x['scenario'],x['fixed_C_year'],x['month'],x['field']):x for x in newcmp}
resolved=[]
for x in oldcmp:
 if x['match']!='False':continue
 key=(x['candidate_key'],x['scenario'],x['fixed_C_year'],x['month'],x['field']);y=index[key]
 assert y['match']=='True' and abs(float(y['error']))<1e-5
 assert abs(float(x['independent_value'])-float(y['independent_value']))<1e-5
 resolved.append({'candidate_key':x['candidate_key'],'scenario':x['scenario'],'month':int(x['month']),'field':x['field'],'before_author_value':float(x['author_value']),'after_author_value':float(y['author_value']),'unchanged_independent_value':float(y['independent_value']),'before_error':float(x['error']),'after_error':float(y['error']),'status':'closed'})
assert len(resolved)==11
assert not any(x['match']=='False' for x in newcmp)
# Confirm copied audit calculation tables are byte-identical; no monetary core change.
for name in ['annual.csv','monthly.csv','launch-annual.csv','launch-monthly.csv','date-prefunding.csv','date-prefunding-late.csv','terminal-tail.csv','resources.csv','capacity.csv','edge-cases.csv']:
 b=(OLD/'checks/finance'/name).read_bytes();a=(P/name).read_bytes();assert a==b,name
 invariants.append({'path':'checks/finance/'+name,'before_sha256':sha(b),'after_sha256':sha(a),'unchanged':True})
concept=(R/'branches/A/concept-013.md').read_text();spec=json.loads((R/'branches/A/finance-spec-013.json').read_text())
assert 'полная стоимость97руб. по норме M05' not in concept
assert 'закупка такого сертификата стоит100руб.' in concept and 'полная стоимость SKU не установлена' in concept
assert '15months' in spec['first_launch_ref'] and '14months' not in spec['first_launch_ref']
out={'status':'pass','scope':'Single targeted delta; no new scenarios, ranking, financial core or bank facts.','current_freeze':'private/versions-after-rework.json == private/versions-before-checks.json','before_freeze':'private/before-targeted-rework/versions-before-checks.json','source_monthly_mismatches_before':11,'source_monthly_mismatches_after':0,'source_annual_mismatches_after':0,'resolved_numeric_fields':resolved,'resolved_text_items':[{'candidate_key':'CON-013@v2','item':'certificate500C nominal100RUB: procurement100RUB, service/fullSKUcost unknown, mixed970 basket not a single certificate price','status':'closed'},{'candidate_key':'CON-013@v2','item':'first_launch_ref15months including late third cohort','status':'closed'},{'candidate_key':'CON-013@v2','item':'day14 stock/payment/availability/single allocation OR verified independent cash, grossordinary7.2m+special0.2m, no cancellation of prior rights','status':'closed_as_explicit_conditional_design'},{'candidate_key':'CON-011@v2','item':'same dated condition; prior quality day28, no monthly ledger treated as daily proof','status':'closed_as_explicit_conditional_design'}],'invariants':invariants,'source_file_hashes':files,'remaining_limits':['Actual bank cash/inventory segregation, delivery dates, SKU and resource capacity unknown.','All previous shared adverse-scenario failures unchanged; not resolved by prose correction.'],'open_delta_findings':[]}
(P/'delta-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','source_monthly_mismatches_before','source_monthly_mismatches_after','source_annual_mismatches_after','open_delta_findings']},ensure_ascii=False))
