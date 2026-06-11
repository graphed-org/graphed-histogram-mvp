graphed-histogram
=================

Deferred `boost-histogram <https://boost-histogram.readthedocs.io>`_ / `hist
<https://hist.readthedocs.io>`_ filling on ``graphed`` task graphs — the ``dask-histogram``
analogue (milestone M23; P0.1 of the ADL-benchmarks port).

``.fill(...)`` **records** instead of executing: each fill is an External node in the graphed IR
(the M3 correctionlib/ONNX family) whose ``PayloadDescriptor`` content hash is the SHA-256 of a
canonical, versioned axes/storage spec — declarative params, never cloudpickle; UHI in, UHI out.
Backends know nothing about histograms, and evaluation is graphed's own machinery: ``plan()``
exports the task graph an R7 executor aggregates (partition-wise through the compiled IR over
the partitioned-source protocol — never whole-dataset materialized — with a native ``+``
tree-combine), and the reference ``session.materialize`` evaluates a fill eagerly. Int64 counts
are exact under any combine tree, float storages are deterministic per fixed-tree executor
configuration.

.. toctree::
   :maxdepth: 2

   api
   improvements
