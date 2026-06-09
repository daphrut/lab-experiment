def make_regression_table(
    fit_list,
    model_names,
    keep_vars,
    var_labels,
    fe_rows=None,
    col_groups=None,
    col_subgroups=None,
    baseline_mean=None,
    outcome_levels=None,
    df_levels=None,
    decimals=3,  # int or list[int], one per model column
    mean_decimals=0,  # int or list[int], decimal places for baseline mean row
    r2_type=None,
    col1_width="5.5cm",
    coln_width="2cm",
    col_widths=None,
):
    """
    Create LaTeX tables for pyfixest and statsmodels results.

    Parameters
    ----------
    fit_list        : list of results objects (pyfixest or statsmodels)
    model_names     : list of strings, e.g. ["(1)", "(2)", "(3)", "(4)"]
    keep_vars       : list of variable names to display
    var_labels      : dict mapping variable names to LaTeX display labels
    fe_rows         : optional dict mapping FE label to list of bools
                      e.g. {"Lab group FE": [True, True, False, False]}
                      if None, FE rows are omitted entirely
    col_groups      : optional dict for top-level column groupings
                      e.g. {"Baseline": [0,1], "Robustness": [2,3]}
    col_subgroups   : optional dict for second-level column groupings
                      e.g. {"Levels": [0,2], "Log": [1,3]}
    baseline_mean   : optional. Pass "auto" to compute from df_levels,
                      or a dict {col_index: value}, or None to omit
    outcome_levels  : string, outcome column name (used if baseline_mean="auto")
    df_levels       : dataframe (used if baseline_mean="auto")
    decimals        : int, decimal places for coefficients (default 3)
    r2_type         : "None" by default, "within" for TWFE (R² Within), "adjr2" for OLS (Adjusted R²),
                      or "both" to show both rows
    col1_width      : width of the first column (row labels)
    coln_width      : width of model number columns (if the same)
    col_widths      : optional list of column widths for model columns i.e. 2 onwards (overrides coln_width)
    """

    n_models = len(fit_list)
    decimals_list      = decimals       if isinstance(decimals,       list) else [decimals]       * n_models
    mean_decimals_list = mean_decimals  if isinstance(mean_decimals,  list) else [mean_decimals]  * n_models

    # ---------------------------
    # Helper: extract stats
    # ---------------------------
    def get_stars(pval):
        if pval < 0.01:   return "***"
        elif pval < 0.05: return "**"
        elif pval < 0.10: return "*"
        else:             return ""

    def checkmark_or_dash(val):
        return r"\checkmark" if val else r"\textemdash"

    def is_pyfixest(fit):
        return hasattr(fit, 'coef') and hasattr(fit, '_r2_within')

    def get_coef(fit, var):
        if is_pyfixest(fit):
            return fit.coef().loc[var]
        else:
            return fit.params[var]

    def get_se(fit, var):
        if is_pyfixest(fit):
            return fit.se().loc[var]
        else:
            return fit.bse[var]

    def get_pval(fit, var):
        if is_pyfixest(fit):
            return fit.pvalue().loc[var]
        else:
            return fit.pvalues[var]

    def get_nobs(fit):
        if is_pyfixest(fit):
            return int(fit._N)
        else:
            return int(fit.nobs)

    def get_r2_within(fit):
        if is_pyfixest(fit):
            return fit._r2_within
        else:
            return None  # not applicable

    def get_r2_adj(fit):
        if is_pyfixest(fit):
            return fit._adj_r2
        else:
            return fit.rsquared_adj

    lines = []

    # ---------------------------
    # Table header
    # ---------------------------

    if col_widths is not None:
        widths = col_widths
    else:
        widths = [coln_width] * n_models
    col_spec = f"@{{}}L{{{col1_width}}}" + "".join(f"C{{{w}}}" for w in widths)
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # Top-level column groups
    # ---------------------------
    if col_groups is not None:
        group_row = " "
        cmidrule_parts = []
        for group_name, col_indices in col_groups.items():
            span  = len(col_indices)
            start = min(col_indices) + 2  # +2: 1 for label col, 1 for 1-indexing
            end   = max(col_indices) + 2
            group_row += f" & \\multicolumn{{{span}}}{{c}}{{{group_name}}}"
            cmidrule_parts.append(f"\\cmidrule(lr){{{start}-{end}}}")
        group_row += r" \\"
        lines.append(group_row)
        lines.append(" ".join(cmidrule_parts))

    # ---------------------------
    # Second-level subgroups
    # ---------------------------
    if col_subgroups is not None:
        subgroup_map = {}
        for subgroup_name, col_indices in col_subgroups.items():
            for idx in col_indices:
                subgroup_map[idx] = subgroup_name
        subgroup_row = " & " + " & ".join(
            [subgroup_map.get(i, "") for i in range(n_models)]
        ) + r" \\"
        lines.append(subgroup_row)

    # ---------------------------
    # Model numbers
    # ---------------------------
    num_row = " & " + " & ".join(model_names) + r" \\"
    lines.append(num_row)
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # Coefficients and SEs
    # ---------------------------
    for var in keep_vars:
        label_str = var_labels.get(var, var.replace("_", " "))
        coef_row = []
        se_row   = []
        for i, fit in enumerate(fit_list):
            fmt = f"{{:.{decimals_list[i]}f}}"
            try:
                coef  = get_coef(fit, var)
                se    = get_se(fit, var)
                pval  = get_pval(fit, var)
                stars = get_stars(pval)
                coef_row.append(f"${fmt.format(coef)}\\rlap{{{stars}}}$")
                se_row.append(f"$({fmt.format(se)})$")
            except KeyError:
                coef_row.append("")
                se_row.append("")

        lines.append(f"{label_str} & " + " & ".join(coef_row) + r" \\")
        lines.append(r" & " + " & ".join(se_row) + r" \\")
        lines.append(r"\addlinespace[0.2cm]")

    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # Bottom panel
    # ---------------------------

    # Observations
    obs_row = "Number of observations & " + " & ".join(
        [f"{get_nobs(fit):,}" for fit in fit_list]
    ) + r" \\"
    lines.append(obs_row)

    # R² rows
    if r2_type == "within":
        r2_row = "R$^2$ Within & " + " & ".join(
            [f"{get_r2_within(fit):.{decimals_list[i]}f}"
             if get_r2_within(fit) is not None else ""
             for i, fit in enumerate(fit_list)]
        ) + r" \\"
        lines.append(r2_row)

    elif r2_type == "adjr2":
        r2_row = "Adjusted R$^2$ & " + " & ".join(
            [f"{get_r2_adj(fit):.{decimals_list[i]}f}" for i, fit in enumerate(fit_list)]
        ) + r" \\"
        lines.append(r2_row)

    elif r2_type == "both":
        r2_within_row = "R$^2$ Within & " + " & ".join(
            [f"{get_r2_within(fit):.{decimals_list[i]}f}"
             if get_r2_within(fit) is not None else ""
             for i, fit in enumerate(fit_list)]
        ) + r" \\"
        r2_adj_row = "Adjusted R$^2$ & " + " & ".join(
            [f"{get_r2_adj(fit):.{decimals_list[i]}f}" for i, fit in enumerate(fit_list)]
        ) + r" \\"
        lines.append(r2_within_row)
        lines.append(r2_adj_row)

    # Baseline mean
    if baseline_mean == "auto":
        bl_means = []
        for fit in fit_list:
            if is_pyfixest(fit) and hasattr(fit, '_depvar') and hasattr(fit, '_data'):
                data, depvar = fit._data, fit._depvar
                if 'survey' in data.columns:
                    val = data[data['survey'] == 'BL'][depvar].mean()
                else:
                    val = None
            elif df_levels is not None and outcome_levels is not None:
                val = df_levels[df_levels['survey'] == 'BL'][outcome_levels].mean()
            else:
                val = None
            bl_means.append(val)
        mean_vals = [
            f"{{:,.{mean_decimals_list[i]}f}}".format(v) if (v is not None and v == v) else ""
            for i, v in enumerate(bl_means)
        ]
        lines.append("Baseline mean & " + " & ".join(mean_vals) + r" \\")
    elif isinstance(baseline_mean, list):
        mean_vals = [
            f"{{:,.{mean_decimals_list[i]}f}}".format(v) if v is not None else ""
            for i, v in enumerate(baseline_mean)
        ]
        lines.append("Baseline mean & " + " & ".join(mean_vals) + r" \\")
    elif isinstance(baseline_mean, dict):
        mean_vals = [
            f"{{:,.{mean_decimals_list[i]}f}}".format(baseline_mean[i]) if i in baseline_mean else ""
            for i in range(n_models)
        ]
        lines.append("Baseline mean & " + " & ".join(mean_vals) + r" \\")

    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # FE rows (optional)
    # ---------------------------
    if fe_rows is not None:
        for fe_label, fe_vals in fe_rows.items():
            fe_row = f"{fe_label} & " + " & ".join(
                [checkmark_or_dash(v) for v in fe_vals]
            ) + r" \\"
            lines.append(fe_row)

    lines.append(r"\addlinespace[0.2cm]")
    lines.append(r"\hline")

    lines.append(r"\end{tabular}")

    return "\n".join(lines)