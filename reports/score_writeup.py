"""Score the writeup with Jev (TypeSafe System One) against the published prize criteria. Documentation aid only;
nothing here feeds the scored submission."""
import json, os, pathlib, sys, urllib.request
sys.path.insert(0,os.path.expanduser('~/.claude/skills/chief-linkedin-officer/scripts'))
from judge import api_key
Q=lambda ins,t,f:{'type':'noul','instructions':ins,'criteria':{'true':t,'false':f}}
DOC={
 'sources_documented':Q('Best Documentation judges want data sources documented. Does the text name every data source used, with file paths or URLs and retrieval dates, and say which available sources were deliberately not used?','Every source named with location and date; exclusions stated','A source is vague, unnamed or undated'),
 'components_explained':Q('Does the text explain how each score component (roads/transport, buildings, POI facilities, POI establishments) and the composite were computed, in enough detail that another analyst could reimplement them?','Each component has its formula and inputs','At least one component is hand-waved'),
 'edge_cases_handled':Q('Does the text state how zero-population tracts, water-dominated tracts and tracts with no Overture data were handled, with counts?','All three edge cases handled with counts','An edge case is missing or has no count'),
 'weightings_justified':Q('Does the text describe the alternative weightings or parameter choices tried, which were kept, and why, including ones that did not help?','Alternatives listed with outcomes and reasons','Choices are given without alternatives or reasons'),
 'reproducible':Q('Could a judge rerun this from the text alone: exact commands, environment, seeds, and a way to confirm the output matches the submitted file?','Commands, environment, seeds and a verification hash are given','Something needed to rerun is missing'),
 'honest_limits':Q('Does the text disclose its own limits and any step whose rule status is uncertain, plainly, without overselling results?','Limits and uncertain steps disclosed plainly','Results are oversold or a doubtful step is hidden'),
}
DISC={
 'impact_concrete':Q('Best Bias Discovery Impact criterion: does the pattern connect to concrete consequences for emergency dispatch, evacuation routing, or disaster relief, specific to the places and people involved rather than generic?','Consequences are specific to named places and services','Consequences are generic'),
 'novel_outside_scorecard':Q('Novelty criterion: the automated scorecard reports five fixed metrics across urban/rural, SVI, CVI, tribal and hazard strata. Does this pattern live outside that grid (for example a data-source or taxonomy behaviour), rather than restating one metric across a predefined stratum?','The pattern is a behaviour the scorecard cannot see','It restates a scorecard metric by stratum'),
 'evidence_quantified':Q('Evidence criterion: are tracts or areas named, the comparison sound, and the size of the disparity quantified with uncertainty?','Named tracts, sound comparison, quantified size with intervals','Missing names, weak comparison or no size'),
 'reproducible_discovery':Q('Reproducibility criterion: can a judge reproduce the finding from the challenge data and the stated commands and files?','Steps and files allow reproduction','Reproduction steps are missing'),
}
STYLE={
 'plain_voice':Q('Is this written in plain direct first-person English with short sentences and concrete numbers, free of AI-writing tics such as hype words (leverage, robust, transformative, delve), fake-profound kickers, rhetorical questions, and "it is not X, it is Y" constructions?','Plain, concrete, no AI tics','Contains hype words or AI-writing tics'),
}
def ask(qs,text):
    body={'model':os.environ.get('TYPESAFE_DEFAULT_MODEL','jev-latest'),'state':{'text':text},'questions':qs}
    req=urllib.request.Request('https://api.typesafe.ai/v1/systemone',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {api_key()}','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)['answers']
s=pathlib.Path(sys.argv[1]).read_text();i=s.index('## Best Bias Discovery')
res={}
for part,text,qs in [('documentation',s[:i],{**DOC,**STYLE}),('discovery',s[i:],{**DISC,**STYLE})]:
    a=ask(qs,text)
    for k,v in a.items():res[f'{part}.{k}']=round(v.get('noul',float('nan')),3)
for k,v in res.items():print(f"{k:40s} {'PASS' if v>=0.5 else 'FAIL'} {v}")
json.dump(res,open('reports/jev-writeup-scores.json','w'),indent=1)
