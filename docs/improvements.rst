Improvements
============

Tracked design improvements and known limitations for ``graphed-histogram`` (plan M0 requires
this file in every package).

Delivered
---------

- M23: deferred fills as content-addressed External nodes; partition-wise compute over the
  partitioned-source protocol; native ``+`` combine for every standard boost storage; the
  ``hist.graphed`` integration lives in the ``hist-graphed-mvp`` fork.

Known limitations / Phase 2
---------------------------

- Growth axes are not supported (combining grown category axes across partitions needs a
  category-union merge; deferred).
- ``persist`` / ``to_delayed``-style dask collection protocols are out of scope; the durable
  artifact is the compiled IR / ``DurablePlan``.
- Float (Weight/Mean) storages are deterministic per executor configuration (fixed combine
  tree), not bit-identical across different worker counts — Int64 counts are.
- One source family per histogram: every fill must come from one ``PartitionedSource`` (or all
  in-memory); mixtures are rejected.
