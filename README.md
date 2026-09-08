# dcc-mcp-gaea

Typed Gaea Build Swarm integration for DCC-MCP. Initial implementation; **real Gaea builds and Unreal imports have not yet been validated**.

## Scope

Six tools inspect operator-registered templates, plan supported CLI arguments, execute a bounded build, and verify exported height/weight images with dimensions and SHA-256 receipts. Builds use Core deferred jobs rather than a second job database. The service is standalone; it does not attach to an unrelated Gaea GUI process.

Supported overrides: exposed **numeric** variables with declared bounds, mutation seed, configured profile, configured region, and cache bypass. No arbitrary shell commands, activation, arbitrary graph edits, downloads or purchases are exposed.

## Configure and run

Install this package in a project environment, then set `DCC_MCP_GAEA_CONFIG` to an operator-owned JSON file matching `examples/config.example.json`. Supply an installed `Gaea.Swarm.exe` and a terrain graph previously built and audited in Gaea. Hashes bind the exact executable and template. Review the graph's output paths and post-build script before registering it; hashing does not establish trust in third-party graphs.

Run `dcc-mcp-gaea`, then discover `gaea-terrain` through `dcc-mcp-cli search`. Load the skill, inspect templates, plan the command, and invoke `build_terrain`. Use the shared Core job status/cancellation interface. No port or GUI PID is hardcoded.

Outputs must be absent before execution. This avoids overwriting or accepting stale files. Interrupted builds can leave partial outputs; reconcile those manually. A stale lock after process loss also requires operator reconciliation.

Installed Swarm 2.2.9.0 and 2.3.0.1 advertise `--buildpath`, `--resolution` and `--silent` in their own help. After verifying the exact executable, the operator can enable the corresponding booleans in configuration `native_cli`. The adapter then supplies the configured output directory and optional per-template integer `resolution`; the build planner never rewrites the graph. Older configurations retain their previous argument list. Output resolution is verified after the build, not assumed supported merely because the CLI accepted a number.

## Unreal handoff

Use the verified heightmap, weightmap receipts and configured physical extents with an isolated Unreal project. The physical extent is an operator declaration, not a measurement of exported metadata. This initial adapter supports image verification, not automatic parsing of Gaea2Unreal metadata. Verify axis orientation, Landscape resolution, vertical scale, material layers, tile seams and save/reopen before declaring terrain accepted. There is no licensed coast template bundled in this repository.

## Validation and known gaps

Run `python -m pytest` and `ruff check src tests`. Tests use synthetic image fixtures and mocked child processes. Core schema validation and server construction use the actual public Core package. They do not prove license availability, host CLI compatibility, terrain quality, actual gateway cancellation propagation, or UE integration.

Cancellation/timeout terminates and waits for the directly owned Swarm process. Whether Swarm worker descendants survive cancellation needs real-host validation; do not claim full process-tree cancellation. Large-world tiled builds, arbitrary graph authoring, automatic metadata extraction and direct UE import are follow-up work. Core remains unchanged.

Native probes found that bundled example graphs may have no nodes marked for export. Swarm 2.2.9.0 reports this clearly in a real console, but its no-console error path can instead fail with an invalid-handle exception. `--silent` did not suppress that console-dependent error prompt. Configure export nodes in Gaea before automation; neither a zero exit code nor an empty output directory counts as a successful build. Licensed production builds remain an outstanding acceptance gate.

## Official contracts

- [Automation](https://docs.gaea.app/developers/automation/index.html)
- [CLI reference](https://docs.gaea.app/developers/automation/cli/index.html)
- [Variable overrides](https://docs.gaea.app/developers/automation/cli/command-line-automation.html)
- [Gaea2Unreal](https://docs.gaea.app/guides/use-in/bridges/gaea2unreal/index.html)

Gaea is a QuadSpinner product. This independent adapter does not bundle Gaea, its license or vendor artwork.

## Native graph file bridge

`inspect_graph(template_id)` reads native Open Terrain Format terrain/node records, scalar parameters and ports. `prepare_graph(template_id, terrain_id, node_id, parameters, output_name)` writes a new graph copy and verifies JSON readback and SHA-256. Existing unknown fields and CLR type labels are preserved as data; no CLR types are loaded. Only existing numeric fields explicitly authorized in operator configuration can change. The output filename cannot contain directories and existing files are never overwritten.

Each template may configure `prepared_directory` (an existing directory) and `graph_parameters`, indexed by terrain ID, node ID, then parameter name with `minimum`/`maximum` bounds. Inspect the graph first to obtain actual IDs; do not invent node schemas. Prepared files require engine validation and explicit registration before builds. `engine_validated: false` is intentional: JSON readback does not prove Gaea accepts or evaluates the graph.

A local Gaea 2.2.9.0 bundled snow graph was read (six nodes), its existing Mountain Seed changed in a separate copy, and every other JSON field preserved. This proves native file-contract operation, not engine output. The installed application targets .NET 8/WPF; internal Engine/Nodes/Server DLL names are not a documented public plugin API. No in-process SDK or hook is claimed.

Community Edition supports free non-commercial work and exports up to 1024 squared according to the [official download page](https://www.quadspinner.com/Download). The [vendor forum clarification](https://talk.gaea.app/t/gaea-3-cli-headless-automation-what-should-third-party-tooling-plan-for/1883) allows Open Terrain Format preparation across license levels, while headless Swarm automation requires Professional or Enterprise. Use graph preparation and output verification with a locally performed build when automation is not licensed. The adapter does not activate, unlock, or infer entitlement from an editor label. Current host evidence is not proof of Community build acceptance.
