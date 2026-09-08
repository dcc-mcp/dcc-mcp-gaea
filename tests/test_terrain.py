import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from dcc_mcp_gaea import terrain


@pytest.fixture
def configured(tmp_path, monkeypatch):
    source = tmp_path / "coast.terrain"
    source.write_text("fixture, not a Gaea graph")
    exe = tmp_path / "Gaea.Swarm.exe"
    exe.write_bytes(b"fixture executable, never launched")
    output = tmp_path / "output"
    output.mkdir()
    config = {
        "schema_version": 1,
        "swarm_executable": str(exe),
        "swarm_sha256": terrain.digest(exe),
        "templates": {
            "coast": {
                "terrain": str(source),
                "sha256": terrain.digest(source),
                "variables": {"erosion": {"minimum": 0, "maximum": 1}},
                "profiles": ["preview"],
                "regions": ["beach"],
                "output_directory": str(output),
                "terrain_extent_m": [1000, 1000, 100],
                "outputs": [{"file": "height.png", "role": "height", "size": [16, 16]}],
            }
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("DCC_MCP_GAEA_CONFIG", str(path))
    return config, path, output


def write_height(output):
    Image.new("I;16", (16, 16), 100).save(output / "height.png")


def test_command_is_argv_and_variables_last(configured):
    result = terrain.plan_build("coast", {"erosion": 0.5}, 12, "preview", "beach")
    assert result["command"][-2:] == ["-v", "erosion=0.5"]
    assert result["executed"] is False
    assert "--profile" in result["command"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"seed": True},
        {"seed": 2**31},
        {"profile": "missing"},
        {"region": "missing"},
        {"variables": {"missing": 1}},
        {"variables": {"erosion": float("nan")}},
        {"variables": {"erosion": "--activate"}},
        {"variables": {"erosion": 2}},
    ],
)
def test_bad_overrides_rejected(configured, arguments):
    with pytest.raises(ValueError):
        terrain.plan_build("coast", **arguments)


def test_changed_template_rejected(configured):
    config, _, _ = configured
    Path(config["templates"]["coast"]["terrain"]).write_text("changed")
    with pytest.raises(ValueError, match="identity"):
        terrain.plan_build("coast")


def test_output_receipt(configured):
    _, _, output = configured
    write_height(output)
    result = terrain.verify_outputs("coast")
    assert result["outputs"][0]["sha256"] == terrain.digest(output / "height.png")
    assert result["unreal_import_verified"] is False


def test_rgb_height_rejected(configured):
    _, _, output = configured
    Image.new("RGB", (16, 16)).save(output / "height.png")
    with pytest.raises(ValueError, match="16-bit"):
        terrain.verify_outputs("coast")


def test_traversal_rejected(configured):
    config, path, _ = configured
    config["templates"]["coast"]["outputs"][0]["file"] = "../height.png"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="escapes"):
        terrain.verify_outputs("coast")


def test_stale_output_never_launches(configured, monkeypatch):
    _, _, output = configured
    write_height(output)
    launch = Mock()
    monkeypatch.setattr(terrain.subprocess, "Popen", launch)
    with pytest.raises(ValueError, match="already exist"):
        terrain.build_terrain("coast")
    launch.assert_not_called()
    assert not (output / ".dcc-mcp-gaea-build.lock").exists()


def test_build_success_requires_outputs(configured, monkeypatch):
    _, _, output = configured
    process = Mock(returncode=0)
    process.poll.return_value = 0

    def launch(*args, **kwargs):
        assert kwargs["shell"] is False
        write_height(output)
        return process

    monkeypatch.setattr(terrain.subprocess, "Popen", launch)
    assert terrain.build_terrain("coast")["exit_code"] == 0


def test_core_cancel_terminates_owned_child(configured, monkeypatch):
    import dcc_mcp_core

    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(terrain.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(
        dcc_mcp_core,
        "check_cancelled",
        Mock(side_effect=[None, RuntimeError("cancelled")]),
    )
    with pytest.raises(RuntimeError, match="cancelled"):
        terrain.build_terrain("coast")
    process.terminate.assert_called_once()
    process.wait.assert_called_once()


def test_concurrent_build_refused(configured):
    _, _, output = configured
    lock = output / ".dcc-mcp-gaea-build.lock"
    lock.write_text("other owner")
    with pytest.raises(FileExistsError):
        terrain.build_terrain("coast")
    assert lock.read_text() == "other owner"


def test_skill_validation_and_server_construction(monkeypatch):
    from dcc_mcp_core import validate_skill

    from dcc_mcp_gaea.server import GaeaMcpServer

    monkeypatch.setenv("DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS", "1")
    skill = Path(terrain.__file__).parent / "skills" / "gaea-terrain"
    report = validate_skill(str(skill))
    assert not report.has_errors, str(report)
    server = GaeaMcpServer(port=0)
    assert server._version_string() == "unknown"
