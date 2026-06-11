# graphed-histogram

Deferred [boost-histogram](https://github.com/scikit-hep/boost-histogram)/[hist](https://github.com/scikit-hep/hist)
filling on [graphed](https://github.com/graphed-org) task graphs — the
[dask-histogram](https://github.com/dask-contrib/dask-histogram) analogue.

`.fill(...)` records into the graphed IR instead of executing; `.plan()` exports the task graph
an executor aggregates (partition-wise fill through the compiled IR, native `+` tree-combine),
and the reference `session.materialize` evaluates a fill eagerly. Fills are
External nodes carrying a content-addressed canonical axes/storage spec (UHI-compatible;
no invented formats). See `CLAUDE.md` and the frozen suite under `tests/frozen/m23/`.
