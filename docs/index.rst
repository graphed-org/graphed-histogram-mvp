graphed-histogram
=================

Deferred `boost-histogram <https://boost-histogram.readthedocs.io>`_ / `hist
<https://hist.readthedocs.io>`_ filling on ``graphed`` task graphs — the ``dask-histogram``
analogue (milestone M23; P0.1 of the ADL-benchmarks port).

``.fill(...)`` **records** instead of executing: each fill is an External node in the graphed IR
(the M3 correctionlib/ONNX family) whose ``PayloadDescriptor`` content hash is the SHA-256 of a
canonical, versioned axes/storage spec — declarative params, never cloudpickle; UHI in, UHI out.
Backends know nothing about histograms. ``.compute()`` fills partition by partition through the
compiled IR (sources implementing the partitioned-source protocol are never whole-dataset
materialized) and tree-reduces per-partition histograms; Int64 counts are exact under any combine
tree, float storages are deterministic per fixed-tree executor configuration.

.. toctree::
   :maxdepth: 2

   api
   improvements
