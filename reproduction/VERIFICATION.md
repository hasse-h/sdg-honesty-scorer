# Reproduction verification — 13 September 2026

The primary workflow was replayed from an exported, isolated source snapshot with a fresh environment installed from `uv.lock`:

```bash
uv sync --frozen --extra reproduce --extra dev
uv run --frozen --extra reproduce python -m reproduction --output /path/to/results
uv run --frozen --extra reproduce --extra dev python -m unittest discover -s tests -v
```

- All 78 unit tests passed in both the working checkout and the fresh environment.
- All 23 analytical CSV files matched the recorded outputs, using relative and absolute tolerances of `1e-12`.
- `manuscript_tables.json` matched exactly. The complete analytical summary and input/provenance records matched at the same numerical tolerance, excluding the deliberately different runtime-environment fields.
- The recorded output used Python 3.9.6, NumPy 2.0.2, pandas 2.3.3 and Matplotlib 3.9.4. The fresh replay used Python 3.11.5, NumPy 2.4.4, pandas 2.3.3 and Matplotlib 3.11.2. Figure binary equality across these rendering versions is not claimed.
- Frozen analytical input checksums passed. The main reproduction driver blocks network connections; no model calls, API keys, original PDFs or fresh translations were needed for numerical replay.
- Ruff passed for the Python files changed for this reproduction work. Historical scripts elsewhere in the repository retain pre-existing lint findings; a repository-wide clean lint result is not claimed.
- The final dependency lock requires Python 3.11 or newer. The commit security hook initially identified vulnerable legacy PDF/image dependencies. After updating cryptography to 50.0.1, pdfminer-six to 20260107, pdfplumber to 0.11.10 and Pillow to 12.3.0, `uv audit --locked` reported no known vulnerabilities or adverse project statuses in 30 packages. The fresh tests and numerical replay were repeated using this corrected lock.

Primary outputs contain 142 source-audited bank-years after ten exclusions. Review of all 35 historically retained financial claims accepts two payments with a unique total of EUR 7,031.77; the separate full-tag exposure is EUR 7,813.54. These are conditional results from the retained cached claims, not an exhaustive inventory of actual bank activity.

## Export a reviewer snapshot

```bash
python -m reproduction.export_archive --output reproduction_archive.zip
python -m reproduction.export_archive --output reproduction_archive_anonymised.zip --anonymised
```

The archives include replay code, locked dependencies, frozen analytical inputs, adjudications, generated tables/figures and instructions. `ARCHIVE_MANIFEST.json` records the source commit and SHA-256 of every included file. The anonymised option removes the repository URL from cover material; it leaves analytical inputs intact. Original PDF reports, git history, secrets and document-review material are excluded. Installation needs network access for dependencies; the numerical replay is offline.

Successful replay establishes computational consistency. It does not validate financial-extraction recall, translation quality, bank-report centrality, observed transactions, causal effects or SDG-washing detection. See the source reviews and reproduction guide for these limits.
