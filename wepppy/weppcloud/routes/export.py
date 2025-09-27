"""Routes for export blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb import Ron


export_bp = Blueprint('export', __name__)


@export_bp.route('/runs/<string:runid>/<config>/export/ermit/')
def export_ermit(runid, config):
    try:
        from wepppy.export import create_ermit_input
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        fn = create_ermit_input(wd)
        name = _split(fn)[-1]
        return send_file(fn, as_attachment=True, download_name=name)
    except:
        return exception_factory('Error exporting ERMiT', runid=runid)


@export_bp.route('/runs/<string:runid>/<config>/export/geopackage')
def export_geopackage(runid, config):
    from wepppy.export import gpkg_export, archive_project, legacy_arc_export

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    # TODO move to RQ or disable lazy build
    try:
        gpkg_fn = _join(ron.export_arc_dir, f'{runid}.gpkg')
        if not _exists(gpkg_fn):
            gpkg_export(wd)
        if not _exists(gpkg_fn):
            raise Exception('GeoPackage file does not exist')
        return send_file(gpkg_fn, as_attachment=True, download_name=f'{runid}.gpkg')
        
    except Exception:
        return exception_factory('Error running gpkg_export', runid=runid)


@export_bp.route('/runs/<string:runid>/<config>/export/geodatabase')
def export_geodatabase(runid, config):
    from wepppy.export import gpkg_export, archive_project, legacy_arc_export

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)

    # TODO move to RQ or disable lazy build
    try:
        gdb_fn = _join(ron.export_arc_dir, f'{runid}.gdb.zip')
        if not _exists(gdb_fn):
            gpkg_export(wd)
        if not _exists(gdb_fn):
            raise Exception('Geodatabase file does not exist')
        return send_file(gdb_fn, as_attachment=True, download_name=f'{runid}.gdb.zip')
        
    except Exception:
        return exception_factory('Error running gpkg_export', runid=runid)


@export_bp.route('/runs/<string:runid>/<config>/export/prep_details')
@export_bp.route('/runs/<string:runid>/<config>/export/prep_details/')
def export_prep_details(runid, config):
    # get working dir of original directory
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    from wepppy.export import archive_project
    from wepppy.export.prep_details import export_channels_prep_details, export_hillslopes_prep_details

    try:
        export_hillslopes_prep_details(wd)
        fn = export_channels_prep_details(wd)
    except Exception:
        return exception_factory(runid=runid)

    if not request.args.get('no_retrieve', None) is not None:
        archive_path = archive_project(_split(fn)[0])
        return send_file(archive_path, as_attachment=True, download_name='{}_prep_details.zip'.format(runid))
    else:
        return success_factory()
