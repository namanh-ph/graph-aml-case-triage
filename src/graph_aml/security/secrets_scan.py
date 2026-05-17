"""Local secret-like string scanning with redacted previews."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pandas as pd

from graph_aml.security.config import SecurityControlConfig
from graph_aml.security.exceptions import SecretsScanError

SECRETS_SCAN_COLUMNS = (
    "security_run_id",
    "file_path",
    "pattern_name",
    "line_number",
    "match_preview",
    "allowed",
    "metadata",
)


def _config(config: SecurityControlConfig | None) -> SecurityControlConfig:
    return config or SecurityControlConfig()


def iter_scannable_files(config: SecurityControlConfig | None = None) -> tuple[Path, ...]:
    """Return files eligible for local secrets scanning."""

    resolved = _config(config)
    max_bytes = resolved.secrets_scan.max_file_size_mb * 1024 * 1024
    extensions = {ext.lower() for ext in resolved.secrets_scan.allowed_extensions}
    files: list[Path] = []
    try:
        for root_value in resolved.secrets_scan.root_dirs:
            root = Path(root_value).resolve()
            if not root.exists():
                continue
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                resolved_path = path.resolve()
                if root != resolved_path and root not in resolved_path.parents:
                    raise SecretsScanError("unsafe path traversal while scanning")
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                if path.stat().st_size > max_bytes:
                    continue
                files.append(path)
    except OSError as exc:
        raise SecretsScanError(f"failed to list scannable files: {exc}") from exc
    return tuple(files)


def is_secret_match_allowlisted(
    file_path: Path,
    line_text: str,
    pattern_name: str,
    config: SecurityControlConfig | None = None,
) -> bool:
    resolved = _config(config)
    target = f"{file_path.as_posix()} {line_text} {pattern_name}".lower()
    return any(pattern.lower() in target for pattern in resolved.secrets_scan.allowlist_patterns)


def _preview(match_text: str) -> str:
    prefix = match_text[:12].replace("\n", " ").replace("\r", " ")
    return f"{prefix}[REDACTED]"


def scan_file_for_secrets(
    file_path: Path,
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> pd.DataFrame:
    """Scan one file for secret-like strings."""

    resolved = _config(config)
    path = Path(file_path)
    rows: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        compiled = [
            (pattern.name, re.compile(pattern.regex))
            for pattern in resolved.secrets_scan.secret_patterns
        ]
    except re.error as exc:
        raise SecretsScanError(f"invalid secret regex: {exc}") from exc
    except OSError as exc:
        raise SecretsScanError(f"failed to read file for scan: {exc}") from exc
    for line_number, line_text in enumerate(text.splitlines(), start=1):
        for pattern_name, regex in compiled:
            for match in regex.finditer(line_text):
                rows.append(
                    {
                        "security_run_id": security_run_id or "",
                        "file_path": path.as_posix(),
                        "pattern_name": pattern_name,
                        "line_number": line_number,
                        "match_preview": _preview(match.group(0)),
                        "allowed": is_secret_match_allowlisted(
                            path, line_text, pattern_name, resolved
                        ),
                        "metadata": {"line_length": len(line_text)},
                    }
                )
    return cast("pd.DataFrame", pd.DataFrame(rows, columns=SECRETS_SCAN_COLUMNS))


def run_secrets_scan(
    config: SecurityControlConfig | None = None,
    security_run_id: str | None = None,
) -> pd.DataFrame:
    """Run local secrets scan over configured root directories."""

    resolved = _config(config)
    if not resolved.secrets_scan.enabled:
        return pd.DataFrame(columns=SECRETS_SCAN_COLUMNS)
    frames = [
        scan_file_for_secrets(path, resolved, security_run_id)
        for path in iter_scannable_files(resolved)
    ]
    if not frames:
        return pd.DataFrame(columns=SECRETS_SCAN_COLUMNS)
    return cast("pd.DataFrame", pd.concat(frames, ignore_index=True)[list(SECRETS_SCAN_COLUMNS)])
