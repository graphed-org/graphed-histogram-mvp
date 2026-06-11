How graphed-histogram works
===========================

Histograms are how a HEP analysis ends: nearly every real query terminates in a fill.
``graphed-histogram`` makes that terminal step a first-class citizen of the deferred graph — a
``.fill(...)`` **records** instead of executing, the fill is an ordinary IR node with a
content-addressed identity, and aggregation is a task graph any executor runs. It is the
``dask-histogram`` analogue, built on graphed's own idioms.

Three design decisions define the package; each gets a section below: fills as *External
nodes* (so backends know nothing about histograms), the *canonical spec* as content identity,
and aggregation through *plans and executors* rather than a ``compute()`` method.

.. contents::
   :local:
   :depth: 2


The deferred histogram in one example
-------------------------------------

::

    import boost_histogram as bh
    import graphed_histogram as gh
    from graphed.write import SequentialRunner

    h = gh.boost.Histogram(bh.axis.Regular(20, 0.0, 10.0), storage=bh.storage.Int64())
    h.fill(x)                  # x is a graphed Array: RECORDS a fill node, returns h
    h.fill(x * 0.5 + 1.0)      # fills accumulate — more nodes, same histogram

    plan   = h.plan(steps_per_file=4)            # the R15.4 task graph
    result = SequentialRunner().run(plan).value  # a CONCRETE boost histogram
    # any R7 executor accepts the same plan:
    #   ProcessExecutor(max_workers=4, persistent=True).run(plan).value

The eager boost API stays available on ``h`` (axes, storage, views of the empty state); what
changed is that filling stages graph nodes and evaluation belongs to executors.


Fills are External nodes — backends know nothing
------------------------------------------------

A fill records through the frontend's ``record_external(descriptor=, form=)`` seam: the
package supplies the ``PayloadDescriptor`` (``kind="histogram"``,
``content_hash=sha256(spec)``, ``io_schema="uhi"``) and an opaque histogram form itself — the
backend is **never consulted**. This is the same architectural family as correctionlib and
ONNX nodes (M3): a call into foreign machinery, carried in the IR with reproducibility
metadata, evaluated by a registered evaluator.

The evaluator (``FillEvaluator``) is a frozen, picklable dataclass: given a chunk's input
arrays it builds a zero histogram from the spec and fills it — ragged inputs flatten
completely, weights and samples ride as additional *graph inputs* (never parameters).
``evaluate_ir`` resolves it by content hash through its ``externals=`` registry, failing
loudly if unregistered. Nothing in graphed-core, graphed, or any backend mentions histograms.

The canonical spec: identity you can ship
-----------------------------------------

A histogram's identity is the SHA-256 of its **canonical axes/storage spec** — versioned,
key-sorted JSON covering every supported axis (Regular/Variable/Integer/IntCategory/
StrCategory/Boolean, with flow flags) and storage (all standard boost storages), plus axis
user attributes: boost axes carry metadata like hist's ``name``/``label`` in their
``__dict__``, and the spec captures and restores it, so named axes survive a round trip.
``zero_of(spec)`` rebuilds the empty histogram anywhere; ``spec_of(h)`` is a fixed point
through rebuild (pinned).

Why this matters beyond tidiness: identical fills **intern** (same spec + same inputs = one
graph node); the spec string itself is the fill's *preservation payload* (graphed-preserve's
histogram plugin synthesizes it from the node's own parameters at bundle-build time); and a
plan re-run on another machine resolves its evaluator by the same hash. Identity, payload, and
registry key are one object.

Aggregation: plans and executors, not ``compute()``
---------------------------------------------------

There is deliberately no ``compute()`` method — evaluation is graphed's machinery, not a
collection protocol:

* ``h.plan(steps_per_file=..., partitions=..., backend=...)`` builds a
  ``Plan(process=fill-partition-through-the-compiled-IR, combine=native +, empty=zero)``. All
  of the histogram's fills compile into **one** multi-output graph, evaluated in a single pass
  per partition. Sources implementing the ``PartitionedSource`` protocol are read partition by
  partition — the whole-dataset loader is never invoked (counter-witnessed in the frozen
  suite). ``partitions=`` lets a caller shape chunking explicitly (benchmark sweeps use
  absolute entry counts).
* Any R7 executor's ``run(plan).value`` **is** the aggregated histogram. Histograms form a
  monoid under native ``+`` for every standard storage, so the executor's fixed combine tree
  applies unchanged: integer counts are exact under any tree; float storages are
  deterministic per fixed-tree configuration.
* The reference path for in-memory sources is ``session.materialize(fill_node)`` — the
  evaluated fill *is* a filled histogram — with the ``zero_of``/``add_histograms`` helpers for
  multi-fill sums.

Worker backends travel safely
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``plan(backend=...)`` accepts a zero-arg factory/class or an importable ``"module:attr"``
string resolved *in the worker* — the required form for behavior-carrying backends, because
behavior dicts contain lambdas and do not pickle. The failure direction is pinned the safe way
round: a worker built without required behaviors **fails loudly** on the behavior property; it
never silently fills the wrong thing. Weighted fills through a spawned pool are pinned exact
(values *and* variances) against the sequential run.

The hist integration
--------------------

``hist.graphed`` (in the ``hist`` fork) supplies ``Hist``/``NamedHist`` as thin MRO sandwiches
over this package's ``Histogram``: the familiar QuickConstruct
(``Hist.new.Reg(100, 0, 200, name="met").Double()``) and named-axis fills record deferred;
executor results wrap back into in-memory ``hist.Hist`` objects with names and labels intact
(they ride the canonical spec). The eight ADL benchmark queries run on exactly this surface.


Phase 2 (deliberately not built)
--------------------------------

* **Growth axes** — combining grown category axes across partitions needs a category-union
  merge; rejected explicitly at spec time for now.
* **Dask-style collection protocols** (``persist``, ``to_delayed``) — the durable artifact is
  the compiled IR / ``DurablePlan``; no parallel collection API is planned.
* **Behavior-reference forwarding by default** — the ``"module:attr"`` mechanism exists;
  defaulting it from the recording session (rather than the bare backend class) awaits the
  same behavior-reference carriage as preservation.

See :doc:`improvements` for the live tracked list.
