# ============================================================
# make_truncated_histogram()
#
# Disclosure-safe variant of make_histogram() (see
# histogram_cont_var_func.r) for skewed, potentially
# re-identifying continuous variables - e.g. a lab's annual
# energy use, where a handful of labs sit far out in a long
# right tail and a sparsely-populated bin up there could let a
# reader infer roughly which specific lab it is.
#
# Drawn as a true discrete bar chart (one labelled category per
# bin), not a continuous histogram, since the open-ended top bin
# isn't the same width as the others and doesn't pretend to be.
#
# Two protections, both checked against the actual data rather
# than assumed:
#   1. Minimum bin-width rule: every regular bin (below
#      `threshold`) must contain at least `min_bin_count`
#      observations. If `binwidth` is too narrow for that to
#      hold, the function warns rather than silently plotting
#      an unsafe bin.
#   2. Open-ended top bin: all values >= threshold are collapsed
#      into a single bar showing only the aggregate share at or
#      above threshold - never a finer breakdown of the tail. Its
#      own label (e.g. ">=50") and % annotation make clear it's an
#      aggregate; it's otherwise styled identically to the other
#      bars.
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

make_truncated_histogram <- function(
  df,
  variable,
  threshold,
  binwidth,
  group_var = NULL,
  group_labels = NULL,
  min_bin_count = 5,
  label_divisor = 1,
  label_suffix = "",
  x_label = NULL,
  output_file = NULL,
  show_median = FALSE,
  median_digits = 0,
  font_family = "",
  output_dir = ".",
  save = TRUE
) {

  breaks <- seq(0, threshold, by = binwidth)
  n_bins <- length(breaks) - 1

  # Bin labels as compact ranges with the unit once per label (e.g.
  # "0-12.5 MWh", ">=50 MWh"), not once per number. `label_divisor`/
  # `label_suffix` let a caller rescale for readability - e.g. divisor=1000,
  # suffix="k" for a variable in the thousands - but the default (no
  # rescale) is right for a variable already in a small-number unit
  # like MWh.
  fmt_num <- function(v) {
    scaled <- v / label_divisor
    ifelse(scaled == round(scaled), as.character(as.integer(round(scaled))), formatC(scaled, format = "f", digits = 1))
  }
  top_label <- paste0(">", fmt_num(threshold), label_suffix)
  bin_labels <- c(
    paste0(fmt_num(breaks[-length(breaks)]), "-", fmt_num(breaks[-1]), label_suffix),
    top_label
  )

  # ----------------------------------------
  # Minimum bin-width rule: verify every regular bin has at least
  # `min_bin_count` observations, within each group if grouped.
  # Warn (don't silently plot) if not.
  # ----------------------------------------
  min_count_for <- function(x) {
    below <- x[x < threshold]
    counts <- table(cut(below, breaks = breaks, right = FALSE, include.lowest = TRUE))
    if (length(counts) == 0) return(NA_integer_)
    min(counts)
  }

  check_groups <- if (is.null(group_var)) list(df) else split(df, df[[group_var]])
  min_count <- min(vapply(check_groups, function(d) min_count_for(d[[variable]]), numeric(1)), na.rm = TRUE)
  if (min_count < min_bin_count) {
    warning(sprintf(
      "make_truncated_histogram('%s'): smallest bin below threshold has only %d obs (< min_bin_count = %d) - widen `binwidth`.",
      variable, min_count, min_bin_count
    ))
  }

  # ----------------------------------------
  # Output filename
  # ----------------------------------------
  if (is.null(output_file)) {
    output_file <- paste0("hist_", variable, "_truncated.pdf")
  }
  output_path <- file.path(output_dir, output_file)

  # Grouped (two-way comparison) panels use blue/vermillion; ungrouped
  # ("overall") panels use a distinct bluish-green, so colour signals
  # "single distribution" vs "group comparison" at a glance across every
  # panel, not just which specific grouping variable it is - all three
  # colours are from the same colourblind-safe Okabe-Ito palette.
  palette <- c("#0072B2", "#D55E00")  # blue, vermillion
  overall_colour <- "#009E73"  # bluish green

  # ----------------------------------------
  # Build one row per bin (discrete category: regular bins + one
  # open-ended top bin), reporting only the aggregate share for
  # the top bin - never a narrower breakdown of who's in it.
  # ----------------------------------------
  build_bar_data <- function(d, grp = NA) {
    x <- d[[variable]]
    n <- length(x)
    below <- x[x < threshold]
    counts <- as.numeric(table(cut(below, breaks = breaks, right = FALSE, include.lowest = TRUE)))
    pct <- c(counts / n * 100, mean(x >= threshold, na.rm = TRUE) * 100)
    data.frame(
      bin_label = factor(bin_labels, levels = bin_labels),
      pct = pct,
      is_top = c(rep(FALSE, n_bins), TRUE),
      group = grp
    )
  }

  if (is.null(group_var)) {
    bar_data <- build_bar_data(df)
  } else {
    df[[group_var]] <- as.factor(df[[group_var]])
    if (!is.null(group_labels)) {
      df[[group_var]] <- factor(df[[group_var]], levels = names(group_labels), labels = unlist(group_labels))
    }
    bar_data <- do.call(rbind, lapply(levels(df[[group_var]]), function(g) {
      build_bar_data(df[df[[group_var]] == g, ], grp = g)
    }))
    bar_data$group <- factor(bar_data$group, levels = levels(df[[group_var]]))
  }

  # ----------------------------------------
  # Build plot. Grouped panels use side-by-side (dodged) bars -
  # the conventional bar-chart layout for comparing groups -
  # rather than overlapping semi-transparent histograms. The top
  # bin is styled identically to the regular bins; its label and
  # % annotation are what mark it as an aggregate.
  # ----------------------------------------
  if (is.null(group_var)) {
    p <- ggplot(bar_data, aes(x = bin_label, y = pct)) +
      geom_col(width = 0.7, fill = scales::alpha(overall_colour, 0.6),
               colour = overall_colour, linewidth = 0.7)
    dodge <- position_identity()
  } else {
    dodge <- position_dodge2(width = 0.8, preserve = "single")

    # Fold each group's median into its legend label (e.g. "Control
    # (median 8.9)") rather than a vline - see the note below on why a
    # single vline doesn't have a clean position in a dodged bar chart.
    group_levels <- levels(df[[group_var]])
    if (show_median) {
      medians <- df |>
        group_by(.data[[group_var]]) |>
        summarise(med = median(.data[[variable]], na.rm = TRUE), .groups = "drop")
      fill_labels <- setNames(
        paste0(group_levels, " (median ",
               vapply(group_levels, function(g) {
                 format(round(medians$med[medians[[group_var]] == g], median_digits),
                        scientific = FALSE, nsmall = median_digits)
               }, character(1)),
               label_suffix, ")"),
        group_levels
      )
    } else {
      fill_labels <- waiver()
    }

    # Fill and outline are set as separate colour scales (rather than a
    # shared `alpha` aesthetic) so the fill can be muted while the outline
    # stays at full strength - `alpha=` would dim both together. The
    # colour scale's guide is suppressed (fill drives the one legend), so
    # override.aes explicitly forces the legend keys to show the same
    # muted-fill/bold-outline combination as the bars.
    p <- ggplot(bar_data, aes(x = bin_label, y = pct, fill = group, colour = group)) +
      geom_col(width = 0.8, position = dodge, linewidth = 0.7) +
      scale_fill_manual(
        values = scales::alpha(palette, 0.6), name = NULL, labels = fill_labels,
        guide = guide_legend(override.aes = list(colour = palette, linewidth = 0.7))
      ) +
      scale_colour_manual(values = palette, guide = "none")
  }

  # Label every bar with its share, not just the open-ended top one.
  # All text (here and the median label below) is black rather than
  # per-group colour, so it stays legible regardless of bar fill.
  if (is.null(group_var)) {
    p <- p + geom_text(
      data = bar_data, aes(x = bin_label, y = pct, label = paste0(round(pct, 1), "%")),
      inherit.aes = FALSE, vjust = -0.6, size = 4.6, family = font_family, colour = "black"
    )
  } else {
    p <- p + geom_text(
      data = bar_data, aes(x = bin_label, y = pct, group = group, label = paste0(round(pct, 1), "%")),
      position = dodge, vjust = -0.6, size = 4.2, family = font_family, colour = "black"
    )
  }

  # ----------------------------------------
  # Median vline: only drawn for ungrouped panels. In a dodged bar
  # chart there's no single unambiguous x-position for a group's
  # median anymore (each group's bar sits in its own slot within a
  # category), so a vline there doesn't read cleanly - the median is
  # folded into the legend label instead (see above) when grouped.
  # ----------------------------------------
  if (show_median && is.null(group_var)) {
    med <- median(df[[variable]], na.rm = TRUE)
    bin_idx <- if (med >= threshold) n_bins + 1 else {
      idx <- findInterval(med, breaks, rightmost.closed = FALSE)
      min(max(idx, 1), n_bins)
    }
    frac <- if (med >= threshold) 0 else (med - breaks[bin_idx]) / binwidth
    xpos <- bin_idx - 0.5 + frac
    p <- p +
      geom_vline(xintercept = xpos, colour = overall_colour,
                 linetype = "dashed", linewidth = 0.6) +
      annotate("text", x = xpos, y = Inf,
               label = paste0("Median = ", format(round(med, median_digits), scientific = FALSE, nsmall = median_digits), label_suffix),
               colour = "black", hjust = -0.1, vjust = 1.5,
               size = 4.6, family = font_family)
  }

  # ----------------------------------------
  # Theme and labels
  # ----------------------------------------
  p <- p +
    labs(x = x_label, y = "Percent") +
    scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
    theme_minimal(base_family = font_family, base_size = 16) +
    theme(
      legend.position    = if (!is.null(group_var)) "bottom" else "none",
      legend.text        = element_text(size = 15),
      axis.title.x       = if (is.null(x_label)) element_blank() else element_text(size = 17),
      axis.title.y       = element_text(size = 17),
      axis.text.x        = element_text(size = 12.5),
      axis.text.y        = element_text(size = 15),
      axis.line          = element_line(colour = "black", linewidth = 0.4),
      axis.ticks         = element_blank(),
      panel.grid.major.x = element_blank(),
      panel.grid.minor   = element_blank(),
      panel.grid.major.y = element_line(colour = "grey85", linewidth = 0.3)
    )

  # ----------------------------------------
  # Save to PDF
  # ----------------------------------------
  if (save) {
    ggsave(output_path, plot = p, width = 7, height = 4.5, device = "pdf")
  }

  p
}
