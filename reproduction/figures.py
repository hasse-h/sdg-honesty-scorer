"""Publication figures and editable table data, derived only from replayed CSVs."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

COLORS = {"finland": "#17617B", "ukraine": "#A44A30"}


def _save(fig, folder, number):
    for suffix in ("png", "svg", "pdf"):
        kwargs = {"metadata": {"Date": None}} if suffix == "svg" else {}
        if suffix == "pdf":
            kwargs = {"metadata": {"CreationDate": None, "ModDate": None}}
        fig.savefig(folder / f"figure_{number}.{suffix}", dpi=300, **kwargs)
    plt.close(fig)


def _format(value, digits=3):
    return "NA" if pd.isna(value) else f"{value:.{digits}f}"


def run(output_dir: Path) -> None:
    root = Path(output_dir)
    folder = root / "figures"
    folder.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "honesty-scorer-reproduction-v1",
            "pdf.fonttype": 42,
        }
    )
    benchmark = pd.read_csv(root / "benchmark/benchmark_thresholds.csv")
    gpt = benchmark[benchmark.model == "gpt_oss_120b"].copy()
    gpt["threshold"] = gpt.threshold.astype(int)
    jrc = benchmark[benchmark.model == "jrc_sdg_mapper"].iloc[0]
    selected = gpt[gpt.threshold == 3].iloc[0]
    fig, ax = plt.subplots(figsize=(5.8333, 3.366), layout="constrained")
    fields = ["precision", "recall", "f1", "accuracy"]
    positions = np.arange(4)
    for offset, row, label, color in [
        (-0.19, selected, "GPT-OSS 120B, priority ≥ 3", COLORS["finland"]),
        (0.19, jrc, "EU/JRC mapper", "#888888"),
    ]:
        bars = ax.bar(positions + offset, [row[k] for k in fields], 0.36, label=label, color=color)
        ax.bar_label(bars, fmt="%.3f", fontsize=7, padding=2)
    ax.set(xticks=positions, xticklabels=[v.title() for v in fields], ylim=(0, 1.14), ylabel="Micro metric")
    ax.legend(loc="upper left", frameon=False)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    _save(fig, folder, 1)

    fig, ax = plt.subplots(figsize=(5.8333, 4.0015), layout="constrained")
    ax.plot(gpt.recall, gpt.precision, "o-", color=COLORS["finland"], label="GPT-OSS thresholds")
    for _, row in gpt.iterrows():
        ax.annotate(f"≥ {row.threshold}", (row.recall, row.precision), xytext=(5, 5), textcoords="offset points")
    ax.scatter([jrc.recall], [jrc.precision], marker="s", color="#666666", label="EU/JRC mapper")
    ax.scatter(
        [selected.recall],
        [selected.precision],
        s=100,
        facecolors="none",
        edgecolors=COLORS["ukraine"],
        label="Primary threshold ≥ 3",
    )
    ax.set(xlabel="Recall", ylabel="Precision", xlim=(0.32, 1), ylim=(0.79, 1.01))
    ax.legend(loc="lower left", frameon=False)
    ax.grid(alpha=0.15)
    _save(fig, folder, 2)

    country = pd.read_csv(root / "banks/country_year.csv")
    fig, ax = plt.subplots(figsize=(5.8333, 3.0038), layout="constrained")
    positions = np.arange(len(country))
    series = [
        ("historical_raw_eligible_unique_amount_eur", -0.25, "Historical extraction", "#888888"),
        ("corrected_historical_eligible_unique_amount_eur", 0, "Earlier harness", COLORS["finland"]),
        ("eligible_unique_amount_eur", 0.25, "Source-adjudicated", "#518044"),
    ]
    for field, offset, label, color in series:
        ax.bar(positions + offset, country[field], 0.24, label=label, color=color)
    ax.set_yscale("symlog", linthresh=100)
    ax.set(
        xticks=positions,
        xticklabels=[("FI" if r.country == "finland" else "UA") + str(r.year)[2:] for r in country.itertuples()],
        ylabel="Disclosed amount (EUR)",
    )
    ax.set_yticks([0, 1000, 1e6, 1e9, 1e11], labels=["0", "1,000", "1 million", "1 billion", "100 billion"])
    ax.legend(loc="upper left", frameon=False, fontsize=6.5)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    _save(fig, folder, 3)

    fig, ax = plt.subplots(figsize=(5.7, 3.705), layout="constrained")
    for name, color in COLORS.items():
        frame = country[country.country == name]
        for column, label, style in [
            ("mean_AS_all", "all included banks", "o-"),
            ("mean_AS_non_silent", "non-silent banks", "s--"),
        ]:
            ax.plot(frame.year, frame[column], style, color=color, label=f"{name.title()}: {label}", markersize=4)
    ax.set(xlabel="Report year", ylabel="Mean AS = 1 − M/85", ylim=(0, 1))
    ax.legend(frameon=False, loc="lower left")
    ax.grid(alpha=0.15)
    _save(fig, folder, 4)

    profiles = pd.read_csv(root / "banks/country_year_sdg_profiles.csv")
    fig, axes = plt.subplots(1, 2, figsize=(5.83, 3.317), layout="constrained", sharey=True)
    cmap = matplotlib.colormaps["RdBu_r"].copy()
    cmap.set_bad("#E2E2E2")
    for ax, (name, _) in zip(axes, COLORS.items()):
        values = profiles[profiles.country == name].pivot(index="sdg", columns="year", values="gap_pp")
        im = ax.imshow(values.values, cmap=cmap, vmin=-100, vmax=100, aspect="auto", interpolation="none")
        ax.set(
            title=name.title(),
            xticks=range(6),
            xticklabels=[str(y)[2:] for y in range(2019, 2025)],
            yticks=range(17),
            yticklabels=range(1, 18),
            xlabel="Report year (20xx)",
        )
    axes[0].set_ylabel("SDG")
    fig.colorbar(im, ax=axes, label="Narrative share − finance share (pp)", shrink=0.82)
    axes[0].legend(
        handles=[Patch(facecolor="#E2E2E2", label="Undefined: no approved finance")],
        loc="upper left",
        bbox_to_anchor=(0, -0.18),
        frameon=False,
        fontsize=6.5,
    )
    _save(fig, folder, 5)

    tables = {}
    tables["1"] = [["Country", *map(str, range(2019, 2025))]] + [
        [c.title(), *[str(int(v)) for v in country[country.country == c].banks]] for c in COLORS
    ]
    tables["2"] = [["Country", "Year", "Retained SDG mentions (priority ≥ 3)", "Extracted financial rows"]] + [
        [r.country.title(), str(r.year), str(r.retained_mentions), str(r.financial_items)] for r in country.itertuples()
    ]
    tables["3"] = [
        [
            "Country",
            "Year",
            "Historical extraction / earlier harness (EUR m)",
            "Source-adjudicated amount (EUR)",
            "Eligible rows (historical → earlier → adjudicated)",
        ]
    ]
    for r in country.itertuples():
        tables["3"].append(
            [
                r.country.title(),
                str(r.year),
                f"{r.historical_raw_eligible_unique_amount_eur / 1e6:,.3f} / "
                f"{r.corrected_historical_eligible_unique_amount_eur / 1e6:,.3f}",
                f"{r.eligible_unique_amount_eur:,.2f}",
                f"{r.historical_raw_eligible_rows} → {r.corrected_historical_eligible_rows} → {r.eligible_rows}",
            ]
        )
    tables["3"].append(
        [
            "Total",
            "2019–2024",
            f"{country.historical_raw_eligible_unique_amount_eur.sum() / 1e6:,.3f} / "
            f"{country.corrected_historical_eligible_unique_amount_eur.sum() / 1e6:,.3f}",
            f"{country.eligible_unique_amount_eur.sum():,.2f}",
            f"{country.historical_raw_eligible_rows.sum()} → "
            f"{country.corrected_historical_eligible_rows.sum()} → {country.eligible_rows.sum()}",
        ]
    )
    tables["4"] = [
        ["Country", "Year", "All-bank AS", "Non-silent AS", "Non-silent n", "Silent n", "Corr. mentions–AS"]
    ] + [
        [
            r.country.title(),
            str(r.year),
            _format(r.mean_AS_all),
            _format(r.mean_AS_non_silent),
            str(r.non_silent_banks),
            str(r.silent_banks),
            _format(r.pearson_AS_retained_mentions_non_silent),
        ]
        for r in country.itertuples()
    ]
    summary = json.loads((root / "banks/summary.json").read_text())["primary"]
    tables["4"].append(
        [
            "Pooled",
            "2019–2024",
            _format(summary["mean_AS_all"]),
            _format(summary["mean_AS_non_silent"]),
            str(summary["non_silent_bank_years"]),
            str(summary["silent_bank_years"]),
            _format(summary["pearson_AS_retained_mentions_non_silent"]),
        ]
    )
    for number, name, field, factor, decimals in [
        (5, "finland", "narrative_share", 100, 1),
        (6, "finland", "finance_share", 100, 1),
        (7, "ukraine", "narrative_share", 100, 1),
        (8, "ukraine", "finance_share", 100, 1),
        (9, "finland", "finance_eur", 1, 2),
        (10, "ukraine", "finance_eur", 1, 2),
    ]:
        frame = profiles[profiles.country == name].pivot(index="sdg", columns="year", values=field)
        tables[str(number)] = [["SDG", *map(str, range(2019, 2025))]] + [
            [str(s), *[_format(v * factor, decimals) for v in frame.loc[s]]] for s in range(1, 18)
        ]
    (root / "manuscript_tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=2) + "\n")
