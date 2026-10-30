"""Recheck provenance only; does not recode feedback or reread full studies."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=ROOT/'analysis/iterations/iteration-002/rounds/001'
oldchecks=json.loads((old/'checks/evidence/source-checks.json').read_text())
rows={}
for key,v in oldchecks['sources'].items():
 p=ROOT/v['path'];actual=sha(p);rows[key]={'path':v['path'],'expected_sha256':v['sha256'],'actual_sha256':actual,'matches':actual==v['sha256'],'scope':'version identity only; substantive check reused from iteration-002 unless current report names selected reread'}
 assert rows[key]['matches'],key
r=OUT.parents[1]
m=json.loads((r/'inputs/manifest.json').read_text())
frozen={n:sha(r/'inputs'/n)==h for n,h in m['files'].items()};assert all(frozen.values())
a=ROOT/'analysis/iterations/iteration-003/incumbent/concept.md';b=old/'branches/A/concept.md'
assert a.read_bytes()==b.read_bytes()
res={'date':'2026-10-30','sources':rows,'frozen_files_match':frozen,'incumbent_exact_copy':True,'incumbent_sha256':sha(a),'diagnosis_reused_without_recoding':True,'full_external_studies_read':False,'external_web_search':False}
(OUT/'version-validation.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print('Verified',len(rows),'source identities, five frozen files and exact incumbent')
