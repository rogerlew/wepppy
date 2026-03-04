"""Browse tree and response flow helpers extracted from browse.py."""

from __future__ import annotations

import asyncio
import json
import math
import os
from os.path import basename
from urllib.parse import quote, urlencode


def _normalize_nodir_request(env, subpath: str, *, filter_pattern_default: str) -> tuple[str, str]:
    nodir_rel_path, nodir_filter = env._extract_nodir_filter(subpath, default=filter_pattern_default)
    if env._allowlisted_raw_nodir_path(nodir_rel_path) is not None and not nodir_rel_path.endswith("/"):
        nodir_rel_path = f"{nodir_rel_path}/"
    return nodir_rel_path, nodir_filter


def _parse_external_nodir_subpath(env, nodir_rel_path: str, *, is_admin: bool) -> tuple[str, str]:
    try:
        return env.parse_external_subpath(
            nodir_rel_path,
            allow_admin_alias=is_admin,
        )
    except ValueError:
        env.abort(400, "Invalid path.")
    raise AssertionError("unreachable")


def _mixed_nodir_alias_redirect(
    env,
    *,
    request,
    subpath: str,
    nodir_root: str,
    nodir_inner: str,
) -> object | None:
    normalized_subpath = env._normalize_nodir_subpath(subpath)
    if not normalized_subpath.startswith(f"{nodir_root}{env._NODIR_SUFFIX}"):
        return None

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


def _resolve_nodir_target(env, wd: str, logical_rel_path: str, *, view: str):
    try:
        return env.nodir_resolve(wd, logical_rel_path, view=view)
    except env.NoDirError as err:
        env._raise_nodir_http_exception(err)
    raise AssertionError("unreachable")


def _stat_nodir_target(env, nodir_target, *, runid: str, subpath: str, wd: str, request, config):
    try:
        return env.nodir_stat(nodir_target)
    except FileNotFoundError:
        return env._path_not_found_response(runid, subpath, wd, request, config)
    except env.NoDirError as err:
        env._raise_nodir_http_exception(err)
    raise AssertionError("unreachable")


async def _browse_nodir_directory(
    env,
    *,
    runid: str,
    subpath: str,
    wd: str,
    request,
    config: str,
    nodir_target,
    nodir_rel_path: str,
    nodir_filter: str,
    is_admin: bool,
):
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


def _read_nodir_file_bytes(env, nodir_target, *, runid: str, subpath: str, wd: str, request, config):
    try:
        with env.nodir_open_read(nodir_target) as fp:
            return fp.read()
    except FileNotFoundError:
        return env._path_not_found_response(runid, subpath, wd, request, config)
    except env.NoDirError as err:
        env._raise_nodir_http_exception(err)
    raise AssertionError("unreachable")


def _nodir_target_path(nodir_target) -> str:
    base = os.path.abspath(nodir_target.dir_path)
    inner = (getattr(nodir_target, "inner_path", "") or "").strip("/")
    if not inner:
        return base
    return os.path.abspath(os.path.join(base, inner))


def _browse_nodir_file(
    env,
    *,
    request,
    nodir_meta,
    file_bytes: bytes,
):
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


async def _handle_nodir_tree(
    env,
    *,
    runid: str,
    subpath: str,
    wd: str,
    request,
    config: str,
    nodir_rel_path: str,
    nodir_filter: str,
    logical_rel_path: str,
    nodir_view: str,
    nodir_root: str,
    nodir_inner: str,
    is_admin: bool,
):
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
        redirect_response = _mixed_nodir_alias_redirect(
            env,
            request=request,
            subpath=subpath,
            nodir_root=nodir_root,
            nodir_inner=nodir_inner,
        )
        if redirect_response is not None:
            return redirect_response

    nodir_target = _resolve_nodir_target(env, wd, logical_rel_path, view=effective_view)
    if nodir_target is None:
        return env._path_not_found_response(runid, subpath, wd, request, config)

    nodir_meta = _stat_nodir_target(
        env,
        nodir_target,
        runid=runid,
        subpath=subpath,
        wd=wd,
        request=request,
        config=config,
    )
    if not hasattr(nodir_meta, "is_dir"):
        return nodir_meta
    if nodir_meta.is_dir:
        return await _browse_nodir_directory(
            env,
            runid=runid,
            subpath=subpath,
            wd=wd,
            request=request,
            config=config,
            nodir_target=nodir_target,
            nodir_rel_path=nodir_rel_path,
            nodir_filter=nodir_filter,
            is_admin=is_admin,
        )

    # NoDir runtime roots are directory-only; delegate parquet files to the
    # standard file renderer so browse previews keep table behavior instead of
    # binary byte responses.
    if nodir_meta.name.lower().endswith((".parquet", ".pq")):
        return await env.browse_response(
            _nodir_target_path(nodir_target),
            runid,
            wd,
            request,
            config,
        )

    file_bytes = _read_nodir_file_bytes(
        env,
        nodir_target,
        runid=runid,
        subpath=subpath,
        wd=wd,
        request=request,
        config=config,
    )
    if not isinstance(file_bytes, bytes):
        return file_bytes
    return _browse_nodir_file(
        env,
        request=request,
        nodir_meta=nodir_meta,
        file_bytes=file_bytes,
    )


def _resolve_regular_directory_path(subpath: str, *, filter_pattern_default: str) -> tuple[str, str]:
    if subpath.endswith('/'):
        return subpath, filter_pattern_default

    components = subpath.split('/')
    if '*' in components[-1]:
        filter_pattern = components[-1]
        dir_components = components[:-1]
    else:
        filter_pattern = filter_pattern_default
        dir_components = components

    dir_path = '/'.join(dir_components) if dir_components else '.'
    return dir_path, filter_pattern


async def _handle_regular_tree(
    env,
    *,
    runid: str,
    subpath: str,
    wd: str,
    request,
    config: str,
    allow_recorder: bool,
    is_admin: bool,
    filter_pattern_default: str,
):
    full_path = os.path.abspath(os.path.join(wd, subpath))
    env._assert_within_root(wd, full_path)
    env._assert_target_within_allowed_roots(wd, full_path, allow_recorder=allow_recorder)
    if os.path.isfile(full_path):
        return await env.browse_response(full_path, runid, wd, request, config)

    dir_path, filter_pattern = _resolve_regular_directory_path(
        subpath,
        filter_pattern_default=filter_pattern_default,
    )
    abs_dir_path = os.path.abspath(os.path.join(wd, dir_path))
    env._assert_within_root(wd, abs_dir_path)
    env._assert_target_within_allowed_roots(wd, abs_dir_path, allow_recorder=allow_recorder)

    if not os.path.isdir(abs_dir_path):
        return env._path_not_found_response(runid, subpath, wd, request, config)
    if not env._validate_filter_pattern(filter_pattern):
        env.abort(400, f"Invalid filter pattern: {filter_pattern}")

    return await env.browse_response(
        abs_dir_path,
        runid,
        wd,
        request,
        config,
        filter_pattern=filter_pattern,
        hide_mixed_nodir=not is_admin,
    )


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
    nodir_rel_path, nodir_filter = _normalize_nodir_request(
        env,
        subpath,
        filter_pattern_default=filter_pattern_default,
    )
    logical_rel_path, nodir_view = _parse_external_nodir_subpath(
        env,
        nodir_rel_path,
        is_admin=is_admin,
    )
    nodir_root, nodir_inner = env.split_nodir_root(logical_rel_path)
    if nodir_root is not None:
        return await _handle_nodir_tree(
            env,
            runid=runid,
            subpath=subpath,
            wd=wd,
            request=request,
            config=config,
            nodir_rel_path=nodir_rel_path,
            nodir_filter=nodir_filter,
            logical_rel_path=logical_rel_path,
            nodir_view=nodir_view,
            nodir_root=nodir_root,
            nodir_inner=nodir_inner,
            is_admin=is_admin,
        )
    return await _handle_regular_tree(
        env,
        runid=runid,
        subpath=subpath,
        wd=wd,
        request=request,
        config=config,
        allow_recorder=allow_recorder,
        is_admin=is_admin,
        filter_pattern_default=filter_pattern_default,
    )


def _sanitize_diff_runid(args) -> str:
    diff_runid = args.get('diff', '')
    if '?' in diff_runid:
        diff_runid = diff_runid.split('?')[0]
    return diff_runid


def _build_base_query(
    *,
    args,
    diff_runid: str,
    sort_by: str,
    sort_order: str,
    parquet_filter_payload: str | None = None,
) -> dict[str, str]:
    base_query: dict[str, str] = {}
    if diff_runid:
        base_query['diff'] = diff_runid
    include_sort_params = ('sort' in args) or ('order' in args) or sort_by != 'name' or sort_order != 'asc'
    if include_sort_params:
        base_query['sort'] = sort_by
        base_query['order'] = sort_order
    if parquet_filter_payload:
        base_query['pqf'] = parquet_filter_payload
    return base_query


def _build_breadcrumbs_html(
    env,
    *,
    runid: str,
    wd: str,
    path: str,
    filter_pattern: str,
    base_browse_url: str,
    query_suffix: str,
) -> str:
    rel_path = os.path.relpath(path, wd)
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
    return ''.join(breadcrumb_segments)


def _normalize_page_or_redirect(env, *, request, page: int, total_items: int):
    total_pages = math.ceil(total_items / env.MAX_FILE_LIMIT) if total_items > 0 else 1
    if page > total_pages:
        query = {k: v for k, v in request.args.items() if k != 'page'}
        query['page'] = total_pages
        return env.redirect(request.path + '?' + urlencode(query)), total_pages
    if page < 1:
        query = {k: v for k, v in request.args.items() if k != 'page'}
        query['page'] = 1
        return env.redirect(request.path + '?' + urlencode(query)), total_pages
    return None, total_pages


def _pages_to_show(*, total_pages: int, page: int) -> list[int]:
    if total_pages <= 10:
        return list(range(1, total_pages + 1))

    pages = [1]
    for idx in range(11, total_pages + 1, 10):
        if idx <= total_pages:
            pages.append(idx)
    window = 3
    for idx in range(max(1, page - window), min(total_pages + 1, page + window + 1)):
        if idx not in pages:
            pages.append(idx)
    if total_pages not in pages:
        pages.append(total_pages)
    return sorted(pages)


def _build_pagination_html(env, *, request, page: int, pages_to_show: list[int]) -> str:
    base_query_for_page = {k: v for k, v in request.args.items() if k != 'page'}
    pagination_html = '<div>'
    for item in pages_to_show:
        starting_item = 1 + (item - 1) * env.MAX_FILE_LIMIT
        if item == page:
            pagination_html += f'<b>[{starting_item}]</b> '
        else:
            query = {**base_query_for_page, 'page': item}
            href = "?" + urlencode(query)
            pagination_html += f'<a href="{href}">[{starting_item}]</a> '
    pagination_html += '</div>'
    return pagination_html


def _build_showing_text(env, *, total_items: int, page: int, using_manifest: bool) -> str:
    start = (page - 1) * env.MAX_FILE_LIMIT
    showing_start = start + 1 if total_items > 0 else 0
    showing_end = min(start + env.MAX_FILE_LIMIT, total_items)
    manifest_note = ' (manifest cached)' if using_manifest else ''
    if total_items > 0:
        return f'<p>Showing items {showing_start} to {showing_end} of {total_items}{manifest_note}</p>'
    return f'<p>No items to display{manifest_note}</p>'


async def _render_directory_response(
    env,
    *,
    path: str,
    runid: str,
    wd: str,
    request,
    config: str,
    filter_pattern: str,
    hide_mixed_nodir: bool,
    page_entries_override: list[tuple] | None,
    total_items_override: int | None,
    using_manifest_override: bool | None,
    diff_runid: str,
    diff_wd: str | None,
    base_query: dict[str, str],
    query_suffix: str,
    sort_by: str,
    sort_order: str,
    base_browse_url: str,
    home_href: str,
    parquet_filters_enabled: bool,
    parquet_filter_payload: str | None,
):
    breadcrumbs = _build_breadcrumbs_html(
        env,
        runid=runid,
        wd=wd,
        path=path,
        filter_pattern=filter_pattern,
        base_browse_url=base_browse_url,
        query_suffix=query_suffix,
    )
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

    redirect_response, total_pages = _normalize_page_or_redirect(
        env,
        request=request,
        page=page,
        total_items=total_items,
    )
    if redirect_response is not None:
        return redirect_response

    pages = _pages_to_show(total_pages=total_pages, page=page)
    pagination_html = _build_pagination_html(env, request=request, page=page, pages_to_show=pages)
    showing_text = _build_showing_text(env, total_items=total_items, page=page, using_manifest=using_manifest)

    return env.render_template(
        'browse/directory.htm',
        runid=runid,
        config=config,
        diff_runid=diff_runid,
        project_href=env.Markup(f'<a href="{home_href}">☁️</a> '),
        breadcrumbs_html=env.Markup(breadcrumbs),
        listing_html=env.Markup(listing_html),
        pagination_html=env.Markup(pagination_html),
        showing_text=env.Markup(showing_text),
        using_manifest=using_manifest,
        mixed_state_roots=env._mixed_nodir_roots(wd),
        parquet_filters_enabled=parquet_filters_enabled,
        parquet_filter_payload=parquet_filter_payload or '',
    )


def _wants_binary_response(args, headers, *, repr_mode: bool) -> bool:
    return (
        repr_mode
        or ('raw' in args)
        or ('Raw' in headers)
        or ('download' in args)
        or ('Download' in headers)
    )


async def _load_primary_contents(env, *, path: str, path_lower: str, repr_mode: bool):
    contents = None
    lowered = path_lower
    if repr_mode:
        contents = env._generate_repr_content(path)
        if contents is None:
            env.abort(404)

    if contents is None:
        if lowered.endswith('.gz'):
            contents = await env._async_read_gzip(path)
            lowered = lowered[:-3]
        else:
            try:
                contents = await env._async_read_text(path)
            except UnicodeDecodeError:
                contents = None
    return contents, lowered


def _raw_response_if_requested(env, *, args, headers, contents):
    if ('raw' in args or 'Raw' in headers) and contents is not None:
        response = env.Response(response=contents, status=200, mimetype="text/plain")
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response
    return None


def _download_response_if_requested(env, *, args, headers, path: str):
    if 'download' in args or 'Download' in headers:
        return env.send_file(path, as_attachment=True, download_name=env._split(path)[-1])
    return None


def _structured_file_response(env, *, path: str, path_lower: str, runid: str, contents):
    if path_lower.endswith('.json') or path_lower.endswith('.nodb') or path_lower.endswith('.dump'):
        assert contents is not None
        return env.jsonify(json.loads(contents))
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
    return None


async def _markdown_response(env, *, path: str, path_lower: str, runid: str, contents):
    if not path_lower.endswith(env.MARKDOWN_EXTENSIONS):
        return None, contents

    rendered_contents = contents
    if rendered_contents is None:
        try:
            rendered_contents = await env._async_read_text(path)
        except UnicodeDecodeError:
            rendered_contents = None
    if rendered_contents is None:
        return None, rendered_contents

    try:
        rendered_markdown = env.markdown_to_html(rendered_contents)
    except Exception:
        # Boundary: markdown backend errors vary by parser/runtime; fallback to plain text rendering.
        env._logger.exception('Failed to render Markdown file at %s', path)
        return None, rendered_contents

    return env.render_template(
        'browse/markdown_file.htm',
        runid=runid,
        path=path,
        filename=basename(path),
        markdown_html=env.Markup(rendered_markdown),
    ), rendered_contents


def _append_query_params(url: str, params: dict[str, str] | None) -> str:
    if not params:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


async def _tabular_preview(env, *, path: str, path_lower: str, request):
    preview_warning = None
    html_table = None
    filter_feedback = None

    if path_lower.endswith('.pkl'):
        df = await asyncio.to_thread(env.pd.read_pickle, path)
        html_table = await env._async_df_to_html(df)

    if path_lower.endswith(('.parquet', '.pq')):
        raw_payload = request.args.get('pqf')
        if env.BROWSE_PARQUET_FILTERS_ENABLED and raw_payload:
            try:
                compiled = await asyncio.to_thread(env.compile_parquet_filter_for_path, path, raw_payload)
                if compiled is None:
                    df = await asyncio.to_thread(env.pd.read_parquet, path)
                    html_table = await env._async_df_to_html(df)
                else:
                    df = await asyncio.to_thread(
                        env.query_parquet_preview,
                        path,
                        compiled,
                        env.BROWSE_PARQUET_PREVIEW_LIMIT,
                    )
                    html_table = await env._async_df_to_html(df)
                    if df.empty:
                        filter_feedback = {
                            'active': True,
                            'summary': compiled.summary,
                            'code': 'no_rows_matched_filter',
                            'message': 'No rows matched the active parquet filter.',
                            'status_code': 200,
                            'pqf': raw_payload,
                        }
                    else:
                        filter_feedback = {
                            'active': True,
                            'summary': compiled.summary,
                            'code': None,
                            'message': (
                                f'Showing {len(df)} filtered rows '
                                f'(preview limit {env.BROWSE_PARQUET_PREVIEW_LIMIT}).'
                            ),
                            'status_code': 200,
                            'pqf': raw_payload,
                        }
            except env.ParquetFilterError as exc:
                filter_feedback = {
                    'active': True,
                    'summary': None,
                    'code': exc.code,
                    'message': exc.message,
                    'status_code': exc.status_code,
                    'pqf': raw_payload,
                    'payload': exc.to_payload(),
                }
        else:
            df = await asyncio.to_thread(env.pd.read_parquet, path)
            html_table = await env._async_df_to_html(df)

    if path_lower.endswith('.csv'):
        skiprows = 1 if 'totalwatsed2' in path_lower else 0
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
            html_table = await env._async_df_to_html(df)

    if path_lower.endswith('.tsv'):
        try:
            df = await asyncio.to_thread(env.pd.read_table, path, sep='\t', skiprows=0)
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
            html_table = await env._async_df_to_html(df)

    return html_table, preview_warning, filter_feedback


def _tabular_response(
    env,
    *,
    html_table: str | None,
    path: str,
    path_lower: str,
    runid: str,
    wd: str,
    request,
    config: str,
    filter_feedback: dict | None,
):
    table_markup = env.Markup(html_table) if html_table is not None else None
    rel_url = os.path.relpath(path, wd).replace('\\', '/')
    dtale_base = env._resolve_dtale_base(request.path, runid, config, env._prefix_path)
    dtale_url = f"{dtale_base}{quote(rel_url, safe='/')}"
    download_url = request.path.replace('/browse/', '/download/', 1)
    csv_url = None
    query_params: dict[str, str] = {}
    if filter_feedback and filter_feedback.get('active') and filter_feedback.get('pqf'):
        query_params['pqf'] = filter_feedback['pqf']
    if path_lower.endswith(('.parquet', '.pq')):
        if query_params:
            dtale_url = _append_query_params(dtale_url, query_params)
            download_url = _append_query_params(download_url, query_params)
        csv_query = {'as_csv': '1'}
        if query_params:
            csv_query.update(query_params)
        csv_url = _append_query_params(download_url.split('?', 1)[0], csv_query)

    rendered = env.render_template(
        'browse/data_table.htm',
        filename=basename(path),
        runid=runid,
        table_html=table_markup,
        download_url=download_url,
        csv_url=csv_url,
        dtale_url=dtale_url,
        parquet_filter_active=bool(filter_feedback and filter_feedback.get('active')),
        parquet_filter_summary=(filter_feedback or {}).get('summary'),
        parquet_filter_message=(filter_feedback or {}).get('message'),
        parquet_filter_code=(filter_feedback or {}).get('code'),
    )
    status_code = (filter_feedback or {}).get('status_code', 200)
    if status_code != 200:
        return rendered, status_code
    return rendered


async def _final_text_response(env, *, path: str, runid: str, contents, preview_warning):
    rendered_contents = contents
    if rendered_contents is None:
        try:
            rendered_contents = await env._async_read_text(path)
        except UnicodeDecodeError:
            return env.send_file(path, as_attachment=True, download_name=env._split(path)[-1])

    return env.render_template(
        'browse/text_file.htm',
        runid=runid,
        path=path,
        filename=basename(path),
        contents=rendered_contents,
        contents_html=env._wrap_usersum_spans(rendered_contents),
        preview_warning=preview_warning,
    )


async def _render_file_response(
    env,
    *,
    path: str,
    path_lower: str,
    runid: str,
    wd: str,
    request,
    config: str,
):
    args = request.args
    headers = request.headers
    repr_mode = args.get('repr') is not None

    if path_lower.endswith('.dss') and not _wants_binary_response(args, headers, repr_mode=repr_mode):
        dss_response = await env._maybe_render_dss_preview(path, runid, config)
        if dss_response is not None:
            return dss_response

    contents, lowered = await _load_primary_contents(
        env,
        path=path,
        path_lower=path_lower,
        repr_mode=repr_mode,
    )
    path_lower = lowered

    raw_response = _raw_response_if_requested(env, args=args, headers=headers, contents=contents)
    if raw_response is not None:
        return raw_response

    download_response = _download_response_if_requested(env, args=args, headers=headers, path=path)
    if download_response is not None:
        return download_response

    structured_response = _structured_file_response(
        env,
        path=path,
        path_lower=path_lower,
        runid=runid,
        contents=contents,
    )
    if structured_response is not None:
        return structured_response

    markdown_response, contents = await _markdown_response(
        env,
        path=path,
        path_lower=path_lower,
        runid=runid,
        contents=contents,
    )
    if markdown_response is not None:
        return markdown_response

    html_table, preview_warning, filter_feedback = await _tabular_preview(
        env,
        path=path,
        path_lower=path_lower,
        request=request,
    )
    if filter_feedback and filter_feedback.get('code') and filter_feedback.get('payload'):
        return env.jsonify(filter_feedback['payload']), filter_feedback['status_code']

    if html_table is not None or (filter_feedback and filter_feedback.get('active')):
        return _tabular_response(
            env,
            html_table=html_table,
            path=path,
            path_lower=path_lower,
            runid=runid,
            wd=wd,
            request=request,
            config=config,
            filter_feedback=filter_feedback,
        )

    return await _final_text_response(
        env,
        path=path,
        runid=runid,
        contents=contents,
        preview_warning=preview_warning,
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
    diff_runid = _sanitize_diff_runid(args)
    sort_by, sort_order = env._normalize_sort_params(args)
    parquet_filter_payload = None
    if env.BROWSE_PARQUET_FILTERS_ENABLED:
        parquet_filter_payload = (args.get('pqf') or '').strip() or None
    base_query = _build_base_query(
        args=args,
        diff_runid=diff_runid,
        sort_by=sort_by,
        sort_order=sort_order,
        parquet_filter_payload=parquet_filter_payload,
    )
    diff_wd = env.get_wd(diff_runid) if diff_runid else None
    query_suffix = f'?{urlencode(base_query)}' if base_query else ''

    if not force_directory and not env._exists(path):
        return env.jsonify({'error': {'message': 'path does not exist'}}), 404

    base_browse_url, home_href = env._resolve_browse_paths(request.path, runid, config)
    if force_directory or os.path.isdir(path):
        return await _render_directory_response(
            env,
            path=path,
            runid=runid,
            wd=wd,
            request=request,
            config=config,
            filter_pattern=filter_pattern,
            hide_mixed_nodir=hide_mixed_nodir,
            page_entries_override=page_entries_override,
            total_items_override=total_items_override,
            using_manifest_override=using_manifest_override,
            diff_runid=diff_runid,
            diff_wd=diff_wd,
            base_query=base_query,
            query_suffix=query_suffix,
            sort_by=sort_by,
            sort_order=sort_order,
            base_browse_url=base_browse_url,
            home_href=home_href,
            parquet_filters_enabled=env.BROWSE_PARQUET_FILTERS_ENABLED,
            parquet_filter_payload=parquet_filter_payload,
        )

    return await _render_file_response(
        env,
        path=path,
        path_lower=path.lower(),
        runid=runid,
        wd=wd,
        request=request,
        config=config,
    )
