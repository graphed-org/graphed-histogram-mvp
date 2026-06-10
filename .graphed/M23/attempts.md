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
