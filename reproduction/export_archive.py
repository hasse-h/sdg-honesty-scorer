"""Export code, frozen analytical inputs, outputs and replay instructions for review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from reproduction.__main__ import input_checksums


def export(repo: Path, destination: Path, anonymised: bool = False) -> dict:
    locked = json.loads((repo / "reproduction/input_checksums.json").read_text())
    if input_checksums(repo) != locked:
        raise ValueError("Frozen analytical input checksums do not match")
    selected = set(locked)
    for folder in ("honesty_scorer", "reproduction", "tests"):
        selected.update(p.relative_to(repo).as_posix() for p in (repo / folder).glob("*.py"))
    if anonymised:
        # Packaging is unnecessary for replay and contains the author repository URL.
        selected.discard("reproduction/export_archive.py")
    selected.update({"pyproject.toml", "uv.lock", "sdg_honesty_scorer.py", "reproduction/input_checksums.json"})
    selected.update({"reproduction/finance_review.md", "reproduction/source_year_review.md"})
    selected.add("reproduction/VERIFICATION.md")
    selected.update(
        p.relative_to(repo).as_posix()
        for p in (repo / "reproduction/output").rglob("*")
        if p.is_file()
    )
    selected.add("evaluations/sdg_benchmark/run_honesty_classifier_sdg_benchmark.py")
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable in exported snapshot"
    readme = (
        "# SDG screening reproduction archive\n\n"
        "Extract this archive, enter its root folder, then run:\n\n"
        "```bash\nuv sync --frozen --extra reproduce --extra dev\n"
        "uv run --frozen --extra reproduce python -m reproduction\n"
        "uv run --frozen --extra reproduce --extra dev python -m unittest discover -s tests -v\n```\n\n"
        "Installation downloads dependencies; numerical replay itself is offline and needs no API keys or PDFs.\n\n"
        "See reproduction/README.md for methods, source rights, limitations and outputs. "
        "Original PDFs, git history, secrets, document review material and unrelated repository files are excluded.\n"
    )
    guide = (repo / "reproduction/README.md").read_text()
    if anonymised:
        guide = guide.replace("Honesty_Scorer", "Reproduction Archive")
        start = guide.index("[Study repository]")
        end = guide.index("\n\n[External SDG benchmark]", start)
        guide = (
            guide[:start]
            + "The repository link is supplied separately to the editor for anonymised review."
            + guide[end:]
        )
    else:
        readme += "\nRepository: https://github.com/hasse-h/Honesty_Scorer\n"
    files = {p: (repo / p).read_bytes() for p in sorted(selected)}
    files["README.md"] = readme.encode()
    files["reproduction/README.md"] = guide.encode()
    manifest = {
        "schema_version": 1,
        "purpose": "Numerical reproduction from frozen cached inputs",
        "source_revision": revision,
        "anonymised_cover_material": anonymised,
        "analytical_inputs_unmodified": True,
        "sha256": {p: hashlib.sha256(data).hexdigest() for p, data in sorted(files.items())},
    }
    files["ARCHIVE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo("reproduction_archive/" + name, date_time=(2026, 9, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {
        "path": str(destination),
        "files": len(files),
        "source_revision": revision,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--anonymised", action="store_true")
    args = parser.parse_args()
    print(json.dumps(export(Path(__file__).resolve().parents[1], args.output.resolve(), args.anonymised), indent=2))


if __name__ == "__main__":
    main()
