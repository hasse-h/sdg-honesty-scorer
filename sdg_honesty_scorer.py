# ruff: noqa: F401,F403,I001
"""Compatibility wrapper for the SDG Honesty Scorer CLI.

The implementation lives in the ``honesty_scorer`` package. This module keeps
the historical ``python3 sdg_honesty_scorer.py`` entrypoint and the import names
used by existing tests and notebooks.
"""

from honesty_scorer import *  # noqa: F403
from honesty_scorer.cli import cli_main


if __name__ == "__main__":
    raise SystemExit(cli_main())
