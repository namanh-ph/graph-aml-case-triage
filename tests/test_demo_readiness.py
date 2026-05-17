from __future__ import annotations

import json

from graph_aml.demo import (
    build_demo_readiness_summary,
    check_python_package_imports,
    check_required_directories_exist,
    check_required_files_exist,
)


def test_required_file_checker_reports_existing_files(tmp_path, monkeypatch) -> None:
    file_path = tmp_path / "README.md"
    file_path.write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = check_required_files_exist(("README.md",))
    assert result["status"] == "ok"


def test_required_file_checker_reports_missing_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = check_required_files_exist(("missing.txt",))
    assert result["missing_count"] == 1


def test_required_directory_checker_reports_existing_directories(tmp_path, monkeypatch) -> None:
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path)
    result = check_required_directories_exist(("src",))
    assert result["status"] == "ok"


def test_required_directory_checker_reports_missing_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = check_required_directories_exist(("missing",))
    assert result["missing_count"] == 1


def test_package_import_checker_reports_importable_packages() -> None:
    result = check_python_package_imports(("json",))
    assert result["status"] == "ok"


def test_package_import_checker_reports_missing_packages() -> None:
    result = check_python_package_imports(("package_that_should_not_exist_12345",))
    assert result["status"] == "warning"


def test_readiness_summary_is_json_serialisable() -> None:
    json.dumps(build_demo_readiness_summary(), default=str)


def test_readiness_checks_do_not_connect_to_services(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError),
    )
    assert build_demo_readiness_summary()["status"] in {"ok", "warning"}
