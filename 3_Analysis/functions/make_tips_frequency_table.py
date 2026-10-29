import re


def build_tip_frequency_data(
    df, tip_col="tip", equipment_col="equipment", labgroupid_col="labgroupid", reference_df=None
):
    """
    From a tips dataframe (one row per labgroupid x tip x type - i.e. tips_cleaned.csv),
    collapse the lab-specific figures embedded in the tip text (e.g. "save 155.89 kWh
    per year") into a canonical tip template, then count the number of distinct
    labgroupids shown each (tip template, equipment) combination - so a lab shown the
    same tip for both "type 1" and "type 2" of an equipment item is counted once, not
    twice.

    Rows with equipment_col missing (the "There are no tips to present at this time."
    placeholder) are excluded from the tip rows and instead summarized as counts of
    distinct labgroupids with any tip displayed vs. no tips displayed.

    Numbers embedded in a tip template are not all lab-specific: many are fixed policy
    assumptions built into the calculator (e.g. the ULT tip's target is always "-70
    degrees", the fridge door-opening tip always says "8 per day") and only the final
    savings figure genuinely varies by lab. So masking is done in two passes: first
    every number is masked to identify which rows share the same template, then within
    each template group, a slot is only masked in the *display* label if its value
    actually varies across that template's occurrences - a slot that's constant across
    every lab keeps its real value.

    Constancy is judged from reference_df (defaults to df itself), not df - if df is
    already a subset (e.g. treated labs only) a rare template can have just one
    occurrence there, which would look "constant" purely for lack of evidence and end
    up displaying that one lab's actual figure. Pass the full, unrestricted tips
    dataset as reference_df so a slot's fixed-vs-varies status reflects the calculator
    tool itself rather than whichever labs happen to be in the reported sample. Even
    within reference_df, a template seen only once is never treated as constant.

    Returns (freq_df, any_tips_count, no_tips_count) where freq_df has columns "tip",
    "equipment", "n_labs", sorted by n_labs descending.
    """

    NUMBER_RE = re.compile(r"[\d,]+\.?\d*|NA")

    # Known typos in the calculator's source tip text, fixed for display only -
    # the underlying tips_cleaned.csv is left untouched.
    known_typos = {
        "prpgram": "program",
        "Celcius": "Celsius",
    }

    def clean_up(text):
        text = text.rstrip(". ").strip()
        for typo, fix in known_typos.items():
            text = text.replace(typo, fix)
        # Capitalize the first letter only (not .capitalize(), which would
        # lowercase e.g. "ULT") - one source template starts lowercase ("warming...").
        return text[:1].upper() + text[1:]

    def full_mask(tip):
        return clean_up(NUMBER_RE.sub("X", tip))

    reference = df if reference_df is None else reference_df
    ref_rows = reference[reference[equipment_col].notna()].copy()
    ref_rows["template"] = ref_rows[tip_col].apply(full_mask)
    ref_rows["numbers"] = ref_rows[tip_col].apply(lambda t: NUMBER_RE.findall(t))

    # Per template, only mask the slots that actually vary across its occurrences -
    # a fixed policy constant (e.g. "-70 degrees") is shown as-is instead of "X".
    # A template seen only once in the reference gives no evidence either way, so
    # every slot is masked rather than risk showing that one lab's real figure.
    display_label = {}
    for template, grp in ref_rows.groupby("template"):
        number_lists = grp["numbers"].tolist()
        n_slots = len(number_lists[0])
        if len(grp) < 2:
            varies = [True] * n_slots
        else:
            varies = [len({nums[i] for nums in number_lists}) > 1 for i in range(n_slots)]

        slot = iter(range(n_slots))

        def sub_fn(m):
            i = next(slot)
            return "X" if varies[i] else m.group(0)

        display_label[template] = clean_up(NUMBER_RE.sub(sub_fn, grp[tip_col].iloc[0]))

    has_equipment = df[equipment_col].notna()

    tip_rows = df[has_equipment].copy()
    tip_rows["template"] = tip_rows[tip_col].apply(full_mask)
    # Fallback to the fully-masked template itself for any template present in df but
    # missing from reference_df (only possible if reference_df doesn't cover df) -
    # errs toward more masking, never less.
    tip_rows["tip_label"] = tip_rows["template"].map(display_label).fillna(tip_rows["template"])

    freq_df = (
        tip_rows.groupby(["tip_label", equipment_col])[labgroupid_col]
        .nunique()
        .reset_index(name="n_labs")
        .rename(columns={"tip_label": "tip", equipment_col: "equipment"})
        .sort_values("n_labs", ascending=False)
        .reset_index(drop=True)
    )

    any_tips_count = df.loc[has_equipment, labgroupid_col].nunique()
    no_tips_count = df.loc[~has_equipment, labgroupid_col].nunique()

    return freq_df, any_tips_count, no_tips_count


def compute_equipment_ownership(panel, labgroupids, equipment_map, survey="BL"):
    """
    For each equipment type (keyed by the tips dataset's equipment display label, e.g.
    "CO2 incubator"), the number of distinct labs in labgroupids that own at least one
    unit of that equipment type at survey - the denominator for the tip frequency
    table's "share of labs with that equipment" column (e.g. a freezer tip shown to 23
    labs, out of the labs that actually have a freezer, not out of every lab).

    panel         : panel_processed_5.csv-shaped DataFrame with "labgroupid", "survey",
                     "equipment", "number" (unit count for that lab/survey/equipment row)
    labgroupids   : the sample of labgroupids the table is being built for
    equipment_map : dict mapping the tips dataset's equipment display label to the
                     panel's equipment code, e.g. {"CO2 incubator": "incubator", ...}
    survey        : restrict ownership to this survey (BL by default, matching the
                     equipment energy table's convention)

    Returns dict {display_label: n_labs_owning}.
    """
    p = panel[(panel["survey"] == survey) & (panel["labgroupid"].isin(labgroupids))]
    unit_counts = p.groupby(["labgroupid", "equipment"])["number"].sum()
    owning_labs = unit_counts[unit_counts > 0].reset_index()
    n_owners = owning_labs.groupby("equipment")["labgroupid"].nunique()
    return {label: int(n_owners.get(code, 0)) for label, code in equipment_map.items()}


def make_tips_frequency_table(
    freq_df,
    any_tips_count,
    no_tips_count,
    any_tips_label="Any tip displayed",
    no_tips_label="No tips displayed",
    tip_label="Tip",
    equipment_label="Equipment",
    share_label="Share of using groups (\\%)",
    suppress_at=5,
    bound_step=5,
    col1_width="18cm",
    col2_width="4.5cm",
    col3_width="3.2cm",
):
    """
    Create a LaTeX table of tip frequency: for each (tip, equipment) combination, the
    share of labs shown that tip (counted once per lab even if shown for multiple
    appliance "types" of that equipment), out of only the labs that actually own that
    equipment type (not of every lab in the sample). Counts themselves are not shown.
    Closed with "Any tip displayed" and "No tips displayed" summary rows giving the
    share of all labs in the sample whose calculator did and didn't show any tips.

    Same visual conventions as make_balance_table/make_equipment_energy_table.

    Parameters
    ----------
    freq_df         : DataFrame with columns "tip", "equipment", "n_labs",
                       "n_equipment_labs" - one row per combination, in the order to
                       display (see build_tip_frequency_data and
                       compute_equipment_ownership for how to build these columns)
    any_tips_count  : number of distinct labgroupids with at least one tip displayed
    no_tips_count   : number of distinct labgroupids with no tips displayed
    tip_label, equipment_label, share_label : column headers
    suppress_at     : small-cell disclosure control - a share whose n_labs count is at
                       or below this threshold is bottom-coded as "< X" (an exact
                       percentage would let the count be backed out from a known
                       denominator), and a share whose complement (owners not shown the
                       tip) is at or below it is top-coded as "> Y". X / Y are the
                       tightest multiples of bound_step whose implied count range still
                       includes counts above suppress_at - e.g. 5 of 31 owners -> "< 20"
                       (20% of 31 = 6.2), since "< 15" would pin the count below 5 - so
                       the bound reveals no more than a plain suppression would.
                       Set to None to disable and always show exact values.
    bound_step      : rounding step (percentage points) for the bounds above
    col1_width, col2_width, col3_width : column widths (tip, equipment, share)
    """

    # The < / > of a bounded share hangs left via \llap (zero width), so its digits line
    # up with the exact shares. Wrapped in $...$ since \llap's box is in text mode,
    # where a bare < / > would print as an inverted punctuation mark.
    def fmt_share(n, d):
        if suppress_at is not None and n <= suppress_at:
            # Smallest multiple of bound_step with bound * d / 100 > suppress_at
            bound = bound_step
            while bound * d / 100 <= suppress_at:
                bound += bound_step
            return f"$\\llap{{$<$}}{bound}$"
        if suppress_at is not None and 0 < d - n <= suppress_at:
            # Largest multiple of bound_step with (100 - bound) * d / 100 > suppress_at
            bound = 100 - bound_step
            while (100 - bound) * d / 100 <= suppress_at:
                bound -= bound_step
            return f"$\\llap{{$>$}}{bound}$"
        return f"${100 * n / d:.1f}$"

    n_sample = int(any_tips_count) + int(no_tips_count)

    # Top-align each cell to its first line (via array's p{} rather than the L/C
    # macros' m{} middle-valign) so a 1-line equipment/count cell sits level with the
    # first line of a multi-line tip cell instead of centering against its full height.
    lines = []
    col_spec = (
        f"@{{}}>{{\\raggedright\\arraybackslash}}p{{{col1_width}}}"
        f">{{\\raggedright\\arraybackslash}}p{{{col2_width}}}"
        f">{{\\centering\\arraybackslash}}p{{{col3_width}}}"
    )
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")
    lines.append(f"{tip_label} & {equipment_label} & {share_label} \\\\")
    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.2cm]")

    for _, row in freq_df.iterrows():
        n_labs = int(row["n_labs"])
        n_equipment_labs = int(row["n_equipment_labs"])
        lines.append(
            f"{row['tip']} & {row['equipment']} & {fmt_share(n_labs, n_equipment_labs)} \\\\"
        )
        lines.append(r"\addlinespace[0.15cm]")

    lines.append(r"\hline")
    lines.append(r"\addlinespace[0.15cm]")
    lines.append(f"{any_tips_label} & & {fmt_share(int(any_tips_count), n_sample)} \\\\")
    lines.append(r"\addlinespace[0.15cm]")
    lines.append(f"{no_tips_label} & & {fmt_share(int(no_tips_count), n_sample)} \\\\")
    lines.append(r"\addlinespace[0.2cm]")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")

    return "\n".join(lines)
