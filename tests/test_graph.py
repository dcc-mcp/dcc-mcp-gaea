import json

import pytest

from dcc_mcp_gaea import graph, terrain


@pytest.fixture
def config(tmp_path, monkeypatch):
    doc = {
        "Assets": {
            "$values": [
                {
                    "Terrain": {
                        "Id": "t",
                        "Nodes": {
                            "$id": "6",
                            "1": {
                                "$type": "Example.Mountain",
                                "Seed": 3,
                                "Height": 1.0,
                                "Ports": {"$values": []},
                                "Unknown": {"$ref": "x"},
                            },
                        },
                    }
                }
            ]
        }
    }
    source = tmp_path / "source.terrain"
    source.write_text(json.dumps(doc))
    entry = {
        "terrain": str(source),
        "sha256": terrain.digest(source),
        "prepared_directory": str(tmp_path),
        "graph_parameters": {"t": {"1": {"Seed": {"minimum": 0, "maximum": 99}}}},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"schema_version": 1, "templates": {"test": entry}}))
    monkeypatch.setenv("DCC_MCP_GAEA_CONFIG", str(path))
    return source, doc


def test_inspect_and_prepare_preserve_native_unknown_data(config):
    source, doc = config
    assert (
        graph.inspect_graph("test")["terrains"][0]["nodes"][0]["parameters"]["Seed"]
        == 3
    )
    result = graph.prepare_graph("test", "t", "1", {"Seed": 5}, "new.terrain")
    assert result["engine_validated"] is False
    updated = json.loads(source.with_name("new.terrain").read_text())
    doc["Assets"]["$values"][0]["Terrain"]["Nodes"]["1"]["Seed"] = 5
    assert updated == doc
    assert (
        json.loads(source.read_text())["Assets"]["$values"][0]["Terrain"]["Nodes"]["1"][
            "Seed"
        ]
        == 3
    )
    with pytest.raises(FileExistsError):
        graph.prepare_graph("test", "t", "1", {"Seed": 5}, "new.terrain")


@pytest.mark.parametrize(
    "values",
    [
        {"Seed": 100},
        {"Seed": True},
        {"Seed": 1.2},
        {"Seed": float("nan")},
        {"Height": 2},
        {"$type": 1},
    ],
)
def test_reject_unauthorized_edit(config, values):
    with pytest.raises(ValueError):
        graph.prepare_graph("test", "t", "1", values, "new.terrain")


def test_reject_traversal(config):
    with pytest.raises(ValueError):
        graph.prepare_graph("test", "t", "1", {"Seed": 5}, "../new.terrain")
