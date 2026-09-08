"""Official Swarm file/CLI contract; no private graph rewriting or shell tools."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def configuration():
    """Only the operator's environment supplies executable and template roots."""
    path = os.environ.get("DCC_MCP_GAEA_CONFIG")
    if not path:
        raise ValueError("DCC_MCP_GAEA_CONFIG is not configured")
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported configuration schema")
    return config


def template(template_id):
    config = configuration()
    entry = config["templates"][template_id]
    source = Path(entry["terrain"]).resolve(strict=True)
    if source.suffix.lower() != ".terrain" or digest(source) != entry["sha256"]:
        raise ValueError("Template identity changed or extension is invalid")
    return config, entry, source


def inspect_templates():
    config = configuration()
    return {
        "success": True,
        "templates": [
            {
                "id": key,
                "variables": value.get("variables", {}),
                "profiles": value.get("profiles", []),
                "regions": value.get("regions", []),
            }
            for key, value in config["templates"].items()
        ],
        "runtime_available": Path(config["swarm_executable"]).is_file(),
        "license_status": "not_verified",
        "graph_authoring": False,
    }


def plan_build(
    template_id, variables=None, seed=0, profile="", region="", ignore_cache=True
):
    config, entry, source = template(template_id)
    if type(seed) is not int or not -(2**31) <= seed < 2**31:
        raise ValueError("Seed must be an int32")
    if type(ignore_cache) is not bool:
        raise ValueError("ignore_cache must be boolean")
    command = [
        str(config["swarm_executable"]),
        "--Filename",
        str(source),
        "--seed",
        str(seed),
    ]
    # Enable only after checking the installed Swarm's own --help output.
    # These switches are available in 2.3.0.1 but absent in older web docs.
    native_cli = config.get("native_cli", {})
    if native_cli.get("buildpath") is True:
        command.extend(["--buildpath", str(Path(entry["output_directory"]).resolve())])
    if native_cli.get("silent") is True:
        command.append("--silent")
    if "resolution" in entry:
        resolution = entry["resolution"]
        if native_cli.get("resolution") is not True:
            raise ValueError("Resolution override is not verified for this Swarm")
        if type(resolution) is not int or not 16 <= resolution <= 65536:
            raise ValueError("Resolution must be an integer from 16 to 65536")
        command.extend(["--resolution", str(resolution)])
    for selection, allowed, flag in (
        (profile, "profiles", "--profile"),
        (region, "regions", "--region"),
    ):
        if selection:
            if selection not in entry.get(allowed, []):
                raise ValueError("Unknown " + allowed)
            command.extend([flag, selection])
    if ignore_cache:
        command.append("--ignorecache")
    variables = variables or {}
    if not isinstance(variables, dict):
        raise TypeError("variables must be an object")
    for key, value in sorted(variables.items()):
        spec = entry.get("variables", {}).get(key)
        if spec is None or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
            raise ValueError("Unknown or invalid exposed variable")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Only finite numeric exposed variables are supported")
        if value < spec["minimum"] or value > spec["maximum"]:
            raise ValueError("Variable outside configured bounds")
        command.extend(["-v", f"{key}={value}"])
    return {
        "success": True,
        "command": command,
        "template_sha256": entry["sha256"],
        "output_directory": entry["output_directory"],
        "executed": False,
    }


def output_paths(entry):
    root = Path(entry["output_directory"]).resolve(strict=True)
    files = []
    for item in entry["outputs"]:
        path = (root / item["file"]).resolve()
        if root not in path.parents:
            raise ValueError("Output escapes configured directory")
        files.append((path, item))
    if not files or not any(item["role"] == "height" for _, item in files):
        raise ValueError("A height output is required")
    return root, files


def verify_outputs(template_id):
    from PIL import Image

    _, entry, _ = template(template_id)
    _, paths = output_paths(entry)
    result = []
    for path, spec in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("Expected output missing: " + path.name)
        if spec["role"] not in ("height", "weight"):
            raise ValueError("Unsupported output role")
        if spec["role"] == "height":
            with path.open("rb") as stream:
                header = stream.read(26)
            if (
                header[:8] != b"\x89PNG\r\n\x1a\n"
                or len(header) != 26
                or header[24:26] != bytes([16, 0])
            ):
                raise ValueError("Height output must be a 16-bit grayscale PNG")
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            img.load()
            if list(img.size) != spec["size"]:
                raise ValueError("Output dimensions do not match contract")
            if spec["role"] == "height" and img.mode not in (
                "I",
                "I;16",
                "I;16L",
                "I;16B",
            ):
                raise ValueError("Height output must be a 16-bit integer image")
            mode = img.mode
        result.append(
            {
                "file": str(path),
                "role": spec["role"],
                "size": spec["size"],
                "mode": mode,
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    return {
        "success": True,
        "outputs": result,
        "terrain_extent_m": entry["terrain_extent_m"],
        "extent_provenance": "operator_template_contract_not_measured",
        "unreal_import_verified": False,
    }


def build_terrain(
    template_id,
    variables=None,
    seed=0,
    profile="",
    region="",
    ignore_cache=True,
    timeout_seconds=600,
):
    """Core owns deferred job status/cancel. This call owns only its child handle."""
    from dcc_mcp_core import check_cancelled

    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError("Timeout must be 1..3600 seconds")
    plan = plan_build(template_id, variables, seed, profile, region, ignore_cache)
    config, entry, source = template(template_id)
    executable = Path(config["swarm_executable"]).resolve(strict=True)
    if (
        executable.name.lower() != "gaea.swarm.exe"
        or digest(executable) != config["swarm_sha256"]
    ):
        raise ValueError("Swarm executable identity mismatch")
    root, paths = output_paths(entry)
    # Swarm output locations and post-build scripts live in the audited template.
    # Refuse overwrite/stale-success; this adapter never removes existing outputs.
    lock_path = root / ".dcc-mcp-gaea-build.lock"
    with lock_path.open("x") as lock:
        lock.write(
            "Build in progress; process loss requires operator reconciliation.\n"
        )
    process = None
    try:
        if any(path.exists() for path, _ in paths):
            raise ValueError(
                "Outputs already exist; use a fresh template output directory"
            )
        check_cancelled()
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(
                plan["command"],
                cwd=str(source.parent),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            deadline = time.monotonic() + timeout_seconds
            while process.poll() is None:
                check_cancelled()
                if time.monotonic() >= deadline:
                    raise TimeoutError("Gaea build exceeded its time budget")
                time.sleep(0.1)
            if process.returncode:
                raise RuntimeError(
                    f"Gaea build failed with exit code {process.returncode}"
                )
        receipt = verify_outputs(template_id)
        receipt.update({"template_sha256": plan["template_sha256"], "exit_code": 0})
        return receipt
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        lock_path.unlink()
