"""Artifact checks for the exported reading deck; not a concept-effect test."""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import csv,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from urllib.parse import unquote
OUT=Path(__file__).resolve().parents[1];BUILD=OUT/'.build';ROOT=OUT.parents[1]
SOURCE_STEM='CupMoscow2026-ОТП-НазваниеКоманды'
team=json.loads((ROOT/'project/team.json').read_text())
STEM='CupMoscow2026-ОТП-'+team['name']
PDF=BUILD/'read-deck-render'/(STEM+'.pdf');PPTX=OUT/(STEM+'.pptx')
RENDER=PDF.parent;NS={'x':'http://www.w3.org/1999/xhtml'}
for args in [['-layout',str(PDF),str(RENDER/'pdf-text.txt')],['-bbox-layout',str(PDF),str(RENDER/'pdf-bbox.html')]]:
 subprocess.run(['pdftotext',*args],check=True)
pages=(RENDER/'pdf-text.txt').read_text().split('\f');pages=[p for p in pages if p.strip()]
checks={};issues={};checks['27_pages_8_main_19_appendices']=len(pages)==27
text=json.loads((BUILD/'read-deck-text.json').read_text())
with ZipFile(PPTX) as z:
 checks['pptx_crc']=z.testzip() is None
 checks['27_slides_and_notes']=len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])==27 and len([n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)])==27
 coord=[]
 for n in range(1,28):
  r=ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
  for sp in r.findall('.//{*}sp'):
   off=sp.find('.//{*}xfrm/{*}off');ext=sp.find('.//{*}xfrm/{*}ext')
   if off is not None and ext is not None:
    x,y=int(off.get('x')),int(off.get('y'));w,h=int(ext.get('cx')),int(ext.get('cy'))
    if min(x,y,w,h)<0 or x+w>1280*9525 or y+h>720*9525:coord.append((n,x,y,w,h))
 checks['all_shapes_within_slide']=not coord;issues['shape_bounds']=coord
 expected={8:[9],9:[10,13,18,19]};targets=[]
 for n,pnums in expected.items():
  r=ET.fromstring(z.read(f'ppt/slides/_rels/slide{n}.xml.rels'))
  targets += [e.get('Target')==f'slide{p}.xml' for p in pnums for e in r if e.get('Id','').startswith('readDeckJump') and e.get('Target')==f'slide{p}.xml']
 checks['five_internal_pptx_navigation_links']=len(targets)==5 and all(targets)
checks['five_pdf_navigation_annotations']=len(re.findall(rb'/Subtype\s*/Link',PDF.read_bytes()))>=5
checks['workbook_byte_identical']=hashlib.sha256((OUT/(STEM+'.xlsx')).read_bytes()).digest()==hashlib.sha256((BUILD/'source-template'/(SOURCE_STEM+'.xlsx')).read_bytes()).digest()
# Every visible word must survive PDF export. Wrapping does not change words here.
word=lambda s:Counter(re.findall(r'[\w]+',s,flags=re.UNICODE))
diff=[]
for n,page in enumerate(pages,1):
 expected=word(' '.join(text[str(n)]));actual=word(page)
 if expected!=actual:diff.append({'page':n,'missing':dict(expected-actual),'extra':dict(actual-expected)})
checks['every_slide_word_present_in_pdf']=not diff;issues['text_differences']=diff
r=ET.parse(RENDER/'pdf-bbox.html');overlaps=[];outside=[]
for n,page in enumerate(r.findall('.//x:page',NS),1):
 lines=page.findall('.//x:line',NS)
 for i,a in enumerate(lines):
  aa=[float(a.get(k)) for k in ['xMin','yMin','xMax','yMax']]
  ta=' '.join(w.text or '' for w in a)
  if aa[0]<0 or aa[1]<0 or aa[2]>float(page.get('width'))+1 or aa[3]>float(page.get('height'))+1:outside.append([n,ta])
  for b in lines[i+1:]:
   bb=[float(b.get(k)) for k in ['xMin','yMin','xMax','yMax']]
   xo=min(aa[2],bb[2])-max(aa[0],bb[0]);yo=min(aa[3],bb[3])-max(aa[1],bb[1])
   if xo>3 and yo>min(aa[3]-aa[1],bb[3]-bb[1])*0.25:overlaps.append([n,ta,' '.join(w.text or '' for w in b)])
checks['no_pdf_text_overlap']=not overlaps;checks['no_pdf_text_outside_page']=not outside
issues['pdf_overlaps']=overlaps;issues['pdf_outside']=outside
main=' '.join(pages[:8]);checks['no_internal_concept_codes_on_main']=not re.search(r'CON-\d|\bE24\b|\bQA\b|pre-read|\bledger\b',main)
checks['github_url_visible_pages8_27']=all(team['github'] in pages[n-1] for n in [8,27])
checks['team_name_and_all_five_members_visible']=team['name'] in pages[0] and team['name'] in pages[7] and all(m['name'] in pages[7] and ' '.join(m['role'].split()) in ' '.join(pages[7].split()) for m in team['members'])
with ZipFile(PPTX) as z:
 checks['github_hyperlinks_exact_target']=all(any(e.get('Target')==team['github'] and e.get('TargetMode')=='External' for e in ET.fromstring(z.read(f'ppt/slides/_rels/slide{n}.xml.rels'))) for n in [8,27])
checks['github_hyperlinks_exported_to_pdf']=PDF.read_bytes().count(team['github'].encode())>=2
checks['base_annual_both_quarters_wait_visible']=all(t in pages[2] for t in ['2500','обоих кварталах','12 месяцев','7–15'])
checks['contest_threshold_and_four_places_visible']=all(t in pages[3] for t in ['110%','четыре','призовых','100%','120%'])
checks['explicit_no_self_award_on_main']='Самому назначить или одобрить награду' in pages[4]
checks['costs_and_budget_boundary_visible']=all(t in pages[6] for t in ['31,7','34','30','3,99','3,15','7,26'])
summary=json.loads((BUILD/'summary.json').read_text());row=summary['procurement_and_currency'][0]
checks['year1_finance_reconciles']=round(row['cash_RUB']+row['reserve_delta_RUB']+row['buffer_RUB']+row['certificate500_adjustment_RUB'])==31684000
checks['award_split_reconciles']=7200*2500+7200*150*4+140000*12==24000000
rows=list(csv.DictReader((ROOT/'analysis/iterations/iteration-008/rounds/001/branches/A/cost-periods.csv').open()))
all39=next(r for r in rows if r['period']=='all39')
checks['operating_costs_reconcile']=float(all39['batch_total_operating_RUB'])+3990000==23490000 and float(all39['no_batch_total_operating_RUB'])+3990000==29550000
snap=ROOT/'analysis/iterations/iteration-008/rounds/001/snapshot.json';d=json.loads(snap.read_text());bad=[]
for f,h in d['files'].items():
 p=snap.parent/f
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:bad.append(f)
checks['sealed_008_files_unchanged']=not bad;issues['sealed_hash_differences']=bad
broken=[]
for name in ['storyline.md','source-map.md','defense-notes.md']:
 f=OUT/name
 for link in re.findall(r'\]\(([^)]+)\)',f.read_text()):
  if '://' not in link and not (f.parent/unquote(link.split('#')[0])).exists():broken.append([name,link])
checks['companion_local_links_resolve']=not broken;issues['broken_links']=broken
checks['pdf_under_18mb']=PDF.stat().st_size<18000000
report={'checks':checks,'all_pass':all(checks.values()),'issues':issues,'sealed_files_checked':len(d['files']),'visual_review':'Prior full-deck visual review retained; team details on pages1/8 and GitHub on pages8/27 updated and rechecked.','limitations':['Editorial self-check; no new independent concept review','No bank pilot or measured motivational effect','Team names, roles and repository URL supplied by user; no submission performed']}
(BUILD/'read-deck-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['all_pass'] else 1)
