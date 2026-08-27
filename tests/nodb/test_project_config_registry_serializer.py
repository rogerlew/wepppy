from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import subprocess

import pytest

import wepppy.nodb.config_builder.registry as registry_module
from wepppy.nodb.config_builder import (
    ALLOWED_CELL_SIZES,
    BuilderConstraintError,
    BuilderSelections,
    ComponentDefinition,
    ComponentKind,
    ConfigWrite,
    Registry,
    RegistryError,
    describe_builder,
    load_registry,
    resolve_builder_config,
)
from wepppy.nodb.config_builder.schema import ConstraintSet
from wepppy.project_config_serialization import (
    parse_config_text,
    validate_canonical_config_text,
)
from wepp_runner.wepp_runner import get_linux_wepp_bin_opts

pytestmark = pytest.mark.unit

EXPECTED_IDS = {
    "continental-us",
    "usgs-ned1-2024",
    "usgs-ned13-2022",
    "topaz",
    "wbt",
    "single-ofe",
    "multiple-ofe",
    "ssurgo-gnatsgso-2025",
    "nlcd-2019",
    "vanilla_cligen",
    "prism_stochastic",
    "observed_daymet",
    "observed_gridmet",
    "continental-us-capabilities",
    "europe",
    "canada",
    "australia",
    "global-earth",
    "europe-capabilities",
    "canada-capabilities",
    "australia-capabilities",
    "global-earth-capabilities",
    "europe-eudem-v1-1",
    "copernicus-dem-30",
    "australia-srtm-1s",
    "esdac-europe",
    "isric-global",
    "asris-australia",
    "eobs_modified",
    "agdc",
    "cligen-stations-legacy",
    "cligen-stations-2015",
    "cligen-stations-ghcn",
    "australia-landuse-2010-2011",
    "corine-1990",
    "corine-2000",
    "corine-2006",
    "corine-2012",
    "corine-2018",
    *(f"c3s-landcover-{year}" for year in range(1992, 2021)),
}


def _selections(
    dem: str = "usgs-ned1-2024",
    backend: str = "topaz",
    *,
    representation: str = "single-ofe",
    wepp_binary: str = "wepp_260803",
    climate: str = "vanilla_cligen",
    mods: tuple[str, ...] = (),
    cellsize: int | None = None,
) -> BuilderSelections:
    return BuilderSelections(
        locale="continental-us",
        dem=dem,
        delineation_backend=backend,
        watershed_representation=representation,
        wepp_binary=wepp_binary,
        soil="ssurgo-gnatsgso-2025",
        landuse="nlcd-2019",
        climate=climate,
        mods=mods,
        cellsize_override=cellsize,
    )


def _with_component(registry: Registry, component: ComponentDefinition) -> Registry:
    components = dict(registry.components)
    components[component.component_id] = component
    return Registry.create(f"test-{registry.revision}", components)


def _minimal_document(**replacements: str) -> str:
    values = {
        "schema": "1",
        "id": '"test-mod"',
        "kind": '"mod"',
        "revision": '"1"',
        "owns": "[]",
        "overrides": "[]",
        "writes": "[]",
        "requires": "[]",
        "conflicts": "[]",
    }
    values.update(replacements)
    return (
        f"schema_version = {values['schema']}\n"
        f"id = {values['id']}\n"
        f"kind = {values['kind']}\n"
        f"source_revision = {values['revision']}\n"
        'label = "Test"\n'
        'description = "Test component."\n'
        f"owns = {values['owns']}\n"
        f"overrides = {values['overrides']}\n"
        f"writes = {values['writes']}\n\n"
        "[constraints]\n"
        f"requires = {values['requires']}\n"
        f"conflicts = {values['conflicts']}\n"
    )


def _provider_fixture_paths(tmp_path: Path, binary_ids: tuple[str, ...]) -> dict[str, tuple[str, str]]:
    paths: dict[str, tuple[str, str]] = {}
    for binary_id in binary_ids:
        watershed = tmp_path / binary_id
        hillslope = tmp_path / f"{binary_id}_hill"
        watershed.write_bytes(f"watershed:{binary_id}".encode())
        hillslope.write_bytes(f"hillslope:{binary_id}".encode())
        watershed.chmod(0o755)
        hillslope.chmod(0o755)
        paths[binary_id] = (str(watershed), str(hillslope))
    return paths


def test_shipped_registry_is_real_toml_with_stable_ids_and_defaults() -> None:
    registry = load_registry()
    provider_ids = set(get_linux_wepp_bin_opts())

    assert set(registry.components) == EXPECTED_IDS | provider_ids
    assert registry.get("usgs-ned1-2024").default_cellsize == 30
    assert registry.get("usgs-ned13-2022").default_cellsize == 10
    assert all(component.schema_version == 1 for component in registry.components.values())
    assert len(registry.revision) == 64


def test_shipped_registry_exposes_complete_provider_list_with_neutral_labels() -> None:
    registry = load_registry()
    provider_ids = tuple(dict.fromkeys(get_linux_wepp_bin_opts()))
    binaries = registry.by_kind(ComponentKind.WEPP_BINARY)

    assert tuple(component.component_id for component in binaries) == tuple(sorted(provider_ids))
    assert tuple(component.label for component in binaries) == tuple(sorted(provider_ids))
    assert all("legacy parity" not in component.label.casefold() for component in binaries)
    assert registry.get("wepp_260803").writes[0] == ConfigWrite(
        "wepp", "bin", "wepp_260803"
    )
    resolved = resolve_builder_config(_selections(), registry=registry)
    assert resolved.config["capabilities"]["wepp_binaries"] == list(provider_ids)


def test_provider_values_are_deduplicated_without_a_second_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary_ids = ("wepp_260803", "latest")
    paths = _provider_fixture_paths(tmp_path, binary_ids)
    monkeypatch.setattr(
        registry_module,
        "get_linux_wepp_bin_opts",
        lambda: ["wepp_260803", "latest", "wepp_260803"],
    )
    monkeypatch.setattr(
        registry_module,
        "get_linux_wepp_bin_role_paths",
        lambda binary_id: paths[binary_id],
    )

    registry = load_registry()

    assert tuple(item.component_id for item in registry.by_kind(ComponentKind.WEPP_BINARY)) == (
        "latest",
        "wepp_260803",
    )
    assert registry.get("continental-us").constraints.allowed_wepp_binary == (
        "wepp_260803",
        "latest",
    )


def test_provider_failure_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _provider_fixture_paths(tmp_path, ("wepp_260803",))
    monkeypatch.setattr(
        registry_module,
        "get_linux_wepp_bin_opts",
        lambda: ["wepp_260803", "wepp_broken"],
    )
    monkeypatch.setattr(
        registry_module,
        "get_linux_wepp_bin_role_paths",
        lambda binary_id: paths.get(binary_id, (str(tmp_path / "missing"),) * 2),
    )

    with pytest.raises(RegistryError, match="unusable watershed executable"):
        load_registry()


def test_provider_role_identity_changes_registry_revision_and_manifest_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary_ids = ("wepp_260803", "latest")
    paths = _provider_fixture_paths(tmp_path, binary_ids)
    monkeypatch.setattr(registry_module, "get_linux_wepp_bin_opts", lambda: list(binary_ids))
    monkeypatch.setattr(
        registry_module,
        "get_linux_wepp_bin_role_paths",
        lambda binary_id: paths[binary_id],
    )
    first = load_registry()
    selected = resolve_builder_config(_selections(wepp_binary="latest"), registry=first)
    latest_revision = first.get("latest").source_revision

    assert selected.config["wepp"]["bin"] == "latest"
    assert next(item.revision for item in selected.parent_chain if item.component_id == "latest") == latest_revision

    replacement = tmp_path / "latest-replacement"
    replacement.write_bytes(b"replacement latest watershed")
    replacement.chmod(0o755)
    paths["latest"] = (str(replacement), paths["latest"][1])
    second = load_registry()

    assert second.revision != first.revision
    assert second.get("latest").source_revision != latest_revision


@pytest.mark.parametrize("binary_id", ["wepp_dcc52a6", "wepp_260803"])
def test_registered_wepp_binary_pairs_execute_without_mocking(binary_id: str, tmp_path: Path) -> None:
    bin_root = Path(__file__).parents[2] / "wepp_runner" / "bin"
    fixture_root = Path(__file__).parents[1] / "wepp" / "interchange" / "fixtures" / "deductive-futurist" / "wepp" / "runs"
    required = (
        "p1.run", "p1.man", "p1.slp", "p1.cli", "p1.sol", "chan.inp",
        "chntyp.txt", "gwcoeff.txt", "pmetpara.txt", "snow.txt", "wepp_ui.txt",
    )
    for suffix in ("", "_hill"):
        binary = bin_root / f"{binary_id}{suffix}"
        assert binary.is_file()
        assert binary.stat().st_mode & 0o111
        work_root = tmp_path / f"builder-{binary_id}{suffix}"
        runs_dir = work_root / "runs"
        (work_root / "output").mkdir(parents=True)
        runs_dir.mkdir()
        for filename in required:
            shutil.copy2(fixture_root / filename, runs_dir / filename)
        completed = subprocess.run(
            [str(binary)],
            input=(runs_dir / "p1.run").read_bytes(),
            cwd=runs_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")
        assert b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" in completed.stdout


@pytest.mark.parametrize("dem", ["usgs-ned1-2024", "usgs-ned13-2022"])
@pytest.mark.parametrize(
    ("backend", "representation", "wepp_binary"),
    [
        ("topaz", "single-ofe", "wepp_dcc52a6"),
        ("topaz", "single-ofe", "wepp_260803"),
        ("wbt", "single-ofe", "wepp_dcc52a6"),
        ("wbt", "single-ofe", "wepp_260803"),
        ("wbt", "multiple-ofe", "wepp_260803"),
    ],
)
def test_initial_local_matrix_resolves_to_canonical_bytes(
    dem: str, backend: str, representation: str, wepp_binary: str,
) -> None:
    registry = load_registry()
    selections = _selections(dem, backend, representation=representation, wepp_binary=wepp_binary)
    first = resolve_builder_config(selections, registry=registry)
    second = resolve_builder_config(selections, registry=registry)

    assert first.config_bytes == second.config_bytes
    assert validate_canonical_config_text(first.config_bytes.decode()) == parse_config_text(
        first.config_bytes.decode()
    )
    assert first.config["config"]["flattened"] is True
    assert first.config["general"]["dem_db"] == (
        "ned1/2024" if dem == "usgs-ned1-2024" else "ned13/2022"
    )
    assert first.config["watershed"]["delineation_backend"] == backend
    assert first.config["wepp"]["multi_ofe"] is (representation == "multiple-ofe")
    assert first.config["wepp"]["bin"] == wepp_binary
    assert first.effective_cellsize == first.dem_default_cellsize
    assert first.cellsize_source == "dem_default"


@pytest.mark.parametrize("cellsize", ALLOWED_CELL_SIZES)
def test_every_fixed_cellsize_override_is_accepted(cellsize: int) -> None:
    result = resolve_builder_config(_selections(cellsize=cellsize))

    assert result.effective_cellsize == cellsize
    assert result.config["general"]["cellsize"] == cellsize
    expected_source = "dem_default" if cellsize == 30 else "privileged_override"
    assert result.cellsize_source == expected_source


def test_composition_order_and_effective_writers_are_explicit() -> None:
    result = resolve_builder_config(_selections(backend="wbt", climate="observed_daymet"))

    assert [entry.component_id for entry in result.parent_chain] == [
        "shared-defaults",
        "continental-us",
        "usgs-ned1-2024",
        "wbt",
        "single-ofe",
        "wepp_260803",
        "ssurgo-gnatsgso-2025",
        "nlcd-2019",
        "observed_daymet",
        "cligen-stations-2015",
        "continental-us-capabilities",
    ]
    assert result.effective_writers[("general", "dem_db")] == "usgs-ned1-2024"
    assert result.effective_writers[("watershed.wbt", "mcl")] == "wbt"
    assert result.effective_writers[("wepp", "bin")] == "wepp_260803"
    assert result.effective_writers[("general", "cellsize")] == "selection:cellsize"


def test_undeclared_writeover_fails_and_declared_writeover_succeeds() -> None:
    registry = load_registry()
    topaz = registry.get("topaz")
    hostile = _with_component(registry, replace(topaz, overrides=()))

    with pytest.raises(BuilderConstraintError) as error:
        resolve_builder_config(_selections(), registry=hostile)
    assert (error.value.field, error.value.code) == (
        "watershed.delineation_backend",
        "undeclared_writeover",
    )
    assert resolve_builder_config(_selections(), registry=registry).config["watershed"][
        "delineation_backend"
    ] == "topaz"


def test_registry_addition_does_not_enable_or_apply_a_mod() -> None:
    registry = load_registry()
    locale = registry.get("continental-us")
    mod = ComponentDefinition(
        component_id="test-mod",
        kind=ComponentKind.MOD,
        schema_version=1,
        source_revision="1",
        label="Test mod",
        description="Test-only optional addition.",
        owns=(("test", "enabled"),),
        overrides=(),
        writes=(ConfigWrite("test", "enabled", True),),
        constraints=ConstraintSet(requires=("continental-us",)),
    )
    registry = _with_component(registry, mod)
    registry = _with_component(
        registry,
        replace(
            locale,
            constraints=replace(locale.constraints, allowed_mods=("test-mod",)),
        ),
    )

    dormant = resolve_builder_config(_selections(), registry=registry)
    active = resolve_builder_config(_selections(mods=("test-mod",)), registry=registry)

    assert "test" not in dormant.config
    assert dormant.config["nodb"]["mods"] == []
    assert active.config["test"]["enabled"] is True
    assert active.config["nodb"]["mods"] == ["test-mod"]


def test_resolution_is_independent_from_caller_base_mutation() -> None:
    base = {"base": {"items": ["original"]}}
    before = {"base": {"items": ["original"]}}
    result = resolve_builder_config(_selections(), base_config=base, base_revision="base-1")

    base["base"]["items"].append("later")
    assert before == {"base": {"items": ["original"]}}
    assert result.config["base"]["items"] == ["original"]
    assert result.parent_chain[0].revision == "base-1"


def test_description_is_deterministic_and_server_ready() -> None:
    registry = load_registry()
    first = describe_builder(registry)
    second = describe_builder(registry)

    assert first == second
    assert first.schema_version == 2
    assert first.registry_revision == registry.revision
    assert first.allowed_cell_sizes == ALLOWED_CELL_SIZES
    assert set(first.capability_graphs_by_locale) == {
        "continental-us", "europe", "canada", "australia", "global-earth"
    }
    assert set(first.components_by_locale) == set(first.capability_graphs_by_locale)
    assert first.capability_graph["capabilities"]["schema_version"] == 2
    assert all(
        graph["capabilities"]["schema_version"] == 3
        for graph in first.capability_graphs_by_locale.values()
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("locale", "missing-locale"),
        ("dem", "missing-dem"),
        ("delineation_backend", "missing-backend"),
        ("watershed_representation", "missing-representation"),
        ("wepp_binary", "missing-binary"),
        ("soil", "missing-soil"),
        ("landuse", "missing-landuse"),
        ("climate", "missing-climate"),
        ("climate_station_database", "missing-station-database"),
        ("capability_profile", "missing-profile"),
    ],
)
def test_excluded_ids_fail_without_fallback(field: str, value: str) -> None:
    selections = replace(_selections(), **{field: value})

    with pytest.raises(BuilderConstraintError) as error:
        resolve_builder_config(selections)
    assert error.value.field == field
    assert error.value.code == "unknown_component"


def test_builder_constraints_reject_invalid_sizes_and_mods() -> None:
    with pytest.raises(BuilderConstraintError) as size_error:
        resolve_builder_config(_selections(cellsize=20))
    assert (size_error.value.field, size_error.value.code) == (
        "cellsize_override",
        "invalid_cellsize",
    )

    with pytest.raises(BuilderConstraintError) as mod_error:
        resolve_builder_config(_selections(mods=("unregistered-mod",)))
    assert (mod_error.value.field, mod_error.value.code) == ("mods", "unknown_component")


@pytest.mark.parametrize(
    "selections",
    [
        _selections("usgs-ned1-2024", "topaz", representation="multiple-ofe"),
        _selections("usgs-ned1-2024", "wbt", representation="multiple-ofe", wepp_binary="wepp_dcc52a6"),
    ],
)
def test_multiple_ofe_rejects_incompatible_backend_or_binary(selections: BuilderSelections) -> None:
    with pytest.raises(BuilderConstraintError) as error:
        resolve_builder_config(selections)
    assert error.value.code in {
        "missing_required_component",
        "conflicting_component",
        "unsupported_combination",
    }


def test_registry_revision_is_path_and_content_deterministic(tmp_path: Path) -> None:
    source = Path(__file__).parents[2] / "wepppy" / "nodb" / "config_builder" / "profiles"
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    shutil.copytree(source, first_root)
    shutil.copytree(source, second_root)

    assert load_registry(first_root).revision == load_registry(second_root).revision
    changed = second_root / "climate" / "vanilla-cligen.toml"
    changed.write_text(changed.read_text() + "\n", encoding="utf-8")
    assert load_registry(first_root).revision != load_registry(second_root).revision


@pytest.mark.parametrize(
    ("document", "match"),
    [
        ("not = [valid", "unable to parse TOML"),
        (_minimal_document(schema="2"), "unsupported registry schema"),
        (_minimal_document(id='"Invalid_ID"'), "invalid stable component ID"),
        (_minimal_document(kind='"unknown"'), "unknown component kind"),
        (
            _minimal_document(owns='["test.value", "test.value"]'),
            "owns contains duplicates",
        ),
        (_minimal_document(requires='["missing"]'), "unknown component reference"),
        (
            _minimal_document(requires='["test-mod"]', conflicts='["test-mod"]'),
            "both required and conflicting",
        ),
    ],
)
def test_invalid_registry_documents_fail_atomically(
    tmp_path: Path,
    document: str,
    match: str,
) -> None:
    (tmp_path / "component.toml").write_text(document, encoding="utf-8")

    with pytest.raises(RegistryError, match=match):
        load_registry(tmp_path)


def test_undeclared_document_write_is_rejected(tmp_path: Path) -> None:
    document = _minimal_document(owns="[]", writes="[]")
    document = document.replace(
        "writes = []",
        '[[writes]]\nsection = "test"\noption = "enabled"\nvalue = true',
    )
    (tmp_path / "component.toml").write_text(document, encoding="utf-8")

    with pytest.raises(RegistryError, match="not declared in owns"):
        load_registry(tmp_path)


def test_duplicate_component_ids_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "one.toml").write_text(_minimal_document(), encoding="utf-8")
    (tmp_path / "two.toml").write_text(_minimal_document(), encoding="utf-8")

    with pytest.raises(RegistryError, match="Duplicate or case-colliding"):
        load_registry(tmp_path)
