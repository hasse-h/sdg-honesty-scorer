# Bank report archive set

**Public archive note.** This public repository contains the plain-text manifests only. The original PDF, XLSX and HTML reports are not included. They remain with their publishers. `python -m reproduction` does not read those files.

The notes below describe the private working archive, where the reports were stored with Git LFS. They are kept so the manifest layout stays intelligible. Do not treat this public repository as a redistribution of the reports.


This directory records the Finnish and Ukrainian bank report archive set used for SDG honesty scoring and audit work.

**Status of the private working copy:** 184 source files (181 PDFs, 2 XLSX, 1 HTML) were stored
under `data/bank_reports/reports/` via Git LFS. They are **not** in this public repository. Manifests driving the production
Finland/Ukraine 2019-2024 classification runs live in `data/bank_reports/manifests/
bank_reports_<country>_<year>.csv` and are plain-text CSVs (not LFS-tracked). See
`../../evaluations/CURRENT_STATUS.md` for the current classification/correction status.

Large binary report files are not committed as normal Git blobs. ZIP archives and unzipped PDFs/spreadsheets are stored with Git LFS.

The expected split ZIP archive names, file counts, byte sizes, and SHA-256 checksums are recorded in `banks_archive_manifest.txt`.

## Supported layouts

### Split archive layout

```text
data/bank_reports/archives/
```

Use this for the rebuilt split ZIP files listed in `banks_archive_manifest.txt`.

### Unzipped report layout

```text
data/bank_reports/reports/Finnish banks/
data/bank_reports/reports/Ukrainian banks/
```

Use this if adding the original unzipped Drive-folder contents one report at a time. PDF, XLSX, and HTML files under `reports/` are tracked with Git LFS by `data/bank_reports/.gitattributes`.

## Recommended local upload procedure

```bash
git lfs install
python scripts/stage_bank_report_files.py /path/to/unzipped/banks_download_work
git status
git commit -m "Add bank report source files"
git push
```

The source folder passed to the script should contain `Finnish banks/` and `Ukrainian banks/` subfolders.

The manifest was generated after rebuilding smaller ZIP archives and validating each archive with Python `ZipFile.testzip()`.
