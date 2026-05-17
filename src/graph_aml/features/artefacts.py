"""Local account feature artefact writers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.features.account import (
    AccountFeatureConfig,
    calculate_account_features,
    calculate_extended_account_features,
    validate_account_features,
    validate_extended_account_features,
)
from graph_aml.features.exceptions import FeatureArtefactError
from graph_aml.features.summary import summarise_account_features


def write_account_features_csv(
    features: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_features.csv",
) -> Path:
    """Validate and write account feature rows to CSV."""

    path = Path(output_path)
    try:
        validate_account_features(features)
        path.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise FeatureArtefactError(f"Failed to write account feature CSV: {exc}") from exc


def write_account_feature_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/account_feature_summary.json",
) -> Path:
    """Write account feature summary JSON."""

    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise FeatureArtefactError(f"Failed to write account feature summary JSON: {exc}") from exc


def generate_account_feature_artefacts(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    output_dir: Path | str = "reports/model_validation",
    config: AccountFeatureConfig | None = None,
) -> dict[str, Path]:
    """Calculate account features and write local feature artefacts."""

    try:
        features = calculate_account_features(accounts, transactions, config=config)
        validate_account_features(features)
        summary = summarise_account_features(features)
        target_dir = Path(output_dir)
        return {
            "features_csv": write_account_features_csv(
                features,
                target_dir / "account_features.csv",
            ),
            "summary_json": write_account_feature_summary_json(
                summary,
                target_dir / "account_feature_summary.json",
            ),
        }
    except FeatureArtefactError:
        raise
    except Exception as exc:
        raise FeatureArtefactError(f"Failed to generate account feature artefacts: {exc}") from exc


def generate_extended_account_feature_artefacts(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    countries: pd.DataFrame,
    output_dir: Path | str = "reports/model_validation",
    config: AccountFeatureConfig | None = None,
) -> dict[str, Path]:
    """Calculate extended account features and write local feature artefacts."""

    try:
        features = calculate_extended_account_features(
            accounts,
            transactions,
            countries,
            config=config,
        )
        validate_extended_account_features(features)
        summary = summarise_account_features(features)
        target_dir = Path(output_dir)
        return {
            "features_csv": write_account_features_csv(
                features,
                target_dir / "account_features.csv",
            ),
            "summary_json": write_account_feature_summary_json(
                summary,
                target_dir / "account_feature_summary.json",
            ),
        }
    except FeatureArtefactError:
        raise
    except Exception as exc:
        raise FeatureArtefactError(
            f"Failed to generate extended account feature artefacts: {exc}"
        ) from exc
