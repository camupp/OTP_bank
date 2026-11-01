import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
P=Path(__file__).parent
f=P/'evaluator.py';s=f.read_text()
s=s.replace("FIXTURE = ROUND / 'supporting/fixtures'", "FIXTURE = ROUND / 'supporting/fixtures'\nADDENDUM = ROUND / 'supporting/round002-stress'\nPUBLIC_CONFIGS = json.loads((ADDENDUM/'business-config.json').read_text())['configs']\n\ndef digest(rows):\n    return hashlib.sha256((json.dumps(rows,ensure_ascii=False,sort_keys=True,indent=2)+'\\n').encode()).hexdigest()\n\ndef stamp(x, end=False):\n    if not x:return None\n    if len(x)==10:x += 'T23:59:59+03:00' if end else 'T00:00:00+03:00'\n    v=datetime.fromisoformat(x)\n    if v.tzinfo is None:v=v.replace(tzinfo=__import__('datetime').timezone(__import__('datetime').timedelta(hours=3)))\n    return v\n\ndef batch_errors(data, period):\n    bs=[b for b in data.get('batch_metadata',[]) if b['period_id']==period]\n    if not bs:return []  # legacy individual path, never invent a batch signature\n    errors=[]\n    for b in bs:\n        regs=[r for r in data['comparison_registry'] if r['period_id']==period]\n        ms=[m for m in data['team_members'] if m['period_id']==period]\n        if b.get('roster_sha256')!=digest(regs) or b.get('roster_count')!=len(regs):errors.append('signed_roster_changed')\n        if b.get('team_members_sha256')!=digest(ms) or b.get('team_member_count')!=len(ms):errors.append('signed_members_changed')\n        forbidden={r['subject_id'] for r in regs}|{m['employee_id'] for m in ms}\n        copy=dict(b,action='source_batch_composition_review')\n        errors+=approval_errors(copy,forbidden,'source_batch_composition_review')\n        if not b.get('version') or not b.get('source_version'):errors.append('batch_version_missing')\n        expected={r['period_id']+':'+r['subject_id'] for r in regs}|{m['period_id']+':'+m['employee_id'] for m in ms}\n        if not expected <= set(b.get('approval_refs',[]))|set(b.get('exception_refs',[])):errors.append('batch_approval_roster_incomplete')\n    return sorted(set(errors))")
s=s.replace("elif len(rows) != m['received_count'] or digest != m['received_sha256']:","elif m['availability']=='partial':\n            problems[period].append((table,'partial_source'))\n        elif len(rows) != m['received_count'] or digest != m['received_sha256']:")
s=s.replace("cap = caps[p, s]; family = cap['family']; rule = rules[p, family]", "cap = caps[p, s]; family = cap['family']; rule = rules[p, family]")
s=s.replace("cfg = spec['roles'][family]; close = day(rule['quality_close'])", "cfg = spec['roles'][family]; close = day(rule['quality_close'])\n        close_at=stamp(rule.get('quality_close_at') or rule['quality_close'],True)\n        start_at=stamp(rule['start']); end_at=stamp(rule['end'],True)")
s=s.replace("own = {s} | {m['employee_id'] for m in members if m['team_id']==s and m['period_id']==p}","own = {s} | {m['employee_id'] for m in members if m['team_id']==s} | {m['team_id'] for m in members if m['employee_id']==s}")
s=s.replace("rows = unique([e for e in data['work_events'] if e['period_id']==p and e['subject_id']==s], 'event_id')", "rows = unique([e for e in data['work_events'] if e['period_id']==p and e['subject_id']==s], 'event_id')\n        if data.get('personal_windows'):\n            # All source partitions may surround a boundary. Preserve unfinished assigned obligations.\n            rows=[e for e in rows if stamp(e['event_at'])>=start_at and (start_at<=stamp(e['assigned_at'])<=end_at or start_at<=stamp(e['due_at'])<=end_at)]")
s=s.replace("and day(a.get('finalized_at')) and day(a['finalized_at'])<=close", "and stamp(a.get('finalized_at')) and stamp(a['finalized_at'])<=close_at")
s=s.replace("scores=[min(max(0,100-2*a['minor']-10*a['major']) for a in group) for group in inspections.values()]", "scores=[min(max(0,100-2*a['minor']-10*a['major']-100*a['critical']) for a in group) for group in inspections.values()]")
s=s.replace("and day(latest['accepted_at'])<=close)","and stamp(latest['accepted_at'])<= (end_at if data.get('personal_windows') else close_at))")
s=s.replace("use_min=None; early_min=None", "use_min=None; early_min=None; project_type=None; business_config=None; business_ready=None")
s=s.replace("x=ps[0]\n                if not x.get('criteria_ref')", "x=ps[0]\n                project_type='analytical_business_decision_package' if x.get('usage_measure')=='distinct_business_decisions_using_deliverable' else 'workflow'\n                configs=[c for c in PUBLIC_CONFIGS if c['comparison_group_id']==reg['comparison_group_id'] and c['source_query']['period_id']==p and c['work_type']==project_type and c['version']==1]\n                if len(configs)!=1:pending.append('business_config_missing_or_ambiguous:'+root)\n                else:\n                    business_config=configs[0]\n                    if stamp(business_config['approved_at'])>=start_at or business_config['owner'] in own:pending.append('business_config_not_prospective_independent')\n                    # Legacy refs are left unchanged; addendum refs bind the prospective config version.\n                    if x.get('criteria_ref','').startswith('CFG-') and x['criteria_ref']!=business_config['config_id']+'-v1':pending.append('conflicting_business_goal_version')\n                if not x.get('criteria_ref')")
s=s.replace("if day(x['acceptance_at'])>close or day(x['usage_observed_at'])>close:", "deadline=stamp(business_config['business_deadline']) if business_config else close_at\n                if stamp(x['acceptance_at'])>deadline or stamp(x['usage_observed_at'])>deadline:")
s=s.replace("fail.append('actual_acceptance_or_use_after_close:'+root)","fail.append('actual_acceptance_or_use_after_business_deadline:'+root)")
s=s.replace("if x['usage_units']<=0: fail.append('unused:'+root)","if x['usage_units']<=0: fail.append('unused:'+root)\n                if business_config and x['usage_units']<business_config['target_value']:fail.append('business_use_target_not_met:'+root)\n                if business_config and business_config.get('readiness_criterion'):\n                    ready=stamp(business_config['readiness_criterion']['ready_by'])\n                    business_ready=stamp(x['acceptance_at'])<=ready and stamp(x['release_at'])<=ready\n                    # Early use only has meaning relative to the one named decision; no extra points for earlier timestamps.")
s=s.replace("stretch=accepted==n and use_min is not None and use_min>=cfg['stretch_usage'] and qmean is not None and qmean>=cfg['stretch_quality']", "stretch=accepted==n and qmean is not None and qmean>=cfg['stretch_quality']")
s=s.replace("if fail:state='not_earned';suff='sufficient'", "# Top is quality only, subject to robust sufficient exposure and normal business conditions.\n        quality_exposure=(len(inspections)>=20 and len({e['event_at'][:10] for e in rows})>=10) if family!='project' else (n>=1 and bool(coverage_trace) and all(t['covered'] for t in coverage_trace))\n        stretch=qmean is not None and qmean>=cfg['stretch_quality'] and quality_exposure\n        rank_key=(qmean or F(0),)\n        if fail:state='not_earned';suff='sufficient'")
s=s.replace("'usage_min':use_min,'early_min_days':early_min", "'usage_min':use_min,'early_min_days':early_min,'project_type':project_type,'business_config':business_config['config_id'] if business_config else None,'business_ready_by_preread':business_ready,'top_exposure_sufficient':quality_exposure")
s=s.replace("a=[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id']==person]", "a=[a for a in data['approvals_audit'] if a['period_id']==p and a['beneficiary_id']==person]\n            source_reviews=[v for v in a if v.get('action')=='source_completeness_review']\n            source_errors_person=[]\n            if data.get('batch_metadata'):\n                source_errors_person=batch_errors(data,p)\n                if not source_reviews:source_errors_person.append('source_review_missing')\n                else:source_errors_person+=approval_errors(max(source_reviews,key=lambda v:v.get('version',0)),forbidden,'source_completeness_review')")
s=s.replace("signed=not errors", "errors+=source_errors_person\n            signed=not errors")
s=s.replace("forbidden={s} | {person for person,_,_,_,_ in persons}","forbidden={s} | {person for person,_,_,_,_ in persons} | {m['employee_id'] for m in members if m['team_id']==s} | {m['team_id'] for m in members if m['employee_id'] in {person for person,_,_,_,_ in persons}}")
s=s.replace("'authorization_errors':errors,", "'authorization_errors':sorted(set(errors)),'source_review_errors':sorted(set(source_errors_person)),")
s=s.replace("eligible.sort(key=lambda u:u['rank_key'],reverse=True)", "eligible.sort(key=lambda u:u['qa_mean'],reverse=True)\n        # Conservative connected clusters: any adjacent difference below one point\n        # makes superiority unresolved. No rank is created by rounding noise.\n        cluster=0; previous=None\n        for u in eligible:\n            if previous is not None and previous-u['qa_mean']>=F(str(spec['quality']['substantive_difference_points'])):cluster+=1\n            u['rank_key']=(-cluster,)\n            previous=u['qa_mean']")
# Replace entrypoint with new source API and compact artifacts.
s=s[:s.index('def run():')]+'''def run():
    spec=json.loads((HERE/'metrics-spec.json').read_text())
    module=importlib.util.spec_from_file_location('public_reader',ADDENDUM/'reader.py')
    reader=importlib.util.module_from_spec(module);module.loader.exec_module(reader)
    decisions=[];unit_rows=[];windows=[];traces=[];groups=[];cal=[];summaries=[]
    for entry in reader.scenario_index(FIXTURE):
        scenario=entry['name'];data=reader.expand_scenario(scenario,FIXTURE);us,ps=evaluate(data,spec)
        states={}
        for u in us:
            states[u['state']]=states.get(u['state'],0)+1
            # All unit numbers remain reproducible without copying raw events.
            unit_rows.append(dict(scenario=scenario,**{k:v for k,v in u.items() if k not in ('qa_coverage','accepted_root_ids')}))
        seen=set()
        for u in us:
            signature=(u['family'],u['state'],u['stretch'],str(u['qa_mean']),tuple(u['reason']))
            if signature not in seen:
                seen.add(signature)
                traces.append({'scenario':scenario,'period':u['period'],'subject':u['subject'],'family':u['family'],'state':u['state'],'qa_mean':u['qa_mean'],'normal':u['normal'],'stretch':u['stretch'],'rank':u['rank'],'reasons':u['reason'],'refs':u['source_refs'],'coverage':u['qa_coverage'][:2], 'source_locator':entry.get('patch_ref') or entry.get('source_ref') or 'fixtures/source/base.json'})
        for x in ps:
            decisions.append(dict(scenario=scenario,**{k:v for k,v in x.items() if k!='approval_trace'}))
        for p,g in sorted({(u['period'],u['group']) for u in us}):
            gp=[x for x in ps if x['period']==p and x['group']==g];gu=[u for u in us if u['period']==p and u['group']==g]
            pool=150*len({x['subject'] for x in gp});unsettled=any(u['top_state']=='pending_group' for u in gu)
            calculated=sum(x['potential_top_R'] for x in gp);authorized=sum(x['top_U_R'] for x in gp)
            reserved=pool if unsettled else sum(x['top_reserved_R'] for x in gp)
            assert authorized+reserved<=pool
            groups.append(dict(scenario=scenario,period=p,group=g,pool_R=pool,calculated_R=calculated,authorized_U_R=authorized,reserved_R=reserved,unissued_R=pool-authorized-reserved))
        rulemap={(r['period_id'],r['family']):r for r in data['period_rules']}
        for person,window in sorted({(x['subject'],x['window_id']) for x in ps}):
            qs=sorted([x for x in ps if x['subject']==person and x['window_id']==window],key=lambda x:stamp(rulemap[x['period'],x['family']]['start']))
            # First TWO contiguous fixed quarters only: never pick the best two.
            qs=qs[:2];same=len(qs)==2
            if same:
                r0=rulemap[qs[0]['period'],qs[0]['family']];r1=rulemap[qs[1]['period'],qs[1]['family']]
                same=day(r1['start'])==day(r0['end'])+timedelta(days=1)
                pw=[w for w in data.get('personal_windows',[]) if w['subject_id']==person and w['window_id']==window]
                if pw:same=same and day(pw[0]['start'])==day(r0['start'])
            passed=same and all(x['calculated_normal'] for x in qs)
            invalid=any(x['calculated_qualification_state']=='not_earned' for x in qs)
            state='not_earned' if invalid else 'calculated_earned' if passed else 'pending'
            authorized=2500 if passed and all(x['authorization']=='authorized' for x in qs) else 0
            windows.append(dict(scenario=scenario,subject=person,window_id=window,quarters=','.join(x['period'] for x in qs),contiguous_fixed_quarters=same,calculated_state=state,calculated_G_R=2500 if passed else 0,authorized_U_R=authorized,reserved_R=0 if invalid else 2500-authorized,original_window_preserved=True,posted_R=0))
        for e in data['work_events'] if data.get('personal_windows') else []:
            rs=[r for r in data['period_rules'] if r['family']==e['family'] and r['comparison_group_id']==next(z['comparison_group_id'] for z in data['comparison_registry'] if z['subject_id']==e['subject_id'] and z['period_id']==e['period_id'])]
            actual=[r['period_id'] for r in rs if stamp(r['start'])<=stamp(e['event_at'])<=stamp(r['end'],True)]
            qas=[a for a in data['quality_acts'] if a.get('event_id')==e['event_id']]
            r=next(r for r in data['period_rules'] if r['period_id']==e['period_id'])
            cal.append(dict(scenario=scenario,event_id=e['event_id'],subject=e['subject_id'],partition_label=e['period_id'],event_at=e['event_at'],actual_periods=','.join(actual),inside_label=stamp(r['start'])<=stamp(e['event_at'])<=stamp(r['end'],True),quality_close_at=r['quality_close_at'],QA_timely=bool(qas) and all(stamp(a['finalized_at'])<=stamp(r['quality_close_at']) for a in qas),QA_available=bool(qas) and all(a['evidence_status']=='present' for a in qas)))
        summaries.append(dict(scenario=scenario,units=len(us),persons=len(ps),states=states,normal=sum(u['normal'] for u in us),strong=sum(u['stretch'] for u in us),authorized_U_R=sum(x['top_U_R'] for x in ps)))
    write_csv(HERE/'decisions.csv',decisions);write_csv(HERE/'unit-decisions.csv',unit_rows);write_csv(HERE/'window-guarantee.csv',windows);write_csv(HERE/'group-top-reserve.csv',groups);write_csv(HERE/'calendar-boundaries.csv',cal)
    (HERE/'traces.json').write_text(json.dumps({'candidate_key':spec['candidate_key'],'locator_base':'round002 supporting; legacy paths resolve under fixtures; use scenario+table PK to reconstruct through public reader','traces':traces},ensure_ascii=False,indent=2,default=serial)+'\\n')
    (HERE/'scenario-summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\\n')
    print(json.dumps({'scenarios':len(summaries),'decisions':len(decisions),'units':len(unit_rows),'compact_traces':len(traces)}))

if __name__=='__main__':run()
'''
f.write_text(s)
spec=json.loads((P/'metrics-spec.json').read_text());spec['candidate_key']='CON-022@v1';spec['quality']['substantive_difference_points']=1
spec['source_version']='OTP-SYN-007-v1 + OTP-SYN-007-R002-v1'
spec['normal']='All absolute role conditions; project all roots independently accepted and used by prospective business deadline, target specific to work_type; workflow100 planned uses, analytical1 named decision. No quotas.'
spec['stretch']='Normal plus compatible quality>=99 with complete coverage. Flow>=20 independent inspections across>=10 distinct working event dates; project>=1 whole root/stage, all original parts or actual whole-act. Only robust quality clusters rank, no use-volume ordering.'
spec['rank']['keys']={x:['QA robust cluster DESC'] for x in spec['roles']}
spec['rank']['precision']='Order descending QA; merge consecutive eligible QA values whose gap is <1 point into conservative tied clusters; gap exactly1 separates; transitive chain ties preserve uncertainty. No tie breaker by hours, IDs, volume, CSAT or earlier timestamps.'
spec['quality']['score']='max(0,100-2minor-10major-100critical), worst per unique inspection_id, mean of compatible independent frozen QA checklist acts; no derived extra inspection from child split'
spec['signature']['posting_action']='input_correction_and_posting_review'
spec['batch_protocol']={'source_signature':'source_completeness_review, never award authorization','award_signature':'input_correction_and_posting_review binds exact period/person plus immutable proposed decision package hash and rule version; no such new signature presumed in public source','invalidation':'roster/member SHA mismatch, missing performed action, wrong scope or conflict -> pending; hold original calculated entitlement and pool; corrections new package version; idempotency key employee/window/benefit/channel/quarter/version with replacement delta not second original award','required_packet_fields':['package_id','source_manifest_sha256','registry_sha256','membership_sha256','decisions_sha256','metrics_spec_sha256','rule_version','version','exceptions','approval_refs','signed_at','input_editor_id','signer_id','operator_id'],'note':'public source has composition metadata and source reviews; awards not posted by this analytical evaluator'}
spec['project_business_config']='unique prospective version1 matching group/period/work_type; conflicting post-start version pending; analytical pre-read readiness reported in business context but not reward rank; full root QA not necessarily many independent projects'
(P/'metrics-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
