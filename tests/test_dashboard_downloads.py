"""Tests for dashboard download helpers."""

import json
import re

import pandas as pd
import pytest

from graph_aml.dashboard.downloads import (
    dataframe_to_csv_bytes,
    dataframe_to_json_bytes,
    dataframe_to_security_csv_bytes,
    dict_to_json_bytes,
    safe_download_filename,
)
from graph_aml.dashboard.exceptions import DashboardDataError


def test_dataframe_csv_conversion_returns_bytes() -> None:
    assert isinstance(dataframe_to_csv_bytes(pd.DataFrame({"a": [1]})), bytes)


def test_dataframe_json_conversion_returns_parseable_bytes() -> None:
    payload = dataframe_to_json_bytes(pd.DataFrame({"a": [1]}))

    assert json.loads(payload.decode("utf-8")) == [{"a": 1}]


def test_dict_json_conversion_returns_parseable_bytes() -> None:
    payload = dict_to_json_bytes({"b": 2, "a": 1})

    assert json.loads(payload.decode("utf-8")) == {"a": 1, "b": 2}


def test_safe_download_filename_removes_unsafe_characters() -> None:
    filename = safe_download_filename("bad/name ? x", "json")

    assert re.match(r"bad_name_x_\d{8}T\d{6}Z\.json", filename)


def test_malformed_download_inputs_raise() -> None:
    with pytest.raises(DashboardDataError):
        dataframe_to_csv_bytes({"bad": "input"})  # type: ignore[arg-type]
    with pytest.raises(DashboardDataError):
        dataframe_to_json_bytes({"bad": "input"})  # type: ignore[arg-type]
    with pytest.raises(DashboardDataError):
        dict_to_json_bytes(["bad"])  # type: ignore[arg-type]


def test_security_csv_download_masks_when_inventory_available() -> None:
    frame = pd.DataFrame({"customer_name": ["Jane"], "amount": [1]})
    fields = pd.DataFrame(
        [
            {
                "column_name": "customer_name",
                "recommended_masking_strategy": "redact",
            }
        ]
    )
    payload = dataframe_to_security_csv_bytes(frame, fields, role="viewer").decode("utf-8")
    assert "[REDACTED]" in payload
    assert "Jane" not in payload
