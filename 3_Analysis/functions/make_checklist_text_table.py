import openpyxl
import pandas as pd


def load_checklist_question_text(
    dictionary_path, questionnaire_path, sheet_name="15. SPARK Checklist", dictionary_sheet="Checklist"
):
    """
    Build {item_key: question_text} for every checklist question, e.g.
    {"bronze_q_1": "A full assessment of laboratory equipment is completed..."} -
    item_key matches the "{tier}_q_{n}" column stem used for the survey's
    bronze_q_i_bl/_el (etc.) columns.

    dictionary_path    : helper_survey_dictionary.xlsx - its "Checklist" sheet has one
                          row per question with columns "Category" (bronze/silver/gold),
                          "Question number", and "Row" - the row in questionnaire_path's
                          SPARK Checklist sheet holding that question's text (column A,
                          section-header rows like "Offices & Travel" already excluded)
    questionnaire_path : the questionnaire template file - column A of sheet_name holds
                          the actual question wording
    """
    row_map = pd.read_excel(dictionary_path, sheet_name=dictionary_sheet)

    wb = openpyxl.load_workbook(questionnaire_path, data_only=True)
    ws = wb[sheet_name]

    question_text = {}
    for _, r in row_map.iterrows():
        item_key = f"{str(r['Category']).strip().lower()}_q_{int(r['Question number'])}"
        cell_value = ws.cell(row=int(r["Row"]), column=1).value
        question_text[item_key] = cell_value.strip() if isinstance(cell_value, str) else cell_value

    return question_text


def make_checklist_text_table(
    items,
    question_text,
    item_categories,
    shares,
    ns,
    section_headers=None,
    caption=None,
    label=None,
    question_label="Question",
    category_label="Category",
    share_label="Achievement share (\\%)",
    n_label="N",
    decimals=0,
    col1_width="10.5cm",
    col2_width="1.8cm",
    col3_width="1.5cm",
    col4_width="0.8cm",
    font_size=r"\tiny",
    align="c",
    row_spacing="0.03cm",
    section_spacing="0.1cm",
):
    """
    Create a LaTeX longtable of checklist questions with their full text: for each
    question, its category and the share of labs with "Yes" at baseline out of labs
    with a substantive answer ("Yes"/"No"/"I don't know") at baseline - i.e. N/A and
    unanswered are excluded from the denominator, unlike make_checklist_tables'
    baseline "Yes (%)" column, which is of a fixed sample size.

    A longtable, not a tabular, since with 49 full-text questions this table is too
    long for one page: it breaks across pages, repeating the column header (and, if
    given, the caption) at the top of each page. This means it must NOT be wrapped in
    a \\begin{table}...\\end{table} float or \\scalebox{} in the .tex this is \\input
    into - both require measuring the whole table as a single, unbroken box, which is
    exactly what page-breaking rules out. The document's preamble needs
    \\usepackage{longtable} (not currently loaded, unlike this project's other tables'
    tabular/threeparttable/scalebox setup).

    Without scalebox to shrink an oversized table to fit, the column widths must
    themselves add up to less than the real page \\textwidth (this project's document
    is 12pt article + fullpage, ~1in margins, so \\textwidth is roughly 16.5cm) - the
    defaults here total 10.5+1.8+1.5+0.8=14.6cm, leaving headroom for the ~1.1cm of
    \\tabcolsep spacing LaTeX inserts between the 4 columns. font_size (\\tiny by
    default, wrapped around the whole longtable) buys back some of the room lost by
    no longer being able to scale the table down, at the cost of smaller print -
    \\tiny is LaTeX's smallest standard size command.

    align sets longtable's own optional alignment argument, \\begin{longtable}[align]:
    "c" (default) centers the table on the page, since a longtable narrower than
    \\textwidth otherwise sits flush left by default ("l") unlike a normal tabular,
    which centers under \\centering.

    Top-level tier section headers (e.g. "Bronze Checklist", bolded), each closed
    before the next. Question/Category cells are top-aligned to their first line
    (array's p{} rather than m{} middle-valign) so a 1-line Category/Share cell sits
    level with the first line of a wrapped multi-line question.

    Parameters
    ----------
    items            : list of item keys (e.g. "bronze_q_1") defining row order
    question_text    : dict {item_key: full question text} (see load_checklist_question_text) -
                        LaTeX-escaped here, so pass the raw questionnaire wording
    item_categories  : dict {item_key: category label}, e.g. "General Lab"
    shares           : dict {item_key: share of "Yes" among substantive BL answers,
                        as a percentage 0-100; NaN where there are no substantive answers}
    ns               : dict {item_key: number of labs with a substantive BL answer} -
                        the share column's denominator, shown in its own "N" column
                        since it varies a lot by question (e.g. only labs with fume
                        cupboards answer the fume cupboard question)
    section_headers  : optional dict {header: [item_keys]} - a bolded, full-width
                        header row is inserted above the first such item (in `items`
                        order)
    caption, label   : optional \\caption/\\label text, placed inside the longtable
                        itself (a plain \\caption{} only works inside a float, which a
                        longtable is not) - pass both or neither
    question_label, category_label, share_label, n_label : column headers
    decimals         : decimal places for the share
    col1_width, col2_width, col3_width, col4_width : column widths (question,
                        category, share, N) - must fit the real page width, see above;
                        there's no scalebox safety net here
    font_size        : LaTeX size command wrapped around the whole table (e.g.
                        "\\scriptsize" for a less extreme size), or None for the
                        document's normal size
    align            : longtable's own [l]/[c]/[r] page-alignment argument, or None to
                        omit it (longtable's own default, "l")
    row_spacing      : \\addlinespace gap used for every vertical gap in the table
                        (header, section header, and between rows) - smaller tightens
                        the table vertically, independent of font_size
    section_spacing  : \\addlinespace gap used only where a new tier section starts
                        (e.g. above "Silver Checklist") - together with a \\hline, this
                        separates a section's last question from the next section's
                        header row. Not used before the very first section, which
                        already sits right below the table's own column header.
    """

    def fmt_share(v):
        if v != v:  # NaN
            return ""
        return f"${v:.{decimals}f}$"

    def fmt_n(v):
        return f"${int(v)}$" if v == v else ""  # NaN check

    # Question text comes straight from the questionnaire spreadsheet, so unlike
    # item_categories/section_headers (hand-written with any needed LaTeX escaping
    # already in place, e.g. "Offices \& Travel") it can contain raw special
    # characters - e.g. one question has "(up to 90%)", where an unescaped "%" starts
    # a LaTeX comment and silently swallows the rest of that row, including its "\\"
    # terminator, breaking the table.
    LATEX_SPECIAL = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    def escape_latex(text):
        return "".join(LATEX_SPECIAL.get(ch, ch) for ch in text)

    header_for_item = {}
    if section_headers is not None:
        for header, section_items in section_headers.items():
            for it in section_items:
                header_for_item[it] = header
    emitted_headers = set()

    col_spec = (
        f"@{{}}>{{\\raggedright\\arraybackslash}}p{{{col1_width}}}"
        f">{{\\raggedright\\arraybackslash}}p{{{col2_width}}}"
        f">{{\\centering\\arraybackslash}}p{{{col3_width}}}"
        f">{{\\centering\\arraybackslash}}p{{{col4_width}}}"
    )
    header_row = [
        r"\hline",
        f"\\addlinespace[{row_spacing}]",
        f"{question_label} & {category_label} & {share_label} & {n_label} \\\\",
        r"\hline",
        f"\\addlinespace[{row_spacing}]",
    ]

    lines = []
    if font_size is not None:
        lines.append("{" + font_size)
    align_arg = f"[{align}]" if align is not None else ""
    lines.append(f"\\begin{{longtable}}{align_arg}{{{col_spec}}}")
    if caption is not None:
        cap = f"\\caption{{{caption}}}"
        if label is not None:
            cap += f"\\label{{{label}}}"
        lines.append(cap + r" \\")
    lines += header_row
    lines.append(r"\endfirsthead")
    lines += header_row
    lines.append(r"\endhead")
    lines.append(r"\hline")
    lines.append(r"\endlastfoot")

    for item in items:
        header = header_for_item.get(item)
        if header is not None and header not in emitted_headers:
            if emitted_headers:
                # A later section (e.g. Silver after Bronze) - separate its last
                # question from this header with a rule and some breathing room. The
                # very first section needs neither - it already sits right below the
                # table's own column header.
                lines.append(r"\hline")
                lines.append(f"\\addlinespace[{section_spacing}]")
            lines.append(f"\\multicolumn{{4}}{{@{{}}l}}{{\\textbf{{{header}}}}} \\\\")
            lines.append(f"\\addlinespace[{row_spacing}]")
            emitted_headers.add(header)

        label_str = escape_latex(question_text.get(item, ""))
        category_str = item_categories.get(item, "")
        share_str = fmt_share(shares.get(item, float("nan")))
        n_str = fmt_n(ns.get(item, float("nan")))

        lines.append(f"{label_str} & {category_str} & {share_str} & {n_str} \\\\")
        lines.append(f"\\addlinespace[{row_spacing}]")

    # No trailing \hline here - \endlastfoot above already supplies the table's
    # closing rule on its final page.
    lines.append(r"\end{longtable}")
    if font_size is not None:
        lines.append("}")

    return "\n".join(lines)
