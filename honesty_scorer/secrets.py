"""Repo-local age secret loading.

Only ``OPENROUTER_API_KEY`` is accepted from ``.env.age``. The decrypted content
is parsed in memory and never written to a plaintext ``.env`` file.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Mapping, Optional

ALLOWED_SECRET_KEYS = {"OPENROUTER_API_KEY"}
DEFAULT_AGE_IDENTITY = Path.home() / ".api_keys" / "age.key"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_env_age_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / ".env.age"


def decrypt_repo_env(
    env_file: Optional[Path] = None,
    identity_file: Optional[Path] = None,
) -> Dict[str, str]:
    path = env_file or repo_env_age_path()
    if not path.exists():
        return {}

    age_bin = _age_binary()
    identity = identity_file or DEFAULT_AGE_IDENTITY
    if not identity.exists():
        raise RuntimeError(f"age identity file not found: {identity}")

    result = subprocess.run(
        [age_bin, "-d", "-i", str(identity), str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    values = _parse_env_lines(result.stdout)
    unexpected = sorted(set(values) - ALLOWED_SECRET_KEYS)
    if unexpected:
        raise RuntimeError(f"{path} contains unsupported secret keys: {', '.join(unexpected)}")
    return values


def load_repo_env(
    env_file: Optional[Path] = None,
    identity_file: Optional[Path] = None,
    *,
    override: bool = False,
) -> Mapping[str, str]:
    values = decrypt_repo_env(env_file=env_file, identity_file=identity_file)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values


def load_openrouter_api_key(
    api_key: Optional[str] = None,
    env_file: Optional[Path] = None,
    identity_file: Optional[Path] = None,
) -> str:
    if api_key is not None:
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required in environment or repo-local .env.age")
        return api_key

    explicit = os.getenv("OPENROUTER_API_KEY", "")
    if explicit:
        return explicit

    values = load_repo_env(env_file=env_file, identity_file=identity_file)
    loaded = values.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
    if not loaded:
        path = env_file or repo_env_age_path()
        raise RuntimeError(f"OPENROUTER_API_KEY is required in environment or repo-local {path}")
    return loaded


def _parse_env_lines(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeError(f"Invalid .env.age line for key-value secret: {raw_line!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise RuntimeError("Invalid .env.age line with empty key")
        values[key] = _strip_shell_quotes(value.strip())
    return values


def _strip_shell_quotes(value: str) -> str:
    if not value:
        return value
    try:
        parts = shlex.split(value, posix=True)
    except ValueError:
        return value.strip("\"'")
    return parts[0] if len(parts) == 1 else value


def _age_binary() -> str:
    candidates = [
        os.getenv("AGE_BIN", ""),
        "/opt/homebrew/bin/age",
        "/usr/local/bin/age",
        "age",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if "/" in candidate:
            if Path(candidate).exists():
                return candidate
        else:
            return candidate
    raise RuntimeError("age binary not found; install age or set AGE_BIN")
