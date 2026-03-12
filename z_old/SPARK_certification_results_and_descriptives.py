 
"""
Descriptive Statistics for Bronze, Silver, and Gold Certified Laboratories
===========================================================================
This script computes descriptive statistics on the number of Bronze-, Silver-,
and Gold-certified laboratories based on baseline (BL) and endline (EL) survey
data stored in individual_processed_1.csv.

Certification logic (SPARKAwardChecker, 70% threshold)
-------------------------------------------------------
A laboratory is certified at a tier if it answered "Yes" to at least 70% of
the questions belonging to that tier at the respective time point:

    Tier    Total Q   70% threshold   Min. "Yes" required
    ------  --------  --------------  --------------------
    Bronze     16        11.2               12
    Silver     18        12.6               13
    Gold       15        10.5               11

Outputs
-------
* Console output with formatted tables
* cert_stats_summary.csv        - certification counts and percentages
* score_stats_summary.csv       - descriptive statistics of the scores
* score_change_summary.csv      - score change BL to EL (endline sub-sample)
* cert_transition_summary.csv   - certification transitions BL to EL
""" 

import sys
import warnings
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Configuration  --  adjust CSV_PATH and OUTPUT_DIR to my local setup
# ---------------------------------------------------------------------------
CODE_ROOT = Path(__file__).parents[2]
sys.path.append(str(CODE_ROOT))
import config_nils
 
#CSV_PATH   = config_nils.PROCESSED_DATA / "individual_processed_1.csv"
CSV_PATH = Path("/Volumes/rutnam_leaf rct/data/16_Processed_Data/individual_processed_1.csv") 
if not CSV_PATH.exists():
    raise FileNotFoundError(f"File not found. Is the network drive mounted? -> {CSV_PATH}")

df = pd.read_csv(CSV_PATH)

OUTPUT_DIR = Path(__file__).parent

# Certification thresholds (70% rule, ceiling applied)
# Bronze: ceil(16 * 0.70) = 12
# Silver: ceil(18 * 0.70) = 13
# Gold:   ceil(15 * 0.70) = 11

CERT_THRESHOLD_PCT = 0.70
TIER_TOTAL_Q = {
    "bronze": 16,
    "silver": 18,
    "gold"  : 15,
}
CERT_MIN_YES = {
    tier: ceil(total * CERT_THRESHOLD_PCT)
    for tier, total in TIER_TOTAL_Q.items()
}

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df = pd.read_csv(CSV_PATH, header=0, low_memory=False)  
print(f"Dataset loaded: {len(df)} laboratories, {len(df.columns)} columns.\n")

# ---------------------------------------------------------------------------
# Identify question columns per tier and time point
# ---------------------------------------------------------------------------
def get_question_cols(df, tier, timepoint):
    """Return sorted list of question columns for a given tier and time point."""
    return sorted(
        c for c in df.columns
        if c.startswith(f"{tier}_q")
        and c.endswith(f"_{timepoint}")
        and not c.endswith("_co")
    )

tiers      = ["bronze", "silver", "gold"]
timepoints = ["bl", "el"]

question_cols = {
    (tier, tp): get_question_cols(df, tier, tp)
    for tier in tiers
    for tp   in timepoints
}

# Print certification thresholds
print("Certification thresholds (SPARKAwardChecker, 70% rule):")
header = f"{'Tier':<10} {'Total Q':>8} {'70% of Q':>10} {'Min Yes':>8}"
print(header)
print("-" * len(header))
for tier in tiers:
    total = TIER_TOTAL_Q[tier]
    pct   = total * CERT_THRESHOLD_PCT
    miny  = CERT_MIN_YES[tier]
    print(f"{tier.capitalize():<10} {total:>8} {pct:>10.1f} {miny:>8}")
print()

# ---------------------------------------------------------------------------
# Determine which labs have endline data
# ---------------------------------------------------------------------------
el_indicator_cols = question_cols[("bronze", "el")]
has_endline = df[el_indicator_cols].notna().any(axis=1)

df_bl = df.copy()               # all labs (baseline)
df_el = df[has_endline].copy()  # only labs with endline data

print(f"Labs with baseline data : {len(df_bl)}")
print(f"Labs with endline data  : {len(df_el)}")
print()

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def compute_scores(data, tier, tp):
    """Count 'Yes' answers per lab for a given tier and time point."""
    cols = question_cols[(tier, tp)]
    return (data[cols] == "Yes").sum(axis=1)

def is_certified(data, tier, tp):
    """Return boolean Series: True if lab meets the 70% threshold."""
    return compute_scores(data, tier, tp) >= CERT_MIN_YES[tier]

# Attach score and certification columns
for tier in tiers:
    df_bl[f"{tier}_score_bl"]     = compute_scores(df_bl, tier, "bl")
    df_bl[f"{tier}_certified_bl"] = is_certified(df_bl, tier, "bl")

    df_el[f"{tier}_score_bl"]     = compute_scores(df_el, tier, "bl")
    df_el[f"{tier}_score_el"]     = compute_scores(df_el, tier, "el")
    df_el[f"{tier}_certified_bl"] = is_certified(df_el, tier, "bl")
    df_el[f"{tier}_certified_el"] = is_certified(df_el, tier, "el")

# ---------------------------------------------------------------------------
# Section 1 - Certification counts and percentages (overall)
# ---------------------------------------------------------------------------
print("=" * 70)
print("SECTION 1: Number and Percentage of Certified Laboratories (Overall)")
print("=" * 70)

rows_cert = []
for tier in tiers:
    n_bl_total = len(df_bl)
    n_bl_cert  = int(df_bl[f"{tier}_certified_bl"].sum())
    pct_bl     = n_bl_cert / n_bl_total * 100

    n_el_total = len(df_el)
    n_el_cert  = int(df_el[f"{tier}_certified_el"].sum())
    pct_el     = n_el_cert / n_el_total * 100

    rows_cert.append({
        "Tier"             : tier.capitalize(),
        "Min Yes (70%)"    : CERT_MIN_YES[tier],
        "BL N"             : n_bl_total,
        "BL Certified (n)" : n_bl_cert,
        "BL Certified (%)" : round(pct_bl, 1),
        "EL N"             : n_el_total,
        "EL Certified (n)" : n_el_cert,
        "EL Certified (%)" : round(pct_el, 1),
    })

cert_df = pd.DataFrame(rows_cert)
print(cert_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Section 2 - Certification counts by Treatment Status
# ---------------------------------------------------------------------------
print("=" * 70)
print("SECTION 2: Certified Laboratories by Treatment Status")
print("=" * 70)

rows_treat = []
for tier in tiers:
    for group, label in [("treatment", "Treatment"), ("control", "Control")]:
        sub_bl = df_bl[df_bl["Treatment Status"] == group]
        n_bl   = len(sub_bl)
        c_bl   = int(sub_bl[f"{tier}_certified_bl"].sum())
        p_bl   = c_bl / n_bl * 100 if n_bl > 0 else np.nan

        sub_el = df_el[df_el["Treatment Status"] == group]
        n_el   = len(sub_el)
        c_el   = int(sub_el[f"{tier}_certified_el"].sum())
        p_el   = c_el / n_el * 100 if n_el > 0 else np.nan

        rows_treat.append({
            "Tier"             : tier.capitalize(),
            "Group"            : label,
            "BL N"             : n_bl,
            "BL Certified (n)" : c_bl,
            "BL Certified (%)" : round(p_bl, 1),
            "EL N"             : n_el,
            "EL Certified (n)" : c_el,
            "EL Certified (%)" : round(p_el, 1) if not np.isnan(p_el) else "n/a",
        })

treat_df = pd.DataFrame(rows_treat)
print(treat_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Section 3 - Descriptive statistics of scores - Baseline (all labs)
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"SECTION 3: Descriptive Statistics of Scores - Baseline (all labs, n={len(df_bl)})")
print("=" * 70)

score_rows_bl = []
for tier in tiers:
    s     = df_bl[f"{tier}_score_bl"]
    max_q = TIER_TOTAL_Q[tier]
    score_rows_bl.append({
        "Tier"   : tier.capitalize(),
        "Max Q"  : max_q,
        "N"      : int(s.count()),
        "Mean"   : round(s.mean(), 2),
        "SD"     : round(s.std(), 2),
        "Min"    : int(s.min()),
        "Q1"     : round(s.quantile(0.25), 1),
        "Median" : round(s.median(), 1),
        "Q3"     : round(s.quantile(0.75), 1),
        "Max"    : int(s.max()),
        "Mean %" : round(s.mean() / max_q * 100, 1),
    })

score_bl_df = pd.DataFrame(score_rows_bl)
print(score_bl_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Section 4 - Descriptive statistics of scores - Endline sub-sample
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"SECTION 4: Descriptive Statistics of Scores - Endline sub-sample (n={len(df_el)})")
print("=" * 70)

score_rows_el = []
for tier in tiers:
    for tp, label in [("bl", "BL"), ("el", "EL")]:
        s     = df_el[f"{tier}_score_{tp}"]
        max_q = TIER_TOTAL_Q[tier]
        score_rows_el.append({
            "Tier"      : tier.capitalize(),
            "Timepoint" : label,
            "Max Q"     : max_q,
            "N"         : int(s.count()),
            "Mean"      : round(s.mean(), 2),
            "SD"        : round(s.std(), 2),
            "Min"       : int(s.min()),
            "Q1"        : round(s.quantile(0.25), 1),
            "Median"    : round(s.median(), 1),
            "Q3"        : round(s.quantile(0.75), 1),
            "Max"       : int(s.max()),
            "Mean %"    : round(s.mean() / max_q * 100, 1),
        })

score_el_df = pd.DataFrame(score_rows_el)
print(score_el_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Section 5 - Score change BL to EL (endline sub-sample)
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"SECTION 5: Score Change BL to EL (endline sub-sample, n={len(df_el)})")
print("=" * 70)

change_rows = []
for tier in tiers:
    diff = df_el[f"{tier}_score_el"] - df_el[f"{tier}_score_bl"]
    change_rows.append({
        "Tier"        : tier.capitalize(),
        "Mean Delta"  : round(diff.mean(), 2),
        "SD Delta"    : round(diff.std(), 2),
        "Min Delta"   : int(diff.min()),
        "Max Delta"   : int(diff.max()),
        "N improved"  : int((diff > 0).sum()),
        "N unchanged" : int((diff == 0).sum()),
        "N declined"  : int((diff < 0).sum()),
    })

change_df = pd.DataFrame(change_rows)
print(change_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Section 6 - Certification transitions BL to EL (endline sub-sample)
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"SECTION 6: Certification Transitions BL to EL (endline sub-sample, n={len(df_el)})")
print("=" * 70)

trans_rows = []
for tier in tiers:
    cert_bl = df_el[f"{tier}_certified_bl"]
    cert_el = df_el[f"{tier}_certified_el"]
    trans_rows.append({
        "Tier"             : tier.capitalize(),
        "BL cert. (n)"     : int(cert_bl.sum()),
        "EL cert. (n)"     : int(cert_el.sum()),
        "Gained cert. (n)" : int((~cert_bl & cert_el).sum()),
        "Lost cert. (n)"   : int((cert_bl & ~cert_el).sum()),
        "Stayed cert. (n)" : int((cert_bl & cert_el).sum()),
        "Never cert. (n)"  : int((~cert_bl & ~cert_el).sum()),
    })

trans_df = pd.DataFrame(trans_rows)
print(trans_df.to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Save outputs to CSV
# ---------------------------------------------------------------------------
cert_out   = OUTPUT_DIR / "cert_stats_summary.csv"
score_out  = OUTPUT_DIR / "score_stats_summary.csv"
change_out = OUTPUT_DIR / "score_change_summary.csv"
trans_out  = OUTPUT_DIR / "cert_transition_summary.csv"

cert_df.to_csv(cert_out, index=False)
pd.concat(
    [score_bl_df.assign(Sample="All labs (BL only)"),
     score_el_df.assign(Sample="Endline sub-sample")],
    ignore_index=True,
).to_csv(score_out, index=False)
change_df.to_csv(change_out, index=False)
trans_df.to_csv(trans_out, index=False)

print("Outputs saved:")
for p in [cert_out, score_out, change_out, trans_out]:
    print(f"  {p}")
    

# ---------------------------------------------------------------------------
# Section 7 - List of all certified laboratories by tier and time point
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("SECTION 7: Certified Laboratories by Tier and Time Point")
print("=" * 70)

ID_COLS = ["labgroupid", "Lab Group", "Faculty", "Institute", "Professor", "Treatment Status"]

cert_lab_rows = []
for tier in tiers:
    # --- Baseline (all labs) ---
    mask_bl = df_bl[f"{tier}_certified_bl"]
    labs_bl = df_bl.loc[mask_bl, ID_COLS].copy()
    labs_bl["Tier"]      = tier.capitalize()
    labs_bl["Timepoint"] = "BL"
    labs_bl["Score"]     = df_bl.loc[mask_bl, f"{tier}_score_bl"].values
    labs_bl["Max Q"]     = TIER_TOTAL_Q[tier]

    # --- Endline (endline sub-sample only) ---
    mask_el = df_el[f"{tier}_certified_el"]
    labs_el = df_el.loc[mask_el, ID_COLS].copy()
    labs_el["Tier"]      = tier.capitalize()
    labs_el["Timepoint"] = "EL"
    labs_el["Score"]     = df_el.loc[mask_el, f"{tier}_score_el"].values
    labs_el["Max Q"]     = TIER_TOTAL_Q[tier]

    cert_lab_rows.append(labs_bl)
    cert_lab_rows.append(labs_el)

    # Print per tier
    print(f"\n{tier.upper()} - Baseline (threshold: {CERT_MIN_YES[tier]}/{TIER_TOTAL_Q[tier]}, n={mask_bl.sum()})")
    if mask_bl.sum() > 0:
        print(labs_bl[["labgroupid", "Lab Group", "Faculty", "Professor",
                        "Treatment Status", "Score", "Max Q"]].to_string(index=False))
    else:
        print("  (none)")

    print(f"\n{tier.upper()} - Endline (threshold: {CERT_MIN_YES[tier]}/{TIER_TOTAL_Q[tier]}, n={mask_el.sum()})")
    if mask_el.sum() > 0:
        print(labs_el[["labgroupid", "Lab Group", "Faculty", "Professor",
                        "Treatment Status", "Score", "Max Q"]].to_string(index=False))
    else:
        print("  (none)")

# Save full certified-labs table
cert_labs_df = pd.concat(cert_lab_rows, ignore_index=True)
cert_labs_out = OUTPUT_DIR / "certified_labs_list.csv"
cert_labs_df.to_csv(cert_labs_out, index=False)
print(f"\nCertified labs list saved to: {cert_labs_out}")

 
"""
Presentation-ready visualisations for SPARK certification data
==============================================================
Produces four publication-quality PNG figures (300 dpi, transparent background):

  fig1_certified_counts.png      - Grouped bar chart: n certified labs BL vs EL
  fig2_certified_pct.png         - Grouped bar chart: % certified labs BL vs EL
  fig3_score_distribution.png    - Box plots of scores BL vs EL (endline sub-sample)
  fig4_score_change.png          - Diverging bar chart: improved / unchanged / declined
"""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CODE_ROOT = Path(__file__).parents[2]
sys.path.append(str(CODE_ROOT))
import config_nils
CSV_PATH = Path("/Volumes/rutnam_leaf rct/data/16_Processed_Data/individual_processed_1.csv") 
#CSV_PATH = Path("/Users/nhandl/Library/CloudStorage/OneDrive-UniversitätZürichUZH/Dateien von Daphne Rutnam - UZH Carbon Neutrality/11_Analysis/1_Code") / "individual_processed_1.csv"
OUTPUT_DIR = Path(__file__).parent / "Nils"

CERT_THRESHOLD_PCT = 0.70
TIER_TOTAL_Q = {"bronze": 16, "silver": 18, "gold": 15}
CERT_MIN_YES = {t: ceil(q * CERT_THRESHOLD_PCT) for t, q in TIER_TOTAL_Q.items()}

# Colour palette (presentation-friendly)
TIER_COLORS = {
    "bronze": "#CD7F32",   # bronze
    "silver": "#A8A9AD",   # silver
    "gold"  : "#D4AF37",   # gold
}
BL_ALPHA = 0.55   # lighter shade for baseline bars
EL_ALPHA = 1.00   # full shade for endline bars

TIERS      = ["bronze", "silver", "gold"]
TIER_LABELS = ["Bronze", "Silver", "Gold"]

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family"      : "sans-serif",
    "font.size"        : 13,
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "axes.titlesize"   : 15,
    "axes.titleweight" : "bold",
    "axes.labelsize"   : 13,
    "xtick.labelsize"  : 12,
    "ytick.labelsize"  : 12,
    "legend.fontsize"  : 11,
    "figure.dpi"       : 150,
})

# ---------------------------------------------------------------------------
# Load & prepare data
# ---------------------------------------------------------------------------
df = pd.read_csv(CSV_PATH, header=0, low_memory=False)

def get_q_cols(df, tier, tp):
    return sorted(c for c in df.columns
                  if c.startswith(f"{tier}_q") and c.endswith(f"_{tp}")
                  and not c.endswith("_co"))

question_cols = {(t, tp): get_q_cols(df, t, tp)
                 for t in TIERS for tp in ["bl", "el"]}

has_endline = df[question_cols[("bronze", "el")]].notna().any(axis=1)
df_bl = df.copy()
df_el = df[has_endline].copy()

def scores(data, tier, tp):
    return (data[question_cols[(tier, tp)]] == "Yes").sum(axis=1)

def certified(data, tier, tp):
    return scores(data, tier, tp) >= CERT_MIN_YES[tier]

for t in TIERS:
    df_bl[f"{t}_score_bl"]     = scores(df_bl, t, "bl")
    df_bl[f"{t}_certified_bl"] = certified(df_bl, t, "bl")
    df_el[f"{t}_score_bl"]     = scores(df_el, t, "bl")
    df_el[f"{t}_score_el"]     = scores(df_el, t, "el")
    df_el[f"{t}_certified_bl"] = certified(df_el, t, "bl")
    df_el[f"{t}_certified_el"] = certified(df_el, t, "el")

n_bl = len(df_bl)   # 138
n_el = len(df_el)   # 50

cert_n_bl  = [int(df_bl[f"{t}_certified_bl"].sum()) for t in TIERS]
cert_n_el  = [int(df_el[f"{t}_certified_el"].sum()) for t in TIERS]
cert_pct_bl = [v / n_bl * 100 for v in cert_n_bl]
cert_pct_el = [v / n_el * 100 for v in cert_n_el]

# ---------------------------------------------------------------------------
# Helper: annotate bars
# ---------------------------------------------------------------------------
def annotate_bars(ax, bars, fmt="{:.0f}"):
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.15,
                    fmt.format(h), ha="center", va="bottom",
                    fontsize=11, fontweight="bold", color="#333333")

# ---------------------------------------------------------------------------
# Figure 1 – Certified labs: absolute counts
# ---------------------------------------------------------------------------
x      = np.arange(len(TIERS))
width  = 0.35

fig, ax = plt.subplots(figsize=(8, 5))
bars_bl = ax.bar(x - width / 2, cert_n_bl, width,
                 color=[TIER_COLORS[t] for t in TIERS],
                 alpha=BL_ALPHA, label=f"Baseline (n={n_bl})", zorder=3)
bars_el = ax.bar(x + width / 2, cert_n_el, width,
                 color=[TIER_COLORS[t] for t in TIERS],
                 alpha=EL_ALPHA, label=f"Endline (n={n_el})", zorder=3)

annotate_bars(ax, bars_bl)
annotate_bars(ax, bars_el)

ax.set_xticks(x)
ax.set_xticklabels(TIER_LABELS)
ax.set_ylabel("Number of certified laboratories")
ax.set_title("Certified Laboratories by Tier\n(Baseline vs. Endline)")
ax.set_ylim(0, max(cert_n_bl + cert_n_el) * 1.35)
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
ax.legend(frameon=False)

fig.tight_layout()
out1 = OUTPUT_DIR / "fig1_certified_counts.png"
fig.savefig(out1, dpi=300, bbox_inches="tight", transparent=True)
plt.close(fig)
print(f"Saved: {out1}")

# ---------------------------------------------------------------------------
# Figure 2 – Certified labs: percentages
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))
bars_bl = ax.bar(x - width / 2, cert_pct_bl, width,
                 color=[TIER_COLORS[t] for t in TIERS],
                 alpha=BL_ALPHA, label=f"Baseline (n={n_bl})", zorder=3)
bars_el = ax.bar(x + width / 2, cert_pct_el, width,
                 color=[TIER_COLORS[t] for t in TIERS],
                 alpha=EL_ALPHA, label=f"Endline (n={n_el})", zorder=3)

annotate_bars(ax, bars_bl, fmt="{:.1f}%")
annotate_bars(ax, bars_el, fmt="{:.1f}%")

ax.set_xticks(x)
ax.set_xticklabels(TIER_LABELS)
ax.set_ylabel("Share of certified laboratories (%)")
ax.set_title("Percentage of Certified Laboratories by Tier\n(Baseline vs. Endline)")
ax.set_ylim(0, max(cert_pct_bl + cert_pct_el) * 1.45)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
ax.legend(frameon=False)

fig.tight_layout()
out2 = OUTPUT_DIR / "fig2_certified_pct.png"
fig.savefig(out2, dpi=300, bbox_inches="tight", transparent=True)
plt.close(fig)
print(f"Saved: {out2}")

# ---------------------------------------------------------------------------
# Figure 3 – Score distributions: box plots BL vs EL (endline sub-sample)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=False)

for i, (tier, label) in enumerate(zip(TIERS, TIER_LABELS)):
    ax    = axes[i]
    color = TIER_COLORS[tier]
    max_q = TIER_TOTAL_Q[tier]
    thresh = CERT_MIN_YES[tier]

    data_bl = df_el[f"{tier}_score_bl"].values
    data_el = df_el[f"{tier}_score_el"].values

    bp = ax.boxplot(
        [data_bl, data_el],
        labels=["BL", "EL"],
        patch_artist=True,
        medianprops=dict(color="white", linewidth=2.5),
        whiskerprops=dict(color="#555555"),
        capprops=dict(color="#555555"),
        flierprops=dict(marker="o", markerfacecolor=color,
                        markeredgecolor="none", markersize=5, alpha=0.6),
        widths=0.45,
        zorder=3,
    )
    for j, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(color)
        patch.set_alpha(BL_ALPHA if j == 0 else EL_ALPHA)

    # Certification threshold line
    ax.axhline(thresh, color="#E63946", linewidth=1.5,
               linestyle="--", zorder=4, label=f"Threshold ({thresh}/{max_q})")

    ax.set_title(f"{label}", fontweight="bold")
    ax.set_ylabel("Score (# Yes answers)" if i == 0 else "")
    ax.set_ylim(-0.5, max_q + 1)
    ax.set_yticks(range(0, max_q + 1, 3))
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax.legend(fontsize=10, frameon=False, loc="upper left")

fig.suptitle("Score Distributions by Tier — Endline Sub-sample (n=50)",
             fontsize=15, fontweight="bold", y=1.02)
fig.tight_layout()
out3 = OUTPUT_DIR / "fig3_score_distribution.png"
fig.savefig(out3, dpi=300, bbox_inches="tight", transparent=True)
plt.close(fig)
print(f"Saved: {out3}")

# ---------------------------------------------------------------------------
# Figure 4 – Score change BL → EL: stacked bar (improved / unchanged / declined)
# ---------------------------------------------------------------------------
n_improved  = []
n_unchanged = []
n_declined  = []

for tier in TIERS:
    diff = df_el[f"{tier}_score_el"] - df_el[f"{tier}_score_bl"]
    n_improved.append(int((diff > 0).sum()))
    n_unchanged.append(int((diff == 0).sum()))
    n_declined.append(int((diff < 0).sum()))

fig, ax = plt.subplots(figsize=(8, 5))

bar_w = 0.5
bars_imp = ax.bar(x, n_improved,  bar_w, label="Improved",  color="#2A9D8F", zorder=3)
bars_unc = ax.bar(x, n_unchanged, bar_w, label="Unchanged", color="#E9C46A",
                  bottom=n_improved, zorder=3)
bars_dec = ax.bar(x, n_declined,  bar_w, label="Declined",  color="#E63946",
                  bottom=[i + u for i, u in zip(n_improved, n_unchanged)], zorder=3)

# Annotate segments
for bars, vals, bottoms in [
    (bars_imp, n_improved,  [0] * 3),
    (bars_unc, n_unchanged, n_improved),
    (bars_dec, n_declined,  [i + u for i, u in zip(n_improved, n_unchanged)]),
]:
    for bar, val, bot in zip(bars, vals, bottoms):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bot + val / 2,
                    str(val), ha="center", va="center",
                    fontsize=11, fontweight="bold", color="white")

ax.set_xticks(x)
ax.set_xticklabels(TIER_LABELS)
ax.set_ylabel("Number of laboratories")
ax.set_title("Score Change BL \u2192 EL by Tier\n(Endline Sub-sample, n=50)")
ax.set_ylim(0, n_el * 1.1)
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
ax.legend(frameon=False, loc="upper right")

fig.tight_layout()
out4 = OUTPUT_DIR / "fig4_score_change.png"
out4.unlink(missing_ok=True) 
fig.savefig(out4, dpi=300, bbox_inches="tight", transparent=True)
plt.close(fig)
print(f"Saved: {out4}")

print("\nAll figures saved successfully.")



###### DESCRIPTIVE STATISTICS

"""
Survey Analysis Script
======================
Generates the following outputs from individual_processed_1.csv:
  1. Histograms / summary tables for all survey questions
  2. Lab characteristics summary
  3. Equipment analysis (all equipment questions)
  4. Energy use (total + by equipment type)
  5. Communication & collaboration
  6. SPARK questions (BL + EL) – Bronze / Silver / Gold
  7. Awareness
  8. Balance tables

All figures are saved as PNG files; all tables are saved as CSV files.
A single multi-page PDF report is also produced.
"""

import os
import re
import warnings
import textwrap

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────────
DATA_PATH = Path("/Volumes/rutnam_leaf rct/data/16_Processed_Data/individual_processed_1.csv") 
OUT_DIR = Path(__file__).parent / "Nils"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#DATA_PATH  = os.path.join(SCRIPT_DIR, "individual_processed_1.csv")
#OUT_DIR    = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

PDF_PATH = os.path.join(OUT_DIR, "survey_report.pdf")


# ── colour palette ─────────────────────────────────────────────────────────────
PALETTE = {
    "Yes":                    "#4CAF50",
    "No":                     "#F44336",
    "I don't know":           "#9E9E9E",
    "Not applicable":         "#BDBDBD",
    "Not sure":               "#FF9800",
    "Strongly agree":         "#1565C0",
    "Agree":                  "#42A5F5",
    "Neither agree nor disagree": "#90A4AE",
    "Disagree":               "#EF9A9A",
    "Strongly disagree":      "#B71C1C",
    "Always":                 "#1B5E20",
    "Frequently":             "#66BB6A",
    "Monthly":                "#FFA726",
    "Weekly":                 "#29B6F6",
    "Daily":                  "#7E57C2",
    "Less than monthly":      "#EF5350",
    "We never use the lab space at the same time": "#BDBDBD",
    "Rarely":                 "#FF8A65",
    "0-3kg":                  "#A5D6A7",
    "4-6kg":                  "#66BB6A",
    "7-9kg":                  "#FFA726",
    "10-12kg":                "#EF5350",
    "Other (write in cell below):": "#CE93D8",
}
DEFAULT_COLORS = plt.cm.tab20.colors

def cat_color(cat):
    return PALETTE.get(str(cat), DEFAULT_COLORS[hash(str(cat)) % len(DEFAULT_COLORS)])


# ── helpers ────────────────────────────────────────────────────────────────────
def wrap(text, width=30):
    return "\n".join(textwrap.wrap(str(text), width))

def save_fig(fig, name):
    path = os.path.join(FIG_DIR, f"{name}.png")
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return path

def save_table(df, name):
    path = os.path.join(TAB_DIR, f"{name}.csv")
    df.to_csv(path)
    return path

def freq_table(series, name=None):
    """Return a frequency + percentage table for a categorical series."""
    vc = series.dropna().value_counts()
    pct = (vc / vc.sum() * 100).round(1)
    tbl = pd.DataFrame({"Count": vc, "Percent (%)": pct})
    tbl.index.name = name or series.name
    return tbl

def bar_chart(series, title, xlabel="", ylabel="Count", figsize=(7, 4),
              horizontal=False, wrap_labels=True, color_map=True):
    """Generic bar chart for a categorical series."""
    vc = series.dropna().value_counts().sort_index()
    labels = [wrap(l, 25) if wrap_labels else str(l) for l in vc.index]
    colors = [cat_color(l) for l in vc.index] if color_map else DEFAULT_COLORS[:len(vc)]

    fig, ax = plt.subplots(figsize=figsize)
    if horizontal:
        bars = ax.barh(labels, vc.values, color=colors, edgecolor="white")
        ax.set_xlabel(ylabel)
        ax.set_ylabel(xlabel)
        for bar, val in zip(bars, vc.values):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{val} ({val/vc.sum()*100:.0f}%)", va="center", fontsize=8)
        ax.set_xlim(0, vc.max() * 1.25)
    else:
        bars = ax.bar(labels, vc.values, color=colors, edgecolor="white")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        for bar, val in zip(bars, vc.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"{val}\n({val/vc.sum()*100:.0f}%)", ha="center", va="bottom", fontsize=8)
        ax.set_ylim(0, vc.max() * 1.3)
        plt.xticks(rotation=30, ha="right")

    ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig

def stacked_bar_bl_el(df, bl_col, el_col, title, figsize=(8, 4)):
    """Side-by-side stacked bar comparing BL vs EL for a SPARK question."""
    order = ["Yes", "No", "I don't know", "Not applicable"]
    bl_vc = df[bl_col].dropna().value_counts().reindex(order, fill_value=0)
    el_vc = df[el_col].dropna().value_counts().reindex(order, fill_value=0)

    x = np.arange(len(order))
    width = 0.35
    fig, ax = plt.subplots(figsize=figsize)
    bl_bars = ax.bar(x - width/2, bl_vc.values, width, label="Baseline",
                     color=[cat_color(o) for o in order], alpha=0.85, edgecolor="white")
    el_bars = ax.bar(x + width/2, el_vc.values, width, label="Endline",
                     color=[cat_color(o) for o in order], alpha=0.55, edgecolor="white",
                     hatch="//")

    ax.set_xticks(x)
    ax.set_xticklabels(order, rotation=20, ha="right")
    ax.set_ylabel("Count")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig

def parse_energy(series):
    """Parse '1234.56 kWh' strings to float."""
    return pd.to_numeric(
        series.astype(str).str.extract(r"([\d.]+)")[0],
        errors="coerce"
    )

def parse_co2(series):
    """Parse '1.23 tCO2e' strings to float."""
    return pd.to_numeric(
        series.astype(str).str.extract(r"([\d.]+)")[0],
        errors="coerce"
    )

# ── load data ──────────────────────────────────────────────────────────────────
print("Loading data …")
df = pd.read_csv(DATA_PATH)
print(f"  {len(df)} rows × {len(df.columns)} columns")

# Collect all figures for PDF
pdf_figures = []   # list of (fig, title)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 – HISTOGRAMS / SUMMARY TABLES FOR ALL SURVEY QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[1] Histograms / summary tables for all survey questions …")

# We treat every column that has ≤15 unique non-null values as categorical
# and every numeric column as continuous.
all_summary_rows = []

for col in df.columns:
    series = df[col].dropna()
    if len(series) == 0:
        continue
    n_unique = series.nunique()

    # Skip metadata / comment / free-text columns
    if col.endswith("_co") or col in [
        "id", "Group name", "Faculty", "PI name", "PI email", "PI website",
        "foldername", "enum_first", "enum_last", "enum_email",
        "Contact person (if different)", "Contact email (if different)",
        "Comments?", "rooms", "rooms_co", "share_equip_groups",
        "share_equip_groups_co", "share_space_groups", "share_space_groups_co",
        "comm_group_1","comm_group_2","comm_group_3","comm_group_4",
        "comm_group_5","comm_group_6","comm_group_7","comm_group_8",
        "survey_date_bl", "survey_date_el",
    ]:
        continue

    # Calc columns are handled in Section 4
    if col.startswith("calc_"):
        continue

    # Boolean / flag columns – skip internal processing flags
    if col in ["november_lab","file_copied","file_missing","file_filled",
               "file_empty","el_file_copied","el_file_missing","el_date_filled",
               "el_awareness_filled","el_email_conf","recovered_data",
               "replace_el_with_missing"]:
        continue

    if n_unique <= 15:
        tbl = freq_table(series, col)
        save_table(tbl, f"q_{col}")
        all_summary_rows.append({
            "Column": col,
            "Type": "Categorical",
            "N": len(series),
            "N_unique": n_unique,
            "Top value": tbl["Count"].idxmax(),
            "Top count": int(tbl["Count"].max()),
            "Top %": float(tbl["Percent (%)"].max()),
        })
    else:
        # Try numeric histogram
        num = pd.to_numeric(series, errors="coerce").dropna()
        if len(num) > 2:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.hist(num, bins=min(20, n_unique), color="#42A5F5", edgecolor="white")
            ax.set_title(f"Distribution: {col}", fontsize=10, fontweight="bold")
            ax.set_xlabel(col)
            ax.set_ylabel("Count")
            ax.spines[["top", "right"]].set_visible(False)
            fig.tight_layout()
            save_fig(fig, f"hist_{col}")
            pdf_figures.append((fig, col))
            all_summary_rows.append({
                "Column": col,
                "Type": "Numeric",
                "N": len(num),
                "N_unique": n_unique,
                "Top value": f"mean={num.mean():.1f}",
                "Top count": "",
                "Top %": "",
            })

summary_all = pd.DataFrame(all_summary_rows)
save_table(summary_all, "00_all_questions_summary")
print(f"  → {len(all_summary_rows)} question columns summarised")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 – LAB CHARACTERISTICS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[2] Lab characteristics …")

# 2a Faculty distribution
fig = bar_chart(df["faculty"], "Faculty Distribution", horizontal=True, figsize=(8, 4))
save_fig(fig, "lab_01_faculty")

tbl = freq_table(df["faculty"], "Faculty")
save_table(tbl, "lab_01_faculty")

# 2b Number of researchers (histogram)
no_res = pd.to_numeric(df["no_researchers"], errors="coerce").dropna()
fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(no_res, bins=15, color="#42A5F5", edgecolor="white")
ax.set_title("Number of Researchers per Lab", fontsize=11, fontweight="bold")
ax.set_xlabel("Number of Researchers")
ax.set_ylabel("Number of Labs")
ax.axvline(no_res.median(), color="red", linestyle="--", label=f"Median = {no_res.median():.0f}")
ax.legend()
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
save_fig(fig, "lab_02_no_researchers")

res_stats = no_res.describe().rename("No. Researchers")
save_table(res_stats.to_frame(), "lab_02_no_researchers_stats")

# 2c FT vs PT researchers
no_ft = pd.to_numeric(df["no_ft"], errors="coerce").dropna()
no_pt = pd.to_numeric(df["no_pt"], errors="coerce").dropna()

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, data, label, color in zip(
    axes,
    [no_ft, no_pt],
    ["Full-Time Researchers", "Part-Time Researchers"],
    ["#42A5F5", "#FFA726"]
):
    ax.hist(data, bins=12, color=color, edgecolor="white")
    ax.set_title(label, fontsize=10, fontweight="bold")
    ax.set_xlabel("Count")
    ax.set_ylabel("Labs")
    ax.axvline(data.median(), color="red", linestyle="--",
               label=f"Median = {data.median():.0f}")
    ax.legend(fontsize=8)
    ax.spines[["top","right"]].set_visible(False)
fig.suptitle("Full-Time vs Part-Time Researchers", fontsize=12, fontweight="bold")
fig.tight_layout()
save_fig(fig, "lab_03_ft_pt")

# 2d Equipment sharing
fig = bar_chart(df["share_equip_ind"], "Do Labs Share Equipment?", figsize=(6, 4))
save_fig(fig, "lab_04_share_equip")
save_table(freq_table(df["share_equip_ind"], "Share Equipment"), "lab_04_share_equip")

# 2e Space sharing
fig = bar_chart(df["share_space_ind"], "Do Labs Share Space?", figsize=(6, 4))
save_fig(fig, "lab_05_share_space")
save_table(freq_table(df["share_space_ind"], "Share Space"), "lab_05_share_space")

# 2f Space sharing frequency
fig = bar_chart(df["share_space_freq"], "Frequency of Shared Space Use",
                horizontal=True, figsize=(8, 4))
save_fig(fig, "lab_06_share_space_freq")
save_table(freq_table(df["share_space_freq"], "Share Space Frequency"),
           "lab_06_share_space_freq")

# 2g Combined lab characteristics table
lab_char = pd.DataFrame({
    "Metric": [
        "Total labs",
        "Median researchers per lab",
        "Mean researchers per lab",
        "Median FT researchers",
        "Median PT researchers",
        "Labs sharing equipment (%)",
        "Labs sharing space (%)",
    ],
    "Value": [
        len(df),
        f"{no_res.median():.1f}",
        f"{no_res.mean():.1f}",
        f"{no_ft.median():.1f}",
        f"{no_pt.median():.1f}",
        f"{(df['share_equip_ind']=='Yes').sum()/df['share_equip_ind'].notna().sum()*100:.1f}%",
        f"{(df['share_space_ind']=='Yes').sum()/df['share_space_ind'].notna().sum()*100:.1f}%",
    ]
})
save_table(lab_char.set_index("Metric"), "lab_00_summary")
print("  → Lab characteristics done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 – EQUIPMENT (ALL QUESTIONS)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[3] Equipment analysis …")

EQUIPMENT = {
    "PCR Machine":          ("pcr_ind",              "pcr_no",              "pcr_share"),
    "Ice Machine":          ("ice_ind",              "ice_no",              "ice_share"),
    "Centrifuge":           ("centrifuge_ind",        "centrifuge_no",       "centrifuge_share"),
    "Coffee Machine":       ("coffee_ind",            "coffee_no",           "coffee_share"),
    "Microwave":            ("microwave_ind",         "microwave_no",        "microwave_share"),
    "Animal Facility":      ("animal_ind",            "animal_no",           "animal_share"),
    "Non-CO₂ Incubator":    ("nonco2_incubator_ind",  "nonco2_incubator_no", "nonco2_incubator_share"),
    "4°C Room":             ("4c_room_ind",           "4c_room_no",          "4c_room_share"),
    "-20°C Room":           ("minus_20c_room_ind",    "minus_20c_room_no",   "minus_20c_room_share"),
    "Other Equipment":      ("other_ind",             "other_no",            "other_share"),
}

equip_summary_rows = []
for equip_name, (ind_col, no_col, share_col) in EQUIPMENT.items():
    ind_series = df[ind_col].replace("\xa0", np.nan).dropna()
    # Normalise "Yes"/"No" (some cells have stray values)
    ind_yn = ind_series[ind_series.isin(["Yes","No"])]
    n_yes = (ind_yn == "Yes").sum()
    n_no  = (ind_yn == "No").sum()
    pct_yes = n_yes / len(ind_yn) * 100 if len(ind_yn) > 0 else 0

    no_series = pd.to_numeric(
        df[no_col].replace("\xa0", np.nan), errors="coerce"
    ).dropna()

    share_series = df[share_col].replace("\xa0", np.nan).dropna()
    share_yn = share_series[share_series.isin(["Yes","No"])]
    n_shared = (share_yn == "Yes").sum()
    pct_shared = n_shared / len(share_yn) * 100 if len(share_yn) > 0 else 0

    equip_summary_rows.append({
        "Equipment": equip_name,
        "Labs with equipment": n_yes,
        "Labs without": n_no,
        "% with equipment": round(pct_yes, 1),
        "Median count (if present)": round(no_series.median(), 1) if len(no_series) > 0 else "–",
        "Mean count (if present)":   round(no_series.mean(),   1) if len(no_series) > 0 else "–",
        "Labs sharing (of those with)": n_shared,
        "% sharing": round(pct_shared, 1),
    })

equip_summary = pd.DataFrame(equip_summary_rows).set_index("Equipment")
save_table(equip_summary, "equip_00_summary")

# 3a Prevalence bar chart
fig, ax = plt.subplots(figsize=(10, 5))
names  = equip_summary.index.tolist()
pct_w  = equip_summary["% with equipment"].values
colors = [DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i in range(len(names))]
bars = ax.barh(names, pct_w, color=colors, edgecolor="white")
for bar, val in zip(bars, pct_w):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{val:.0f}%", va="center", fontsize=9)
ax.set_xlabel("% of Labs with Equipment")
ax.set_title("Equipment Prevalence Across Labs", fontsize=12, fontweight="bold")
ax.set_xlim(0, 115)
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
save_fig(fig, "equip_01_prevalence")

# 3b Sharing rate bar chart
fig, ax = plt.subplots(figsize=(10, 5))
pct_sh = equip_summary["% sharing"].values
bars = ax.barh(names, pct_sh, color=colors, edgecolor="white")
for bar, val in zip(bars, pct_sh):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{val:.0f}%", va="center", fontsize=9)
ax.set_xlabel("% of Labs Sharing Equipment (among those with it)")
ax.set_title("Equipment Sharing Rate", fontsize=12, fontweight="bold")
ax.set_xlim(0, 115)
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
save_fig(fig, "equip_02_sharing")

# 3c Individual bar charts per equipment type
for equip_name, (ind_col, no_col, share_col) in EQUIPMENT.items():
    ind_s = df[ind_col].replace("\xa0", np.nan)
    ind_s = ind_s[ind_s.isin(["Yes","No"])]
    if len(ind_s) == 0:
        continue
    safe = equip_name.replace("/","").replace("°","").replace(" ","_").replace("₂","2")
    fig = bar_chart(ind_s, f"{equip_name} – Presence", figsize=(5,3.5))
    save_fig(fig, f"equip_{safe}_presence")

    share_s = df[share_col].replace("\xa0", np.nan)
    share_s = share_s[share_s.isin(["Yes","No"])]
    if len(share_s) > 0:
        fig = bar_chart(share_s, f"{equip_name} – Shared?", figsize=(5,3.5))
        save_fig(fig, f"equip_{safe}_shared")

    no_s = pd.to_numeric(df[no_col].replace("\xa0", np.nan), errors="coerce").dropna()
    if len(no_s) > 2:
        fig, ax = plt.subplots(figsize=(5,3.5))
        ax.hist(no_s, bins=min(15, no_s.nunique()), color="#42A5F5", edgecolor="white")
        ax.set_title(f"{equip_name} – Number per Lab", fontsize=10, fontweight="bold")
        ax.set_xlabel("Count")
        ax.set_ylabel("Labs")
        ax.spines[["top","right"]].set_visible(False)
        fig.tight_layout()
        save_fig(fig, f"equip_{safe}_count")

print("  → Equipment analysis done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 – ENERGY USE
# ══════════════════════════════════════════════════════════════════════════════
print("\n[4] Energy use …")

ENERGY_TYPES = {
    "Fridge":          ("calc_fridge_energy",    "calc_fridge_co2"),
    "Freezer (-20°C)": ("calc_freezer_energy",   "calc_freezer_co2"),
    "ULT Freezer":     ("calc_ult_energy",        "calc_ult_co2"),
    "Glassware":       ("calc_glassware_energy",  "calc_glassware_co2"),
    "Microbiology":    ("calc_microbio_energy",   "calc_microbio_co2"),
    "Cryostat":        ("calc_cryostat_energy",   "calc_cryostat_co2"),
    "Water Bath":      ("calc_bath_energy",       "calc_bath_co2"),
    "Incubator":       ("calc_incubator_energy",  "calc_incubator_co2"),
    "Heater":          ("calc_heater_energy",     "calc_heater_co2"),
    "IT Equipment":    ("calc_it_energy",         "calc_it_co2"),
}

total_energy = parse_energy(df["calc_total_energy"])
total_co2    = parse_co2(df["calc_total_co2"])

# 4a Total energy distribution
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, data, label, unit in zip(
    axes,
    [total_energy, total_co2],
    ["Total Energy Consumption per Lab", "Total CO₂ Emissions per Lab"],
    ["kWh/year", "tCO₂e/year"]
):
    ax.hist(data.dropna(), bins=20, color="#42A5F5", edgecolor="white")
    ax.axvline(data.median(), color="red", linestyle="--",
               label=f"Median = {data.median():.0f}")
    ax.set_title(label, fontsize=10, fontweight="bold")
    ax.set_xlabel(unit)
    ax.set_ylabel("Labs")
    ax.legend(fontsize=8)
    ax.spines[["top","right"]].set_visible(False)
fig.suptitle("Total Energy & CO₂ per Lab", fontsize=12, fontweight="bold")
fig.tight_layout()
save_fig(fig, "energy_01_total_distribution")

# 4b Energy by equipment type – mean kWh
energy_means = {}
energy_totals = {}
for etype, (ecol, co2col) in ENERGY_TYPES.items():
    e_vals = parse_energy(df[ecol])
    energy_means[etype]  = e_vals.mean()
    energy_totals[etype] = e_vals.sum()

em_series = pd.Series(energy_means).sort_values(ascending=False)
et_series = pd.Series(energy_totals).sort_values(ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
colors = [DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i in range(len(em_series))]

for ax, data, title, xlabel in zip(
    axes,
    [em_series, et_series],
    ["Mean Energy per Lab by Equipment Type", "Total Energy Across All Labs by Equipment Type"],
    ["Mean kWh/year", "Total kWh/year"]
):
    bars = ax.barh(data.index, data.values, color=colors, edgecolor="white")
    for bar, val in zip(bars, data.values):
        ax.text(bar.get_width() + data.max()*0.01,
                bar.get_y() + bar.get_height()/2,
                f"{val:,.0f}", va="center", fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.spines[["top","right"]].set_visible(False)
    ax.set_xlim(0, data.max() * 1.2)
fig.tight_layout()
save_fig(fig, "energy_02_by_type")

# 4c Pie chart – share of total energy by type
fig, ax = plt.subplots(figsize=(8, 6))
wedge_vals = [v for v in et_series.values if v > 0]
wedge_labs = [l for l, v in zip(et_series.index, et_series.values) if v > 0]
ax.pie(wedge_vals, labels=wedge_labs, autopct="%1.1f%%",
       colors=colors[:len(wedge_vals)], startangle=140,
       wedgeprops={"edgecolor": "white"})
ax.set_title("Share of Total Energy by Equipment Type", fontsize=12, fontweight="bold")
fig.tight_layout()
save_fig(fig, "energy_03_pie")

# 4d Energy summary table
energy_tbl_rows = []
for etype, (ecol, co2col) in ENERGY_TYPES.items():
    e_vals  = parse_energy(df[ecol])
    co2_vals = parse_co2(df[co2col])
    energy_tbl_rows.append({
        "Equipment Type": etype,
        "N labs with data": e_vals.notna().sum(),
        "Mean kWh/year": round(e_vals.mean(), 1),
        "Median kWh/year": round(e_vals.median(), 1),
        "Total kWh/year": round(e_vals.sum(), 1),
        "Mean tCO₂e/year": round(co2_vals.mean(), 3),
        "Total tCO₂e/year": round(co2_vals.sum(), 3),
    })

energy_tbl = pd.DataFrame(energy_tbl_rows).set_index("Equipment Type")
# Add totals row
energy_tbl.loc["TOTAL"] = [
    "",
    round(total_energy.mean(), 1),
    round(total_energy.median(), 1),
    round(total_energy.sum(), 1),
    round(total_co2.mean(), 3),
    round(total_co2.sum(), 3),
]
save_table(energy_tbl, "energy_00_summary")

# 4e Per-type histograms
for etype, (ecol, co2col) in ENERGY_TYPES.items():
    e_vals = parse_energy(df[ecol]).dropna()
    e_vals = e_vals[e_vals > 0]
    if len(e_vals) < 3:
        continue
    safe = etype.replace(" ","_").replace("(","").replace(")","").replace("°","").replace("₂","2").replace("/","")
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.hist(e_vals, bins=min(15, e_vals.nunique()), color="#66BB6A", edgecolor="white")
    ax.axvline(e_vals.median(), color="red", linestyle="--",
               label=f"Median = {e_vals.median():.0f} kWh")
    ax.set_title(f"Energy: {etype}", fontsize=10, fontweight="bold")
    ax.set_xlabel("kWh/year")
    ax.set_ylabel("Labs")
    ax.legend(fontsize=8)
    ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, f"energy_{safe}_hist")

print("  → Energy analysis done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 – COMMUNICATION & COLLABORATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n[5] Communication & collaboration …")

# 5a Number of collaboration groups per lab
comm_group_cols = [f"comm_group_{i}" for i in range(1, 9)]
n_collab = df[comm_group_cols].notna().sum(axis=1)
n_collab = n_collab[n_collab > 0]

fig, ax = plt.subplots(figsize=(7, 4))
vc = n_collab.value_counts().sort_index()
ax.bar(vc.index.astype(str), vc.values, color="#7E57C2", edgecolor="white")
for i, (idx, val) in enumerate(zip(vc.index, vc.values)):
    ax.text(i, val + 0.1, str(val), ha="center", va="bottom", fontsize=9)
ax.set_title("Number of Collaborating Groups per Lab", fontsize=11, fontweight="bold")
ax.set_xlabel("Number of Groups")
ax.set_ylabel("Labs")
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
save_fig(fig, "comm_01_n_groups")

# 5b Communication frequency distribution (all groups pooled)
freq_cols = [f"comm_freq_group_{i}" for i in range(1, 9)]
all_freqs = pd.concat([df[c] for c in freq_cols], ignore_index=True).dropna()
# Normalise
all_freqs = all_freqs.str.strip()

fig = bar_chart(all_freqs, "Communication Frequency with Collaborating Groups\n(all groups pooled)",
                horizontal=True, figsize=(9, 4))
save_fig(fig, "comm_02_freq_all")
save_table(freq_table(all_freqs, "Comm Frequency"), "comm_02_freq_all")

# 5c Heatmap: frequency per group slot
freq_matrix = pd.DataFrame({
    f"Group {i}": df[f"comm_freq_group_{i}"].str.strip()
    for i in range(1, 9)
})
freq_order = ["Daily", "Weekly", "Monthly", "Less than monthly"]
heatmap_data = pd.DataFrame(
    {col: freq_matrix[col].value_counts().reindex(freq_order, fill_value=0)
     for col in freq_matrix.columns}
)

fig, ax = plt.subplots(figsize=(10, 4))
im = ax.imshow(heatmap_data.values, aspect="auto", cmap="YlOrRd")
ax.set_xticks(range(len(heatmap_data.columns)))
ax.set_xticklabels(heatmap_data.columns, rotation=30, ha="right")
ax.set_yticks(range(len(heatmap_data.index)))
ax.set_yticklabels(heatmap_data.index)
for i in range(len(heatmap_data.index)):
    for j in range(len(heatmap_data.columns)):
        val = heatmap_data.values[i, j]
        ax.text(j, i, str(val), ha="center", va="center",
                color="black" if val < heatmap_data.values.max()*0.6 else "white",
                fontsize=9)
plt.colorbar(im, ax=ax, label="Count")
ax.set_title("Communication Frequency by Group Slot", fontsize=11, fontweight="bold")
fig.tight_layout()
save_fig(fig, "comm_03_heatmap")

# 5d Consent to data merge
fig = bar_chart(df["consent_data_merge"], "Consent to Data Merge",
                horizontal=True, figsize=(8, 3.5))
save_fig(fig, "comm_04_consent_merge")
save_table(freq_table(df["consent_data_merge"], "Consent Data Merge"),
           "comm_04_consent_merge")

# 5e Checklist discussion
fig = bar_chart(df["checklist_discussion"],
                "Amount of Checklist Discussion During Visit",
                horizontal=True, figsize=(8, 4))
save_fig(fig, "comm_05_checklist_discussion")
save_table(freq_table(df["checklist_discussion"], "Checklist Discussion"),
           "comm_05_checklist_discussion")

print("  → Communication & collaboration done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 – SPARK QUESTIONS (BL + EL)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[6] SPARK questions (BL + EL) …")

TIERS = {
    "Bronze": (16, "bronze"),
    "Silver": (18, "silver"),
    "Gold":   (15, "gold"),
}

SPARK_RESPONSE_ORDER = ["Yes", "No", "I don't know", "Not applicable"]

for tier_name, (n_q, prefix) in TIERS.items():
    tier_rows = []
    for q_num in range(1, n_q + 1):
        bl_col = f"{prefix}_q_{q_num}_bl"
        el_col = f"{prefix}_q_{q_num}_el"
        if bl_col not in df.columns:
            continue

        bl_s = df[bl_col].dropna()
        el_s = df[el_col].dropna() if el_col in df.columns else pd.Series(dtype=str)

        # Frequency tables
        bl_tbl = freq_table(bl_s, bl_col)
        save_table(bl_tbl, f"spark_{prefix}_q{q_num}_bl")

        if len(el_s) > 0:
            el_tbl = freq_table(el_s, el_col)
            save_table(el_tbl, f"spark_{prefix}_q{q_num}_el")

        # BL bar chart
        fig = bar_chart(bl_s, f"{tier_name} Q{q_num} – Baseline", figsize=(6, 3.5))
        save_fig(fig, f"spark_{prefix}_q{q_num}_bl")

        # BL vs EL comparison
        if len(el_s) > 0 and el_col in df.columns:
            fig = stacked_bar_bl_el(df, bl_col, el_col,
                                    f"{tier_name} Q{q_num}: Baseline vs Endline")
            save_fig(fig, f"spark_{prefix}_q{q_num}_bl_vs_el")

        # Collect summary
        for resp in SPARK_RESPONSE_ORDER:
            bl_n   = (bl_s == resp).sum()
            bl_pct = bl_n / len(bl_s) * 100 if len(bl_s) > 0 else 0
            el_n   = (el_s == resp).sum() if len(el_s) > 0 else np.nan
            el_pct = el_n / len(el_s) * 100 if len(el_s) > 0 else np.nan
            tier_rows.append({
                "Tier": tier_name,
                "Question": f"Q{q_num}",
                "Response": resp,
                "BL Count": bl_n,
                "BL %": round(bl_pct, 1),
                "EL Count": el_n,
                "EL %": round(el_pct, 1) if not np.isnan(el_pct) else np.nan,
            })

    tier_df = pd.DataFrame(tier_rows)
    save_table(tier_df, f"spark_{prefix}_summary")

    # Overview heatmap: % "Yes" at BL and EL per question
    q_labels = [f"Q{i}" for i in range(1, n_q + 1)
                if f"{prefix}_q_{i}_bl" in df.columns]
    bl_yes_pct = []
    el_yes_pct = []
    for q_num in range(1, n_q + 1):
        bl_col = f"{prefix}_q_{q_num}_bl"
        el_col = f"{prefix}_q_{q_num}_el"
        if bl_col not in df.columns:
            continue
        bl_s = df[bl_col].dropna()
        el_s = df[el_col].dropna() if el_col in df.columns else pd.Series(dtype=str)
        bl_yes_pct.append((bl_s == "Yes").sum() / len(bl_s) * 100 if len(bl_s) > 0 else 0)
        el_yes_pct.append((el_s == "Yes").sum() / len(el_s) * 100 if len(el_s) > 0 else 0)

    x = np.arange(len(q_labels))
    fig, ax = plt.subplots(figsize=(max(10, len(q_labels)*0.7), 4))
    ax.plot(x, bl_yes_pct, "o-", color="#1565C0", label="Baseline % Yes", linewidth=2)
    ax.plot(x, el_yes_pct, "s--", color="#4CAF50", label="Endline % Yes", linewidth=2)
    ax.fill_between(x, bl_yes_pct, el_yes_pct, alpha=0.1, color="gray")
    ax.set_xticks(x)
    ax.set_xticklabels(q_labels)
    ax.set_ylabel("% 'Yes' responses")
    ax.set_ylim(0, 110)
    ax.set_title(f"{tier_name} SPARK Questions – % 'Yes': Baseline vs Endline",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, f"spark_{prefix}_overview")

print("  → SPARK questions done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 – AWARENESS
# ══════════════════════════════════════════════════════════════════════════════
print("\n[7] Awareness …")

# 7a SPARK awareness
fig = bar_chart(df["spark_awareness"], "Awareness of SPARK Programme", figsize=(6, 4))
save_fig(fig, "aware_01_spark")
save_table(freq_table(df["spark_awareness"], "SPARK Awareness"), "aware_01_spark")

# 7b When they became aware
fig = bar_chart(df["spark_awareness_when"].dropna(),
                "When Did Labs Become Aware of SPARK?",
                horizontal=True, figsize=(9, 4))
save_fig(fig, "aware_02_when")
save_table(freq_table(df["spark_awareness_when"], "SPARK Awareness When"),
           "aware_02_when")

# 7c Attitude questions (8 Likert items)
ATTITUDE_LABELS = {
    "attitude_q_1": "Q1 – Universities have a responsibility to reduce their environmental impact",
    "attitude_q_2": "Q2 – Research groups consume more energy and resources than necessary for their scientific work",
    "attitude_q_3": "Q3 – I try to consider sustainability when making decisions about equipment, protocols, or practices in my research group",
    "attitude_q_4": "Q4 – Sustainability requirements risk slowing down scientific research",
    "attitude_q_5": "Q5 – Sustainable research practices can improve research quality or efficiency",
    "attitude_q_6": "Q6 – I am generally aware of the energy and resource costs associated with my research group's activitites",
    "attitude_q_7": "Q7 – I would be more motivated to adopt energy-saving practices if my research group directly faced the financial costs of its energy and resource use",
    "attitude_q_8": "Q8 – Initiatives from the university administration are more effective in changing research culture than those from within research groups",
}
LIKERT_ORDER = ["Strongly agree", "Agree", "Neither agree nor disagree",
                "Disagree", "Strongly disagree"]
LIKERT_COLORS = ["#1565C0", "#42A5F5", "#90A4AE", "#EF9A9A", "#B71C1C"]

# Individual bar charts
for col, label in ATTITUDE_LABELS.items():
    if col not in df.columns:
        continue
    s = df[col].dropna()
    fig = bar_chart(s, label, figsize=(7, 4))
    save_fig(fig, f"aware_{col}")
    save_table(freq_table(s, label), f"aware_{col}")

# Diverging stacked bar for all attitude questions
attitude_data = {}
for col, label in ATTITUDE_LABELS.items():
    if col not in df.columns:
        continue
    s = df[col].dropna()
    vc = s.value_counts().reindex(LIKERT_ORDER, fill_value=0)
    attitude_data[label] = vc

att_df = pd.DataFrame(attitude_data).T
att_pct = att_df.div(att_df.sum(axis=1), axis=0) * 100

fig, ax = plt.subplots(figsize=(12, 6))
y_pos = np.arange(len(att_pct))
lefts = np.zeros(len(att_pct))
for resp, color in zip(LIKERT_ORDER, LIKERT_COLORS):
    vals = att_pct[resp].values
    bars = ax.barh(y_pos, vals, left=lefts, color=color, label=resp, edgecolor="white")
    for bar, val in zip(bars, vals):
        if val > 5:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_y() + bar.get_height()/2,
                    f"{val:.0f}%", ha="center", va="center", fontsize=7, color="white")
    lefts += vals

ax.set_yticks(y_pos)
ax.set_yticklabels([textwrap.fill(l, 45) for l in att_pct.index], fontsize=8)
ax.set_xlabel("Percentage (%)")
ax.set_title("Attitude Questions – Likert Scale Responses", fontsize=12, fontweight="bold")
ax.legend(loc="lower right", fontsize=8, ncol=2)
ax.set_xlim(0, 100)
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
save_fig(fig, "aware_attitude_diverging")
save_table(att_pct.round(1), "aware_attitude_pct")

# 7d Consent to attitudes study
fig = bar_chart(df["consent_attitudes"], "Consent to Attitudes Study",
                horizontal=True, figsize=(8, 3))
save_fig(fig, "aware_consent_attitudes")
save_table(freq_table(df["consent_attitudes"], "Consent Attitudes"),
           "aware_consent_attitudes")

print("  → Awareness done")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 – BALANCE TABLES
# ══════════════════════════════════════════════════════════════════════════════
print("\n[8] Balance tables …")

# A balance table checks whether key lab characteristics differ between groups.
# We compare:
#   (a) Faculty (MEF vs MNF)
#   (b) Equipment sharing (Yes vs No)
#   (c) SPARK awareness (Yes vs No vs Not sure)

def clean_faculty(s):
    s = str(s).strip()
    if "MEF" in s or "Medicine" in s or "Medizin" in s:
        return "MEF"
    if "MNF" in s or "Science" in s or "Naturwissen" in s:
        return "MNF"
    return "Other/Unknown"

df["faculty_clean"] = df["faculty"].apply(clean_faculty)

BALANCE_VARS = {
    "No. Researchers":     pd.to_numeric(df["no_researchers"], errors="coerce"),
    "No. FT Researchers":  pd.to_numeric(df["no_ft"],          errors="coerce"),
    "No. PT Researchers":  pd.to_numeric(df["no_pt"],          errors="coerce"),
    "Shares Equipment":    (df["share_equip_ind"] == "Yes").astype(float),
    "Shares Space":        (df["share_space_ind"] == "Yes").astype(float),
    "Total Energy (kWh)":  parse_energy(df["calc_total_energy"]),
    "Total CO₂ (tCO₂e)":  parse_co2(df["calc_total_co2"]),
    "SPARK Aware":         (df["spark_awareness"] == "Yes").astype(float),
}

def balance_table(df, group_col, var_dict, group_label="Group"):
    groups = df[group_col].dropna().unique()
    rows = []
    for var_name, var_series in var_dict.items():
        row = {"Variable": var_name}
        for g in sorted(groups):
            mask = df[group_col] == g
            vals = var_series[mask].dropna()
            if len(vals) == 0:
                row[f"{g} Mean"] = "–"
                row[f"{g} Median"] = "–"
                row[f"{g} N"] = 0
            else:
                row[f"{g} Mean"]   = round(vals.mean(),   2)
                row[f"{g} Median"] = round(vals.median(), 2)
                row[f"{g} N"]      = len(vals)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Variable")

# 8a By faculty
bt_faculty = balance_table(df, "faculty_clean", BALANCE_VARS, "Faculty")
save_table(bt_faculty, "balance_01_faculty")

fig, ax = plt.subplots(figsize=(10, 5))
ax.axis("off")
tbl_data = bt_faculty.reset_index()
table = ax.table(
    cellText=tbl_data.values,
    colLabels=tbl_data.columns,
    cellLoc="center",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(7)
table.scale(1, 1.4)
ax.set_title("Balance Table: MEF vs MNF vs Other", fontsize=11, fontweight="bold", pad=20)
fig.tight_layout()
save_fig(fig, "balance_01_faculty")

# 8b By equipment sharing
bt_equip = balance_table(df, "share_equip_ind", BALANCE_VARS, "Share Equipment")
save_table(bt_equip, "balance_02_equip_sharing")

fig, ax = plt.subplots(figsize=(10, 5))
ax.axis("off")
tbl_data = bt_equip.reset_index()
table = ax.table(
    cellText=tbl_data.values,
    colLabels=tbl_data.columns,
    cellLoc="center",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(7)
table.scale(1, 1.4)
ax.set_title("Balance Table: Equipment Sharing (Yes vs No)", fontsize=11, fontweight="bold", pad=20)
fig.tight_layout()
save_fig(fig, "balance_02_equip_sharing")

# 8c By SPARK awareness
bt_aware = balance_table(df, "spark_awareness", BALANCE_VARS, "SPARK Awareness")
save_table(bt_aware, "balance_03_spark_awareness")

fig, ax = plt.subplots(figsize=(12, 5))
ax.axis("off")
tbl_data = bt_aware.reset_index()
table = ax.table(
    cellText=tbl_data.values,
    colLabels=tbl_data.columns,
    cellLoc="center",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(7)
table.scale(1, 1.4)
ax.set_title("Balance Table: SPARK Awareness (Yes / No / Not sure)", fontsize=11, fontweight="bold", pad=20)
fig.tight_layout()
save_fig(fig, "balance_03_spark_awareness")

print("  → Balance tables done")


# ══════════════════════════════════════════════════════════════════════════════
# COMPILE PDF REPORT
# ══════════════════════════════════════════════════════════════════════════════
print("\nCompiling PDF report …")

SECTION_FIGS = [
    # (section_title, list_of_png_paths)
    ("1 – Overview: All Survey Questions",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("hist_")])),

    ("2 – Lab Characteristics",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("lab_")])),

    ("3 – Equipment Analysis",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("equip_")])),

    ("4 – Energy Use",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("energy_")])),

    ("5 – Communication & Collaboration",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("comm_")])),

    ("6 – SPARK Questions (BL + EL)",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("spark_")])),

    ("7 – Awareness",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("aware_")])),

    ("8 – Balance Tables",
     sorted([os.path.join(FIG_DIR, f) for f in os.listdir(FIG_DIR) if f.startswith("balance_")])),
]

with PdfPages(PDF_PATH) as pdf:
    for section_title, fig_paths in SECTION_FIGS:
        if not fig_paths:
            continue
        # Section title page
        fig_title = plt.figure(figsize=(11, 2))
        fig_title.patch.set_facecolor("#1565C0")
        fig_title.text(0.5, 0.5, section_title, ha="center", va="center",
                       fontsize=18, fontweight="bold", color="white")
        pdf.savefig(fig_title, bbox_inches="tight")
        plt.close(fig_title)

        for fp in fig_paths:
            if not os.path.exists(fp):
                continue
            img = plt.imread(fp)
            fig_img, ax_img = plt.subplots(figsize=(11, 7))
            ax_img.imshow(img)
            ax_img.axis("off")
            pdf.savefig(fig_img, bbox_inches="tight")
            plt.close(fig_img)

print(f"  → PDF saved: {PDF_PATH}")

# ── final summary ──────────────────────────────────────────────────────────────
n_figs  = len([f for f in os.listdir(FIG_DIR) if f.endswith(".png")])
n_tables = len([f for f in os.listdir(TAB_DIR) if f.endswith(".csv")])
print(f"\nDone. Generated {n_figs} figures and {n_tables} tables.")
print(f"Figures : {FIG_DIR}")
print(f"Tables  : {TAB_DIR}")
print(f"PDF     : {PDF_PATH}")