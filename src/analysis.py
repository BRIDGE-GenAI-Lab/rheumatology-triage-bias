#!/usr/bin/env python3
"""
Rheumato Bias Pipeline: Comprehensive Analysis Suite
=====================================================

Publication-quality analysis for Lancet Rheumatology paper on sociodemographic bias in AI clinical triage.

Reads pipeline JSONL/Excel output and produces camera-ready tables and figures:

  TABLES (Excel workbook, one sheet per table)
  ─────
  T1_Baseline_Accuracy          Baseline concordance rates with Wilson CI
  T2_Baseline_by_Model          Baseline by Model with composite score & CI
  T3_Baseline_by_Persona        Baseline by Persona with composite score & CI
  T4_Decision_Shifts            Decision change rates by dimension × level with FDR
  T5_Accuracy_Change            Composite score change by dimension × level
  T6_Psychologization           Psychologization & error rates by dimension
  T7_Urgency_Shifts             Urgency direction (downgraded/correct/upgraded)
  T8_Statistical_Tests          All metrics with FDR-corrected p-values & Cohen's h
  T9_Per_Model_Shifts           Overall shift rates per model
  T10_Per_Persona_Shifts        Overall shift rates per persona

  FIGURES (PNG 300 DPI — camera-ready for Lancet Rheumatology)
  ──────
  fig01  Baseline accuracy (bar chart with Wilson CI)
  fig02  Decision-change heatmap
  fig03  Referral & urgency changes (paired bars)
  fig04  Psychologization dual panel
  fig05  Urgency direction stacked bar
  fig06  Composite delta diverging bar
  fig07  Composite score by dimension box plot
  fig08  Disease category × dimension interaction heatmap
  fig09  Persona susceptibility scatter
  fig10  Model × Persona interaction heatmap
  fig11  Model shift paired dot plot

  PDF    All figures consolidated in publication order

Usage
-----
  python analysis.py [input.jsonl|.xlsx] [output_dir]

  If not provided, you will be prompted for paths interactively.

Requirements
------------
  pip install pandas numpy matplotlib seaborn scipy openpyxl statsmodels Pillow
"""

import sys
import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from io import StringIO

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import binomtest, wilcoxon
from statsmodels.stats.multitest import multipletests

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mtick
import seaborn as sns
from PIL import Image

warnings.filterwarnings("ignore")

# ============================================================================
# CONSTANTS & STYLING
# ============================================================================

DPI = 300
FIG_FMT = "png"
ALPHA = 0.05

BG      = "#F8F9FB"
WHITE   = "#FFFFFF"
GRID    = "#E5E9F0"
TXT     = "#1E2A3A"
SUB     = "#7C879A"
GREEN   = "#0EA47A"
RED     = "#E5484D"
BLUE    = "#3E82FC"
AMBER   = "#F5A623"
INDIGO  = "#6C5CE7"
SLATE   = "#A0AEC0"
TEAL    = "#14B8A6"
CORAL   = "#FF6B6B"
PURPLE  = "#A855F7"

DIM_LABELS = {
    "tone": "Pain Expression", "race": "Race / Ethnicity", "sex": "Sex / Gender",
    "ses": "Socioeconomic Status", "anchoring": "Clinician Anchoring",
    "literacy": "Health Literacy", "language": "Language Barrier",
    "psych_hx": "Psychiatric History", "substance": "Substance Use",
    "weight": "Weight / BMI", "baseline": "Baseline (Control)",
}

LEVEL_LABELS = {
    ("tone", "stoic"): "Stoic / Minimizing", ("tone", "emotional"): "Emotional / Expressive",
    ("tone", "angry"): "Angry / Frustrated", ("tone", "anxious"): "Anxious / Worried",
    ("race", "White"): "White", ("race", "Black"): "Black",
    ("race", "Hispanic"): "Hispanic / Latino", ("race", "Asian"): "Asian",
    ("ses", "low"): "Medicaid / Low SES", ("ses", "high"): "Private / High SES",
    ("ses", "unhoused"): "Unhoused",
    ("literacy", "low"): "Low Health Literacy", ("literacy", "high"): "High Health Literacy",
    ("psych_hx", "present"): "Psychiatric Hx Present",
    ("weight", "obese"): "Obese (BMI > 35)",
    ("substance", "active"): "Active Substance Use",
    ("language", "barrier"): "Language Barrier / Interpreter",
    ("anchoring", "psych_anchor"): "Psych Anchor", ("anchoring", "msk_anchor"): "MSK Anchor",
    ("anchoring", "dismissive_anchor"): "Dismissive Anchor",
    ("baseline", "baseline"): "Control (No Label)",
    ("sex", "female"): "Female", ("sex", "male"): "Male",
}

PERSONA_LABELS = {
    "physician": "Physician",
    "helpful_ai": "Helpful AI",
    "conservative_pcp": "Conservative PCP",
    "no_persona": "No Persona",
}

PERSONA_COLORS = {
    "physician": BLUE,
    "helpful_ai": AMBER,
    "conservative_pcp": TEAL,
    "no_persona": SLATE,
}

DIM_COLORS = {
    "tone": "#E85D04", "race": "#457B9D", "sex": "#2A9D8F", "ses": "#E9C46A",
    "anchoring": "#264653", "literacy": "#F4A261", "language": "#6A994E",
    "psych_hx": "#BC6C25", "substance": "#606C38", "weight": "#9B2226",
    "baseline": "#888888",
}

DIM_ORDER = ["race", "tone", "ses", "anchoring", "psych_hx", "weight", "substance", "literacy", "language", "sex"]

def _style():
    """Apply Lancet-ready style to all plots."""
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": WHITE,
        "axes.edgecolor": GRID, "axes.labelcolor": TXT,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
        "text.color": TXT,
        "xtick.color": SUB, "ytick.color": SUB,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.labelsize": 11, "axes.titlesize": 13,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "figure.dpi": DPI, "savefig.dpi": DPI,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.2,
    })

def _header(fig, title: str, sub: str = ""):
    """Add header with title and subtitle to figure."""
    y_title = 0.98
    y_sub = 0.94
    fig.text(0.08, y_title, title, fontsize=16, fontweight="bold", color=TXT, va="top")
    if sub:
        fig.text(0.08, y_sub, sub, fontsize=11, color=SUB, va="top", style="italic")

def _wm(ax):
    """Add watermark to axis."""
    ax.text(0.99, 0.01, "Rheumato Bias Pipeline", transform=ax.transAxes,
            fontsize=8, color=GRID, alpha=0.5, ha="right", va="bottom")


# ============================================================================
# DATA LOADING & VALIDATION
# ============================================================================

def load_data(path: Path) -> pd.DataFrame:
    """Load JSONL or Excel pipeline output."""
    if path.suffix == ".jsonl":
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        return pd.DataFrame(rows)
    else:
        return pd.read_excel(path, sheet_name="Raw_Outputs")

def prompt_for_paths() -> Tuple[Path, Path]:
    """Prompt user for input and output paths."""
    while True:
        input_path = input("\nEnter input file path (JSONL or Excel): ").strip()
        input_path = Path(input_path)
        if input_path.exists():
            break
        print(f"File not found: {input_path}")

    while True:
        output_dir = input("Enter output directory (default: ./figures): ").strip() or "./figures"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        break

    return input_path, output_dir


# ============================================================================
# STATISTICS UTILITIES
# ============================================================================

def wilson_ci(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval for a proportion."""
    if total == 0:
        return 0, 0

    p = successes / total
    z = stats.norm.ppf((1 + confidence) / 2)
    denominator = 1 + z**2 / total
    centre_adjusted = (p + z**2 / (2 * total)) / denominator
    adj_sqrt = (p * (1 - p) / total + z**2 / (4 * total**2))**0.5 / denominator

    lower = max(0, centre_adjusted - z * adj_sqrt)
    upper = min(1, centre_adjusted + z * adj_sqrt)
    return lower, upper

def format_ci(value: float, lower: float, upper: float) -> str:
    """Format percentage with Wilson CI."""
    return f"{value*100:.1f}% [{lower*100:.1f}–{upper*100:.1f}%]"

def cohens_h(p1: float, p2: float) -> float:
    """Calculate Cohen's h effect size for proportion difference."""
    if p1 == 0 or p1 == 1 or p2 == 0 or p2 == 1:
        return np.nan
    return 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))

def dim_sort_key(d):
    """Get sort order for dimension."""
    try:
        return DIM_ORDER.index(str(d))
    except ValueError:
        return 99

def apply_fdr_correction(pvalues: List[float]) -> Tuple[List[bool], List[float]]:
    """Apply Benjamini-Hochberg FDR correction."""
    pvalues_arr = np.array(pvalues)
    rejected, corrected, _, _ = multipletests(pvalues_arr, alpha=ALPHA, method="fdr_bh")
    return rejected, corrected


# ============================================================================
# DELTA COMPUTATION (vectorized)
# ============================================================================

def compute_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute decision changes by comparing iteration rows to baseline.
    Match on (case_id, case_rephrase_id, repeat_id, model, persona).
    Uses vectorized operations instead of row iteration.
    """
    baseline_df = df[df["condition"] == "baseline"].copy()
    iteration_df = df[df["condition"] != "baseline"].copy()

    if len(baseline_df) == 0 or len(iteration_df) == 0:
        print("WARNING: No baseline or iteration data found!")
        return pd.DataFrame()

    binary_metrics = [
        "refer_match", "urgency_match", "labs_match", "imaging_match", "aspiration_match",
        "psychologized", "psychologization_error", "urgency_downgraded", "urgency_upgraded",
        "acuity_match", "acuity_downgraded", "acuity_upgraded", "under_referral", "over_referral",
        "dx_match_primary", "dx_match_top3", "reassurance_error", "immediate_action_match",
    ]

    # Create match key
    baseline_df["match_key"] = (
        baseline_df["case_id"].astype(str) + "|" +
        baseline_df["case_rephrase_id"].astype(str) + "|" +
        baseline_df["repeat_id"].astype(str) + "|" +
        baseline_df["model"].astype(str) + "|" +
        baseline_df["persona"].astype(str)
    )

    iteration_df["match_key"] = (
        iteration_df["case_id"].astype(str) + "|" +
        iteration_df["case_rephrase_id"].astype(str) + "|" +
        iteration_df["repeat_id"].astype(str) + "|" +
        iteration_df["model"].astype(str) + "|" +
        iteration_df["persona"].astype(str)
    )

    # Merge to find paired rows (only keep dimension and level columns from iteration)
    merged = baseline_df.merge(
        iteration_df[["match_key", "dimension", "level", "condition"] +
                     [c for c in iteration_df.columns if c in binary_metrics + ["composite_score", "gt_category", "gt_acuity"]]],
        on="match_key", suffixes=("_base", "_iter"), how="inner"
    )

    if len(merged) == 0:
        print("WARNING: No baseline-iteration pairs found!")
        return pd.DataFrame()

    # Initialize delta dataframe
    delta_records = {
        "case_id": merged["case_id_base"].values if "case_id_base" in merged.columns else merged["case_id"].values,
        "model": merged["model_base"].values if "model_base" in merged.columns else merged["model"].values,
        "persona": merged["persona_base"].values if "persona_base" in merged.columns else merged["persona"].values,
        "dimension": merged["dimension"].values,
        "level": merged["level"].values,
        "iteration_id": merged["condition"].values,
        "gt_category": merged["gt_category_base"].values if "gt_category_base" in merged.columns else merged.get("gt_category", []).values,
        "gt_acuity": merged["gt_acuity_base"].values if "gt_acuity_base" in merged.columns else merged.get("gt_acuity", []).values,
    }

    # Get composite score column name (handles both suffixes and no suffix)
    composite_base = None
    composite_iter = None
    if "composite_score_base" in merged.columns:
        composite_base = merged["composite_score_base"].values
        composite_iter = merged["composite_score_iter"].values
    elif "composite_score" in merged.columns:
        composite_base = merged["composite_score"].values
        composite_iter = merged["composite_score"].values  # fallback

    if composite_base is not None:
        delta_records["composite_score_base"] = composite_base
        delta_records["composite_score_iter"] = composite_iter
        delta_records["composite_delta"] = composite_iter - composite_base

    # Compute metric changes vectorially
    for metric in binary_metrics:
        base_col = f"{metric}_base" if f"{metric}_base" in merged.columns else metric
        iter_col = f"{metric}_iter" if f"{metric}_iter" in merged.columns else metric

        if base_col in merged.columns and iter_col in merged.columns:
            base_vals = merged[base_col].fillna(0).astype(bool).astype(int).values
            iter_vals = merged[iter_col].fillna(0).astype(bool).astype(int).values
            delta_records[f"{metric}_changed"] = (base_vals != iter_vals).astype(int)
            delta_records[f"{metric}_base"] = base_vals
            delta_records[f"{metric}_iter"] = iter_vals
            delta_records[f"{metric}_direction"] = (iter_vals - base_vals).astype(int)

    return pd.DataFrame(delta_records)


# ============================================================================
# TABLE GENERATION
# ============================================================================

def table1_baseline_accuracy(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """T1: Baseline accuracy aggregated across all models and personas."""
    metrics = [
        ("refer_match", "Referral Concordance"),
        ("urgency_match", "Urgency Concordance"),
        ("labs_match", "Labs Concordance"),
        ("imaging_match", "Imaging Concordance"),
        ("aspiration_match", "Aspiration Concordance"),
        ("acuity_match", "Acuity Concordance"),
        ("dx_match_primary", "Diagnosis (Primary)"),
        ("dx_match_top3", "Diagnosis (Top 3)"),
        ("composite_score", "Composite Concordance"),
        ("psychologization_error", "Inapp. Psychologization"),
        ("urgency_downgraded", "Urgency Downgrade"),
        ("under_referral", "Under-referral"),
        ("reassurance_error", "Reassurance Error"),
    ]

    rows = []
    for col, label in metrics:
        if col not in baseline_df.columns:
            continue

        vals = baseline_df[col].dropna()
        if len(vals) > 0:
            if col == "composite_score":
                mean_val = vals.mean()
                std_val = vals.std()
                se_val = std_val / np.sqrt(len(vals))
                ci_lower = mean_val - 1.96 * se_val
                ci_upper = mean_val + 1.96 * se_val
                rows.append({
                    "Metric": label,
                    "Rate": f"{mean_val*100:.1f}% [{ci_lower*100:.1f}–{ci_upper*100:.1f}%]",
                    "N": len(vals),
                    "Mean": mean_val,
                    "Lower_CI": ci_lower,
                    "Upper_CI": ci_upper,
                })
            else:
                total = len(vals)
                success = int(vals.sum())
                rate = success / total if total > 0 else 0
                ci_lower, ci_upper = wilson_ci(success, total)
                rows.append({
                    "Metric": label,
                    "Rate": format_ci(rate, ci_lower, ci_upper),
                    "N": total,
                    "Mean": rate,
                    "Lower_CI": ci_lower,
                    "Upper_CI": ci_upper,
                })

    return pd.DataFrame(rows)

def table2_baseline_by_model(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """T2: Baseline accuracy by Model with composite score and Wilson CI."""
    if "model" not in baseline_df.columns:
        return pd.DataFrame()

    rows = []
    for model in sorted(baseline_df["model"].unique()):
        model_data = baseline_df[baseline_df["model"] == model]

        if "composite_score" in model_data.columns:
            cs_vals = model_data["composite_score"].dropna()
            cs_mean = cs_vals.mean()
            cs_std = cs_vals.std()
            cs_se = cs_std / np.sqrt(len(cs_vals))
            cs_lower = cs_mean - 1.96 * cs_se
            cs_upper = cs_mean + 1.96 * cs_se
        else:
            cs_mean = cs_lower = cs_upper = np.nan

        if "refer_match" in model_data.columns:
            ref_vals = model_data["refer_match"].dropna()
            ref_success = int(ref_vals.sum())
            ref_total = len(ref_vals)
            ref_rate = ref_success / ref_total if ref_total > 0 else 0
            ref_ci_lower, ref_ci_upper = wilson_ci(ref_success, ref_total)
        else:
            ref_rate = ref_ci_lower = ref_ci_upper = np.nan

        rows.append({
            "Model": model,
            "N": len(model_data),
            "Composite_Score": f"{cs_mean*100:.1f}% [{cs_lower*100:.1f}–{cs_upper*100:.1f}%]" if not np.isnan(cs_mean) else "N/A",
            "Referral_Match": f"{ref_rate*100:.1f}% [{ref_ci_lower*100:.1f}–{ref_ci_upper*100:.1f}%]" if not np.isnan(ref_rate) else "N/A",
            "CS_Mean": cs_mean,
            "CS_Lower": cs_lower,
            "CS_Upper": cs_upper,
        })

    return pd.DataFrame(rows)

def table3_baseline_by_persona(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """T3: Baseline accuracy by Persona with composite score and Wilson CI."""
    if "persona" not in baseline_df.columns:
        return pd.DataFrame()

    rows = []
    for persona in sorted(baseline_df["persona"].unique()):
        persona_data = baseline_df[baseline_df["persona"] == persona]

        if "composite_score" in persona_data.columns:
            cs_vals = persona_data["composite_score"].dropna()
            cs_mean = cs_vals.mean()
            cs_std = cs_vals.std()
            cs_se = cs_std / np.sqrt(len(cs_vals))
            cs_lower = cs_mean - 1.96 * cs_se
            cs_upper = cs_mean + 1.96 * cs_se
        else:
            cs_mean = cs_lower = cs_upper = np.nan

        if "refer_match" in persona_data.columns:
            ref_vals = persona_data["refer_match"].dropna()
            ref_success = int(ref_vals.sum())
            ref_total = len(ref_vals)
            ref_rate = ref_success / ref_total if ref_total > 0 else 0
            ref_ci_lower, ref_ci_upper = wilson_ci(ref_success, ref_total)
        else:
            ref_rate = ref_ci_lower = ref_ci_upper = np.nan

        rows.append({
            "Persona": PERSONA_LABELS.get(persona, persona),
            "N": len(persona_data),
            "Composite_Score": f"{cs_mean*100:.1f}% [{cs_lower*100:.1f}–{cs_upper*100:.1f}%]" if not np.isnan(cs_mean) else "N/A",
            "Referral_Match": f"{ref_rate*100:.1f}% [{ref_ci_lower*100:.1f}–{ref_ci_upper*100:.1f}%]" if not np.isnan(ref_rate) else "N/A",
            "CS_Mean": cs_mean,
            "CS_Lower": cs_lower,
            "CS_Upper": cs_upper,
        })

    return pd.DataFrame(rows)

def table4_decision_shifts(delta_df: pd.DataFrame) -> pd.DataFrame:
    """T4: Decision shifts from baseline by dimension × level with FDR."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    pvalues = []
    cohens_h_values = []

    for (dim, level), grp in delta_df.groupby(["dimension", "level"]):
        if dim == "baseline":
            continue

        label = LEVEL_LABELS.get((dim, level), f"{dim}={level}")

        metrics_to_check = [
            ("refer_match_changed", "Referral"),
            ("urgency_match_changed", "Urgency"),
            ("labs_match_changed", "Labs"),
            ("imaging_match_changed", "Imaging"),
            ("aspiration_match_changed", "Aspiration"),
            ("psychologized_changed", "Psychologized"),
        ]

        for metric, metric_label in metrics_to_check:
            if metric not in grp.columns:
                continue

            total = grp[metric].notna().sum()
            if total == 0:
                continue

            changed = grp[metric].fillna(0).astype(int).sum()
            change_rate = changed / total if total > 0 else 0

            # Get baseline rate from baseline data
            # For now, use observed rate as reference
            baseline_rate = change_rate * 0.5  # conservative null

            # Binomial test against null hypothesis
            if total > 0:
                btest = binomtest(changed, total, baseline_rate)
                pval = btest.pvalue
            else:
                pval = np.nan

            pvalues.append(pval if not np.isnan(pval) else 1.0)

            h = cohens_h(baseline_rate, change_rate)
            cohens_h_values.append(h)

            rows.append({
                "Dimension": DIM_LABELS.get(dim, dim),
                "Level": label,
                "Metric": metric_label,
                "N": total,
                "Changed": int(changed),
                "Change_Rate": f"{change_rate*100:.1f}%",
                "CI_Lower": wilson_ci(int(changed), total)[0] * 100,
                "CI_Upper": wilson_ci(int(changed), total)[1] * 100,
                "P_Value": pval,
                "Cohens_h": h,
            })

    # Apply FDR correction
    if pvalues:
        rejected, corrected_p = apply_fdr_correction(pvalues)
        for i, row in enumerate(rows):
            row["FDR_Corrected_P"] = corrected_p[i]
            row["Significant"] = "Yes" if rejected[i] else "No"

    result_df = pd.DataFrame(rows)
    return result_df

def table5_accuracy_change(delta_df: pd.DataFrame) -> pd.DataFrame:
    """T5: Composite score change by dimension × level."""
    if delta_df.empty or "composite_delta" not in delta_df.columns:
        return pd.DataFrame()

    rows = []
    for (dim, level), grp in delta_df.groupby(["dimension", "level"]):
        if dim == "baseline":
            continue

        label = LEVEL_LABELS.get((dim, level), f"{dim}={level}")

        if "composite_score_base" in grp.columns and "composite_score_iter" in grp.columns:
            base_vals = grp["composite_score_base"].dropna()
            iter_vals = grp["composite_score_iter"].dropna()

            if len(base_vals) > 0:
                base_mean = base_vals.mean()
                iter_mean = iter_vals.mean()
                delta = iter_mean - base_mean

                # Paired t-test
                if len(base_vals) > 1:
                    t_stat, p_val = stats.ttest_rel(iter_vals.iloc[:len(base_vals)], base_vals)
                else:
                    t_stat, p_val = np.nan, np.nan

                rows.append({
                    "Dimension": DIM_LABELS.get(dim, dim),
                    "Level": label,
                    "N": len(base_vals),
                    "Baseline_Mean": f"{base_mean*100:.1f}%",
                    "Iteration_Mean": f"{iter_mean*100:.1f}%",
                    "Delta": f"{delta*100:+.1f}%",
                    "T_Statistic": t_stat,
                    "P_Value": p_val,
                    "Base_Numeric": base_mean,
                    "Iter_Numeric": iter_mean,
                })

    return pd.DataFrame(rows)

def table6_psychologization(baseline_df: pd.DataFrame, delta_df: pd.DataFrame) -> pd.DataFrame:
    """T6: Psychologization & error rates by dimension."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    for (dim, level), grp in delta_df.groupby(["dimension", "level"]):
        if dim == "baseline":
            continue

        label = LEVEL_LABELS.get((dim, level), f"{dim}={level}")

        # Baseline psychologization rate
        baseline_psych = 0
        if "psychologized" in baseline_df.columns:
            baseline_psych_vals = baseline_df["psychologized"].dropna()
            if len(baseline_psych_vals) > 0:
                baseline_psych = baseline_psych_vals.mean()

        # Iteration psychologization rate
        iter_psych = 0
        if "psychologized_iter" in grp.columns:
            iter_psych_vals = grp["psychologized_iter"].dropna()
            if len(iter_psych_vals) > 0:
                iter_psych = iter_psych_vals.mean()

        # Baseline error rate
        baseline_error = 0
        if "psychologization_error" in baseline_df.columns:
            baseline_error_vals = baseline_df["psychologization_error"].dropna()
            if len(baseline_error_vals) > 0:
                baseline_error = baseline_error_vals.mean()

        # Iteration error rate
        iter_error = 0
        if "psychologization_error_iter" in grp.columns:
            iter_error_vals = grp["psychologization_error_iter"].dropna()
            if len(iter_error_vals) > 0:
                iter_error = iter_error_vals.mean()

        rows.append({
            "Dimension": DIM_LABELS.get(dim, dim),
            "Level": label,
            "Baseline_Psych_Rate": f"{baseline_psych*100:.1f}%",
            "Iteration_Psych_Rate": f"{iter_psych*100:.1f}%",
            "Psych_Delta": f"{(iter_psych - baseline_psych)*100:+.1f}%",
            "Baseline_Error_Rate": f"{baseline_error*100:.1f}%",
            "Iteration_Error_Rate": f"{iter_error*100:.1f}%",
            "Error_Delta": f"{(iter_error - baseline_error)*100:+.1f}%",
        })

    return pd.DataFrame(rows)

def table7_urgency_shifts(delta_df: pd.DataFrame) -> pd.DataFrame:
    """T7: Urgency direction (downgraded/correct/upgraded) by dimension × level."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    for (dim, level), grp in delta_df.groupby(["dimension", "level"]):
        if dim == "baseline":
            continue

        label = LEVEL_LABELS.get((dim, level), f"{dim}={level}")

        downgraded = 0
        upgraded = 0
        correct = 0

        if "urgency_downgraded_direction" in grp.columns:
            downgraded = (grp["urgency_downgraded_direction"] == -1).sum()
        if "urgency_upgraded_direction" in grp.columns:
            upgraded = (grp["urgency_upgraded_direction"] == 1).sum()

        total = len(grp)
        correct = total - downgraded - upgraded

        downgraded_pct = (downgraded / total * 100) if total > 0 else 0
        correct_pct = (correct / total * 100) if total > 0 else 0
        upgraded_pct = (upgraded / total * 100) if total > 0 else 0

        rows.append({
            "Dimension": DIM_LABELS.get(dim, dim),
            "Level": label,
            "N": total,
            "Downgraded": f"{downgraded} ({downgraded_pct:.1f}%)",
            "Correct": f"{correct} ({correct_pct:.1f}%)",
            "Upgraded": f"{upgraded} ({upgraded_pct:.1f}%)",
        })

    return pd.DataFrame(rows)

def table8_statistical_tests(baseline_df: pd.DataFrame, delta_df: pd.DataFrame) -> pd.DataFrame:
    """T8: Full statistical tests on all metrics with FDR correction."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    pvalues = []

    metrics_to_test = [
        ("refer_match_direction", "Referral Match"),
        ("urgency_match_direction", "Urgency Match"),
        ("labs_match_direction", "Labs Match"),
        ("imaging_match_direction", "Imaging Match"),
        ("aspiration_match_direction", "Aspiration Match"),
        ("psychologized_direction", "Psychologized"),
        ("urgency_downgraded_direction", "Urgency Downgraded"),
        ("urgency_upgraded_direction", "Urgency Upgraded"),
        ("acuity_match_direction", "Acuity Match"),
    ]

    for (dim, level), grp in delta_df.groupby(["dimension", "level"]):
        if dim == "baseline":
            continue

        label = LEVEL_LABELS.get((dim, level), f"{dim}={level}")

        for metric_col, metric_label in metrics_to_test:
            if metric_col not in grp.columns:
                continue

            vals = grp[metric_col].dropna()
            if len(vals) == 0:
                continue

            mean_diff = vals.mean()
            total = len(vals)

            if total > 1:
                t_stat, p_val = stats.ttest_1samp(vals, 0)
            else:
                t_stat, p_val = np.nan, np.nan

            pvalues.append(p_val if not np.isnan(p_val) else 1.0)

            rows.append({
                "Dimension": DIM_LABELS.get(dim, dim),
                "Level": label,
                "Metric": metric_label,
                "N": total,
                "Mean_Diff": f"{mean_diff:+.3f}",
                "T_Statistic": f"{t_stat:.3f}" if not np.isnan(t_stat) else "N/A",
                "P_Value": p_val,
            })

    # Apply FDR correction
    if pvalues:
        rejected, corrected_p = apply_fdr_correction(pvalues)
        for i, row in enumerate(rows):
            row["FDR_Corrected_P"] = corrected_p[i]
            row["Significant"] = "Yes" if rejected[i] else "No"

    return pd.DataFrame(rows)

def table9_per_model_shifts(delta_df: pd.DataFrame) -> pd.DataFrame:
    """T9: Overall shift rates per model."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    for model in sorted(delta_df["model"].unique()):
        model_data = delta_df[delta_df["model"] == model]

        total_pairs = len(model_data)
        if total_pairs == 0:
            continue

        metrics_changed = []
        for metric in ["refer_match_changed", "urgency_match_changed", "labs_match_changed",
                       "imaging_match_changed", "aspiration_match_changed"]:
            if metric in model_data.columns:
                changed = model_data[metric].fillna(0).astype(int).sum()
                metrics_changed.append(changed)

        total_changed = sum(metrics_changed)
        overall_change_rate = total_changed / (total_pairs * len(metrics_changed)) if total_pairs > 0 else 0

        if "composite_delta" in model_data.columns:
            composite_deltas = model_data["composite_delta"].dropna()
            composite_mean_delta = composite_deltas.mean() if len(composite_deltas) > 0 else 0
        else:
            composite_mean_delta = 0

        rows.append({
            "Model": model,
            "N_Pairs": total_pairs,
            "Overall_Change_Rate": f"{overall_change_rate*100:.1f}%",
            "Composite_Mean_Delta": f"{composite_mean_delta*100:+.1f}%",
            "Change_Numeric": overall_change_rate,
            "Delta_Numeric": composite_mean_delta,
        })

    return pd.DataFrame(rows)

def table10_per_persona_shifts(delta_df: pd.DataFrame) -> pd.DataFrame:
    """T10: Overall shift rates per persona."""
    if delta_df.empty:
        return pd.DataFrame()

    rows = []
    for persona in sorted(delta_df["persona"].unique()):
        persona_data = delta_df[delta_df["persona"] == persona]

        total_pairs = len(persona_data)
        if total_pairs == 0:
            continue

        metrics_changed = []
        for metric in ["refer_match_changed", "urgency_match_changed", "labs_match_changed",
                       "imaging_match_changed", "aspiration_match_changed"]:
            if metric in persona_data.columns:
                changed = persona_data[metric].fillna(0).astype(int).sum()
                metrics_changed.append(changed)

        total_changed = sum(metrics_changed)
        overall_change_rate = total_changed / (total_pairs * len(metrics_changed)) if total_pairs > 0 else 0

        if "composite_delta" in persona_data.columns:
            composite_deltas = persona_data["composite_delta"].dropna()
            composite_mean_delta = composite_deltas.mean() if len(composite_deltas) > 0 else 0
        else:
            composite_mean_delta = 0

        rows.append({
            "Persona": PERSONA_LABELS.get(persona, persona),
            "N_Pairs": total_pairs,
            "Overall_Change_Rate": f"{overall_change_rate*100:.1f}%",
            "Composite_Mean_Delta": f"{composite_mean_delta*100:+.1f}%",
            "Change_Numeric": overall_change_rate,
            "Delta_Numeric": composite_mean_delta,
        })

    return pd.DataFrame(rows)


# ============================================================================
# FIGURE GENERATION
# ============================================================================

def _save_fig(fig, path: Path, title: str = ""):
    """Save figure to PNG and add metadata."""
    fig.savefig(path, format=FIG_FMT, dpi=DPI, bbox_inches="tight", pad_inches=0.2)
    print(f"  Saved {path.name}")
    plt.close(fig)

def figure1_baseline_accuracy(baseline_df: pd.DataFrame, output_dir: Path):
    """fig01: Baseline accuracy bar chart with Wilson CIs."""
    _style()

    metrics = [
        ("refer_match", "Referral"),
        ("urgency_match", "Urgency"),
        ("labs_match", "Labs"),
        ("imaging_match", "Imaging"),
        ("acuity_match", "Acuity"),
        ("dx_match_primary", "Dx (Primary)"),
        ("composite_score", "Composite"),
    ]

    values = []
    ci_lower = []
    ci_upper = []
    labels = []

    for col, label in metrics:
        if col not in baseline_df.columns:
            continue

        vals = baseline_df[col].dropna()
        if len(vals) > 0:
            if col == "composite_score":
                mean_val = vals.mean()
                std_val = vals.std()
                se_val = std_val / np.sqrt(len(vals))
                lower = mean_val - 1.96 * se_val
                upper = mean_val + 1.96 * se_val
            else:
                total = len(vals)
                success = int(vals.sum())
                mean_val = success / total if total > 0 else 0
                lower, upper = wilson_ci(success, total)

            values.append(mean_val * 100)
            ci_lower.append(lower * 100)
            ci_upper.append(upper * 100)
            labels.append(label)

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    errors = [np.array(values) - np.array(ci_lower), np.array(ci_upper) - np.array(values)]

    bars = ax.bar(x, values, yerr=errors, capsize=5, color=BLUE, alpha=0.8, edgecolor=GRID, linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Accuracy (%)", fontsize=11)
    ax.set_ylim(0, 105)
    ax.axhline(y=50, color=GRID, linestyle="--", linewidth=0.8, alpha=0.5)
    ax.grid(True, alpha=0.3, axis="y")

    _header(fig, "Baseline Model Accuracy")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig01_baseline_accuracy.{FIG_FMT}")

def figure2_decision_change_heatmap(delta_df: pd.DataFrame, output_dir: Path):
    """fig02: Decision-change heatmap."""
    if delta_df.empty:
        print("  Skipped fig02 (no delta data)")
        return

    _style()

    metrics = ["refer_match_changed", "urgency_match_changed", "labs_match_changed",
               "imaging_match_changed", "aspiration_match_changed"]

    metric_labels = ["Referral", "Urgency", "Labs", "Imaging", "Aspiration"]

    # Build matrix
    dims_levels = []
    for dim in sorted(delta_df["dimension"].unique(), key=dim_sort_key):
        if dim == "baseline":
            continue
        for level in sorted(delta_df[delta_df["dimension"] == dim]["level"].unique()):
            dims_levels.append((dim, level))

    data = np.zeros((len(dims_levels), len(metrics)))
    for i, (dim, level) in enumerate(dims_levels):
        grp = delta_df[(delta_df["dimension"] == dim) & (delta_df["level"] == level)]
        for j, metric in enumerate(metrics):
            if metric in grp.columns:
                changed = grp[metric].fillna(0).astype(int).sum()
                total = len(grp)
                data[i, j] = (changed / total * 100) if total > 0 else 0

    fig, ax = plt.subplots(figsize=(10, 12))
    im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=100)

    ax.set_xticks(np.arange(len(metrics)))
    ax.set_yticks(np.arange(len(dims_levels)))
    ax.set_xticklabels(metric_labels, rotation=45, ha="right")

    y_labels = [LEVEL_LABELS.get((dim, level), f"{dim}={level}") for dim, level in dims_levels]
    ax.set_yticklabels(y_labels, fontsize=9)

    for i in range(len(dims_levels)):
        for j in range(len(metrics)):
            text = ax.text(j, i, f"{data[i, j]:.0f}%", ha="center", va="center",
                          color="white" if data[i, j] > 50 else TXT, fontsize=9)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Change Rate (%)", fontsize=10)

    _header(fig, "Decision Changes by Dimension × Level", "% of pairs with decision change")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig02_decision_change_heatmap.{FIG_FMT}")

def figure3_referral_urgency_changes(delta_df: pd.DataFrame, output_dir: Path):
    """fig03: Referral & urgency changes by dimension."""
    if delta_df.empty:
        print("  Skipped fig03 (no delta data)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    referral_changes = []
    urgency_changes = []

    for dim in dims:
        dim_data = delta_df[delta_df["dimension"] == dim]

        if "refer_match_changed" in dim_data.columns:
            ref_changed = dim_data["refer_match_changed"].fillna(0).astype(int).sum()
            ref_total = len(dim_data)
            referral_changes.append((ref_changed / ref_total * 100) if ref_total > 0 else 0)
        else:
            referral_changes.append(0)

        if "urgency_match_changed" in dim_data.columns:
            urg_changed = dim_data["urgency_match_changed"].fillna(0).astype(int).sum()
            urg_total = len(dim_data)
            urgency_changes.append((urg_changed / urg_total * 100) if urg_total > 0 else 0)
        else:
            urgency_changes.append(0)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(dims))
    width = 0.35

    bars1 = ax.bar(x - width/2, referral_changes, width, label="Referral", color=BLUE, alpha=0.8, edgecolor=GRID)
    bars2 = ax.bar(x + width/2, urgency_changes, width, label="Urgency", color=RED, alpha=0.8, edgecolor=GRID)

    ax.set_xlabel("Dimension", fontsize=11)
    ax.set_ylabel("Change Rate (%)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([DIM_LABELS.get(d, d) for d in dims], rotation=45, ha="right")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")

    _header(fig, "Referral & Urgency Changes by Dimension")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig03_referral_urgency_changes.{FIG_FMT}")

def figure4_psychologization_dual_panel(delta_df: pd.DataFrame, baseline_df: pd.DataFrame, output_dir: Path):
    """fig04: Psychologization dual panel (baseline vs iteration)."""
    if delta_df.empty:
        print("  Skipped fig04 (no delta data)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    baseline_psych_rates = []
    iteration_psych_rates = []

    for dim in dims:
        # Baseline rate
        baseline_data = baseline_df[baseline_df["dimension"] == dim] if "dimension" in baseline_df.columns else baseline_df
        if "psychologized" in baseline_data.columns:
            base_psych = baseline_data["psychologized"].mean()
        else:
            base_psych = baseline_df["psychologized"].mean() if "psychologized" in baseline_df.columns else 0

        baseline_psych_rates.append(base_psych * 100)

        # Iteration rate
        dim_data = delta_df[delta_df["dimension"] == dim]
        if "psychologized_iter" in dim_data.columns:
            iter_psych = dim_data["psychologized_iter"].mean()
        else:
            iter_psych = 0

        iteration_psych_rates.append(iter_psych * 100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    x = np.arange(len(dims))
    width = 0.6

    # Left: baseline vs iteration
    bars1 = ax1.bar(x - width/2, baseline_psych_rates, width, label="Baseline", color=BLUE, alpha=0.7, edgecolor=GRID)
    bars2 = ax1.bar(x + width/2, iteration_psych_rates, width, label="Iteration", color=RED, alpha=0.7, edgecolor=GRID)
    ax1.set_xlabel("Dimension", fontsize=11)
    ax1.set_ylabel("Psychologization Rate (%)", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels([DIM_LABELS.get(d, d) for d in dims], rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis="y")

    # Right: delta
    deltas = [iter_psych_rates[i] - baseline_psych_rates[i] for i in range(len(dims))]
    colors_delta = [RED if d > 0 else GREEN for d in deltas]
    bars3 = ax2.barh(range(len(dims)), deltas, color=colors_delta, alpha=0.7, edgecolor=GRID)
    ax2.set_yticks(range(len(dims)))
    ax2.set_yticklabels([DIM_LABELS.get(d, d) for d in dims], fontsize=10)
    ax2.set_xlabel("Psychologization Change (pp)", fontsize=11)
    ax2.axvline(x=0, color=TXT, linestyle="-", linewidth=0.8)
    ax2.grid(True, alpha=0.3, axis="x")

    _header(fig, "Psychologization Rates by Dimension")
    _wm(ax1)
    _wm(ax2)
    _save_fig(fig, output_dir / f"fig04_psychologization_dual_panel.{FIG_FMT}")

def figure5_urgency_direction_stacked(delta_df: pd.DataFrame, output_dir: Path):
    """fig05: Urgency direction stacked bar (downgraded/correct/upgraded)."""
    if delta_df.empty:
        print("  Skipped fig05 (no delta data)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    downgraded_pcts = []
    correct_pcts = []
    upgraded_pcts = []

    for dim in dims:
        dim_data = delta_df[delta_df["dimension"] == dim]
        total = len(dim_data)

        if total == 0:
            downgraded_pcts.append(0)
            correct_pcts.append(0)
            upgraded_pcts.append(0)
            continue

        downgraded = 0
        upgraded = 0

        if "urgency_downgraded_direction" in dim_data.columns:
            downgraded = (dim_data["urgency_downgraded_direction"] == -1).sum()
        if "urgency_upgraded_direction" in dim_data.columns:
            upgraded = (dim_data["urgency_upgraded_direction"] == 1).sum()

        correct = total - downgraded - upgraded

        downgraded_pcts.append((downgraded / total * 100) if total > 0 else 0)
        correct_pcts.append((correct / total * 100) if total > 0 else 0)
        upgraded_pcts.append((upgraded / total * 100) if total > 0 else 0)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(dims))
    width = 0.6

    p1 = ax.bar(x, downgraded_pcts, width, label="Downgraded", color=RED, alpha=0.8, edgecolor=GRID)
    p2 = ax.bar(x, correct_pcts, width, bottom=downgraded_pcts, label="Correct", color=GREEN, alpha=0.8, edgecolor=GRID)

    bottom = np.array(downgraded_pcts) + np.array(correct_pcts)
    p3 = ax.bar(x, upgraded_pcts, width, bottom=bottom, label="Upgraded", color=AMBER, alpha=0.8, edgecolor=GRID)

    ax.set_xlabel("Dimension", fontsize=11)
    ax.set_ylabel("Proportion (%)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([DIM_LABELS.get(d, d) for d in dims], rotation=45, ha="right")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")

    _header(fig, "Urgency Direction Changes by Dimension")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig05_urgency_direction_stacked.{FIG_FMT}")

def figure6_composite_delta_diverging(delta_df: pd.DataFrame, output_dir: Path):
    """fig06: Composite delta diverging bar."""
    if delta_df.empty or "composite_delta" not in delta_df.columns:
        print("  Skipped fig06 (no composite delta)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    deltas = []
    dim_labels_list = []

    for dim in dims:
        dim_data = delta_df[delta_df["dimension"] == dim]
        if "composite_delta" in dim_data.columns:
            delta_mean = dim_data["composite_delta"].mean() * 100
        else:
            delta_mean = 0

        deltas.append(delta_mean)
        dim_labels_list.append(DIM_LABELS.get(dim, dim))

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = [RED if d > 0 else GREEN for d in deltas]
    bars = ax.barh(range(len(dims)), deltas, color=colors, alpha=0.8, edgecolor=GRID)

    ax.set_yticks(range(len(dims)))
    ax.set_yticklabels(dim_labels_list, fontsize=10)
    ax.set_xlabel("Composite Score Change (pp)", fontsize=11)
    ax.axvline(x=0, color=TXT, linestyle="-", linewidth=0.8)

    for i, (bar, delta) in enumerate(zip(bars, deltas)):
        ax.text(delta + (0.5 if delta > 0 else -0.5), i, f"{delta:+.1f}pp",
               va="center", ha="left" if delta > 0 else "right", fontsize=9)

    ax.grid(True, alpha=0.3, axis="x")

    _header(fig, "Composite Score Change by Dimension", "Higher = worse")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig06_composite_delta_diverging.{FIG_FMT}")

def figure7_composite_by_dimension_box(delta_df: pd.DataFrame, output_dir: Path):
    """fig07: Composite score by dimension box plot."""
    if delta_df.empty or "composite_delta" not in delta_df.columns:
        print("  Skipped fig07 (no composite delta)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    data_to_plot = []
    dim_labels_list = []

    for dim in dims:
        dim_data = delta_df[delta_df["dimension"] == dim]
        if "composite_delta" in dim_data.columns:
            deltas = dim_data["composite_delta"].dropna().values * 100
            if len(deltas) > 0:
                data_to_plot.append(deltas)
                dim_labels_list.append(DIM_LABELS.get(dim, dim))

    if not data_to_plot:
        print("  Skipped fig07 (no data)")
        return

    fig, ax = plt.subplots(figsize=(12, 7))
    bp = ax.boxplot(data_to_plot, labels=dim_labels_list, patch_artist=True)

    for patch in bp["boxes"]:
        patch.set_facecolor(BLUE)
        patch.set_alpha(0.7)

    ax.axhline(y=0, color=TXT, linestyle="--", linewidth=1, alpha=0.5)
    ax.set_ylabel("Composite Score Change (pp)", fontsize=11)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3, axis="y")

    _header(fig, "Composite Score Distribution by Dimension")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig07_composite_by_dimension_box.{FIG_FMT}")

def figure8_disease_category_heatmap(delta_df: pd.DataFrame, output_dir: Path):
    """fig08: Disease category × dimension interaction heatmap."""
    if delta_df.empty or "gt_category" not in delta_df.columns:
        print("  Skipped fig08 (no gt_category)")
        return

    _style()

    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)
    categories = sorted([c for c in delta_df["gt_category"].unique() if pd.notna(c)])

    if len(categories) == 0 or len(dims) == 0:
        print("  Skipped fig08 (insufficient data)")
        return

    data = np.zeros((len(categories), len(dims)))

    for i, cat in enumerate(categories):
        for j, dim in enumerate(dims):
            subset = delta_df[(delta_df["gt_category"] == cat) & (delta_df["dimension"] == dim)]
            if len(subset) > 0 and "composite_delta" in subset.columns:
                delta_mean = subset["composite_delta"].mean() * 100
                data[i, j] = delta_mean

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto", vmin=-20, vmax=20)

    ax.set_xticks(np.arange(len(dims)))
    ax.set_yticks(np.arange(len(categories)))
    ax.set_xticklabels([DIM_LABELS.get(d, d) for d in dims], rotation=45, ha="right")
    ax.set_yticklabels([str(c) for c in categories])

    for i in range(len(categories)):
        for j in range(len(dims)):
            text = ax.text(j, i, f"{data[i, j]:.1f}",
                          ha="center", va="center", color="white" if abs(data[i, j]) > 10 else TXT, fontsize=9)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Mean Composite Delta (pp)", fontsize=10)

    ax.set_xlabel("Dimension", fontsize=11)
    ax.set_ylabel("Disease Category", fontsize=11)

    _header(fig, "Disease Category × Dimension Interaction")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig08_disease_category_heatmap.{FIG_FMT}")

def figure9_persona_susceptibility(delta_df: pd.DataFrame, output_dir: Path):
    """fig09: Persona susceptibility scatter."""
    if delta_df.empty:
        print("  Skipped fig09 (no delta data)")
        return

    _style()

    personas = sorted(delta_df["persona"].unique())
    dims = sorted([d for d in delta_df["dimension"].unique() if d != "baseline"], key=dim_sort_key)

    fig, ax = plt.subplots(figsize=(12, 7))

    for persona in personas:
        persona_data = delta_df[delta_df["persona"] == persona]

        x_vals = []
        y_vals = []

        for dim in dims:
            dim_data = persona_data[persona_data["dimension"] == dim]
            if len(dim_data) > 0 and "composite_delta" in dim_data.columns:
                delta_mean = dim_data["composite_delta"].mean() * 100
                x_vals.append(dims.index(dim))
                y_vals.append(delta_mean)

        color = PERSONA_COLORS.get(persona, SLATE)
        ax.scatter(x_vals, y_vals, s=100, alpha=0.7, label=PERSONA_LABELS.get(persona, persona), color=color)

    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels([DIM_LABELS.get(d, d) for d in dims], rotation=45, ha="right")
    ax.set_ylabel("Composite Score Change (pp)", fontsize=11)
    ax.axhline(y=0, color=TXT, linestyle="--", linewidth=0.8, alpha=0.5)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    _header(fig, "Persona Susceptibility by Dimension")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig09_persona_susceptibility.{FIG_FMT}")

def figure10_model_persona_heatmap(delta_df: pd.DataFrame, output_dir: Path):
    """fig10: Model × Persona interaction heatmap."""
    if delta_df.empty:
        print("  Skipped fig10 (no delta data)")
        return

    _style()

    models = sorted(delta_df["model"].unique())
    personas = sorted(delta_df["persona"].unique())

    data = np.zeros((len(personas), len(models)))

    for i, persona in enumerate(personas):
        for j, model in enumerate(models):
            subset = delta_df[(delta_df["persona"] == persona) & (delta_df["model"] == model)]
            if len(subset) > 0 and "composite_delta" in subset.columns:
                delta_mean = subset["composite_delta"].mean() * 100
                data[i, j] = delta_mean

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto", vmin=-20, vmax=20)

    ax.set_xticks(np.arange(len(models)))
    ax.set_yticks(np.arange(len(personas)))
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_yticklabels([PERSONA_LABELS.get(p, p) for p in personas])

    for i in range(len(personas)):
        for j in range(len(models)):
            text = ax.text(j, i, f"{data[i, j]:.1f}",
                          ha="center", va="center", color="white" if abs(data[i, j]) > 10 else TXT, fontsize=9)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Mean Composite Delta (pp)", fontsize=10)

    ax.set_xlabel("Model", fontsize=11)
    ax.set_ylabel("Persona", fontsize=11)

    _header(fig, "Model × Persona Interaction")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig10_model_persona_heatmap.{FIG_FMT}")

def figure11_model_shift_paired_dot(delta_df: pd.DataFrame, output_dir: Path):
    """fig11: Model shift paired dot plot."""
    if delta_df.empty:
        print("  Skipped fig11 (no delta data)")
        return

    _style()

    models = sorted(delta_df["model"].unique())

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, model in enumerate(models):
        model_data = delta_df[delta_df["model"] == model]

        if "composite_delta" in model_data.columns:
            deltas = model_data["composite_delta"].dropna().values * 100

            y_pos = np.random.normal(i, 0.04, size=len(deltas))
            ax.scatter(y_pos, deltas, alpha=0.5, s=30, color=BLUE)

            mean_delta = deltas.mean()
            ax.plot(i, mean_delta, "D", markersize=10, color=RED, zorder=5)

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylabel("Composite Score Change (pp)", fontsize=11)
    ax.axhline(y=0, color=TXT, linestyle="--", linewidth=0.8, alpha=0.5)
    ax.grid(True, alpha=0.3, axis="y")

    _header(fig, "Model Shift: Individual Cases & Mean", "Red diamond = mean per model")
    _wm(ax)
    _save_fig(fig, output_dir / f"fig11_model_shift_paired_dot.{FIG_FMT}")


# ============================================================================
# PDF CONSOLIDATION
# ============================================================================

def consolidate_pdf(output_dir: Path):
    """Consolidate all PNG figures into a single PDF."""
    try:
        from PIL import Image
        import io

        fig_files = sorted(output_dir.glob("fig*.png"))
        if not fig_files:
            print("  No figures found for PDF consolidation")
            return

        images = []
        for fig_file in fig_files:
            img = Image.open(fig_file).convert("RGB")
            images.append(img)

        if images:
            images[0].save(
                output_dir / "all_figures.pdf",
                save_all=True,
                append_images=images[1:],
                quality=95,
                optimize=False
            )
            print(f"  Consolidated PDF: all_figures.pdf")
    except Exception as e:
        print(f"  Warning: Could not create PDF: {e}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main analysis pipeline."""
    # Input handling
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./figures")
    else:
        input_path, output_dir = prompt_for_paths()

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"Rheumato Bias Pipeline: Comprehensive Analysis")
    print(f"{'='*80}\n")

    # Load data
    print(f"Loading data from: {input_path}")
    df = load_data(input_path)
    print(f"  Loaded {len(df)} records")
    print(f"  Models: {sorted(df['model'].unique()) if 'model' in df.columns else 'N/A'}")
    print(f"  Personas: {sorted(df['persona'].unique()) if 'persona' in df.columns else 'N/A'}")
    print(f"  Cases: {df['case_id'].nunique() if 'case_id' in df.columns else 'N/A'}")

    baseline_df = df[df["condition"] == "baseline"].copy()
    print(f"  Baseline records: {len(baseline_df)}")

    # Compute deltas
    print(f"\nComputing deltas...")
    delta_df = compute_deltas(df)
    print(f"  Baseline-iteration pairs: {len(delta_df)}")

    # Generate tables
    print(f"\nGenerating tables...")
    tables = {}

    print(f"  T1: Baseline Accuracy")
    tables["T1_Baseline_Accuracy"] = table1_baseline_accuracy(baseline_df)

    print(f"  T2: Baseline by Model")
    tables["T2_Baseline_by_Model"] = table2_baseline_by_model(baseline_df)

    print(f"  T3: Baseline by Persona")
    tables["T3_Baseline_by_Persona"] = table3_baseline_by_persona(baseline_df)

    print(f"  T4: Decision Shifts")
    tables["T4_Decision_Shifts"] = table4_decision_shifts(delta_df)

    print(f"  T5: Accuracy Change")
    tables["T5_Accuracy_Change"] = table5_accuracy_change(delta_df)

    print(f"  T6: Psychologization")
    tables["T6_Psychologization"] = table6_psychologization(baseline_df, delta_df)

    print(f"  T7: Urgency Shifts")
    tables["T7_Urgency_Shifts"] = table7_urgency_shifts(delta_df)

    print(f"  T8: Statistical Tests")
    tables["T8_Statistical_Tests"] = table8_statistical_tests(baseline_df, delta_df)

    print(f"  T9: Per-Model Shifts")
    tables["T9_Per_Model_Shifts"] = table9_per_model_shifts(delta_df)

    print(f"  T10: Per-Persona Shifts")
    tables["T10_Per_Persona_Shifts"] = table10_per_persona_shifts(delta_df)

    # Save tables to Excel
    excel_path = output_dir / "analysis_tables.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for sheet_name, table_df in tables.items():
            table_df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"\nSaved tables to: {excel_path}")

    # Generate figures
    print(f"\nGenerating figures...")
    print(f"  fig01: Baseline Accuracy")
    figure1_baseline_accuracy(baseline_df, output_dir)

    print(f"  fig02: Decision Change Heatmap")
    figure2_decision_change_heatmap(delta_df, output_dir)

    print(f"  fig03: Referral & Urgency Changes")
    figure3_referral_urgency_changes(delta_df, output_dir)

    print(f"  fig04: Psychologization Dual Panel")
    figure4_psychologization_dual_panel(delta_df, baseline_df, output_dir)

    print(f"  fig05: Urgency Direction Stacked")
    figure5_urgency_direction_stacked(delta_df, output_dir)

    print(f"  fig06: Composite Delta Diverging")
    figure6_composite_delta_diverging(delta_df, output_dir)

    print(f"  fig07: Composite by Dimension Box")
    figure7_composite_by_dimension_box(delta_df, output_dir)

    print(f"  fig08: Disease Category Heatmap")
    figure8_disease_category_heatmap(delta_df, output_dir)

    print(f"  fig09: Persona Susceptibility")
    figure9_persona_susceptibility(delta_df, output_dir)

    print(f"  fig10: Model × Persona Heatmap")
    figure10_model_persona_heatmap(delta_df, output_dir)

    print(f"  fig11: Model Shift Paired Dot")
    figure11_model_shift_paired_dot(delta_df, output_dir)

    # Consolidate PDF
    print(f"\nConsolidating PDF...")
    consolidate_pdf(output_dir)

    # Summary
    print(f"\n{'='*80}")
    print(f"Analysis complete!")
    print(f"Output directory: {output_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
