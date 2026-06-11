# M23 attempts — graphed-histogram (deferred histogram filling; P0.1)

## Iteration 0 — M0 spine + TEST_AUTHORING/TEST_SANITY/IMPLEMENTING — 2026-06-10 (freeze-M23-0)

- Repo created per the lazy-repo recipe (spine adapted from graphed-checkpoint: CI matrix,
  tooling, Sphinx + improvements.rst, CONTRIBUTING, distilled CLAUDE.md).
- frozen suite tests/frozen/m23 (14 tests); NON-VACUOUS (10/10 initial tests fail on the missing
  package; 4 coverage tests added pre-freeze, recorded).
- Design (user-confirmed plan): fills are External nodes recorded via graphed M23's
  record_external(descriptor=, form=) — backends know nothing about histograms; identity =
  SHA-256 of the canonical versioned axes/storage spec (declarative JSON; growth axes rejected
  as Phase 2); evaluators resolve through evaluate_ir(externals=); compute() = partition-wise
  fill through the compiled IR over the PartitionedSource protocol (whole-dataset loader never
  invoked, counter-witnessed) + native `+` tree-combine; in-memory sources via materialize;
  plan() exports the R15.4 task graph (ProcessExecutor pin). dask-histogram-parity surface:
  boost.Histogram / factory / histogram / histogram2d / histogramdd.
- gates: frozen 14/14 PASS · coverage 95.07% (>=90, branch) · ruff+format clean · mypy --strict
  clean · sphinx -W clean · IR byte-determinism pinned in-suite.

## Iteration 1 — the hist.graphed integration surface — 2026-06-10

- `_wrap_result` hook: compute() converts to the subclass's `_in_memory_type` when declared
  (the hist.dask convention) — `hist.graphed.Hist.compute()` returns a real `hist.Hist`.
- Axis identity metadata: boost axes carry user attributes (hist's name/label) in `__dict__`,
  not in a `metadata=` kwarg — the canonical spec now captures/restores `__dict__` entries, so
  names and labels survive record -> compute -> wrap. Spec encode/rebuild remains a fixed point
  (pinned).

## Iteration 2 — USER-DIRECTED: no compute() helper (graphed idiom) — 2026-06-11 (freeze-M23-1)

- USER: "graphed has its own [idioms] ... we have materialize and the executors for that.
  Remove compute() from graphed-histogram."
- Histogram.compute() and the _wrap_result/_in_memory_type machinery are REMOVED. Evaluation is
  graphed's: plan() (R15.4) + any R7 executor's run(plan).value IS the aggregated histogram;
  the reference session.materialize(fill_node) evaluates one fill eagerly (multi-fill in-memory:
  zero_of + add_histograms over per-fill materializes — pinned).
- frozen m23 respun under this authorization (executor/materialize idiom; same pins otherwise);
  freeze tag bumped freeze-M23-0 -> freeze-M23-1.
- gates: 14/14 · coverage 94.85% · ruff/mypy/sphinx clean.
