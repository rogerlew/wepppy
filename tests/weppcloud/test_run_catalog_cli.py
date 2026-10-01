from contextlib import nullcontext
import json
from types import SimpleNamespace

import pytest
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from wepppy.weppcloud.run_catalog import __main__ as cli
from wepppy.weppcloud.run_catalog.adapter import Settings

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("failure", ["database", "queue"])
def test_outage_output_preserves_operator_gate(monkeypatch, capsys, failure):
    import redis
    from wepppy.rq import run_catalog_rq
    monkeypatch.setattr(cli, "initialize", lambda: Settings("postgres", "catalog"))
    monkeypatch.setattr(redis, "Redis", lambda **kwargs: nullcontext(object()))

    def unavailable():
        raise OperationalError("private-database-canary", {}, RuntimeError("private-password"))

    def operational(connection):
        if failure == "queue":
            raise RedisError("private-redis-canary")
        return {}

    monkeypatch.setattr(cli, "get_engine", lambda **kwargs: SimpleNamespace(begin=unavailable))
    monkeypatch.setattr(run_catalog_rq, "operational_status", operational)
    assert cli.main(["preflight", "--json"]) == 1
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["technical_ready"] is False
    assert payload["gate_status"] == "operator_evidence_required"
    assert payload["promotion_requires"]
    assert "private" not in output
