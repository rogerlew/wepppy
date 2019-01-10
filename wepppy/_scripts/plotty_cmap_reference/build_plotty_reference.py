template = """
<head>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
    <script src="http://127.0.0.1:5000/static/js/plotty.js"></script>
    <script  type="text/javascript">// Generate or load some data (Working with buffer arrays for now)
function render_legend(cmap, canvasID) {{
    var canvas = $("#" + canvasID);
    
    var width = canvas.outerWidth();
    var height = canvas.outerHeight();
    var exampledata = new Float32Array(height * width);

    var xoff = width / 3;
    var yoff = height / 3;

    for (y = 0; y <= height; y++) {{
        for (x = 0; x <= width; x++) {{
            exampledata[(y*width)+x] = x / (width - 1.0);
        }}
    }}

    plot = new plotty.plot({{
        canvas: canvas["0"],
        data: exampledata, width: width, height: height,
        domain: [0, 1], colorScale: cmap
    }});
    plot.render();
}}

function do_onload() {{
{}
}}
    </script>
</head>
<body onload='do_onload()'>
{}
</body>
"""

load_js_stub = """  render_legend("{cmap}", "{cmap}_legend");"""
canvas_stub = """  <h3>{cmap}</h3><canvas id="{cmap}_legend" width=200 height=20></canvas>"""

cmaps = """viridis 	inferno 	rainbow
jet 	hsv 	hot
cool 	spring 	summer
autumn 	winter 	bone
copper 	greys 	yignbu
greens 	yiorrd 	bluered
rdbu 	picnic 	portland
blackbody 	earth 	electric
magma 	plasma"""

cmaps = cmaps.split()

loads = '\n'.join(load_js_stub.format(cmap=cmap) for cmap in cmaps[:15])
canvases = '\n'.join(canvas_stub.format(cmap=cmap) for cmap in cmaps[:15])

s = template.format(loads, canvases)
with open('plotty_legend1.htm', 'w') as fp:
    fp.write(s)


loads = '\n'.join(load_js_stub.format(cmap=cmap) for cmap in cmaps[15:])
canvases = '\n'.join(canvas_stub.format(cmap=cmap) for cmap in cmaps[15:])

s = template.format(loads, canvases)
with open('plotty_legend2.htm', 'w') as fp:
    fp.write(s)