"""Tests for local secrets scanning."""

import pytest

from graph_aml.security import (
    SECRETS_SCAN_COLUMNS,
    SecretPatternConfig,
    SecretsScanConfig,
    SecretsScanError,
    SecurityControlConfig,
    iter_scannable_files,
    run_secrets_scan,
    scan_file_for_secrets,
)


def _config(root: str, **kwargs: object) -> SecurityControlConfig:
    return SecurityControlConfig(
        secrets_scan=SecretsScanConfig(
            root_dirs=(root,),
            allowed_extensions=(".py", ".env", ".example"),
            max_file_size_mb=1,
            secret_patterns=(SecretPatternConfig("token", r"token\s*=\s*[A-Za-z0-9]{16,}"),),
            allowlist_patterns=(".env.example", "local_dev"),
            **kwargs,
        )
    )


def test_iter_scannable_files_filters_extension_and_size(tmp_path) -> None:
    (tmp_path / "a.py").write_text("x=1", encoding="utf-8")
    (tmp_path / "b.bin").write_text("x", encoding="utf-8")
    files = iter_scannable_files(_config(str(tmp_path)))
    assert [path.name for path in files] == ["a.py"]


def test_scan_detects_and_redacts_secret_like_strings(tmp_path) -> None:
    path = tmp_path / "a.py"
    path.write_text("token = ABCDEFGHIJKLMNOP\n", encoding="utf-8")
    result = scan_file_for_secrets(path, _config(str(tmp_path)), "run")
    assert tuple(result.columns) == SECRETS_SCAN_COLUMNS
    assert len(result) == 1
    assert "ABCDEFGHIJKLMNOP" not in result.loc[0, "match_preview"]


def test_allowlisted_and_missing_dirs_are_handled(tmp_path) -> None:
    path = tmp_path / ".env.example"
    path.write_text("token = ABCDEFGHIJKLMNOP\n", encoding="utf-8")
    result = run_secrets_scan(_config(str(tmp_path)), "run")
    assert bool(result.loc[0, "allowed"])
    assert run_secrets_scan(_config(str(tmp_path / "missing"))).empty


def test_regex_failures_raise(tmp_path) -> None:
    bad = SecurityControlConfig(
        secrets_scan=SecretsScanConfig(
            root_dirs=(str(tmp_path),),
            secret_patterns=(SecretPatternConfig("bad", "["),),
        )
    )
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    with pytest.raises(SecretsScanError):
        scan_file_for_secrets(tmp_path / "a.py", bad)
