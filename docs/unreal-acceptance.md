# First real-host acceptance

This is a proposed acceptance contract, not generated terrain or a completed import.

1. Obtain an installed, licensed Gaea Build Swarm and an operator-reviewed coastal `.terrain` graph. Build once in Gaea and record the version, template SHA-256, exported variables, profile and region names. Confirm configured outputs and post-build actions.
2. Prefer a single 1009 by 1009 16-bit grayscale PNG heightmap, with a 1008 m horizontal span (1 m sample spacing). Confirm this resolution is supported by the actual Gaea graph/export profile; do not relabel another resolution.
3. Export sand, rock and vegetation weights as aligned 8-bit grayscale maps. Declare normalization rules and preserve row/column orientation. Use an asymmetric corner/peak to make orientation errors observable.
4. Record horizontal spacing, minimum/maximum elevation, sea-level datum, actor Z, axis conventions, graph/version/hash, build terminal state, and every output SHA-256. The initial adapter returns declared extents and file receipts; it does not yet extract all this information from Gaea's metadata.
5. Import as an actual Landscape with LayerInfo in an isolated Unreal project. A Texture import is not sufficient. Verify the height interpretation against native Unreal measurements, including vertical scale and datum. The planned first host is UE 5.5, followed separately by UE 5.8.
6. Save, close and reopen in a new process; read back dimensions, layer references and physical extents. Capture native views and preserve the project and receipts. Do not modify an unrelated rendering project.

Remaining live gates include worker-process cancellation, exit-code/error semantics, image export metadata, licensing, actual coastal terrain quality, and Landscape import. No capability is considered validated merely because the adapter tests use a synthetic image with the right dimensions.
