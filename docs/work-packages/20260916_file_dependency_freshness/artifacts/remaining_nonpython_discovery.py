"""Read-only discovery commands; writes evidence only beside this script."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
EXCLUDED_STATIC = {
    "qrcode.js", "plotty.js", "colormap.js", "leaflet-ajax.js", "d3.js",
    "leaflet-1.71.js", "polylabel.js", "sorttable.js", "leaflet-glify-layer.js",
    "leaflet-geotiff.js", "geotiff.js", "leaflet-spin.js", "tinyqueue.js",
    "leaflet-geotiff-vector-arrows.js", "glify-browser.js", "spin.js",
    "underscore.js", "d3fc.js", "controllers-gl.js",
}
records = []

def command(name, args):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    output = OUT / f"remaining_nonpython_{name}.txt"
    output.write_text(result.stdout + result.stderr)
    records.append({"name": name, "argv": args, "exit_code": result.returncode,
                    "output": output.name})
    if result.returncode not in (0, 1):
        raise RuntimeError(f"{name}: {result.stderr}")
    return result.stdout.splitlines()

common = ["-g", "!**/node_modules/**", "-g", "!**/vendor/**", "-g", "!**/tests/**",
          "-g", "!**/__tests__/**", "-g", "!**/test/**", "-g", "!**/*_test.go",
          "-g", "!**/test_*", "-g", "!**/*.test.js", "-g", "!*.min.js"]
operations = command("operations_files", ["rg", "--files", "services", "tools", "scripts", "wctl",
                       "-g", "*.go", "-g", "*.py", "-g", "*.sh", "-g", "*.js", *common])
operations += command("docker_operations_files", ["rg", "--files", "docker", "-g", "*.sh", *common])
browser = command("browser_candidates", ["rg", "--files", "wepppy/weppcloud/controllers_js",
    "wepppy/weppcloud/static/js", "wepppy/weppcloud/static-src", "-g", "*.js", "-g", "*.mjs",
    "-g", "*.ts", *common])
browser = [path for path in browser if Path(path).name not in EXCLUDED_STATIC]
(OUT / "remaining_nonpython_browser_files.txt").write_text("\n".join(browser) + "\n")
patterns = {
    "metadata": r"st_ctime|ctime_ns|st_mtime|mtime_ns|ModTime|LastWriteTime|mtimeMs|ctimeMs|getmtime|ETag|etag|If-Modified-Since|Last-Modified|If-None-Match|lastModified|file_signature|fingerprint",
    "reuse": r"(?i)cache|checksum|sha256|sha1|if.match|signature|digest|fresh|reuse|skip.existing",
    "filesystem": r"ReadFile|WriteFile|os\.(Stat|Open|Create|ReadDir)|ioutil\.|http\.FileServer|ServeFile|statSync|readFileSync|writeFileSync|\.stat\(|read_file|read_text|write_text|fs\.(read|write|stat|open)",
}
for group, paths in (("operations", operations), ("browser", browser)):
    for label, pattern in patterns.items():
        command(f"{group}_{label}", ["rg", "-n", "--max-columns", "400", "--max-columns-preview", pattern, *paths])
command("inline_template_identity", ["rg", "-n", "--max-columns", "400", "--max-columns-preview",
    r"(?i)sha256|checksum|if.match|etag|mtime|fingerprint|schemaCache|dataCache|fileCache",
    "wepppy/weppcloud/templates", "-g", "*.htm", "-g", "*.html"])
command("go_transport_trace", ["rg", "-n",
    r"ReadFile|WriteFile|os\.(Stat|Open|Create|ReadDir)|ioutil\.|FileServer|ServeFile|Equal\(|HGetAll|Subscribe|Publish|lastSeen|PongTimeout",
    *[p for p in operations if p.endswith('.go')]])
command("browser_producer_trace", ["rg", "-n",
    r"subcatchment_delineation|GL_EXCLUDED_MODULES|loadBaseWeppYearlyData|weppYearlyCache|baseWeppYearlyCache|wepp:run:completed|WEPP_RUN_TASK_COMPLETED|loss_pw0\.hill\.parquet|run_wepp_watershed_interchange|force_refresh=True",
    "wepppy/weppcloud/controllers_js/build_controllers_js.py",
    "wepppy/weppcloud/controllers_js/wepp.js",
    "wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js",
    "wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js",
    "wepppy/wepp/interchange/watershed_loss_interchange.py",
    "wepppy/rq/wepp_rq_stage_post.py"])
manifest = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "excluded_static_basenames": sorted(EXCLUDED_STATIC),
    "exclusion_note": "Bundled third-party libraries excluded from semantic inspection; generated/minified/vendor/node_modules/test trees excluded. First-party leaflet wrappers with vendor-style names are explicitly listed as excluded and not claimed reviewed.",
    "operations_files": len(operations), "browser_files": len(browser), "commands": records}
(OUT / "remaining_nonpython_scope.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({key: manifest[key] for key in ("revision", "operations_files", "browser_files")}, indent=2))
