"""Streamlit renderers for local validation report artefacts."""

from __future__ import annotations

import pandas as pd

from graph_aml.dashboard.components import render_dataframe_table
from graph_aml.dashboard.exceptions import DashboardRenderError


def render_validation_report_index(index: dict[str, object]) -> None:
    try:
        import streamlit as st

        st.subheader("Validation Report Index")
        st.json({key: value for key, value in index.items() if key != "files"})
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render validation report index: {exc}") from exc


def render_validation_file_table(files: pd.DataFrame) -> None:
    render_dataframe_table(files, "Validation Artefacts")


def render_validation_file_preview(preview: dict[str, object]) -> None:
    try:
        import streamlit as st

        if not preview:
            st.info("No validation artefact selected.")
            return
        extension = str(preview.get("extension") or "")
        st.subheader(str(preview.get("relative_path") or preview.get("file_name") or "Preview"))
        if extension == ".md":
            st.markdown(str(preview.get("preview_text") or ""))
        elif extension == ".json":
            st.json(preview.get("json") if preview.get("json") is not None else preview)
        elif extension == ".csv":
            st.write(
                {
                    "row_count": preview.get("row_count", 0),
                    "column_count": preview.get("column_count", 0),
                }
            )
            st.dataframe(pd.DataFrame(preview.get("sample_rows", [])), use_container_width=True)
        else:
            st.code(str(preview.get("preview_text") or ""))
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render validation file preview: {exc}") from exc


def render_validation_report_empty_state(report_dir: str) -> None:
    try:
        import streamlit as st

        st.info(f"No validation artefacts are available under {report_dir}.")
    except Exception as exc:
        raise DashboardRenderError(f"Failed to render validation empty state: {exc}") from exc
