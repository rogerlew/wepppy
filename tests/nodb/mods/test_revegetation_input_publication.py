"""Direct executable input publication, failure retention and link isolation."""
import os
from pathlib import Path
import pytest
from wepppy.nodb.mods.rap.revegetation_inputs import cover_output, publish_revegetation_input

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('name', ['firedate.txt', 'simfire.txt', 'p2.cov'])
def test_hardlinked_source_and_private_mode_survive(tmp_path, name):
    source = tmp_path / 'source'
    source.write_text('old')
    source.chmod(0o600)
    target = tmp_path / name
    os.link(source, target)
    publish_revegetation_input(str(tmp_path), name, 'new')
    assert source.read_text() == 'old'
    assert target.read_text() == 'new'
    assert target.stat().st_mode & 0o777 == 0o600
    assert next(tmp_path.glob(f'revegetation-input-*/{name}')).read_text() == 'old'
    before = sorted(tmp_path.iterdir())
    publish_revegetation_input(str(tmp_path), name, 'new')
    assert sorted(tmp_path.iterdir()) == before


def test_cover_symlink_rejected_and_writer_failure_retained(tmp_path):
    source = tmp_path / 'source'
    source.write_text('protected')
    target = tmp_path / 'p1.cov'
    target.symlink_to(source)
    with pytest.raises(ValueError):
        with cover_output(str(tmp_path), 'p1.cov') as out:
            out.write('replacement')
    assert source.read_text() == 'protected'
    target.unlink()
    with pytest.raises(RuntimeError):
        with cover_output(str(tmp_path), 'p1.cov') as out:
            out.write('partial evidence')
            raise RuntimeError('injected writer failure')
    assert not target.exists()
    assert next(tmp_path.glob('p1.cov.revegetation-*.tmp')).read_text() == 'partial evidence'


def test_failed_final_replace_retains_prior_and_attempt(tmp_path, monkeypatch):
    import wepppy.nodb.mods.rap.revegetation_inputs as module
    target = tmp_path / 'firedate.txt'
    target.write_text('old')
    replace = module.os.replace
    def failing_replace(source, destination):
        if Path(destination) == target:
            raise OSError('injected publication failure')
        return replace(source, destination)
    monkeypatch.setattr(module.os, 'replace', failing_replace)
    with pytest.raises(OSError):
        publish_revegetation_input(str(tmp_path), 'firedate.txt', 'new')
    assert next(tmp_path.glob('revegetation-input-*/firedate.txt')).read_text() == 'old'
    assert next(tmp_path.glob('firedate.txt.revegetation-*.tmp')).read_text() == 'new'
