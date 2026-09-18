def make_equipment_energy_table(
    panels,
    energy_label="Mean Energy (kWh)",
    units_label="Mean Units",
    per_unit_label="Mean Energy per Unit (kWh)",
    energy_decimals=1,
    units_decimals=2,
    col1_width="6.5cm",
    coln_width="3.2cm",
):
    """
    Create a LaTeX table of equipment-type energy composition, one panel per
    group (e.g. Overall, then by faculty): for each equipment type, mean
    energy use, mean unit count, and mean energy per unit, across labs in
    that group, plus a "Total" row aggregating across every equipment type.

    "Mean energy per unit" (both per equipment type and in the Total row) is
    a ratio of averages - the group's mean energy divided by its mean unit
    count, not an average of each lab's own energy/unit ratio - matching the
    convention used for equipment shares elsewhere in this project.

    Same visual conventions as make_regression_table/make_ml_comparison_table.
    No significance stars/SEs - these are descriptive means, not estimates.

    Parameters
    ----------
    panels      : list of dicts, one per panel, each with:
                    "label"       : panel heading, e.g. "Overall"
                    "df"          : DataFrame with columns "label", "mean_energy",
                                     "mean_units", one row per equipment type,
                                     in the order to display
                    "total_energy": group's mean of total energy (all types)
                    "total_units" : group's mean of total unit count (all types)
    energy_label, units_label, per_unit_label : column headers
    energy_decimals, units_decimals : decimal places for each metric
                  (per-unit energy uses energy_decimals too)
    col1_width  : width of the first column (equipment labels)
    coln_width  : width of each of the 3 data columns
    """

    def fmt_val(val, d):
        if val != val:  # NaN
            return r"\textemdash"
        magnitude = f"{{:,.{d}f}}".format(abs(val)).replace(",", "{,}")
        sign = r"\llap{-}" if val < 0 else " "
        return f"${sign}{magnitude}$"

    def data_row(label, energy, units, bold=False):
        per_unit = energy / units if units > 0 else float("nan")
        vals = [fmt_val(energy, energy_decimals), fmt_val(units, units_decimals),
                fmt_val(per_unit, energy_decimals)]
        label_str = f"\\textbf{{{label}}}" if bold else label
        return f"{label_str} & " + " & ".join(vals) + r" \\"

    lines = []

    col_spec = f"@{{}}L{{{col1_width}}}C{{{coln_width}}}C{{{coln_width}}}C{{{coln_width}}}"
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")
    lines.append(f" & {energy_label} & {units_label} & {per_unit_label} \\\\")
    lines.append(r"\hline")

    for i, panel in enumerate(panels):
        lines.append(r"\addlinespace[0.2cm]")
        lines.append(f"\\multicolumn{{4}}{{l}}{{\\textit{{{panel['label']}}}}} \\\\")
        lines.append(r"\addlinespace[0.1cm]")

        for _, row in panel["df"].iterrows():
            lines.append(data_row(row["label"], row["mean_energy"], row["mean_units"]))
            lines.append(r"\addlinespace[0.1cm]")

        lines.append(r"\addlinespace[0.05cm]")
        lines.append(data_row("Total", panel["total_energy"], panel["total_units"], bold=True))

        if i < len(panels) - 1:
            lines.append(r"\addlinespace[0.15cm]")
            lines.append(r"\hline")

    lines.append(r"\addlinespace[0.2cm]")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")

    return "\n".join(lines)
