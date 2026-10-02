"""Run metadata helpers for reproducible workbooks and benchmark outputs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .constants import (
    INVESTMENT_SYSTEM_PROMPT,
    INVESTMENT_USER_TEMPLATE,
    SCORER_VERSION,
    SDG_MENTIONS_SYSTEM_PROMPT,
    SDG_MENTIONS_USER_TEMPLATE,
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(root: str | Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def prompt_hashes() -> dict[str, str]:
    return {
        "sdg_mentions_system_prompt_sha256": sha256_text(SDG_MENTIONS_SYSTEM_PROMPT),
        "sdg_mentions_user_template_sha256": sha256_text(SDG_MENTIONS_USER_TEMPLATE),
        "investment_system_prompt_sha256": sha256_text(INVESTMENT_SYSTEM_PROMPT),
        "investment_user_template_sha256": sha256_text(INVESTMENT_USER_TEMPLATE),
    }


def build_run_metadata(model: str, input_files: Iterable[str], root: str | Path) -> dict[str, Any]:
    files = list(input_files)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorer_version": SCORER_VERSION,
        "model": model,
        "git_revision": git_revision(root),
        "input_file_count": len(files),
        "input_files_sha256": json.dumps(
            {str(Path(path)): sha256_file(path) for path in files if Path(path).exists()},
            sort_keys=True,
        ),
        **prompt_hashes(),
    }


def metadata_rows(metadata: Mapping[str, Any]) -> list[dict[str, str]]:
    return [{"key": str(key), "value": str(value)} for key, value in sorted(metadata.items())]
