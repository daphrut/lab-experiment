import statsmodels.api as sm


def make_balance_table(
    df,
    treatment_var,
    var_labels,
    section_headers=None,
    control_val=0,
    treatment_val=1,
    control_label="Control",
    treatment_label="Treatment",
    decimals=3,  # int (applied to all vars), or dict {var_name: decimals}
    default_decimals=3,  # fallback used for vars not in the decimals dict
    col1_width="9cm",
    coln_width="2cm",
    indent=r"\hspace{0.3cm} ",
):
    """
    Create a LaTeX balance table comparing a control and a treatment group
    on a set of baseline variables.

    For each variable in var_labels, reports the control and treatment mean
    (with SD below in parentheses) and the treatment-control difference
    (with significance stars from a robust-SE OLS regression of the
    variable on the treatment dummy).

    Parameters
    ----------
    df              : dataframe containing treatment_var and the variables in var_labels
    treatment_var    : column name for the treatment variable
    var_labels      : dict mapping variable names to LaTeX display labels;
                      keys also define which variables are shown and in what order
    section_headers : optional dict mapping a header string to the list of
                      variable names shown under it, e.g.
                      {"Annual baseline electricity consumption": ["annual_electricity_fc", ...]}
                      A full-width header row is inserted above the first such
                      variable (in var_labels order) and those rows are indented.
    control_val     : value of treatment_var identifying the control group
    treatment_val   : value of treatment_var identifying the treatment group
    control_label   : header label for the control column
    treatment_label : header label for the treatment column
    decimals        : int applied to all variables, or dict {var_name: decimals}
                      for per-variable precision (e.g. 0 for large kWh totals,
                      3 for 0/1 dummies). A variable's control mean, treatment
                      mean, SD, and diff have same d.p.'s.
    default_decimals : fallback d.p. for variables not listed in
                      the decimals dict (ignored when decimals is an int)
    col1_width      : width of the first column (row labels)
    coln_width      : width of the mean/diff columns
    indent          : LaTeX prefix applied to row labels under a section header
    """

    def get_decimals(var):
        if isinstance(decimals, dict):
            return decimals.get(var, default_decimals)
        return decimals

    # ---------------------------
    # Helper: significance stars
    # ---------------------------
    def get_stars(pval):
        if pval < 0.01:   return "***"
        elif pval < 0.05: return "**"
        elif pval < 0.10: return "*"
        else:             return ""

    def fmt_val(val, d):
        # Negative sign hangs left via \llap (zero width); positive values get a
        # leading space in its place, so decimal points stay aligned down the column.
        # "," -> "{,}" since a bare comma in math mode gets extra spacing.
        if val != val:  # NaN
            return ""
        magnitude = f"{{:,.{d}f}}".format(abs(val)).replace(",", "{,}")
        sign = r"\llap{-}" if val < 0 else " "
        return f"{sign}{magnitude}"

    control_mask = df[treatment_var] == control_val
    treat_mask   = df[treatment_var] == treatment_val

    # Invert section_headers into {var: header} so each variable's header
    # (if any) can be looked up while iterating var_labels in order
    header_for_var = {}
    if section_headers is not None:
        for header, section_vars in section_headers.items():
            for v in section_vars:
                header_for_var[v] = header
    emitted_headers = set()

    n_cols = 4  # label column + control, treatment, diff

    lines = []

    # ---------------------------
    # Table header
    # ---------------------------
    col_spec = f"@{{}}L{{{col1_width}}}" + "".join(f"C{{{coln_width}}}" for _ in range(3))
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")
    lines.append(f" & {control_label} & {treatment_label} & \\\\")
    lines.append(r"Variable & (1) & (2) & (2)-(1) \\")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # Variable rows
    # ---------------------------
    for var in var_labels:
        header = header_for_var.get(var)
        if header is not None and header not in emitted_headers:
            lines.append(f"\\multicolumn{{{n_cols}}}{{@{{}}l}}{{{header}}} \\\\")
            lines.append(r"\addlinespace[0.1cm]")
            emitted_headers.add(header)

        label_str = var_labels[var]
        if header is not None:
            label_str = f"{indent}{label_str}"

        d = get_decimals(var)

        c_vals = df.loc[control_mask, var].dropna()
        t_vals = df.loc[treat_mask, var].dropna()

        mean_c, sd_c = c_vals.mean(), c_vals.std()
        mean_t, sd_t = t_vals.mean(), t_vals.std()

        # Difference and stars from a robust-SE OLS of var on the treatment dummy
        sub = df.loc[control_mask | treat_mask, [var, treatment_var]].dropna()
        dummy = (sub[treatment_var] == treatment_val).astype(float)
        y = sub[var].astype(float)
        if dummy.nunique() < 2 or len(sub) < 3:
            diff_str = ""
        elif y.nunique() < 2:
            # Variable is constant across the whole sample (both groups): the true
            # diff is exactly 0, but an OLS/HC1 fit on zero variance would divide
            # floating-point noise by floating-point noise and can spuriously
            # report "significant" stars. Report the (exact) zero diff directly.
            diff_str = f"${fmt_val(0.0, d)}$"
        else:
            X = sm.add_constant(dummy)
            fit = sm.OLS(y, X).fit(cov_type="HC1")
            diff  = fit.params[treatment_var]
            pval  = fit.pvalues[treatment_var]
            stars = get_stars(pval)
            diff_str = f"${fmt_val(diff, d)}\\rlap{{{stars}}}$"

        mean_c_str = f"${fmt_val(mean_c, d)}$" if mean_c == mean_c else ""
        mean_t_str = f"${fmt_val(mean_t, d)}$" if mean_t == mean_t else ""
        sd_c_str   = f"(${fmt_val(sd_c, d)}$)" if sd_c == sd_c else ""
        sd_t_str   = f"(${fmt_val(sd_t, d)}$)" if sd_t == sd_t else ""

        lines.append(f"{label_str} & {mean_c_str} & {mean_t_str} & {diff_str} \\\\")
        lines.append(f" & {sd_c_str} & {sd_t_str} & \\\\")
        lines.append(r"\addlinespace[0.2cm]")

    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    # ---------------------------
    # Observations
    # ---------------------------
    n_c = int(control_mask.sum())
    n_t = int(treat_mask.sum())
    n_c_str = f"{n_c:,}".replace(",", "{,}")
    n_t_str = f"{n_t:,}".replace(",", "{,}")
    lines.append(f"Number of observations & $ {n_c_str}$ & $ {n_t_str}$ & \\\\")

    lines.append(r"\hline")
    lines.append(r"\end{tabular}")

    return "\n".join(lines)
