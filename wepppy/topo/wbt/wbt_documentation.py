"""Generate Markdown documentation for WhiteboxTools workspace outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
import re

__all__ = ["ResourceDefinition", "generate_wbt_documentation"]


@dataclass(frozen=True)
class ResourceDefinition:
    filename: str
    summary: str
    description: str
    units: str
    tool: str
    notes: Optional[str] = None
    inputs: tuple[str, ...] = ()


STATIC_INPUTS: Dict[str, str] = {
    "DEM": "DEM (input)",
    "Outlet request": "Outlet request (lon/lat)",
}


RESOURCE_SEQUENCE: List[ResourceDefinition] = [
    ResourceDefinition(
        filename="relief.tif",
        summary="Hydrologically conditioned DEM.",
        description="Depressions are filled or breached to enforce drainage prior to flow routing.",
        units="meters (elevation)",
        tool="WhiteboxTools `fill_depressions`, `breach_depressions`, or `breach_depressions_least_cost`.",
        inputs=("DEM",),
    ),
    ResourceDefinition(
        filename="flovec.tif",
        summary="D8 flow direction raster.",
        description="Each cell stores the primary flow direction using D8 pointer codes.",
        units="direction code (1, 2, 4, … 128)",
        tool="WhiteboxTools `d8_pointer`.",
        inputs=("relief.tif",),
    ),
    ResourceDefinition(
        filename="floaccum.tif",
        summary="D8 flow accumulation (cells).",
        description="Counts upslope contributing cells derived from the D8 pointer grid.",
        units="number of cells (dimensionless)",
        tool="WhiteboxTools `d8_flow_accumulation` (`out_type=cells`).",
        inputs=("flovec.tif",),
    ),
    ResourceDefinition(
        filename="netful0.tif",
        summary="Initial stream network mask.",
        description="Binary channel raster extracted from the accumulation grid before short reach filtering.",
        units="1 for channel cell, 0 elsewhere",
        tool="WhiteboxTools `extract_streams` (threshold based on CSA).",
        inputs=("floaccum.tif",),
    ),
    ResourceDefinition(
        filename="netful.tif",
        summary="Stream network mask (filtered).",
        description="Binary channel raster after removing reaches shorter than the minimum channel length.",
        units="1 for channel cell, 0 elsewhere",
        tool="WhiteboxTools `remove_short_streams`.",
        inputs=("netful0.tif", "flovec.tif"),
    ),
    ResourceDefinition(
        filename="chnjnt.tif",
        summary="Stream junction raster.",
        description="Identifies confluence cells within the stream network.",
        units="1 at junction cells, background elsewhere",
        tool="WhiteboxTools `stream_junction_identifier`.",
        inputs=("flovec.tif", "netful.tif"),
    ),
    ResourceDefinition(
        filename="netful.json",
        summary="Stream network polygons (project CRS).",
        description="Vectorized representation of the filtered stream network in the DEM projection.",
        units="planar coordinates (EPSG of the DEM)",
        tool="`polygonize_netful` utility (GDAL polygonize).",
        inputs=("netful.tif",),
    ),
    ResourceDefinition(
        filename="netful.WGS.json",
        summary="Stream network polygons (WGS84).",
        description="Reprojected copy of `netful.json` for web and GIS clients requiring latitude/longitude.",
        units="degrees (EPSG:4326)",
        tool="`json_to_wgs` utility.",
        inputs=("netful.json",),
    ),
    ResourceDefinition(
        filename="outlet.geojson",
        summary="Watershed outlet point(s).",
        description="Outlet snapped to the channel network with metadata about the requested location.",
        units="planar coordinates (EPSG of the DEM)",
        tool="WhiteboxTools `find_outlet`.",
        inputs=("flovec.tif", "netful.tif", "Outlet request"),
    ),
    ResourceDefinition(
        filename="bound.tif",
        summary="Watershed raster mask.",
        description="Binary watershed extent derived from the outlet and flow directions.",
        units="1 inside watershed, nodata outside",
        tool="WhiteboxTools `watershed`.",
        inputs=("flovec.tif", "outlet.geojson"),
    ),
    ResourceDefinition(
        filename="bound.geojson",
        summary="Watershed polygon (project CRS).",
        description="Polygonized watershed boundary in the DEM projection (if polygonization was requested).",
        units="planar coordinates (EPSG of the DEM)",
        tool="`polygonize_bound` utility.",
        notes="Invoke `polygonize_bound` to create this file when needed.",
        inputs=("bound.tif",),
    ),
    ResourceDefinition(
        filename="bound.WGS.geojson",
        summary="Watershed polygon (WGS84).",
        description="Reprojected watershed polygon for web delivery.",
        units="degrees (EPSG:4326)",
        tool="`json_to_wgs` utility.",
        inputs=("bound.geojson",),
    ),
    ResourceDefinition(
        filename="taspec.tif",
        summary="Aspect raster.",
        description="Cell aspect measured clockwise from north.",
        units="degrees (0–360)",
        tool="WhiteboxTools `aspect`.",
        inputs=("DEM",),
    ),
    ResourceDefinition(
        filename="fvslop.tif",
        summary="Slope raster.",
        description="Slope magnitude derived from the conditioned DEM.",
        units="rise/run (dimensionless ratio)",
        tool="WhiteboxTools `slope` (`units=ratio`).",
        inputs=("DEM",),
    ),
    ResourceDefinition(
        filename="netw0.tif",
        summary="Stream mask clipped to watershed.",
        description="Stream network limited to the watershed extent.",
        units="1 for channel cell, 0 elsewhere",
        tool="WhiteboxTools `clip_raster_to_raster`.",
        inputs=("netful.tif", "bound.tif"),
    ),
    ResourceDefinition(
        filename="discha.tif",
        summary="Distance-to-channel raster.",
        description="Downslope distance from each cell to the nearest channel.",
        units="meters",
        tool="WhiteboxTools `downslope_distance_to_stream`.",
        inputs=("DEM", "netw0.tif"),
    ),
    ResourceDefinition(
        filename="strahler.tif",
        summary="Strahler stream order raster.",
        description="Stream order value for each channel cell.",
        units="Strahler order (integer)",
        tool="WhiteboxTools `strahler_stream_order`.",
        inputs=("flovec.tif", "netw0.tif"),
    ),
    ResourceDefinition(
        filename="subwta.tif",
        summary="Subcatchment identifier raster.",
        description="Topaz subcatchment IDs assigned to each hillslope area.",
        units="TopazID (integer)",
        tool="WhiteboxTools `hillslopes_topaz`.",
        inputs=(
            "relief.tif",
            "flovec.tif",
            "netw0.tif",
            "outlet.geojson",
            "bound.tif",
            "chnjnt.tif",
            "strahler.tif",
        ),
    ),
    ResourceDefinition(
        filename="netw.tsv",
        summary="Channel network attributes table.",
        description="Topaz network summary table including connectivity and geometry metrics.",
        units="mixed units (meters, booleans, identifiers)",
        tool="WhiteboxTools `hillslopes_topaz`.",
        inputs=(
            "relief.tif",
            "flovec.tif",
            "netw0.tif",
            "outlet.geojson",
            "bound.tif",
            "chnjnt.tif",
            "strahler.tif",
        ),
    ),
    ResourceDefinition(
        filename="subwta.geojson",
        summary="Subcatchment polygons (Topaz IDs).",
        description="Polygonized subcatchment extents with original Topaz identifiers.",
        units="planar coordinates (EPSG of the DEM)",
        tool="`polygonize_subcatchments` utility.",
        inputs=("subwta.tif",),
    ),
    ResourceDefinition(
        filename="subcatchments.geojson",
        summary="Subcatchment polygons (WEPP IDs).",
        description="Subcatchments filtered to hillslopes and annotated with WEPP identifiers.",
        units="planar coordinates (EPSG of the DEM)",
        tool="`polygonize_subcatchments` utility with `WeppTopTranslator` mapping.",
        inputs=("subwta.geojson",),
    ),
    ResourceDefinition(
        filename="subcatchments.WGS.geojson",
        summary="Subcatchment polygons (WGS84).",
        description="Reprojected copy of `subcatchments.geojson` for web use.",
        units="degrees (EPSG:4326)",
        tool="`json_to_wgs` utility.",
        inputs=("subcatchments.geojson",),
    ),
    ResourceDefinition(
        filename="channels.geojson",
        summary="Channel centerlines (project CRS).",
        description="Channel geometries annotated with WEPP IDs and stream order.",
        units="planar coordinates (EPSG of the DEM)",
        tool="`_polygonize_channels` helper (GDAL) with `WeppTopTranslator`.",
        inputs=("subwta.geojson", "netw.tsv"),
    ),
    ResourceDefinition(
        filename="channels.WGS.geojson",
        summary="Channel centerlines (WGS84).",
        description="Reprojected channel geometries for web and mapping clients.",
        units="degrees (EPSG:4326)",
        tool="`json_to_wgs` utility.",
        inputs=("channels.geojson",),
    ),
]


def _format_timestamp(path: Path) -> str:
    """Return the file modification time formatted as an ISO-8601 string."""
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


def _format_context(context: Mapping[str, object]) -> List[str]:
    """Render context key/value pairs as Markdown bullet points."""
    lines: List[str] = []
    for key in sorted(context):
        value = context[key]
        if value is None:
            continue
        if isinstance(value, float):
            display = f"{value:g}"
        else:
            display = str(value)
        lines.append(f"- {key}: {display}")
    return lines


def _format_resource(defn: ResourceDefinition, path: Path) -> str:
    """Produce a Markdown section documenting the specified resource."""
    lines = [
        f"### `{defn.filename}`",
        defn.summary,
        "",
        defn.description,
        "",
        f"- Units: {defn.units}",
        f"- Generated by: {defn.tool}",
        f"- Created: {_format_timestamp(path)}",
    ]
    if defn.notes:
        lines.append(f"- Notes: {defn.notes}")
    lines.append("")  # terminating blank line
    return "\n".join(lines)


def _tool_label(tool: str) -> str:
    """Summarise the WhiteboxTools command names used to generate an artifact."""
    codes = re.findall(r"`([^`]*)`", tool)
    if codes:
        label = " / ".join(codes)
    else:
        label = tool
    label = label.replace("WhiteboxTools", "").strip(" .")
    label = label.replace("`", "")
    label = re.sub(r"\s+", " ", label)
    return label


def _node_id(name: str) -> str:
    """Generate a stable GraphViz node identifier from a filename."""
    identifier = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_")
    if not identifier:
        identifier = "node"
    return f"node_{identifier}"


def _build_dependency_graph(existing_files: Dict[str, Path]) -> Tuple[
    Dict[str, str],
    Dict[str, List[tuple[str, str]]],
    Dict[str, int],
    Dict[str, tuple[str, ...]],
    Dict[str, str],
]:
    """Construct dependency graph structures for the available resources."""
    existing = set(existing_files)
    nodes: Dict[str, str] = {}
    label_to_node: Dict[str, str] = {}
    resource_inputs: Dict[str, tuple[str, ...]] = {}
    adjacency: Dict[str, List[tuple[str, str]]] = {}
    indegree: Dict[str, int] = {}
    node_keys: Dict[str, str] = {}
    filtered_defs: List[ResourceDefinition] = []

    for defn in RESOURCE_SEQUENCE:
        if defn.filename not in existing:
            continue

        filtered_defs.append(defn)
        target_id = _node_id(defn.filename)
        nodes[target_id] = defn.filename
        label_to_node[defn.filename] = target_id
        resource_inputs[defn.filename] = defn.inputs
        node_keys[target_id] = defn.filename

        for input_name in defn.inputs:
            if input_name in STATIC_INPUTS:
                node_id = _node_id(input_name)
                nodes.setdefault(node_id, STATIC_INPUTS[input_name])
                label_to_node.setdefault(input_name, node_id)
                node_keys.setdefault(node_id, input_name)
            elif input_name in existing:
                existing_id = label_to_node.get(input_name)
                if existing_id is None:
                    node_id = _node_id(input_name)
                    nodes.setdefault(node_id, input_name)
                    label_to_node[input_name] = node_id
                    node_keys[node_id] = input_name
                else:
                    node_id = existing_id
                    node_keys.setdefault(node_id, input_name)
            else:
                continue

    for node_id in nodes:
        adjacency.setdefault(node_id, [])

    for defn in filtered_defs:
        target_id = label_to_node[defn.filename]
        for input_name in defn.inputs:
            if input_name in STATIC_INPUTS:
                source_id = label_to_node[input_name]
            elif input_name in existing:
                existing_source = label_to_node.get(input_name)
                if existing_source is None:
                    continue
                source_id = existing_source
            else:
                continue

            tool_label = _tool_label(defn.tool)
            adjacency[source_id].append((target_id, tool_label))
            indegree[target_id] = indegree.get(target_id, 0) + 1

    return nodes, adjacency, indegree, resource_inputs, node_keys


def _ascii_dependency_tree(existing_files: Dict[str, Path]) -> str:
    """Render an ASCII tree describing resource dependencies."""
    nodes, adjacency, indegree, resource_inputs, node_keys = _build_dependency_graph(existing_files)

    if not any(adjacency.values()):
        return ""

    roots = [node_id for node_id in nodes if indegree.get(node_id, 0) == 0]
    if not roots:
        roots = list(nodes.keys())
    roots.sort(key=lambda node_id: nodes[node_id])

    lines: List[str] = ["## Dependency Tree", "```text"]
    rendered: set[str] = set()

    def format_extras(target_key: str, source_key: str) -> str:
        inputs = resource_inputs.get(target_key, ())
        extras: List[str] = []
        for name in inputs:
            if name == source_key:
                continue
            if name in STATIC_INPUTS:
                extras.append(STATIC_INPUTS[name])
            else:
                extras.append(name)
        extras = sorted(set(extras))
        if extras:
            return f" [also uses: {', '.join(extras)}]"
        return ""

    def walk(node_id: str, prefix: str):
        children = sorted(adjacency.get(node_id, []), key=lambda item: nodes[item[0]])
        for idx, (child_id, tool_label) in enumerate(children):
            connector = "└─" if idx == len(children) - 1 else "├─"
            line = f"{prefix}{connector} {nodes[child_id]}"

            if tool_label:
                line += f"  ({tool_label})"

            child_key = node_keys.get(child_id, nodes[child_id])
            source_key = node_keys.get(node_id, nodes[node_id])
            line += format_extras(child_key, source_key)

            if child_id in rendered:
                line += " [see above]"
                lines.append(line)
                continue

            lines.append(line)
            rendered.add(child_id)

            next_prefix = prefix + ("   " if idx == len(children) - 1 else "│  ")
            walk(child_id, next_prefix)

    for root in roots:
        label = nodes[root]
        if root not in rendered:
            lines.append(label)
            rendered.add(root)
            walk(root, "")

    lines.append("```")
    return "\n".join(lines)


def generate_wbt_documentation(
    workspace: Path | str,
    *,
    context: Optional[Mapping[str, object]] = None,
    to_readme_md: bool = True,
    readme_name: str = "README.md",
) -> str:
    """
    Build Markdown documentation for a WhiteboxTools working directory.

    Parameters
    ----------
    workspace : Path or str
        Directory containing WhiteboxTools outputs (``wbt_wd``).
    context : Mapping[str, object], optional
        Additional key/value metadata to include (e.g., DEM path, EPSG, CSA).
    to_readme_md : bool, default True
        When True, write the Markdown to ``readme_name`` within ``workspace``.
    readme_name : str, default "README.md"
        Filename for the generated documentation.

    Returns
    -------
    str
        The Markdown content that was generated.
    """
    base = Path(workspace)
    if not base.exists():
        raise FileNotFoundError(base)

    existing_files: Dict[str, Path] = {
        path.name: path for path in base.iterdir() if path.is_file()
    }

    dependency_tree = _ascii_dependency_tree(existing_files)

    sections: List[str] = ["# WhiteboxTools Workspace Documentation", ""]

    if dependency_tree:
        sections.extend([dependency_tree, ""])

    sections.extend(
        [
            f"- Workspace: `{base}`",
            f"- Documentation generated: {datetime.now(tz=timezone.utc).isoformat().replace('+00:00', 'Z')}",
            "",
        ]
    )

    if context:
        context_lines = _format_context(context)
        if context_lines:
            sections.extend(
                [
                    "## Workspace Context",
                    "",
                    *context_lines,
                    "",
                ]
            )

    sections.extend(["## Workflow Artifacts", ""])

    documented: List[str] = []
    for defn in RESOURCE_SEQUENCE:
        path = existing_files.get(defn.filename)
        if path is None:
            continue
        sections.append(_format_resource(defn, path))
        documented.append(defn.filename)

    undocumented = sorted(
        name for name in existing_files if name not in documented
    )
    if undocumented:
        sections.extend(
            [
                "## Additional Files",
                "",
                "The following files are present but not part of the standard workflow:",
                "",
            ]
        )
        sections.extend(f"- `{name}`" for name in undocumented)
        sections.append("")

    markdown = "\n".join(sections).rstrip() + "\n"

    if to_readme_md:
        readme_path = base / readme_name
        readme_path.write_text(markdown)

    return markdown
