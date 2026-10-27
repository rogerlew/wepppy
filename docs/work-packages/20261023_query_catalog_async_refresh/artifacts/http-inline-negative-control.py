"""Expected failure: reproduce inline blocking through the same real HTTP test."""
from tests.query_engine import test_mcp_router as suite


def test_inline_guard_blocks_http_loop(monkeypatch, tmp_path):
    original = suite._make_client

    def make_client(*args, **kwargs):
        result = original(*args, **kwargs)
        from wepppy.query_engine.app import server

        async def inline(function, *args, **kwargs):
            return function(*args, **kwargs)

        monkeypatch.setattr(server, 'run_in_threadpool', inline)
        return result

    monkeypatch.setattr(suite, '_make_client', make_client)
    suite.test_catalog_contention_keeps_http_loop_responsive(monkeypatch, tmp_path, 'schema')
