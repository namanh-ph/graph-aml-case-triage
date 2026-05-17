"""Small CLI for local developer utility commands."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from shutil import rmtree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

REQUIRED_SCAFFOLD_PATHS = (
    "README.md",
    ".env.example",
    ".gitignore",
    "Makefile",
    "pyproject.toml",
    "docker-compose.yml",
    "config",
    "config/project.yaml",
    "config/paths.yaml",
    "config/database.yaml",
    "config/neo4j.yaml",
    "config/rules.yaml",
    "config/scoring.yaml",
    "config/model.yaml",
    "config/dashboard.yaml",
    "src/graph_aml",
    "src/graph_aml/config",
    "src/graph_aml/observability",
    "app/streamlit_app.py",
    "tests",
)

CACHE_DIR_NAMES = (
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "dist",
    "build",
)


def _project_root(project_root: Path | None = None) -> Path:
    return Path.cwd() if project_root is None else project_root


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _python_version() -> str:
    result = subprocess.run(
        [sys.executable, "--version"],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() or result.stderr.strip()


def check_environment(project_root: Path | None = None) -> int:
    """Print local environment status."""

    root = _project_root(project_root)
    print(f"Python: {_python_version()}")
    print(f"Working directory: {Path.cwd()}")
    print(f".env exists: {_yes_no((root / '.env').exists())}")
    print(f".env.example exists: {_yes_no((root / '.env.example').exists())}")
    print(f"docker-compose.yml exists: {_yes_no((root / 'docker-compose.yml').exists())}")
    print(f"config/ exists: {_yes_no((root / 'config').exists())}")
    print(f"src/graph_aml/ exists: {_yes_no((root / 'src/graph_aml').exists())}")
    return 0


def clean_caches(project_root: Path | None = None) -> int:
    """Remove local Python and tooling caches."""

    root = _project_root(project_root)
    for directory_name in CACHE_DIR_NAMES:
        rmtree(root / directory_name, ignore_errors=True)

    coverage_file = root / ".coverage"
    if coverage_file.exists():
        coverage_file.unlink()

    for path in root.rglob("__pycache__"):
        rmtree(path, ignore_errors=True)
    for path in root.glob("*.egg-info"):
        rmtree(path, ignore_errors=True)

    print("Local caches removed.")
    return 0


def show_project_info(project_root: Path | None = None) -> int:
    """Print concise project information from typed configuration."""

    from graph_aml.config import load_app_config

    root = _project_root(project_root)
    config = load_app_config(root / "config")
    print(f"Project: {config.project.project.name}")
    print(f"Package: {config.project.project.package_name}")
    print(f"Version: {config.project.project.version}")
    print(f"Environment: {config.project.project.environment}")
    print(
        "PostgreSQL default: "
        f"{config.database.postgres.defaults.host}:{config.database.postgres.defaults.port}"
    )
    print(f"Neo4j default URI: {config.neo4j.neo4j.defaults.uri}")
    print(f"Dashboard title: {config.dashboard.dashboard.app_title}")
    return 0


def verify_scaffold(project_root: Path | None = None) -> int:
    """Verify required scaffold paths exist."""

    root = _project_root(project_root)
    missing = [
        relative_path
        for relative_path in REQUIRED_SCAFFOLD_PATHS
        if not (root / relative_path).exists()
    ]
    if missing:
        print("Scaffold verification: FAILED")
        for relative_path in missing:
            print(f"Missing: {relative_path}")
        return 1

    print("Scaffold verification: OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the developer CLI parser."""

    parser = argparse.ArgumentParser(description="Local developer utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-env", help="Print local environment status.")
    subparsers.add_parser("clean", help="Remove local Python and tooling caches.")
    subparsers.add_parser("info", help="Print project information from typed config.")
    subparsers.add_parser("verify-scaffold", help="Verify required scaffold paths.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the developer CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "check-env":
        return check_environment()
    if args.command == "clean":
        return clean_caches()
    if args.command == "info":
        return show_project_info()
    if args.command == "verify-scaffold":
        return verify_scaffold()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
