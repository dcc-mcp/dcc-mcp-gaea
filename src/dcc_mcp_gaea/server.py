"""Standalone build coordinator using Core registration and job lifecycle."""

import signal
import threading
from pathlib import Path

from dcc_mcp_core import DccServerOptions, MinimalModeConfig
from dcc_mcp_core.server_base import DccServerBase


class GaeaMcpServer(DccServerBase):
    def __init__(self, **kwargs):
        super().__init__(
            options=DccServerOptions.from_env(
                "gaea",
                Path(__file__).parent / "skills",
                server_name="dcc-mcp-gaea",
                server_version="0.1.0",
                adapter_version="0.1.0",
                instance_type="standalone",
                **kwargs,
            )
        )

    def _version_string(self):
        return "unknown"


def main():
    stopped = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    server = GaeaMcpServer()
    server.register_builtin_actions(
        minimal_mode=MinimalModeConfig(skills=("gaea-terrain",))
    )
    server.start()
    try:
        stopped.wait()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
