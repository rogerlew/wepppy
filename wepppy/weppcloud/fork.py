from flask import Flask, stream_with_context, request, Response
from subprocess import Popen, PIPE
from os.path import join as _join
from time import sleep

app = Flask(__name__)


@app.route('/')
def console():
    runid = request.args['runid']
    new_runid = request.args['new_runid']

    return Response('''\
<html>
  <head>
    <title>fork</title>
    <script type="text/javascript">
window.onload = function(e){{ 
    
    var bottom = document.getElementById("bottom");
    var the_console = document.getElementById("the_console");
    var params = "runid={runid}&new_runid={new_runid}";

    // set headers
    var xhr = new XMLHttpRequest();

    xhr.open("POST", "/stream", true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    
    xhr.onprogress = function (event) {{
        console.log(event);
    
        the_console.innerHTML = event.srcElement.responseText; 
        bottom.scrollIntoView();
    }};
    xhr.send(params);
}}
    </script>
  </head>
  <body>
    <div style="margin-left:2em;">
      <pre>
      <span id="the_console"></span>
      </pre
    </div>
    <div id="bottom"></div>
  </body>
</html>  
'''.format(runid=runid, new_runid=new_runid))


@app.route('/stream', methods=['POST'])
def streamed_response():
    def generate():
        print('form', request.form)
        print('data', request.data)
        runid = request.form['runid']
        new_runid = request.form['new_runid']

        yield '%s\n' % runid
        sleep(0.5)
        yield '%s\n' % new_runid

        for i in range(100):
            yield '<a href="%i">%i</a>\n' % (i, i)
            sleep(0.1)

    return Response(stream_with_context(generate()))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
