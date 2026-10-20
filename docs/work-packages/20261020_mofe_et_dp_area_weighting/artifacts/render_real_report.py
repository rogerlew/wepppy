"""Fresh-process view rendering; authorization decorators are outside this harness."""
import inspect
import json
from pathlib import Path
from wepppy.weppcloud.app import app
from wepppy.weppcloud.routes.nodb_api.wepp_bp import report_wepp_avg_annual_watbal
from wepppy.nodb.core import Ron

root = Path('/wc1/runs/mo/mofe-et-dp-validation-20261020')
runid = root.name
config = Ron.getInstance(str(root)).config_stem
view = inspect.unwrap(report_wepp_avg_annual_watbal)
url = f'/runs/{runid}/{config}/report/wepp/avg_annual_watbal'
for suffix, query in [('html',''), ('csv','?format=csv&table=hillslopes')]:
    with app.test_request_context(url+query):
        response = view(runid, config)
        content = response if isinstance(response,str) else response.get_data(as_text=True)
        (root/'mofe-validation'/f'report-view.{suffix}').write_text(content)
        print(suffix,len(content),config)
