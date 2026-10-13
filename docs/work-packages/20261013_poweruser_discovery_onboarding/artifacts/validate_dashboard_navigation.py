import json, runpy
from types import SimpleNamespace
from html.parser import HTMLParser
m=runpy.run_path('/workdir/wepppy/tests/weppcloud/routes/test_pure_controls_render.py')
env=m['jinja_env'].__wrapped__()
class Links(HTMLParser):
 def __init__(self): super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a' and 'gl_dashboard.gl_dashboard' in dict(attrs).get('href',''):self.links.append(dict(attrs))
results=[]
for role in ('ordinary','public','PowerUser','Admin','Root'):
 user=SimpleNamespace(has_role=lambda r,role=role:r==role,roles=[] if role in ('ordinary','public') else [role],is_authenticated=role!='public')
 for run in ('test-run','test-run;;omni;;child'):
  for name in ('header/_run_header_fixed.htm','reports/_base_report.htm'):
   html=env.get_template(name).render(user=user,current_user=user,request=SimpleNamespace(view_args={'runid':run,'config':'view-config'}),url_for_run=lambda endpoint,**kw:f"/run/{endpoint}/{kw.get('runid','')}/{kw.get('config','')}")
   parser=Links();parser.feed(html);assert len(parser.links)==1,(role,run,name,parser.links)
   link=parser.links[0];assert link['href']==f'/run/gl_dashboard.gl_dashboard/{run}/view-config'
   assert link['target']=='_blank' and link['rel']=='noopener' and 'data-open-tab-pref' in link
   assert html.index('Browse')<html.index('GL Dashboard')
   results.append({'role':role,'runid':run,'template':name,'href':link['href']})
 html=env.get_template('controls/poweruser_panel.htm').render(user=user,current_user=user)
 assert 'gl_dashboard.gl_dashboard' not in html
print(json.dumps({'rendered_cases':len(results),'cases':results,'panel_duplicate_absent':True},indent=2))
