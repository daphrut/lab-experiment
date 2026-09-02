def make_ml_comparison_table(
    model_coefs,
    model_names,
    n_obs,
    r2,
    keep_vars,
    var_labels,
    r2_label="Cross-validated R$^2$",
    fe_rows=None,
    decimals=2,
    col1_width="6cm",
    coln_width="2.5cm",
    col_widths=None,
    model_numbers=None,
    section_labels=None,
):
    """
    Create a LaTeX comparison table for regularized/ML model coefficients
    (e.g. LASSO) that do not have valid standard errors or p-values.

    Deliberately has no significance stars and no SE row. Report predictive 
    performance (R², typically cross-validated) instead; coefficients are descriptive.

    Same visual conventions as make_regression_table/make_balance_table

    Parameters
    ----------
    model_coefs : list of dicts, one per model column, {var_name: coefficient}
    model_names : list of strings, e.g. ["(1)", "(2)"]
    n_obs       : list of int, one per model
    r2          : list of float, one per model
    keep_vars   : list of variable names to display, in order
    var_labels  : dict mapping variable names to LaTeX display labels
    r2_label    : row label for the R² row
    fe_rows     : optional dict mapping FE label to list of bools,
                  e.g. {"Institute FE": [True, True]}; omitted if None
    decimals    : int or list[int], one per model column
    col1_width  : width of the first column (row labels)
    coln_width  : width of model number columns (if the same)
    col_widths  : optional list of column widths for model columns (overrides coln_width)
    model_numbers : optional list of strings, one per model column, e.g. ["(1)", "(2)"] -
                  added as its own row directly below model_names if given
    section_labels : optional dict mapping a keep_vars entry to a subtitle string,
                  inserted as its own italicized row directly above that variable's
                  row - e.g. {"topic_2": "Research topics"} to label a group of rows
    """

    n_models = len(model_coefs)
    decimals_list = decimals if isinstance(decimals, list) else [decimals] * n_models

    def fmt_val(val, d):
        if val != val:  # NaN
            return ""
        magnitude = f"{{:,.{d}f}}".format(abs(val)).replace(",", "{,}")
        sign = r"\llap{-}" if val < 0 else " "
        return f"{sign}{magnitude}"

    def checkmark_or_dash(val):
        return r"\checkmark" if val else r"\textemdash"

    lines = []

    # Header
    widths = col_widths if col_widths is not None else [coln_width] * n_models
    col_spec = f"@{{}}L{{{col1_width}}}" + "".join(f"C{{{w}}}" for w in widths)
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")
    lines.append(" & " + " & ".join(model_names) + r" \\")
    if model_numbers is not None:
        lines.append(" & " + " & ".join(model_numbers) + r" \\")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # Coefficient rows - one row per variable, no SE row underneath (none exist)
    for var in keep_vars:
        if section_labels is not None and var in section_labels:
            lines.append(f"\\multicolumn{{{n_models + 1}}}{{l}}{{\\textit{{{section_labels[var]}}}}} \\\\")
            lines.append(r"\addlinespace[0.1cm]")
        label_str = var_labels.get(var, var.replace("_", " "))
        row_vals = []
        for i, coefs in enumerate(model_coefs):
            if var not in coefs:
                row_vals.append(r"\textemdash")
            else:
                row_vals.append(f"${fmt_val(coefs[var], decimals_list[i])}$")
        lines.append(f"{label_str} & " + " & ".join(row_vals) + r" \\")
        lines.append(r"\addlinespace[0.1cm]")

    lines.append(r"\addlinespace[0.1cm]")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # Bottom panel
    if fe_rows is not None:
        for fe_label, fe_vals in fe_rows.items():
            lines.append(f"{fe_label} & " + " & ".join(checkmark_or_dash(v) for v in fe_vals) + r" \\")

    obs_row = "Number of observations & " + " & ".join(
        f"${fmt_val(n, 0)}$" for n in n_obs
    ) + r" \\"
    lines.append(obs_row)

    r2_row = f"{r2_label} & " + " & ".join(
        f"${fmt_val(v, decimals_list[i])}$" for i, v in enumerate(r2)
    ) + r" \\"
    lines.append(r2_row)

    lines.append(r"\addlinespace[0.2cm]")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")

    return "\n".join(lines)
