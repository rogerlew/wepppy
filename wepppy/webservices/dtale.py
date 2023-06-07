import pandas as pd
from dtale.app import build_app
from dtale.views import startup
from flask import redirect

app = build_app(reaper_on=False)
app.config['SITE_PREFIX'] = '/webservices/dtale'

@app.route("/create-df")
def create_df():
    df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]))
    instance = startup(data=df, ignore_duplicate=True)
    return redirect(f"/dtale/main/{instance._data_id}", code=302)


@app.route("/")
def hello_world():
    return f'Hi there, load data using <a href="/create-df">create-df</a>'


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
