"""Data-only Open Terrain Format bridge; never loads serialized CLR types."""

import json
import math
import re
from pathlib import Path

from .terrain import digest, template


def _document(source):
    document = json.loads(source.read_text(encoding="utf-8-sig"))
    assets = document.get("Assets", {}).get("$values", [])
    if not assets or not all(
        isinstance(a.get("Terrain", {}).get("Nodes"), dict) for a in assets
    ):
        raise ValueError("Unsupported Open Terrain Format shape")
    return document, assets


def inspect_graph(template_id):
    _, _, source = template(template_id)
    _, assets = _document(source)
    terrains = []
    for asset in assets:
        terrain = asset["Terrain"]
        nodes = []
        for key, node in terrain["Nodes"].items():
            if key.startswith("$"):
                continue
            if not isinstance(node, dict):
                raise TypeError("Unsupported node record")
            nodes.append(
                {
                    "id": key,
                    "type": node.get("$type"),
                    "name": node.get("Name"),
                    "parameters": {
                        k: v
                        for k, v in node.items()
                        if not k.startswith("$") and type(v) in (int, float, bool, str)
                    },
                    "ports": node.get("Ports", {}),
                }
            )
        terrains.append(
            {
                "id": terrain.get("Id"),
                "metadata": terrain.get("Metadata", {}),
                "nodes": nodes,
            }
        )
    return {
        "success": True,
        "source_sha256": digest(source),
        "terrains": terrains,
        "engine_validated": False,
        "transport": "open_terrain_format",
    }


def prepare_graph(template_id, terrain_id, node_id, parameters, output_name):
    """Edit pre-existing numeric fields authorized by operator config into a new copy."""
    _, entry, source = template(template_id)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.terrain", output_name):
        raise ValueError("Invalid output filename")
    if not parameters or not isinstance(parameters, dict):
        raise ValueError("Nonempty parameters required")
    document, assets = _document(source)
    matches = [a["Terrain"] for a in assets if a["Terrain"].get("Id") == terrain_id]
    if len(matches) != 1:
        raise ValueError("Unknown or ambiguous terrain")
    node = matches[0]["Nodes"].get(str(node_id))
    if not isinstance(node, dict):
        raise TypeError("Unknown node")
    allowed = (
        entry.get("graph_parameters", {}).get(terrain_id, {}).get(str(node_id), {})
    )
    for name, value in parameters.items():
        bounds = allowed.get(name)
        previous = node.get(name)
        if name.startswith("$") or bounds is None or type(previous) not in (int, float):
            raise ValueError("Parameter is not an authorized numeric field")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Parameter must be finite numeric data")
        if type(previous) is int and type(value) is not int:
            raise ValueError("Integer parameter requires an integer")
        if not bounds["minimum"] <= value <= bounds["maximum"]:
            raise ValueError("Parameter out of configured bounds")
        node[name] = value
    root = Path(entry["prepared_directory"]).resolve(strict=True)
    destination = root / output_name
    payload = json.dumps(
        document, indent=2, ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    with destination.open("xb") as stream:
        stream.write(payload)
    readback, _ = _document(destination)
    if readback != document:
        raise RuntimeError("Prepared graph readback mismatch")
    return {
        "success": True,
        "output": str(destination),
        "sha256": digest(destination),
        "source_sha256": digest(source),
        "engine_validated": False,
        "transport": "open_terrain_format",
        "changed_parameters": list(parameters),
    }
