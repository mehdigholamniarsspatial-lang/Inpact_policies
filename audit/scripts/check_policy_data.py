"""Read-only audit. Run from any directory with python -B; outputs only under audit/."""
from pathlib import Path
import csv, json, os, sys, hashlib, math
from collections import defaultdict, Counter
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'audit'
DATA = ROOT / 'data/policy_timeline'
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
def read(name):
    with (DATA/name).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write(name, rows, fields=None):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields or list(rows[0])); w.writeheader(); w.writerows(rows)
def n(v): return float(v) if v not in ('',None) else None
def yes(v): return str(v).lower() in ('true','1')
def eq(a,b): return a is None and b is None or a is not None and b is not None and math.isclose(a,b,abs_tol=2e-9)
protected = list(DATA.rglob('*')) + list((ROOT/'policies').rglob('*'))
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
main=read('ireland_core_policy_timeline.csv'); cat=read('policy_catalogue.csv'); members=read('qa/residual_members.csv')
sel=read('selection_log.csv'); raw=read('raw/capmf_ireland.csv'); timing={r['mechanism_class']:r for r in read('config/timing_parameters.csv')}
groups=defaultdict(list)
for r in main: groups[r['policy_id'],r['sector']].append(r)
from policies.editorial import POLICY_MILESTONES
lineage=read('policy_id_lineage.csv')
register=[]
for (pid,sec), rows in sorted(groups.items()):
    r=rows[0]; fields=['policy_id','policy_name','sector','multi_sector_flag','layer','mechanism','instrument_type','start_year','start_year_basis','end_year','capmf_code','match_confidence','aggregation_role','member_policy_ids','source_citation']
    entry={f:r[f] for f in fields}
    entry['key_amendments_or_successors']='; '.join(f'{y}: {t}' for y,t in POLICY_MILESTONES.get(pid,[]))
    entry['source_record_lineage']='; '.join(f"PaM {x['pam_id']}: {x['Name of policy or measure']}" for x in lineage if x['policy_id']==pid)
    entry['implementation_source_by_year']='; '.join(f"{x['year']}:{x['implementation_source']}" for x in sorted(rows,key=lambda x:int(x['year'])))
    entry['assumed_years']=';'.join(x['year'] for x in rows if x['implementation_source']=='assumed')
    slug=f'{pid}--{sec}'.lower().replace(' ','-').replace('_','-')
    entry['profile_slug']=slug
    entry['pages']='/policy/; /policy/timeline/; /policy/policies/; /policy/categories/; /policy/instruments/; /policy/policies/'+slug+'/'
    if r['capmf_code']: entry['pages']+='; /policy/oecd-scores/'
    register.append(entry)
write('policy_register.csv',register)
dis=[]; checked=Counter()
def check(ok,r,field,expected,actual,source,index):
    checked[field]+=1
    if not ok: dis.append(dict(policy_id=r.get('policy_id',''),sector=r.get('sector',''),year=r.get('year',''),field=field,expected=expected,actual=actual,location=f'{source}:CSV record {index+2} (header=1)'))
obs={(r['CLIM_ACT_POL'],int(r['TIME_PERIOD'])): (None if r['OBS_STATUS'] in ('M','K') else n(r['OBS_VALUE'])) for r in raw if r['MEASURE']=='POL_STRINGENCY'}
for source,table in [('ireland_core_policy_timeline.csv',main),('qa/residual_members.csv',members)]:
    for i,r in enumerate(table):
        y=int(r['year']); start=int(r['start_year']); end=n(r['end_year']); residual=r['layer']=='residual'
        expected='pre_implementation' if y<start else 'active' if end is None or y<=end else 'post_expiry_residual' if r['legacy']=='continues' else 'post_expiry_no_effect'
        check(expected==r['status_in_year'],r,'status_in_year',expected,r['status_in_year'],source,i)
        val=n(r['intensity_index']); check(val is not None and 0<=val<=1,r,'intensity_range','[0,1]',val,source,i)
        if residual: continue
        prod=n(r['implementation_level'])*n(r['coverage_share'])*n(r['bindingness'])
        check(eq(prod,val),r,'intensity_product',prod,val,source,i)
        t=timing[r['mechanism_class']]
        for field in ['lag_years','ramp_years','half_life_years']:
            check(eq(n(r[field]),n(t[field])),r,field,t[field],r[field],source,i)
        lag=n(t['lag_years']); ramp=n(t['ramp_years']); half=n(t['half_life_years'])
        def ramp_at(yr): return max(0,min(1,(yr-start-lag+0.5)/ramp))
        tw=0 if y<start else ramp_at(y)
        if end is not None and y>end: tw=ramp_at(end)*2**(-(y-end)/half) if r['legacy']=='continues' and half else 0
        check(eq(tw,n(r['temporal_weight'])),r,'temporal_weight',tw,r['temporal_weight'],source,i)
        if r['implementation_source']=='capmf_derived':
            vals=[obs.get((c.strip(),y)) for c in set(r['capmf_code'].split(';'))]
            expected_score=sum(vals)/len(vals) if vals and all(v is not None for v in vals) else None
            check(eq(expected_score,n(r['capmf_stringency'])),r,'same_year_capmf',expected_score,r['capmf_stringency'],source,i)
            check(eq(expected_score/10 if expected_score is not None else None,n(r['implementation_level'])),r,'capmf_implementation',expected_score/10 if expected_score is not None else None,r['implementation_level'],source,i)
        elif r['status_in_year'] in ('active','pre_implementation','post_expiry_no_effect'):
            # Frameworks use a legal-presence fallback, explicitly distinct from a ramp.
            expected_impl=(1 if y>=start else 0) if r['mechanism_class']=='framework' else tw
            check(eq(expected_impl,n(r['implementation_level'])),r,'assumed_implementation',expected_impl,r['implementation_level'],source,i)
for i,r in enumerate(main):
    if r['layer']!='residual': continue
    ms=[m for m in members if m['sector']==r['sector'] and m['year']==r['year']]
    values=[n(m['intensity_index']) for m in ms]
    expected=sum(values)/len(values) if values and all(v is not None for v in values) else None
    check(eq(expected,n(r['intensity_index'])),r,'residual_mean',expected,r['intensity_index'],'ireland_core_policy_timeline.csv',i)
    check(set(r['member_policy_ids'].split(';'))=={m['policy_id'] for m in ms},r,'residual_member_list','fixed QA member set',r['member_policy_ids'],'ireland_core_policy_timeline.csv',i)
for key,rs in groups.items():
    check(sorted(int(r['year']) for r in rs)==list(range(2000,2024)),rs[0],'annual_grid','2000-2023 once each',','.join(r['year'] for r in rs),'ireland_core_policy_timeline.csv',main.index(rs[0]))
for i,r in enumerate(sel):
    tests=[yes(v) for k,v in r.items() if k.startswith('eligibility_')]
    check(all(tests)==yes(r['eligible']),r,'five_eligibility_tests',all(tests),r['eligible'],'selection_log.csv',i)
materiality=[]
for s in read('sector_materiality.csv'):
    eligible=[r for r in sel if r['candidate_origin']=='EEA_deduplicated_PaM' and yes(r['eligible']) and r['primary_sector']==s['sector']]
    positive=sorted([r for r in eligible if (n(r['reported_effect_kt']) or 0)>0],key=lambda r:-n(r['reported_effect_kt']))
    total=sum(n(r['reported_effect_kt']) for r in positive); chosen=[]; cumulative=0
    for r in positive:
        if cumulative>=0.9*total: break
        chosen.append(r['candidate_id']); cumulative+=n(r['reported_effect_kt'])
    stored={r['candidate_id'] for r in eligible if yes(r['materiality_group_flag'])}
    materiality.append(dict(sector=s['sector'],eligible=len(eligible),positive=len(positive),selected=len(chosen),ranking_total=total,selected_total=cumulative,share=cumulative/total if total else '',chosen_ids=';'.join(chosen),membership_matches=set(chosen)==stored,totals_match=eq(total,n(s['ranking_total_kt'])) and eq(cumulative,n(s['selected_ranking_kt']))))
write('selection_recomputed.csv',materiality)
write('timeline_discrepancies.csv',dis,['policy_id','sector','year','field','expected','actual','location'])
active=[dict(year=y,active_series=sum(int(r['year'])==y and r['status_in_year']=='active' for r in main)) for y in range(2000,2024)]
write('active_series_by_year.csv',active)
write('assumed_years.csv',[{k:r[k] for k in ['policy_id','sector','year','status_in_year','implementation_detail','lag_years','ramp_years','half_life_years']} for r in main if r['implementation_source']=='assumed'])
jumps=[]
for key,rs in groups.items():
    rs=sorted(rs,key=lambda r:int(r['year']))
    for a,b in zip(rs,rs[1:]):
        delta=n(b['implementation_level'])-n(a['implementation_level'])
        if abs(delta)>=0.20 or (a['implementation_source']!=b['implementation_source'] and a['status_in_year']!='pre_implementation'):
            jumps.append(dict(policy_id=key[0],sector=key[1],year=b['year'],delta=delta,previous_source=a['implementation_source'],source=b['implementation_source'],explanation='activation from structural zero' if a['status_in_year']=='pre_implementation' else 'source switch; not evidence of a legal amendment' if a['implementation_source']!=b['implementation_source'] else 'same-year OECD change; underlying cause not independently established' if b['implementation_source']=='capmf_derived' else 'assumed ramp or member mean; not an observed effect',flags=b['data_quality_flag']))
write('implementation_changes.csv',jumps)
os.environ['DJANGO_SETTINGS_MODULE']='inpact_platform.settings'
import django
from django.conf import settings
settings.DATABASES['default']['NAME']=f'file:{DATA.as_posix()}/policy_timeline.sqlite3?mode=ro'
settings.DATABASES['default']['OPTIONS']={'uri':True}
django.setup()
from policies import services, models
from django.test import Client
stats=services.overview_stats(); client=Client(HTTP_HOST='localhost')
pages=['/policy/','/policy/timeline/','/policy/policies/','/policy/categories/','/policy/instruments/','/policy/oecd-scores/','/policy/method/','/policy/about/']
pages += ['/policy/policies/'+r['profile_slug']+'/' for r in register]
pagechecks=[]
for url in pages:
    response=client.get(url); html=response.content.decode()
    pagechecks.append(dict(url=url,status=response.status_code,bytes=len(response.content),retrospective_caveat='retrospective' in html.lower()))
write('page_checks.csv',pagechecks)
api=client.get('/policy/api/series/').json()
(OUT/'local_series_payload.json').write_text(json.dumps(api,ensure_ascii=False,indent=2),encoding='utf-8')
import pandas as pd
eea=pd.read_excel(DATA/'raw/eea_pams_ireland.xlsx')
raw_selection=[]
for r in sel:
    if r['candidate_origin']!='EEA_deduplicated_PaM' or not r['source_row'] or not yes(r['eligible']): continue
    source=eea.iloc[int(float(r['source_row']))-2]
    priority=[('expost_2024','Average expost emission reduction  kt CO2eq y GHG'),('exante_2025','Total GHG emissions reductions in 2025  kt CO2eq y GHG'),('exante_2030','Total GHG emissions reductions in 2030  kt CO2eq y GHG')]
    expected=None; origin='not_quantified'
    for label,field in priority:
        v=pd.to_numeric(source[field],errors='coerce')
        if pd.notna(v): expected=float(v); origin=label; break
    raw_selection.append(dict(candidate_id=r['candidate_id'],source_row=r['source_row'],expected=expected,actual=n(r['reported_effect_kt']),priority_source=origin,stored_source=r['effect_source'],value_matches=eq(expected,n(r['reported_effect_kt']))))
write('source_estimate_priority.csv',raw_selection)
decays=[]
all_lookup={(r['policy_id'],r['sector'],int(r['year'])):r for r in main+members if r['layer']!='residual'}
for r in main+members:
    if r['layer']=='residual' or r['status_in_year']!='post_expiry_residual': continue
    end=int(float(r['end_year'])); endrow=all_lookup.get((r['policy_id'],r['sector'],end)); half=n(r['half_life_years'])
    expected=n(endrow['implementation_level'])*2**(-(int(r['year'])-end)/half) if endrow and half else None
    decays.append(dict(policy_id=r['policy_id'],sector=r['sector'],year=r['year'],expected=expected,actual=n(r['implementation_level']),matches=eq(expected,n(r['implementation_level']))))
write('post_expiry_checks.csv',decays)
database_differences=[]
for s in models.PolicySeries.objects.prefetch_related('years'):
    rs=groups[s.policy_id,s.sector]; first=rs[0]
    for field in ['policy_name','start_year','end_year','capmf_code','member_policy_ids']:
        expected=n(first[field]) if field in ('start_year','end_year') else first[field]
        if getattr(s,field)!=expected: database_differences.append(dict(policy_id=s.policy_id,sector=s.sector,year='',field=field,expected=expected,actual=getattr(s,field)))
    byyear={int(r['year']):r for r in rs}
    for y in s.years.all():
        r=byyear[y.year]
        for field in ['status_in_year','implementation_source','implementation_level','intensity_index','capmf_stringency']:
            expected=r[field] if field in ('status_in_year','implementation_source') else n(r[field]); actual=getattr(y,field)
            if (expected!=actual if isinstance(expected,str) else not eq(expected,actual)):
                database_differences.append(dict(policy_id=s.policy_id,sector=s.sector,year=y.year,field=field,expected=expected,actual=actual))
write('database_differences.csv',database_differences,['policy_id','sector','year','field','expected','actual'])
rawcounts=eea['Single policy or measure  or group of measures'].value_counts().to_dict()
positive3={r['CLIM_ACT_POL'] for r in raw if r['CLIM_ACT_POL'].startswith('LEV3_') and r['MEASURE']=='POL_STRINGENCY' and r['OBS_STATUS'] not in ('K','M') and (n(r['OBS_VALUE']) or 0)>0}
rawlabels={r['CLIM_ACT_POL']:r['Climate actions and policies'] for r in raw}
category_label_mismatches=[c.code for c in models.CapmfCategory.objects.all() if rawlabels.get(c.code)!=c.label]
proxychecks=[]
for (pid,sec),rs in groups.items():
    r=rs[0]
    if 'capmf_first_positive_start_not_verified_enactment' not in r['data_quality_flag']:continue
    code=r['capmf_code']; positive=[y for (c,y),v in obs.items() if c==code and v is not None and v>0]
    proxychecks.append(dict(policy_id=pid,sector=sec,code=code,start_year=int(r['start_year']),first_positive=min(positive) if positive else None,matches=bool(positive) and int(r['start_year'])==min(positive)))
write('proxy_start_checks.csv',proxychecks)
anchors=read('config/anchor_register.csv')
anchor_coverage=[dict(policy_id=r['policy_id'],sector=r['sector'],present=(r['policy_id'],r['sector']) in groups) for r in anchors]
write('anchor_coverage.csv',anchor_coverage)
eea_columns=list(eea.columns)
(OUT/'eea_columns.json').write_text(json.dumps(eea_columns,indent=2),encoding='utf-8')
summary=dict(recomputed=dict(unique_ids_including_residuals=len({r['policy_id'] for r in main}),core_families=len({r['policy_id'] for r in main if r['layer']!='residual'}),series=len(groups),rows=len(main),residual_bundles=len({r['policy_id'] for r in main if r['layer']=='residual'}),candidates=len(sel),eligible=sum(yes(r['eligible']) for r in sel),eea_records=len(eea),active_2000=active[0]['active_series'],active_2023=active[-1]['active_series']),app_stats=stats,checks=dict(checked),discrepancies_by_field=dict(Counter(d['field'] for d in dis)),capmf_flags=sorted({(r['OBS_STATUS'],r['Observation status']) for r in raw}),capmf_levels=dict(Counter(c.split('_')[0] for c in {r['CLIM_ACT_POL'] for r in raw})),capmf_years=[min(int(r['TIME_PERIOD']) for r in raw),max(int(r['TIME_PERIOD']) for r in raw)],multi_sector={pid:sorted({sec for p,sec in groups if p==pid}) for pid in {p for p,s in groups} if len({sec for p,sec in groups if p==pid})>1},page_checks=len(pagechecks),page_failures=[p for p in pagechecks if p['status']!=200],residual_core_overlap=sorted({(r['policy_id'],r['sector']) for r in members}&{(r['policy_id'],r['sector']) for r in main}))
after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
summary['protected_files_unchanged']=hashes==after
summary['eea_record_types']=rawcounts
summary['source_estimate_priority_mismatches']=[r for r in raw_selection if not r['value_matches']]
summary['post_expiry_mismatches']=[r for r in decays if not r['matches']]
summary['database_differences']=len(database_differences)
summary['capmf_positive_level3_categories']=len(positive3)
summary['category_label_mismatches']=category_label_mismatches
summary['proxy_start_mismatches']=[r for r in proxychecks if not r['matches']]
summary['anchor_missing_series']=[r for r in anchor_coverage if not r['present']]
summary['raw_stringency_out_of_range']=sum(r['MEASURE']=='POL_STRINGENCY' and r['OBS_STATUS'] not in ('M','K') and n(r['OBS_VALUE']) is not None and not 0<=n(r['OBS_VALUE'])<=10 for r in raw)
(OUT/'input_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
(OUT/'checks_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
