"""Hold Roads read admission through response construction and ASGI streaming."""
from contextlib import ExitStack
from pathlib import Path
import os

from starlette.responses import JSONResponse, Response

from wepppy.wepp.interchange import _roads_lifecycle as lifecycle


class _GuardedResponse(Response):
    def __init__(self, response, stack):
        self.response = response
        self.stack = stack
        self.status_code = response.status_code
        self.raw_headers = response.raw_headers
        self.background = response.background
        self.media_type = response.media_type
        self.headers['Cache-Control'] = 'no-store'

    async def __call__(self, scope, receive, send):
        try:
            await self.response(scope, receive, send)
        finally:
            self.stack.close()


async def guarded_response(path, build):
    lexical = Path(path).absolute()
    resolved = Path(os.path.realpath(lexical))
    stack = ExitStack()
    handed_off = False
    try:
        owner = lifecycle.path_owner(lexical)
        if owner is not None and owner.resolve() / lexical.relative_to(owner) != resolved:
            raise lifecycle.RoadsResultsUnavailable('Current Roads paths cannot alias other resources.')
        owners = {lifecycle.path_owner(p) for p in (lexical, resolved)} - {None}
        for root in sorted(owners):
            stack.enter_context(lifecycle.current_read(root))
        response = await build()
        if not owners:
            return response
        handed_off = True
        return _GuardedResponse(response, stack)
    except lifecycle.RoadsResultsUnavailable as exc:
        return JSONResponse({'error': {'message': str(exc), 'code': exc.code}},
                            status_code=409, headers={'Cache-Control': 'no-store'})
    finally:
        if not handed_off:
            stack.close()


def visible(path):
    lexical = Path(path).absolute()
    roots = {lifecycle.path_owner(p) for p in (lexical, Path(os.path.realpath(lexical)))} - {None}
    return all(lifecycle.available(root) for root in roots)
