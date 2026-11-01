#!/usr/bin/env python3
"""Rebind current candidate metadata to pinned parent decisions, without scoring.
All business decisions and amounts are copied; no performed award is invented.
"""
import sys
sys.dont_write_bytecode=True
import csv,json,importlib.util,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parents[2];ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists() and (p/'project').exists());PARENT=ROOT/'analysis/iterations/iteration-007/rounds/002/branches/B/con-023'
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 ev=mod('current_evaluator',HERE/'evaluator.py');reader=mod('public_reader',ROUND/'supporting/round002-stress/reader.py')
 current=json.loads((HERE/'metrics-spec.json').read_text());old=json.loads((PARENT/'metrics-spec.json').read_text());cache={}
 rows=list(csv.DictReader((PARENT/'decisions.csv').open()))
 assert all(float(r['top_U_R'])==0 for r in rows)
 for r in rows:
  name=r['scenario']
  if name not in cache:
   d=reader.expand_scenario(name,ROUND/'supporting/fixtures');cache[name]={p:[x for x in d['period_rules'] if x['period_id']==p] for p in {x['period_id'] for x in d['period_rules']}}
  package=json.loads(r['authorization_package']);rules=cache[name][r['period']]
  assert package['binding_hashes']['rule_sha256']==ev.digest({'policy':old,'period_rules':rules})
  package['candidate_key']=current['candidate_key'];package['decision_version']=current['version'];package['binding_hashes']['rule_sha256']=ev.digest({'policy':current,'period_rules':rules})
  r['authorization_package']=json.dumps(package,ensure_ascii=False);r['authorization_package_sha256']=ev.digest(package)
 with (HERE/'decisions.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps({'business_decisions_reused':len(rows),'raw_scenarios_for_metadata_hash_only':len(cache),'scoring_evaluations':0,'current_candidate':current['candidate_key']}))
if __name__=='__main__':main()
