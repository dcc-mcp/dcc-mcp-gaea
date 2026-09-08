"""Actual Core HTTP transport; no Gaea binary or license is simulated here."""

import json
import urllib.request

from dcc_mcp_core import MinimalModeConfig

from dcc_mcp_gaea.server import GaeaMcpServer
from dcc_mcp_gaea.terrain import digest


def test_http_discovery_and_typed_inspection(tmp_path, monkeypatch):
    source = tmp_path / "test.terrain"
    source.write_text(
        json.dumps(
            {
                "Assets": {
                    "$values": [{"Terrain": {"Id": "t", "Nodes": {"1": {"Seed": 3}}}}]
                }
            }
        )
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "swarm_executable": str(tmp_path / "missing.exe"),
                "templates": {
                    "test": {"terrain": str(source), "sha256": digest(source)}
                },
            }
        )
    )
    monkeypatch.setenv("DCC_MCP_GAEA_CONFIG", str(config))
    monkeypatch.setenv("DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS", "1")
    server = GaeaMcpServer(
        port=0,
        registry_dir=str(tmp_path / "registry"),
        enable_gateway_failover=False,
        enable_telemetry=False,
    )
    server.register_builtin_actions(
        minimal_mode=MinimalModeConfig(skills=("gaea-terrain",))
    )

    def request(method, params):
        req = urllib.request.Request(
            server.mcp_url,
            data=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read())
        assert "error" not in result, result
        return result["result"]

    try:
        server.start()
        names = set()
        params = {}
        for _ in range(20):
            page = request("tools/list", params)
            names.update(tool["name"] for tool in page["tools"])
            if not page.get("nextCursor"):
                break
            params = {"cursor": page["nextCursor"]}
        assert {
            "inspect_templates",
            "inspect_graph",
            "prepare_graph",
            "plan_build",
            "build_terrain",
            "verify_outputs",
        } <= names
        result = request("tools/call", {"name": "inspect_templates", "arguments": {}})
        assert not result.get("isError"), result
        payload = json.loads(
            next(item["text"] for item in result["content"] if item["type"] == "text")
        )
        assert payload["context"]["runtime_available"] is False
        assert payload["context"]["license_status"] == "not_verified"
        graph_result = request(
            "tools/call",
            {"name": "inspect_graph", "arguments": {"template_id": "test"}},
        )
        assert not graph_result.get("isError"), graph_result
        graph_payload = json.loads(
            next(
                item["text"]
                for item in graph_result["content"]
                if item["type"] == "text"
            )
        )
        assert (
            graph_payload["context"]["terrains"][0]["nodes"][0]["parameters"]["Seed"]
            == 3
        )
        assert graph_payload["context"]["engine_validated"] is False
    finally:
        server.stop()
