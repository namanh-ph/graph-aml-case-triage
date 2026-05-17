"""Tests for checked-in AML rule documentation Markdown files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "rules"

EXPECTED_FILES = (
    "index.md",
    "aml_rule_documentation_pack.md",
    "structuring.md",
    "fan_in.md",
    "fan_out.md",
    "rapid_movement.md",
    "dormant_reactivation.md",
    "circular_flow.md",
)

REQUIRED_PAGE_SECTIONS = (
    "Purpose",
    "Detection Logic",
    "Inputs",
    "Thresholds",
    "Alert Output",
    "Evidence",
    "Reason Code",
    "Risk Scoring",
    "Example Scenario",
    "Example Alert",
    "Limitations",
    "Validation Tests",
    "Operational Notes",
)


def test_rule_documentation_files_exist() -> None:
    for filename in EXPECTED_FILES:
        assert (DOCS_DIR / filename).is_file(), filename


def test_individual_rule_pages_include_required_sections() -> None:
    for filename in EXPECTED_FILES[2:]:
        text = (DOCS_DIR / filename).read_text(encoding="utf-8")
        for section in REQUIRED_PAGE_SECTIONS:
            assert f"## {section}" in text, f"{filename}: {section}"
