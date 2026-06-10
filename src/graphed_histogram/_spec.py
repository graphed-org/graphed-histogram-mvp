"""The canonical, versioned axes/storage spec — the content-addressed IDENTITY of a fill.

A deferred fill's `PayloadDescriptor.content_hash` is the SHA-256 of this encoding, so two fills
with the same axes/storage (and inputs) intern to ONE graph node, and a plan re-run resolves its
evaluator by the same hash on any machine. The encoding is declarative JSON (sorted keys, fixed
float formatting via repr of Python floats) — never pickle; rebuilding axes from it round-trips
exactly (UHI-compatible boost-histogram objects; no invented formats).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import boost_histogram as bh

SPEC_VERSION = 1

_STORAGES: dict[str, Any] = {
    "Double": bh.storage.Double,
    "Int64": bh.storage.Int64,
    "AtomicInt64": bh.storage.AtomicInt64,
    "Unlimited": bh.storage.Unlimited,
    "Weight": bh.storage.Weight,
    "Mean": bh.storage.Mean,
    "WeightedMean": bh.storage.WeightedMean,
}


def _metadata_of(axis: Any) -> dict[str, str]:
    md = getattr(axis, "metadata", None)
    if md is None:
        return {}
    if isinstance(md, dict):
        return {str(k): str(v) for k, v in sorted(md.items())}
    return {"metadata": str(md)}


def _axis_spec(axis: Any) -> dict[str, Any]:
    if isinstance(axis, bh.axis.Regular):
        return {
            "type": "Regular",
            "bins": int(axis.size),
            "start": float(axis.edges[0]),
            "stop": float(axis.edges[-1]),
            "underflow": bool(axis.traits.underflow),
            "overflow": bool(axis.traits.overflow),
            "metadata": _metadata_of(axis),
        }
    if isinstance(axis, bh.axis.Variable):
        return {
            "type": "Variable",
            "edges": [float(e) for e in axis.edges],
            "underflow": bool(axis.traits.underflow),
            "overflow": bool(axis.traits.overflow),
            "metadata": _metadata_of(axis),
        }
    if isinstance(axis, bh.axis.Integer):
        return {
            "type": "Integer",
            "start": int(axis.edges[0]),
            "stop": int(axis.edges[-1]),
            "underflow": bool(axis.traits.underflow),
            "overflow": bool(axis.traits.overflow),
            "metadata": _metadata_of(axis),
        }
    if isinstance(axis, bh.axis.IntCategory):
        if axis.traits.growth:
            raise TypeError("growth axes are not supported (Phase 2)")
        return {"type": "IntCategory", "categories": [int(c) for c in axis], "metadata": _metadata_of(axis)}
    if isinstance(axis, bh.axis.StrCategory):
        if axis.traits.growth:
            raise TypeError("growth axes are not supported (Phase 2)")
        return {"type": "StrCategory", "categories": [str(c) for c in axis], "metadata": _metadata_of(axis)}
    if isinstance(axis, bh.axis.Boolean):
        return {"type": "Boolean", "metadata": _metadata_of(axis)}
    raise TypeError(f"unsupported axis type for a deferred fill: {type(axis).__name__}")


def _make_axis(spec: dict[str, Any]) -> Any:
    md = spec.get("metadata") or None
    kind = spec["type"]
    if kind == "Regular":
        return bh.axis.Regular(
            spec["bins"],
            spec["start"],
            spec["stop"],
            underflow=spec["underflow"],
            overflow=spec["overflow"],
            metadata=md,
        )
    if kind == "Variable":
        return bh.axis.Variable(
            spec["edges"], underflow=spec["underflow"], overflow=spec["overflow"], metadata=md
        )
    if kind == "Integer":
        return bh.axis.Integer(
            spec["start"], spec["stop"], underflow=spec["underflow"], overflow=spec["overflow"], metadata=md
        )
    if kind == "IntCategory":
        return bh.axis.IntCategory(spec["categories"], metadata=md)
    if kind == "StrCategory":
        return bh.axis.StrCategory(spec["categories"], metadata=md)
    if kind == "Boolean":
        return bh.axis.Boolean(metadata=md)
    raise TypeError(f"unknown axis spec type {kind!r}")  # pragma: no cover - encode/decode parity


def spec_of(hist: bh.Histogram) -> str:
    """The canonical spec string of a histogram's axes + storage (its content identity)."""
    payload = {
        "version": SPEC_VERSION,
        "storage": type(hist.storage_type()).__name__,
        "axes": [_axis_spec(ax) for ax in hist.axes],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def content_hash(spec: str) -> str:
    return "sha256:" + hashlib.sha256(spec.encode()).hexdigest()


def zero_of(spec: str) -> bh.Histogram:
    """An EMPTY histogram rebuilt from the canonical spec (the monoid identity)."""
    payload = json.loads(spec)
    if payload["version"] != SPEC_VERSION:  # pragma: no cover - future-proofing
        raise ValueError(f"unsupported histogram spec version {payload['version']}")
    storage = _STORAGES[payload["storage"]]()
    return bh.Histogram(*(_make_axis(a) for a in payload["axes"]), storage=storage)
