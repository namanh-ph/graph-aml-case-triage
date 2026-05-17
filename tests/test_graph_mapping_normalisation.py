"""Tests for graph mapping normalisation helpers."""

from __future__ import annotations

import json
from decimal import Decimal

import numpy as np
import pandas as pd

from graph_aml.graph import (
    dataframe_to_graph_rows,
    normalise_graph_bool,
    normalise_graph_float,
    normalise_graph_scalar,
    normalise_graph_timestamp,
)


def test_null_like_values_normalise_to_none() -> None:
    for value in (None, "", "nan", "None", "null", pd.NA, np.nan, pd.NaT):
        assert normalise_graph_scalar(value) is None


def test_timestamps_normalise_to_iso_strings() -> None:
    assert normalise_graph_timestamp("2024-01-01T12:00:00Z") == "2024-01-01T12:00:00+00:00"


def test_booleans_normalise_to_python_bools() -> None:
    assert normalise_graph_bool("true") is True
    assert normalise_graph_bool("0") is False


def test_floats_normalise_to_python_floats() -> None:
    assert normalise_graph_float(Decimal("10.50")) == 10.5


def test_numpy_scalars_normalise_to_plain_python_values() -> None:
    value = normalise_graph_scalar(np.int64(3))

    assert value == 3
    assert isinstance(value, int)


def test_dataframe_rows_convert_to_list_of_dictionaries() -> None:
    frame = pd.DataFrame([{"id": np.int64(1), "empty": ""}])

    rows = dataframe_to_graph_rows(frame)

    assert rows == [{"id": 1, "empty": None}]
    json.dumps(rows)


def test_input_dataframes_are_not_mutated() -> None:
    frame = pd.DataFrame([{"id": 1, "empty": ""}])
    original = frame.copy(deep=True)

    dataframe_to_graph_rows(frame)

    pd.testing.assert_frame_equal(frame, original)


def test_empty_dataframes_convert_to_empty_rows() -> None:
    assert dataframe_to_graph_rows(pd.DataFrame()) == []
