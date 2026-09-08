# dcc-mcp-gaea

Typed Gaea Build Swarm integration for DCC-MCP. Initial implementation; **real Gaea builds and Unreal imports have not yet been validated**.

## Scope

Four tools inspect operator-registered templates, plan supported CLI arguments, execute a bounded build, and verify exported height/weight images with dimensions and SHA-256 receipts. Builds use Core deferred jobs rather than a second job database. The service is standalone; it does not attach to an unrelated Gaea GUI process.

Supported overrides: exposed **numeric** variables with declared bounds, mutation seed, configured profile, configured region, and cache bypass. No arbitrary shell commands, activation, private graph edits, downloads or purchases are exposed.

## Configure and run

Install this package in a project environment, then set `DCC_MCP_GAEA_CONFIG` to an operator-owned JSON file matching `examples/config.example.json`. Supply an installed `Gaea.Swarm.exe` and a terrain graph previously built and audited in Gaea. Hashes bind the exact executable and template. Review the graph's output paths and post-build script before registering it; hashing does not establish trust in third-party graphs.

Run `dcc-mcp-gaea`, then discover `gaea-terrain` through `dcc-mcp-cli search`. Load the skill, inspect templates, plan the command, and invoke `build_terrain`. Use the shared Core job status/cancellation interface. No port or GUI PID is hardcoded.

Outputs must be absent before execution. This avoids overwriting or accepting stale files. Repeated runs need a separately audited template/output directory; the adapter does not invent an undocumented output-directory switch or rewrite terrain graphs. Interrupted builds can leave partial outputs; reconcile those manually. A stale lock after process loss also requires operator reconciliation.

## Unreal handoff

Use the verified heightmap, weightmap receipts and configured physical extents with an isolated Unreal project. The physical extent is an operator declaration, not a measurement of exported metadata. This initial adapter supports image verification, not automatic parsing of Gaea2Unreal metadata. Verify axis orientation, Landscape resolution, vertical scale, material layers, tile seams and save/reopen before declaring terrain accepted. There is no licensed coast template bundled in this repository.

## Validation and known gaps

Run `python -m pytest` and `ruff check src tests`. Tests use synthetic image fixtures and mocked child processes. Core schema validation and server construction use the actual public Core package. They do not prove license availability, host CLI compatibility, terrain quality, actual gateway cancellation propagation, or UE integration.

Cancellation/timeout terminates and waits for the directly owned Swarm process. Whether Swarm worker descendants survive cancellation needs real-host validation; do not claim full process-tree cancellation. Large-world tiled builds, arbitrary graph authoring, automatic metadata extraction and direct UE import are follow-up work. Core remains unchanged.

## Official contracts

- [Automation](https://docs.gaea.app/developers/automation/index.html)
- [CLI reference](https://docs.gaea.app/developers/automation/cli/index.html)
- [Variable overrides](https://docs.gaea.app/developers/automation/cli/command-line-automation.html)
- [Gaea2Unreal](https://docs.gaea.app/guides/use-in/bridges/gaea2unreal/index.html)

Gaea is a QuadSpinner product. This independent adapter does not bundle Gaea, its license or vendor artwork.
