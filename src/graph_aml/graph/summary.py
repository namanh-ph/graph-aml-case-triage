"""Compact summaries for Neo4j utility outputs."""

from __future__ import annotations


def summarise_neo4j_health(health: dict[str, object]) -> dict[str, object]:
    """Return a compact JSON-serialisable Neo4j health summary."""

    return {
        "status": health.get("status", "unknown"),
        "database": health.get("database"),
        "connectivity_verified": bool(health.get("connectivity_verified", False)),
        "query_ok": bool(health.get("query_ok", False)),
    }


def summarise_graph_constraints(constraints: list[dict[str, object]]) -> dict[str, object]:
    """Return a compact summary of listed Neo4j constraints."""

    names: list[str] = []
    labels: set[str] = set()
    for constraint in constraints:
        name = constraint.get("name")
        if name is not None:
            names.append(str(name))
        label = _extract_label(constraint)
        if label:
            labels.add(label)
    return {
        "constraint_count": len(constraints),
        "constraint_names": sorted(names),
        "labels": sorted(labels),
    }


def _extract_label(constraint: dict[str, object]) -> str | None:
    labels_or_types = constraint.get("labelsOrTypes")
    if isinstance(labels_or_types, list) and labels_or_types:
        return str(labels_or_types[0])
    label = constraint.get("label")
    if label is not None:
        return str(label)
    entity_type = constraint.get("entityType")
    if entity_type is not None and constraint.get("name"):
        name = str(constraint["name"])
        parts = name.split("_")
        if len(parts) >= 3 and parts[0] == "constraint":
            return parts[1].title()
    return None
