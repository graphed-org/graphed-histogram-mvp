# Frozen acceptance suite — M23 (graphed-histogram): deferred histogram filling

P0.1 of the ADL-benchmarks port (user-confirmed plan, 2026-06-10). Traceability:

| Test file | Verifies | Item |
|---|---|---|
| `test_deferred_histograms.py` | fill stages + returns self (nothing read); compute == eager boost-histogram BIT FOR BIT, partition-wise, whole-dataset loader never invoked (counters); multi-fill accumulation; weighted fills + Weight storage (same-source rule; mixed sources rejected); 2D/Variable/IntCategory axes; content-addressed identity hash-consed (same spec+input ⇒ one node); compute-disabled plan run on a process executor == compute (R15.4); in-memory sources via materialize; numpy-like histogram/histogram2d == np.histogram; byte-identical IR + the UHI PayloadDescriptor | M23 |
