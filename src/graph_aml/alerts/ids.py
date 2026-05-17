"""Deterministic alert ID helpers."""

from __future__ import annotations

import hashlib
import re

from graph_aml.alerts.exceptions import AlertValidationError


def normalise_rule_name_for_id(rule_name: str) -> str:
    """Normalise rule names for stable alert ID prefixes."""

    text = str(rule_name).strip()
    if not text:
        raise AlertValidationError("rule_name is required")
    normalised = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()
    if not normalised:
        raise AlertValidationError("rule_name must contain alphanumeric characters")
    return normalised


def build_alert_id(
    rule_name: str,
    account_id: str,
    detection_window_start: str | None,
    evidence_ids: tuple[str, ...] | list[str],
) -> str:
    """Build a deterministic alert ID from rule, account, window, and evidence."""

    rule_part = normalise_rule_name_for_id(rule_name)
    account = str(account_id).strip()
    if not account:
        raise AlertValidationError("account_id is required")
    evidence = tuple(sorted(str(value).strip() for value in evidence_ids if str(value).strip()))
    if not evidence:
        raise AlertValidationError("evidence_ids must contain at least one evidence ID")
    key = "|".join([rule_part, account.upper(), str(detection_window_start or ""), *evidence])
    suffix = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8].upper()
    return f"AL_{rule_part}_{suffix}"


def build_sequential_alert_id(prefix: str, sequence: int) -> str:
    """Build a human-readable sequential alert ID."""

    prefix_text = str(prefix).strip().upper()
    if not prefix_text:
        raise AlertValidationError("prefix is required")
    if sequence < 0:
        raise AlertValidationError("sequence must be non-negative")
    return f"{prefix_text}{sequence:06d}"
