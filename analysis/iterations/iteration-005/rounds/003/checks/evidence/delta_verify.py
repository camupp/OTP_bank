"""Targeted rework check only. No synthetic/source/financial model rerun.
Writes only delta-verification.json beside this script.
"""
import hashlib,json
from pathlib import Path
O=Path(__file__).resolve().parent
R=O.parent.parent
A=R/'private/before-targeted-rework'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(A/'versions-before-checks.json')
new=read(R/'private/versions-after-rework.json')
before=read(R/'private/versions-before-checks.json')
assert new==before and old.keys()==new.keys() and len(new)==38
assert all(sha(A/p)==h for p,h in old.items())
assert all(sha(R/p)==h for p,h in new.items())
changed=[p for p in old if old[p]!=new[p]]
assert set(changed)=={'branches/B/concept-015.md','branches/B/changes.md'}
p='branches/B/concept-015.md'
original=(A/p).read_text();current=(R/p).read_text()
assert original.count('с lower это42500 в год')==1
assert current==original.replace('с lower это42500 в год','с lower это42000 в год',1)
assert 'с lower это42000 в год' in current.splitlines()[44]
assert 4*(10000+500)==42000 and 42000+15000==57000
q='branches/B/changes.md'
original_changes=(A/q).read_text();current_changes=(R/q).read_text()
expected='\nЦелевой возврат1/1 (`rounds/003/rework.md`): в concept-015.md:45 исправлена только опечатка42500→42000R/год. Проверка:4×(10000+500)=42000;42000+15000=57000. Механика, cap97000, формулы спецификации, CSV/JSON и скрипты без изменений; модели/синтетика не запускались. SHA256 concept до: `'+old[p]+'`; после: `'+new[p]+'`.\n'
assert current_changes==original_changes+expected
initial='checks/evidence/verification.json'
assert sha(A/initial)==sha(R/initial)
v=read(R/initial)
assert v['candidate_hashes']==old and v['counts']['checks']==10030
coordinator=read(R/'private/rework-coordinator-check.json')
assert set(coordinator['changed_files'])==set(changed) and coordinator['unchanged_files']==36
out={'scope':'Only one arithmetic phrase and append-only rework record; no repeated synthetic/source/finance check','candidate_key':'CON-015@v1','status':'supported','closed_finding':'B06','concept_locator':'branches/B/concept-015.md:45','correction':{'old_ordinary_annual_R':42500,'current_ordinary_annual_R':42000,'formula':'4*(10000+500)=42000;42000+15000=57000','special_inclusive_max_R':57000,'formal_cap_R':97000},'concept_exactly_one_expected_replacement':True,'changes_md_exact_expected_append_only':True,'changed_files':[{ 'path':p,'before_sha256':old[p],'after_sha256':new[p]} for p in changed],'unchanged_files':36,'all_38_current_hashes_match_both_current_manifests':True,'all_38_archive_hashes_match_original_manifest':True,'coordinator_check_independently_confirmed':True,'initial_verification_unchanged':{'path':initial,'sha256':sha(R/initial),'archive_path':'private/before-targeted-rework/'+initial,'prior_assertions_reused':10030,'assertions_rerun':0},'preserved_limits':['SHA/ID formats choose different samples; equal outcomes apply to current homogeneousQA98fixtures, not arbitrary heterogeneous bank errors.','A8+2min unmeasured design assumption; actual source/QAexisting/time/ACL/capacity unknown.','Cards do not measure employee understanding; real usefulSKU/value/motivation unknown.','Full finance/stock/resource assessment separate.'],'new_web_or_diagnosis_or_source_reading':False,'full_synthetic_or_financial_grid_rerun':False,'candidate_inputs_registries_modified_by_checker':False}
(O/'delta-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'concept_single_replacement':True,'changes_append_only':True,'current_hashes':38,'unchanged_files':36,'B06':'closed','synthetic_assertions_rerun':0},ensure_ascii=False))
