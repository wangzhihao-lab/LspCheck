"""Engine of the functional-oracle tool for language servers (design: plan/tool_design_v1.md).

Modules are imported as top-level modules with scripts/lsptest on sys.path (each
module adds itself and ../lsp_repro), e.g. `from driver import Driver, DriverConfig`:

- model:    fixed data contract (Op, QueryKey, QueryResult, Snapshot, RunConfig, Violation)
- ops:      OpApplier (Ops -> LSP notifications), DocumentStore, LineIndex, inverse_change,
            invert_ops, load_ops/save_ops
- settle:   ProtocolMonitor, PullSettle/PushSettle/AutoSettle, SETTLE_STRATEGIES, strategy_for
- queries:  run_suite, NORMALIZERS, QueryConfig, PathMapper, snapshot_to_json/snapshot_from_json
- targets:  choose_targets, identifiers, diagnostic_ranges, TargetConfig, FileTargets
- driver:   Driver (one isolated live session), DriverConfig, diff_keys, stability
- engine_smoke: validation run of design section 9.1

Run line: not run directly; see engine_smoke.py for an end-to-end example.
"""

__all__ = ["driver", "engine_smoke", "model", "ops", "queries", "settle", "targets"]
