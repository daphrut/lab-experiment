import re

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
    yes_counts,
    substantive_counts,
    energy_labels=None,
    min_count=5,
    top_code=90,
    section_headers=None,
    caption=None,
    label=None,
    note=None,
    question_label="Question",
    category_label="Category",
    energy_label="Energy-relevant",
    share_label="BL Share (\\%)",
    suppressed_str="--",
    decimals=0,
    col1_width="11.4cm",
    col2_width="1.6cm",
    energy_width="1.8cm",
    col3_width="1.5cm",
    note_width="14.5cm",
    font_size=r"\tiny",
    align="c",
    row_spacing="0.03cm",
    section_spacing="0.1cm",
):
    """
    Create a LaTeX longtable of checklist questions with their full text: for each
    question, its category and the share of labs with "Yes" out of labs with a
    substantive answer ("Yes"/"No"/"I don't know") - i.e. N/A and unanswered are
    excluded from the denominator - plus, if energy_labels is given, a column
    marking which actions can move the energy measure. 7_2_checklist_text_table.ipynb uses this for
    baseline only: a BL-vs-EL comparison can't be shown per question without
    disclosing small groups of labs (see disclosure control below).

    Disclosure control: no group of labs smaller than min_count may be identifiable,
    so a share is only shown if both its "Yes" count and its not-"Yes" count are
    either 0 or >= min_count (0 is fine - e.g. 100% "Yes" doesn't single out any
    lab). A share failing this is shown as "$>$top_code" if it is above top_code
    (the failing group is then the small not-"Yes" group, and the bound reveals no
    more than a plain suppression marker would - that some group of 1 to
    min_count-1 labs exists), otherwise as suppressed_str. The number of labs
    behind each share is deliberately not shown, since N x share gives back the
    exact counts. Pass top_code=None to never top-code.

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
    defaults here total 11.4+1.6+1.5=14.5cm, leaving headroom for the \\tabcolsep
    spacing LaTeX inserts between the 3 columns. font_size (\\tiny by default,
    wrapped around the whole longtable) buys back some of the room lost by no longer
    being able to scale the table down, at the cost of smaller print - \\tiny is
    LaTeX's smallest standard size command.

    align sets longtable's own optional alignment argument, \\begin{longtable}[align]:
    "c" (default) centers the table on the page, since a longtable narrower than
    \\textwidth otherwise sits flush left by default ("l") unlike a normal tabular,
    which centers under \\centering.

    Top-level tier section headers (e.g. "Bronze Checklist", bolded), each closed
    before the next. Cells are top-aligned to their first line (array's p{} rather
    than m{} middle-valign) so a 1-line Category/Share cell sits level with the first
    line of a wrapped multi-line question.

    Parameters
    ----------
    items              : list of item keys (e.g. "bronze_q_1") defining row order
    question_text      : dict {item_key: full question text} (see load_checklist_question_text) -
                          LaTeX-escaped here, so pass the raw questionnaire wording
    item_categories    : dict {item_key: category label}, e.g. "General Lab"
    yes_counts         : dict {item_key: number of labs answering "Yes"}
    substantive_counts : dict {item_key: number of labs with a substantive answer}
    energy_labels      : optional dict {item_key: text for the energy-relevance column,
                          e.g. "Fume cupboard"; "" for not relevant} - LaTeX-escaped
                          here. None omits the column (then col1_width can take its
                          energy_width back)
    min_count          : smallest group of labs that may be shown (see above)
    top_code           : suppressed shares above this are shown as "$>$top_code"
                          rather than suppressed_str; None to disable
    section_headers    : optional dict {header: [item_keys]} - a bolded, full-width
                          header row is inserted above the first such item (in `items`
                          order)
    caption, label     : optional \\caption/\\label text, placed inside the longtable
                          itself (a plain \\caption{} only works inside a float, which a
                          longtable is not) - pass both or neither
    note               : optional table note (LaTeX), printed below the closing rule
                          on the table's final page
    question_label, category_label, energy_label, share_label : column headers
    suppressed_str     : what a suppressed share is shown as
    decimals           : decimal places for the shares
    col1_width, col2_width, energy_width, col3_width : column widths (question,
                          category, energy relevance, share) -
                          must fit the real page width, see above; there's no
                          scalebox safety net here
    note_width         : width of the note's paragraph - roughly the column widths' sum
    font_size          : LaTeX size command wrapped around the whole table (e.g.
                          "\\scriptsize" for a less extreme size), or None for the
                          document's normal size
    align              : longtable's own [l]/[c]/[r] page-alignment argument, or None to
                          omit it (longtable's own default, "l")
    row_spacing        : \\addlinespace gap used for every vertical gap in the table
                          (header, section header, and between rows) - smaller tightens
                          the table vertically, independent of font_size
    section_spacing    : \\addlinespace gap used only where a new tier section starts
                          (e.g. above "Silver Checklist") - together with a \\hline, this
                          separates a section's last question from the next section's
                          header row. Not used before the very first section, which
                          already sits right below the table's own column header.
    """

    def is_disclosive(count):
        return 0 < count < min_count

    def fmt_share(item):
        n = substantive_counts.get(item, 0)
        if n == 0:
            return ""
        yes = yes_counts.get(item, 0)
        share = yes / n * 100
        if is_disclosive(yes) or is_disclosive(n - yes):
            if top_code is not None and share > top_code:
                # \llap gives the ">" zero width, so the number itself is centered
                # in line with the column's other numbers. \leavevmode first, since a
                # p{} cell starts in vertical mode, where \llap's box would sit on a
                # line of its own above the number instead of beside it
                return f"\\leavevmode\\llap{{$>$}}${top_code}$"
            return suppressed_str
        return f"${share:.{decimals}f}$"

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
        # Text-mode < and > print as inverted !/? under pdflatex's default encoding
        "<": r"$<$",
        ">": r"$>$",
        "°": r"$^{\circ}$",
        "‐": "-",  # Unicode hyphen, not in pdflatex's default fonts
    }

    # Numbers go in math mode, along with a leading </> and a trailing °C, so e.g.
    # ">50 °C" becomes "$>50\,^{\circ}$C" rather than three separate pieces
    NUMBER = re.compile(r"([<>]\s?)?(\d+(?:\.\d+)?)(\s?°C)?")

    def escape_chars(text):
        return "".join(LATEX_SPECIAL.get(ch, ch) for ch in text)

    def number_to_math(m):
        op = m.group(1).strip() if m.group(1) else ""
        degrees = r"\,^{\circ}$C" if m.group(3) else "$"
        return f"${op}{m.group(2)}{degrees}"

    def escape_latex(text):
        out, pos = [], 0
        for m in NUMBER.finditer(text):
            out.append(escape_chars(text[pos:m.start()]))
            out.append(number_to_math(m))
            pos = m.end()
        out.append(escape_chars(text[pos:]))
        return "".join(out)

    header_for_item = {}
    if section_headers is not None:
        for header, section_items in section_headers.items():
            for it in section_items:
                header_for_item[it] = header
    emitted_headers = set()

    col_spec = (
        f"@{{}}>{{\\raggedright\\arraybackslash}}p{{{col1_width}}}"
        f">{{\\raggedright\\arraybackslash}}p{{{col2_width}}}"
    )
    header_cells = [question_label, category_label]
    if energy_labels is not None:
        col_spec += f">{{\\raggedright\\arraybackslash}}p{{{energy_width}}}"
        header_cells.append(energy_label)
    col_spec += f">{{\\centering\\arraybackslash}}p{{{col3_width}}}"
    header_cells.append(share_label)
    n_cols = len(header_cells)

    header_row = [
        r"\hline",
        f"\\addlinespace[{row_spacing}]",
        " & ".join(header_cells) + r" \\",
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
    if note is not None:
        lines.append(f"\\addlinespace[{row_spacing}]")
        lines.append(f"\\multicolumn{{{n_cols}}}{{@{{}}p{{{note_width}}}}}{{{note}}} \\\\")
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
            lines.append(f"\\multicolumn{{{n_cols}}}{{@{{}}l}}{{\\textbf{{{header}}}}} \\\\")
            lines.append(f"\\addlinespace[{row_spacing}]")
            emitted_headers.add(header)

        label_str = escape_latex(question_text.get(item, ""))
        category_str = item_categories.get(item, "")
        cells = [label_str, category_str]
        if energy_labels is not None:
            cells.append(escape_latex(energy_labels.get(item, "")))
        cells.append(fmt_share(item))

        lines.append(" & ".join(cells) + r" \\")
        lines.append(f"\\addlinespace[{row_spacing}]")

    # No trailing \hline here - \endlastfoot above already supplies the table's
    # closing rule on its final page.
    lines.append(r"\end{longtable}")
    if font_size is not None:
        lines.append("}")

    return "\n".join(lines)
