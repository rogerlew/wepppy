# Normal active pair and supplemental ledger prereview

Independent completed-trace extraction for normal-ks1 finds 19 actual positive clearings with paired post-clear NWFRZZ zero. Nine appear in the original valid-state ledger; ten were excluded. Valid-state clearing magnitudes range from 4.0017766878e-11 to 0.000168069556821 m. All 1,978 valid G layer occurrences involve exactly zero support (8,149 cells), with no positive thin support. The maximum direction-1 profile residual is +0.000310955595133 m at map 1596; minimum is -0.00000206291163815 m at map 814. Both maps include layer-1 zero-ST reset and finish with zero carry. This is not evidence that the profile residual equals final carry.

Among excluded transfer states, 1,543 before-map coarse ice components and 249 before-map coarse liquid components are negative. No before/after fine liquid or fine ice totals are negative. Component counts need not sum to excluded events. These observations do not demonstrate negative fine ice or establish a universal cause for exclusion.

The separate read_clearing_ownership_v2.py analysis appropriately retains actual paired clear assignments independently of coarse-coordinate validity. It preserves each clearing identity across later mappings, records the first subsequent mapping (including zero-ST branch), and records the next initialization with pre/post stocks. The first next-mapping endpoint is bounded by termination at the next initialization; absence must not imply no mapping ever occurs afterward. Recorded boundaries do not establish causal recovery or an external water budget. Coarse/fine component flags describe reconstructed quantities, not comprehensive physical admissibility of every individual fine cell.

Code inspection and retained supplemental controls support this approach. Actual supplemental receipt comparison remains pending; this document does not claim that those scans have finished. Native execution results and frozen-reader outputs remain unchanged.

## Bindings

- `check_active_v2.py`: `82919a74b13cf80210b8e793724bd9cf347c595eef85dc1d35d1c8f66076a9a4`.
- `receipt.json`: `6d5033576af2797885e3abf582e3d69cc37354927f39f84b67f5a841a7852def`.
- `receipt.json`: `b47ba48c32f011aff9730714cbb49b991ba1e360c8dfedecd0a896bfb8642cfa`.
- `read_clearing_ownership_v2.py`: `988a173bbd7a359ff0625f4d6c180da7b0e9407b448018227320a6076704dcbc`.
