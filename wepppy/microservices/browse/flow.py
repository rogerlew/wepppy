"""Browse tree and response flow helpers extracted from browse.py."""

from __future__ import annotations

import asyncio
import json
import math
import os
from os.path import basename
from urllib.parse import quote, urlencode


async def browse_tree_helper(
    env,
    runid,
    subpath,
    wd,
    request,
    config,
    *,
    allow_recorder: bool,
    is_admin: bool,
    filter_pattern_default='',
):
    """Handle browse tree traversal for both nodir and regular filesystem paths."""
    nodir_rel_path, nodir_filter = env._extract_nodir_filter(subpath, default=filter_pattern_default)
    if env._allowlisted_raw_nodir_path(nodir_rel_path) is not None and not nodir_rel_path.endswith("/"):
        nodir_rel_path = f"{nodir_rel_path}/"
    try:
        logical_rel_path, nodir_view = env.parse_external_subpath(
            nodir_rel_path,
            allow_admin_alias=is_admin,
        )
    except ValueError:
        env.abort(400, "Invalid path.")

    nodir_root, nodir_inner = env.split_nodir_root(logical_rel_path)
    if nodir_root is not None:
        mixed_state = env._is_mixed_nodir_root(wd, nodir_root)
        if mixed_state and not is_admin:
            env._raise_nodir_http_exception(
                env.NoDirError(
                    http_status=env.HTTPStatus.CONFLICT,
                    code="NODIR_MIXED_STATE",
                    message=f"{nodir_root} is in mixed state (dir + .nodir present)",
                )
            )

        effective_view = nodir_view
        if mixed_state and is_admin and nodir_view == "effective":
            effective_view = "dir"
        if mixed_state and is_admin and nodir_view == "archive":
            normalized_subpath = env._normalize_nodir_subpath(subpath)
            if normalized_subpath.startswith(f"{nodir_root}{env._NODIR_SUFFIX}"):
                alias_rel = f"{nodir_root}/nodir"
                if nodir_inner:
                    alias_rel = f"{alias_rel}/{nodir_inner}"
                if subpath.endswith("/") and not alias_rel.endswith("/"):
                    alias_rel = f"{alias_rel}/"
                browse_prefix = request.path.split("/browse/", 1)[0] + "/browse/"
                redirect_url = f"{browse_prefix}{alias_rel}"
                query_string = str(request.query_params)
                if query_string:
                    redirect_url = f"{redirect_url}?{query_string}"
                return env.RedirectResponse(redirect_url, status_code=307)

        try:
            nodir_target = env.nodir_resolve(wd, logical_rel_path, view=effective_view)
        except env.NoDirError as err:
            env._raise_nodir_http_exception(err)

        if nodir_target is None:
            return env._path_not_found_response(runid, subpath, wd, request, config)

        try:
            nodir_meta = env.nodir_stat(nodir_target)
        except FileNotFoundError:
            return env._path_not_found_response(runid, subpath, wd, request, config)
        except env.NoDirError as err:
            env._raise_nodir_http_exception(err)

        if nodir_meta.is_dir:
            if not env._validate_filter_pattern(nodir_filter):
                env.abort(400, f"Invalid filter pattern: {nodir_filter}")
            try:
                nodir_entries = env.nodir_listdir(nodir_target)
            except env.NoDirError as err:
                env._raise_nodir_http_exception(err)
            page = request.args.get('page', 1, type=int)
            page_entries, total_items = env._nodir_entries_to_page(
                nodir_entries,
                filter_pattern=nodir_filter,
                page=page,
                page_size=env.MAX_FILE_LIMIT,
            )
            virtual_path = os.path.abspath(os.path.join(wd, nodir_rel_path))
            return await env.browse_response(
                virtual_path,
                runid,
                wd,
                request,
                config,
                filter_pattern=nodir_filter,
                force_directory=True,
                hide_mixed_nodir=not is_admin,
                page_entries_override=page_entries,
                total_items_override=total_items,
                using_manifest_override=False,
            )

        try:
            with env.nodir_open_read(nodir_target) as fp:
                file_bytes = fp.read()
        except FileNotFoundError:
            return env._path_not_found_response(runid, subpath, wd, request, config)
        except env.NoDirError as err:
            env._raise_nodir_http_exception(err)

        args = request.args
        headers = request.headers
        filename = nodir_meta.name
        if 'download' in args or 'Download' in headers:
            download_response = env.Response(
                response=file_bytes,
                status=200,
                mimetype="application/octet-stream",
            )
            download_response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            return download_response
        if 'raw' in args or 'Raw' in headers:
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return env.Response(response=file_bytes, status=200, mimetype="application/octet-stream")
            raw_response = env.Response(response=text, status=200, mimetype="text/plain")
            raw_response.headers["Content-Type"] = "text/plain; charset=utf-8"
            return raw_response
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return env.Response(response=file_bytes, status=200, mimetype="application/octet-stream")
        return env.Response(response=text, status=200, mimetype="text/plain")

    full_path = os.path.abspath(os.path.join(wd, subpath))
    env._assert_within_root(wd, full_path)
    env._assert_target_within_allowed_roots(wd, full_path, allow_recorder=allow_recorder)

    if os.path.isfile(full_path):
        return await env.browse_response(full_path, runid, wd, request, config)

    if subpath.endswith('/'):
        filter_pattern = filter_pattern_default
        dir_path = subpath
    else:
        components = subpath.split('/')
        if '*' in components[-1]:
            filter_pattern = components[-1]
            dir_components = components[:-1]
        else:
            filter_pattern = filter_pattern_default
            dir_components = components

        dir_path = '/'.join(dir_components) if dir_components else '.'

    dir_path = os.path.abspath(os.path.join(wd, dir_path))
    env._assert_within_root(wd, dir_path)
    env._assert_target_within_allowed_roots(wd, dir_path, allow_recorder=allow_recorder)

    if not os.path.isdir(dir_path):
        return env._path_not_found_response(runid, subpath, wd, request, config)

    if not env._validate_filter_pattern(filter_pattern):
        env.abort(400, f"Invalid filter pattern: {filter_pattern}")

    return await env.browse_response(
        dir_path,
        runid,
        wd,
        request,
        config,
        filter_pattern=filter_pattern,
        hide_mixed_nodir=not is_admin,
    )


async def browse_response(
    env,
    path,
    runid,
    wd,
    request,
    config,
    filter_pattern='',
    *,
    force_directory: bool = False,
    hide_mixed_nodir: bool = False,
    page_entries_override: list[tuple] | None = None,
    total_items_override: int | None = None,
    using_manifest_override: bool | None = None,
):
    args = request.args
    headers = request.headers

    diff_runid = args.get('diff', '')
    if '?' in diff_runid:
        diff_runid = diff_runid.split('?')[0]

    sort_by, sort_order = env._normalize_sort_params(args)

    diff_wd = None
    base_query: dict[str, str] = {}
    if diff_runid:
        diff_wd = env.get_wd(diff_runid)
        base_query['diff'] = diff_runid

    include_sort_params = ('sort' in args) or ('order' in args) or sort_by != 'name' or sort_order != 'asc'
    if include_sort_params:
        base_query['sort'] = sort_by
        base_query['order'] = sort_order

    query_suffix = f'?{urlencode(base_query)}' if base_query else ''

    if not force_directory and not env._exists(path):
        return env.jsonify({'error': {'message': 'path does not exist'}}), 404

    path_lower = path.lower()

    rel_path = os.path.relpath(path, wd)
    breadcrumbs = ''

    base_browse_url, home_href = env._resolve_browse_paths(request.path, runid, config)

    if force_directory or os.path.isdir(path):
        root_href = f'{base_browse_url}{query_suffix}'
        breadcrumb_items = [(f'<a href="{root_href}"><b>{runid}</b></a>', os.path.abspath(wd))]

        if rel_path != '.':
            parts = rel_path.split('/')

            rel_path_acc = ''
            for idx, part in enumerate(parts):
                rel_path_acc = env._join(rel_path_acc, part)
                abs_part_path = os.path.abspath(os.path.join(wd, rel_path_acc))
                is_last = idx == len(parts) - 1
                if is_last:
                    breadcrumb_html = f'<b>{part}</b>'
                else:
                    part_href = f'{base_browse_url}{rel_path_acc}/{query_suffix}'
                    breadcrumb_html = f'<a href="{part_href}"><b>{part}</b></a>'
                breadcrumb_items.append((breadcrumb_html, abs_part_path))

        breadcrumb_segments: list[str] = []
        previous_abs_path = None
        for idx, (crumb_html, abs_path_str) in enumerate(breadcrumb_items):
            if idx and previous_abs_path is not None:
                escaped_abs_path = env.html_escape(previous_abs_path, quote=True)
                breadcrumb_segments.append(
                    f' <span class="breadcrumb-separator" data-copy-path="{escaped_abs_path}" title="Copy absolute path" role="button" tabindex="0">❯</span> '
                )
            breadcrumb_segments.append(crumb_html)
            previous_abs_path = abs_path_str

        current_abs_path = previous_abs_path or os.path.abspath(path)
        breadcrumb_segments.append(
            f' <span class="breadcrumb-separator" data-copy-path="{env.html_escape(current_abs_path, quote=True)}" title="Copy absolute path" role="button" tabindex="0">❯</span> '
        )
        breadcrumb_segments.append(
            f'<input type="text" id="pathInput" value="{env.html_escape(filter_pattern, quote=True)}" '
            'placeholder="../output/p1.*" size="50">'
        )
        breadcrumbs = ''.join(breadcrumb_segments)

        page = request.args.get('page', 1, type=int)

        listing_html, total_items, using_manifest = await env.html_dir_list(
            path,
            runid,
            wd,
            request.path,
            diff_wd,
            base_query,
            page=page,
            page_size=env.MAX_FILE_LIMIT,
            filter_pattern=filter_pattern,
            sort_by=sort_by,
            sort_order=sort_order,
            hide_mixed_nodir=hide_mixed_nodir,
            page_entries_override=page_entries_override,
            total_items_override=total_items_override,
            using_manifest_override=using_manifest_override,
        )

        total_pages = math.ceil(total_items / env.MAX_FILE_LIMIT) if total_items > 0 else 1
        if page > total_pages:
            query = {k: v for k, v in request.args.items() if k != 'page'}
            query['page'] = total_pages
            return env.redirect(request.path + '?' + urlencode(query))
        if page < 1:
            query = {k: v for k, v in request.args.items() if k != 'page'}
            query['page'] = 1
            return env.redirect(request.path + '?' + urlencode(query))

        if total_pages <= 10:
            pages_to_show = list(range(1, total_pages + 1))
        else:
            pages = [1]
            for i in range(11, total_pages + 1, 10):
                if i <= total_pages:
                    pages.append(i)
            window = 3
            for i in range(max(1, page - window), min(total_pages + 1, page + window + 1)):
                if i not in pages:
                    pages.append(i)
            if total_pages not in pages:
                pages.append(total_pages)
            pages_to_show = sorted(pages)

        display_pages = []
        for i in range(len(pages_to_show) - 1):
            display_pages.append(pages_to_show[i])
        display_pages.append(pages_to_show[-1])

        base_query_for_page = {k: v for k, v in request.args.items() if k != 'page'}
        pagination_html = '<div>'
        for item in display_pages:
            starting_item = 1 + (item - 1) * env.MAX_FILE_LIMIT
            if item == page:
                pagination_html += f'<b>[{starting_item}]</b> '
            else:
                query = {**base_query_for_page, 'page': item}
                href = "?" + urlencode(query)
                pagination_html += f'<a href="{href}">[{starting_item}]</a> '
        pagination_html += '</div>'

        start = (page - 1) * env.MAX_FILE_LIMIT
        showing_start = start + 1 if total_items > 0 else 0
        showing_end = min(start + env.MAX_FILE_LIMIT, total_items)
        manifest_note = ' (manifest cached)' if using_manifest else ''
        if total_items > 0:
            showing_text = f'<p>Showing items {showing_start} to {showing_end} of {total_items}{manifest_note}</p>'
        else:
            showing_text = f'<p>No items to display{manifest_note}</p>'

        project_href = env.Markup(f'<a href="{home_href}">☁️</a> ')
        breadcrumbs_markup = env.Markup(breadcrumbs)
        listing_markup = env.Markup(listing_html)
        pagination_markup = env.Markup(pagination_html)
        showing_markup = env.Markup(showing_text)
        mixed_state_roots = env._mixed_nodir_roots(wd)

        return env.render_template(
            'browse/directory.htm',
            runid=runid,
            config=config,
            diff_runid=diff_runid,
            project_href=project_href,
            breadcrumbs_html=breadcrumbs_markup,
            listing_html=listing_markup,
            pagination_html=pagination_markup,
            showing_text=showing_markup,
            using_manifest=using_manifest,
            mixed_state_roots=mixed_state_roots,
        )

    repr_mode = args.get('repr') is not None
    wants_binary = (
        repr_mode
        or ('raw' in args)
        or ('Raw' in headers)
        or ('download' in args)
        or ('Download' in headers)
    )

    if path_lower.endswith('.dss') and not wants_binary:
        dss_response = await env._maybe_render_dss_preview(path, runid, config)
        if dss_response is not None:
            return dss_response

    contents = None
    preview_warning = None

    if repr_mode:
        contents = env._generate_repr_content(path)
        if contents is None:
            env.abort(404)

    if contents is None:
        if path_lower.endswith('.gz'):
            contents = await env._async_read_gzip(path)
            path_lower = path_lower[:-3]
        else:
            try:
                contents = await env._async_read_text(path)
            except UnicodeDecodeError:
                contents = None

    if 'raw' in args or 'Raw' in headers:
        if contents is not None:
            response = env.Response(response=contents, status=200, mimetype="text/plain")
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            return response

    if 'download' in args or 'Download' in headers:
        return env.send_file(path, as_attachment=True, download_name=env._split(path)[-1])

    if path_lower.endswith('.json') or path_lower.endswith('.nodb') or path_lower.endswith('.dump'):
        assert contents is not None
        jsobj = json.loads(contents)
        return env.jsonify(jsobj)

    if path_lower.endswith('.xml'):
        assert contents is not None
        response = env.Response(response=contents, status=200, mimetype="text/xml")
        response.headers["Content-Type"] = "text/xml; charset=utf-8"
        return response

    if path_lower.endswith('.arc'):
        assert contents is not None
        return env.render_template(
            'browse/arc_file.htm',
            filename=basename(path),
            runid=runid,
            contents=contents,
        )

    markdown_markup = None
    if path_lower.endswith(env.MARKDOWN_EXTENSIONS):
        if contents is None:
            try:
                contents = await env._async_read_text(path)
            except UnicodeDecodeError:
                contents = None
        if contents is not None:
            try:
                rendered_markdown = env.markdown_to_html(contents)
            except Exception:
                # Boundary: markdown backend errors vary by parser/runtime; fallback to plain text rendering.
                env._logger.exception('Failed to render Markdown file at %s', path)
            else:
                markdown_markup = env.Markup(rendered_markdown)
        if markdown_markup is not None:
            return env.render_template(
                'browse/markdown_file.htm',
                runid=runid,
                path=path,
                filename=basename(path),
                markdown_html=markdown_markup,
            )

    html = None
    if path_lower.endswith('.pkl'):
        df = await asyncio.to_thread(env.pd.read_pickle, path)
        html = await env._async_df_to_html(df)

    if path_lower.endswith('.parquet'):
        df = await asyncio.to_thread(env.pd.read_parquet, path)
        html = await env._async_df_to_html(df)

    if path_lower.endswith('.csv'):
        skiprows = 0
        if 'totalwatsed2' in path_lower:
            skiprows = 1
        try:
            df = await asyncio.to_thread(env.pd.read_csv, path, skiprows=skiprows)
        except (env.pd.errors.ParserError, env.pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            preview_warning = (
                f'CSV preview failed: {env._format_exception_message(exc)}. '
                'Showing raw text instead.'
            )
            env._logger.warning(
                'Unable to parse CSV at %s; falling back to text view',
                path,
                exc_info=True,
            )
        else:
            html = await env._async_df_to_html(df)

    if path_lower.endswith('.tsv'):
        skiprows = 0
        try:
            df = await asyncio.to_thread(env.pd.read_table, path, sep='\t', skiprows=skiprows)
        except (env.pd.errors.ParserError, env.pd.errors.EmptyDataError, UnicodeDecodeError, ValueError) as exc:
            preview_warning = (
                f'TSV preview failed: {env._format_exception_message(exc)}. '
                'Showing raw text instead.'
            )
            env._logger.warning(
                'Unable to parse TSV at %s; falling back to text view',
                path,
                exc_info=True,
            )
        else:
            html = await env._async_df_to_html(df)

    if html is not None:
        table_markup = env.Markup(html)
        rel_url = os.path.relpath(path, wd).replace('\\', '/')
        dtale_base = env._resolve_dtale_base(request.path, runid, config, env._prefix_path)
        dtale_url = f"{dtale_base}{quote(rel_url, safe='/')}"
        return env.render_template(
            'browse/data_table.htm',
            filename=basename(path),
            runid=runid,
            table_html=table_markup,
            dtale_url=dtale_url,
        )

    if contents is None:
        try:
            contents = await env._async_read_text(path)
        except UnicodeDecodeError:
            return env.send_file(path, as_attachment=True, download_name=env._split(path)[-1])

    contents_html = env._wrap_usersum_spans(contents)

    return env.render_template(
        'browse/text_file.htm',
        runid=runid,
        path=path,
        filename=basename(path),
        contents=contents,
        contents_html=contents_html,
        preview_warning=preview_warning,
    )
