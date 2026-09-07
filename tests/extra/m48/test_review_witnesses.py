"""Witnesses for the m48 review repairs — the mechanisms no frozen anchor reaches yet.

Frozen is law; these live here until m49 freezes real anchors for them. Each carries the mutation
that reds it, stated in the docstring so the check's own discriminating power is checkable.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import awkward as ak
import boost_histogram as bh
import graphed
import numpy as np
import pytest
from graphed import GraphedError, compile_ir
from graphed.awkward import from_awkward, gak, gnano
from graphed.core.execution import SequentialRunner
from graphed.numpy import NumpyBackend, NumpyForm, from_array

# the frozen tree's own fixtures, without putting its dir on the packaged pythonpath
sys.path.append(str(Path(__file__).resolve().parents[2] / "frozen" / "m48"))

from vary_hist_fixtures import (
    EVENTS,
    broadcast_reference,
    eager_weighted,
    flat,
    in_memory_events,
    partitioned_events,
    weighted,
    weighted_2d,
)

import graphed_histogram as gh
from graphed_histogram import boost


def _pu(source: Any, scale: float = 1.0) -> Any:
    return source.MET.pt * 0.01 * scale


def _weighted_context(source: Any) -> Any:
    events = gnano.events(source)
    return graphed.vary(events, "pu", _pu(events), is_weight=True, up=_pu(events, 1.1))


# --- A7/A6: the guard's identity is the blame COORDINATE, not the diagnostic's prose ------------
def _guarded_blob(monkeypatch: Any, factor_prose: str) -> bytes:
    monkeypatch.setattr(boost, "_FACTOR_ROWS", factor_prose)
    session, root = in_memory_events()
    ctx = _weighted_context(root)
    h = weighted(bins=20, lo=0.0, hi=400.0)
    h.fill(ctx.Jet.pt, weight=[ctx.MET.pt * 0.5 + 1.0])
    return bytes(compile_ir(session, *h.fill_nodes()).ir)


def test_rewording_a_diagnostic_moves_no_recorded_bytes(monkeypatch: Any) -> None:
    """A7: the message is evaluator-side only. Keying the payload hash on the prose instead of the
    coordinate reds this — and with it every varied fill's checkpoint identity."""
    before = _guarded_blob(monkeypatch, "weight[{index}] is not at this fill's row space")
    after = _guarded_blob(monkeypatch, "weight[{index}] sits at a different row count entirely")
    assert before == after


def _blames(session: Any) -> set[str]:
    """The blame coordinates of the row-space guards this session recorded — the seam's witness,
    since a guard is recorded only where the fill decided a factor needs broadcasting."""
    return {
        node["params"]["blame"]
        for node in session._store.nodes()
        if node.get("params", {}).get("blame") is not None
    }


def test_two_different_offenders_stay_two_different_nodes() -> None:
    """A6: collapsing the guards' identities would let one evaluator answer for both coordinates,
    which mis-blames on the plan path. Ambient and explicit guards must differ."""
    session, root = in_memory_events()
    ctx = _weighted_context(root)
    h = weighted(bins=20, lo=0.0, hi=400.0)
    h.fill(ctx.Jet.pt, weight=[ctx.MET.pt * 0.5 + 1.0])
    assert _blames(session) == {"ambient", "weight[0]"}


# --- A6: the plan path blames the same operand the materialize path does -----------------------
def _offender_at(index: int) -> gh.boost.Histogram:
    """Two explicit factors, one of them per-EVENT against a flattened per-object value."""
    _session, source, _data = partitioned_events()
    events = gnano.events(source)
    value = gak.flatten(events.Jet.pt)
    fine = gak.flatten(events.Jet.pt * 0.0 + 1.0)
    offender = events.MET.pt * 0.01
    factors = [offender, fine] if index == 0 else [fine, offender]
    h = weighted(bins=20, lo=0.0, hi=400.0)
    h.fill(value, weight=factors)
    return h


@pytest.mark.parametrize("index", [0, 1])
def test_the_plan_path_names_the_same_offending_factor_as_materialize(index: int) -> None:
    with pytest.raises(GraphedError) as excinfo:
        SequentialRunner().run(gh.plan({"jets": _offender_at(index)}, steps_per_file=2))
    message = str(excinfo.value)
    assert f"weight[{index}]" in message
    assert f"weight[{1 - index}]" not in message


# --- A2: only the FIRST value can take the loose blame ----------------------------------------
def _two_axis(session_root: tuple[Any, Any], factor: Any) -> Any:
    """Axis 0 contexted, axis 1 LOOSE but at the correct row count — the shape that separates
    "any loose arg" from "args[0] is loose"."""
    _session, root = session_root
    events = gnano.events(root)
    sel = events[events.MET.pt > 20.0]
    loose_at_the_right_rows = root.MET.phi[root.MET.pt > 20.0]
    h = weighted_2d()
    h.fill(sel.MET.pt, loose_at_the_right_rows, weight=[factor(sel)])
    return h


def test_a_loose_value_away_from_index_zero_does_not_take_the_blame() -> None:
    """The guard compares each factor against the fill's FIRST value, so a loose value at another
    axis position is not what the comparison is about. Blaming on ANY loose arg reds this."""
    session, root = in_memory_events()
    h = _two_axis((session, root), lambda sel: gak.flatten(sel.Jet.pt))
    with pytest.raises(GraphedError) as excinfo:
        session.materialize(h.fill_nodes()[0])
    message = str(excinfo.value)
    assert "weight[0]" in message
    assert "value[0]" not in message


def test_the_same_program_with_a_matching_factor_runs() -> None:
    """The positive control: same shape, factor at the fill's row space."""
    session, root = in_memory_events()
    h = _two_axis((session, root), lambda sel: sel.MET.pt * 0.01)
    assert session.materialize(h.fill_nodes()[0]).sum(flow=True).value > 0


# --- A4: the merge refusal names the output whose fills actually merged ------------------------
def test_a_merge_inside_an_unvaried_sibling_names_that_sibling() -> None:
    """In a mixed plan the shortfall is global but the culprit need not be varied; naming only the
    varied outputs sends the reader to the wrong histogram with an inapplicable workaround."""
    _session, source, _data = partitioned_events()
    events = gnano.events(source)
    factor = events.MET.pt * 0.01

    varied = weighted()
    varied.fill(events.MET.pt, weight=[graphed.vary(factor, "sig", up=factor * 1.2)])
    merging = weighted()  # two fills the M4 identity rules collapse into one output
    merging.fill(events.MET.pt, weight=[factor])
    merging.fill(events.MET.pt, weight=[factor * 1.0])

    with pytest.raises(GraphedError) as excinfo:
        gh.plan({"varied": varied, "merging": merging}, steps_per_file=2)
    message = str(excinfo.value)
    assert "merging" in message
    assert "varied carries" not in message
    assert "points=" not in message, "the workaround does not apply to an unvaried output"


# --- A5: ancestor-context weight factors are re-indexed ----------------------------------------
def test_an_ancestor_context_weight_factor_is_re_indexed_to_the_fill() -> None:
    """Mutating `factors = [reindex_to(w, ctx) ...]` to `list(weights)` reds this: the parent-space
    factor then reaches the guard at the parent's row count."""
    session, root = in_memory_events()
    events = gnano.events(root)
    parent_factor = events.MET.pt * 0.0 + 2.0  # read at the PARENT, applied at the child
    sel = events[events.MET.pt > 20.0]

    h = weighted()
    h.fill(sel.MET.pt, weight=[parent_factor])
    got = session.materialize(h.fill_nodes()[0])

    mask = ak.to_numpy(EVENTS.MET.pt) > 20.0
    want = bh.Histogram(*weighted().axes, storage=bh.storage.Weight())
    want.fill(ak.to_numpy(EVENTS.MET.pt)[mask], weight=np.full(int(mask.sum()), 2.0))
    assert np.array_equal(got.view(flow=True)["value"], want.view(flow=True)["value"])
    assert got.sum(flow=True).value > 0


# --- A9: one compile per plan, spied on every binding of the definition ------------------------
def test_one_compile_ir_per_group_plan_call(monkeypatch: Any) -> None:
    """§7.2's anti-quadratic budget. `compile_ir` is imported BY NAME in several modules, so each
    binding is patched from the defining function — patching one module's re-export alone would
    miss a call made through another's."""
    import graphed.execute as execute  # noqa: PLC0415  (the spy starts from the definition)

    calls: list[int] = []
    real = execute.compile_ir

    def spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real(*args, **kwargs)

    for module in list(sys.modules.values()):
        if getattr(module, "compile_ir", None) is real:
            monkeypatch.setattr(module, "compile_ir", spy)

    _session, source, _data = partitioned_events()
    ctx = _weighted_context(source)
    h = weighted()
    h.fill(ctx.MET.pt)
    gh.plan({"met": h}, steps_per_file=2)
    assert calls == [1]


# --- the form-based seam rule: a matched row space still records ONE node ----------------------
def test_a_plain_fill_at_one_row_space_records_a_single_node() -> None:
    """The control on the seam trigger. A plain per-EVENT fill weighted per EVENT needs no
    broadcast, so it must record exactly the one fill node it always did — the pre-m48 golden blob
    is that same shape. Triggering the seam on the mere presence of a weight (or unconditionally)
    reds here and moves that golden; the mismatched twin next to it shows the rule still fires."""
    session, root = in_memory_events()
    value, factor = root.MET.pt, root.MET.pt * 0.5 + 1.0
    h = weighted(bins=20, lo=0.0, hi=400.0)
    before = session.node_count()
    h.fill(value, weight=[factor])
    assert session.node_count() - before == 1

    mixed_session, mixed_root = in_memory_events()
    mixed_value, mixed_factor = mixed_root.Jet.pt, mixed_root.MET.pt * 0.5 + 1.0
    mixed = weighted(bins=20, lo=0.0, hi=400.0)
    before = mixed_session.node_count()
    mixed.fill(mixed_value, weight=[mixed_factor])
    assert mixed_session.node_count() - before > 1


def test_an_awkward_scalar_weight_is_no_row_space_and_takes_no_seam() -> None:
    """A scalar broadcasts against anything, so it is at NO row space — the same contract `_rows`
    already holds at execution time. Reading a scalar's depth as 0 and calling it "shallower than
    1" fires the seam on a fill that works, moving its graph to record a guard that provably cannot
    trip."""
    session, root = in_memory_events()
    value, factor = root.MET.pt, gak.sum(root.MET.pt, axis=None)
    h = weighted(bins=20, lo=0.0, hi=400.0)
    before = session.node_count()
    h.fill(value, weight=[factor])
    assert session.node_count() - before == 1

    reference = eager_weighted(bins=20, lo=0.0, hi=400.0)
    reference.fill(flat(EVENTS.MET.pt), weight=ak.sum(EVENTS.MET.pt, axis=None))
    got = session.materialize(h.fill_nodes()[0])
    assert np.allclose(got.view(flow=True)["value"], reference.view(flow=True)["value"], rtol=1e-12)


def _ravelled_value(session: Any) -> Any:
    """A 2-D value the evaluator's `_flat` ravels — its ndim disagrees with a weight that is
    nonetheless at the fill's row space."""
    return session.source(
        "x2",
        form=NumpyForm(np.dtype("float64"), kind="vector", shape=(None, 2)),
        data=np.arange(8.0).reshape(4, 2),
    )


def _scalar_weight(session: Any) -> Any:
    return session.source(
        "s", form=NumpyForm(np.dtype("float64"), kind="scalar", shape=()), data=np.float64(2.0)
    )


@pytest.mark.parametrize(
    ("value_of", "factor_of"),
    [
        (_ravelled_value, lambda s: from_array(s, "w", np.full(8, 2.0))),
        (lambda s: from_array(s, "x", np.arange(8.0)), _scalar_weight),
    ],
    ids=["2-D value / 1-D weight", "1-D value / scalar weight"],
)
def test_the_numpy_idiom_records_no_seam_at_any_row_space(value_of: Any, factor_of: Any) -> None:
    """A rectilinear backend supplies no `broadcast_like`, so `graphed.broadcast_like` takes the
    bound no-op: firing the row-space rule here can only turn a working fill into a guard error,
    never repair one. Both ends of the range are driven, each keeping the single fill node it
    recorded before the rule existed and still evaluating to 16.0."""
    session = graphed.Session(NumpyBackend())
    value, factor = value_of(session), factor_of(session)
    h = gh.boost.Histogram(bh.axis.Regular(4, 0.0, 8.0), storage=bh.storage.Weight())
    before = session.node_count()
    h.fill(value, weight=[factor])
    assert session.node_count() - before == 1
    assert _blames(session) == set()
    got = session.materialize(h.fill_nodes()[0])
    assert float(got.view(flow=True)["value"].sum()) == 16.0


def _at_the_jet_row_space(session: Any, name: str, weights: np.ndarray) -> Any:
    """A weight already at the JET row space — one entry per object across the whole fixture, the
    shape a record-time form cannot tell from a per-event column."""
    return from_awkward(session, name, ak.Array(weights))


def test_an_already_flat_per_object_weight_fills_while_its_per_event_twin_takes_the_seam() -> None:
    """The two 1-D factors a per-object fill can carry, which no form tells apart: one already at
    the value's LEAF row space (nothing to broadcast — the evaluator would multiply it elementwise
    unaided), one at the value's OUTER row space (the seam's whole purpose). Deciding either at
    record time, or refusing the leaf one in the guard, turns a working fill into a hard error.

    The leaf factor is asserted twice: flat 2.0s pin the total, and a factor that varies per jet
    pins the ORDER, which re-nesting the factor into the value's structure could otherwise scramble
    without moving any total."""
    n_jets = int(ak.count(EVENTS.Jet.pt))
    session, root = in_memory_events()
    h = weighted(bins=20, lo=0.0, hi=400.0)
    h.fill(root.Jet.pt, weight=[_at_the_jet_row_space(session, "flat_sf", np.full(n_jets, 2.0))])
    got = session.materialize(h.fill_nodes()[0])
    reference = eager_weighted(bins=20, lo=0.0, hi=400.0)
    reference.fill(flat(EVENTS.Jet.pt), weight=np.full(n_jets, 2.0))
    assert np.array_equal(got.view(flow=True)["value"], reference.view(flow=True)["value"])
    assert float(got.view(flow=True)["value"].sum()) == 2.0 * n_jets

    varying = 1.0 + np.arange(n_jets, dtype=float) / n_jets
    ordered = weighted(bins=20, lo=0.0, hi=400.0)
    ordered.fill(root.Jet.pt, weight=[_at_the_jet_row_space(session, "varying_sf", varying)])
    ordered_got = session.materialize(ordered.fill_nodes()[0])
    ordered_ref = eager_weighted(bins=20, lo=0.0, hi=400.0)
    ordered_ref.fill(flat(EVENTS.Jet.pt), weight=varying)
    assert np.allclose(ordered_got.view(flow=True)["value"], ordered_ref.view(flow=True)["value"], rtol=1e-12)

    event_session, event_root = in_memory_events()
    per_event = weighted(bins=20, lo=0.0, hi=400.0)
    per_event.fill(event_root.Jet.pt, weight=[event_root.MET.pt * 0.5 + 1.0])
    assert _blames(event_session) == {"weight[0]"}
    event_got = event_session.materialize(per_event.fill_nodes()[0])
    broadcast_ref = eager_weighted(bins=20, lo=0.0, hi=400.0)
    broadcast_ref.fill(
        flat(EVENTS.Jet.pt), weight=broadcast_reference(EVENTS.Jet.pt, EVENTS.MET.pt * 0.5 + 1.0)
    )
    assert np.allclose(event_got.view(flow=True)["value"], broadcast_ref.view(flow=True)["value"], rtol=1e-12)


def _outer_option(root: Any) -> tuple[Any, ak.Array]:
    """`option[var * float64]`: whole events masked away, their jets still in the layout."""
    keep = ak.to_numpy(EVENTS.MET.pt) > 20.0
    return gak.mask(root.Jet.pt, root.MET.pt > 20.0), ak.mask(EVENTS.Jet.pt, keep)


def _inner_option(root: Any) -> tuple[Any, ak.Array]:
    """`var * ?float64`: every event padded out, the padding missing at the leaf."""
    return gak.pad_none(root.Jet.pt, 8), ak.pad_none(EVENTS.Jet.pt, 8)


@pytest.mark.parametrize("value_of", [_outer_option, _inner_option], ids=["outer", "inner"])
def test_a_value_with_missing_entries_keeps_its_pre_seam_fill_and_still_blames(value_of: Any) -> None:
    """The evaluator's flatten DROPS missing entries, so such a value's leaf row space is not the
    one its structure counts out: a factor already flat at it cannot be re-nested into the value,
    and at record time it cannot be told from a per-event factor either. Both ends of the seam
    stand down — the plain fill keeps the one node and the elementwise semantics it had before the
    seam existed, and the guard, wherever a broadcast is forced anyway, blames the factor by name
    instead of dying inside awkward with a message naming neither the fill nor the factor."""
    session, root = in_memory_events()
    value, eager = value_of(root)
    leaf = 1.0 + np.arange(len(flat(eager)), dtype=float) / 10.0
    at_the_leaf = _at_the_jet_row_space(session, "leaf_sf", leaf)

    h = weighted(bins=20, lo=0.0, hi=400.0)
    before = session.node_count()
    h.fill(value, weight=[at_the_leaf])
    assert session.node_count() - before == 1
    assert _blames(session) == set()
    got = session.materialize(h.fill_nodes()[0])
    reference = eager_weighted(bins=20, lo=0.0, hi=400.0)
    reference.fill(flat(eager), weight=leaf)
    assert np.allclose(got.view(flow=True)["value"], reference.view(flow=True)["value"], rtol=1e-12)

    varied_session, varied_root = in_memory_events()
    varied_value, _ = value_of(varied_root)
    factor = _at_the_jet_row_space(varied_session, "leaf_sf", leaf)
    forced = weighted(bins=20, lo=0.0, hi=400.0)
    forced.fill(varied_value, weight=[graphed.vary(factor, "sf", up=factor * 1.1)])
    with pytest.raises(GraphedError) as excinfo:
        varied_session.materialize(forced.fill_nodes()[0])
    assert "weight[0]" in str(excinfo.value)


def test_a_factor_deeper_than_the_value_records_no_seam_but_a_shallower_one_does() -> None:
    """`broadcast_like` lines a SHALLOWER factor up with a deeper value and does nothing else, so a
    per-object weight on a per-event value must record exactly the graph it recorded before the
    rule existed — one fill node, no guard — while the shallower twin still takes the seam. A rule
    keyed on "the depths differ" records a step here that cannot repair anything, moving the graph
    of a fill (this one, over a one-object-per-event collection) that evaluates correctly."""
    session, root = in_memory_events()
    singleton = ak.Array([[float(pt)] for pt in ak.to_numpy(EVENTS.MET.pt)])
    value, factor = root.MET.pt, from_awkward(session, "singleton", singleton)
    h = weighted(bins=20, lo=0.0, hi=400.0)
    before = session.node_count()
    h.fill(value, weight=[factor])
    assert session.node_count() - before == 1
    assert _blames(session) == set()
    got = session.materialize(h.fill_nodes()[0])
    reference = eager_weighted(bins=20, lo=0.0, hi=400.0)
    reference.fill(flat(EVENTS.MET.pt), weight=flat(singleton))
    assert np.allclose(got.view(flow=True)["value"], reference.view(flow=True)["value"], rtol=1e-12)

    shallow_session, shallow_root = in_memory_events()
    shallow = weighted(bins=20, lo=0.0, hi=400.0)
    before = shallow_session.node_count()
    shallow.fill(shallow_root.Jet.pt, weight=[shallow_root.MET.pt * 0.5 + 1.0])
    assert shallow_session.node_count() - before > 1
    assert _blames(shallow_session) == {"weight[0]"}
