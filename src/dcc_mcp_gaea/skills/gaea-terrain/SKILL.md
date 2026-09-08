---
name: gaea-terrain
description: Inspect audited Gaea templates, build terrain through Swarm, and verify Unreal heightmap handoff.
metadata:
  dcc-mcp:
    dcc: gaea
    version: "0.1.0"
    tools: tools.yaml
---
# Gaea terrain workflow
Inspect templates, plan exposed numeric variable overrides, then build. Use Core job status and cancellation for deferred builds. Verify output receipts before Unreal import. The operator must supply an audited known-good terrain template, including its configured outputs and any post-build scripts. No arbitrary graph editing, activation, or script execution tool is provided. Source extent is declared, not measured. A successful build does not prove Unreal import or terrain visual quality. Cancellation terminates only the owned Swarm process; worker-tree termination and live host cancellation remain acceptance gates.

Native file route: use `inspect_graph` to discover actual terrain and node IDs, then `prepare_graph` for operator-allowlisted numeric edits into a new copy. Preserve the original and require engine validation before accepting a prepared graph. This route does not use UI clicks. Community workflows can prepare files and verify user-built outputs; do not invoke headless automation without Professional/Enterprise entitlement. Never interpret the editor edition label as license verification.
