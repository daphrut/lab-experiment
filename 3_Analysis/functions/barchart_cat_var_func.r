# ============================================================
# make_barchart()
#
# A flexible, reusable bar chart function for ggplot2, styled
# to match make_histogram() (histogram_cont_var_func.r), for use
# with binary/categorical variables (indicators, waste bands, etc.)
# rather than continuous ones.
#
# Produces a single PDF bar chart of the share (%) of observations
# in each category of a variable, optionally split by a grouping
# variable (e.g. treatment status).
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

make_barchart <- function(
  df,
  variable,
  group_var = NULL,
  restriction = NULL,
  output_file = NULL,
  category_order = NULL,
  category_labels = NULL,
  group_labels = NULL,
  show_pct_labels = TRUE,
  font_family = "",
  output_dir = ".",
  # Style overrides - all default to this function's original look, so
  # existing calls (e.g. spark_awareness in 3_10_hist_el_vars.rmd) are
  # unaffected. Pass these to match a different chart's style instead, e.g.
  # make_truncated_histogram's ungrouped ("overall") panels: bar_colour =
  # "#009E73", alpha = 0.6, outline_alpha = 1, linewidth = 0.7, base_size =
  # 16, label_size = 4.6, label_vjust = -0.6, show_ticks = FALSE,
  # axis_text_x_size = 12.5, axis_text_y_size = 15, axis_title_y_size = 17,
  # y_expand = 0.15, width = 7, height = 4.5.
  bar_colour = NULL,          # NULL -> palette[1] (ungrouped only)
  alpha = 0.8,                # fill opacity
  outline_alpha = alpha,      # outline opacity - defaults to matching alpha
                               # (the original single geom_col(alpha=) look);
                               # pass 1 for a muted fill / full-strength
                               # outline, as in make_truncated_histogram
  linewidth = 0.3,
  base_size = 14,
  label_size = 4,
  label_vjust = -0.4,
  show_ticks = TRUE,
  axis_text_x_size = 12,
  axis_text_y_size = 12,
  axis_title_y_size = 14,
  y_expand = 0.12,
  width = 6,
  height = 4
) {

  # ----------------------------------------
  # Apply restriction (e.g. "survey == 'BL'")
  # ----------------------------------------
  if (!is.null(restriction)) {
    df <- df |> filter(!!rlang::parse_expr(restriction))
  }

  # ----------------------------------------
  # Output filename
  # ----------------------------------------
  if (is.null(output_file)) {
    output_file <- paste0("bar_", variable, ".pdf")
  }
  output_path <- file.path(output_dir, output_file)

  # ----------------------------------------
  # Blue/red palette (matches make_histogram)
  # ----------------------------------------
  palette <- c("#0072B2", "#D55E00")  # blue, vermillion (Okabe-Ito)

  # ----------------------------------------
  # Restrict/order categories
  # ----------------------------------------
  df <- df |> filter(!is.na(.data[[variable]]))
  if (!is.null(category_order)) {
    df <- df |> filter(.data[[variable]] %in% category_order)
    levels_use <- category_order
  } else {
    levels_use <- sort(unique(df[[variable]]))
  }
  labels_use <- if (!is.null(category_labels)) unlist(category_labels) else levels_use
  df[[variable]] <- factor(df[[variable]], levels = levels_use, labels = labels_use)

  # ----------------------------------------
  # Compute shares
  # ----------------------------------------
  if (is.null(group_var)) {

    plot_data <- df |>
      count(.data[[variable]], name = "n") |>
      mutate(pct = n / sum(n) * 100)

    # Fill and outline opacity set separately via scales::alpha() rather than
    # geom_col's own `alpha=` (which would force both to match) - defaults
    # keep them equal (this function's original look); pass outline_alpha=1
    # for a muted fill / full-strength outline, as in make_truncated_histogram.
    fill_colour <- if (is.null(bar_colour)) palette[1] else bar_colour
    p <- ggplot(plot_data, aes(x = .data[[variable]], y = pct)) +
      geom_col(fill = scales::alpha(fill_colour, alpha),
               colour = scales::alpha(fill_colour, outline_alpha), linewidth = linewidth)

  } else {

    df[[group_var]] <- as.factor(df[[group_var]])
    if (!is.null(group_labels)) {
      df[[group_var]] <- factor(
        df[[group_var]],
        levels = names(group_labels),
        labels = unlist(group_labels)
      )
    }

    plot_data <- df |>
      count(.data[[group_var]], .data[[variable]], name = "n") |>
      group_by(.data[[group_var]]) |>
      mutate(pct = n / sum(n) * 100) |>
      ungroup()

    # Fill in group x category combinations with no observations as 0 rather
    # than leaving them absent: otherwise position_dodge() only splits the
    # dodge width among the bars actually present at that category, so a
    # category where one group has 0 observations renders the other group's
    # bar at full (undodged) width instead of a same-width 0-height gap.
    full_grid <- expand.grid(
      group_col = levels(df[[group_var]]),
      cat_col   = levels(df[[variable]]),
      stringsAsFactors = FALSE
    )
    names(full_grid) <- c(group_var, variable)
    plot_data <- full_grid |>
      left_join(plot_data, by = c(group_var, variable)) |>
      mutate(pct = ifelse(is.na(pct), 0, pct),
             n   = ifelse(is.na(n), 0, n))
    plot_data[[group_var]] <- factor(plot_data[[group_var]], levels = levels(df[[group_var]]))
    plot_data[[variable]] <- factor(plot_data[[variable]], levels = levels(df[[variable]]))

    p <- ggplot(plot_data, aes(x = .data[[variable]], y = pct, fill = .data[[group_var]])) +
      geom_col(aes(colour = .data[[group_var]]),
               position = position_dodge(width = 0.8), width = 0.7,
               alpha = 0.8, linewidth = 0.3) +
      scale_fill_manual(values = palette, name = NULL) +
      scale_colour_manual(values = palette, guide = "none")
  }

  # ----------------------------------------
  # Percent labels above bars
  # ----------------------------------------
  if (show_pct_labels) {
    if (is.null(group_var)) {
      p <- p + geom_text(aes(label = paste0(round(pct), "%")),
                          vjust = label_vjust, size = label_size, family = font_family,
                          colour = "black")
    } else {
      p <- p + geom_text(aes(label = paste0(round(pct), "%")),
                          position = position_dodge(width = 0.8),
                          vjust = -0.4, size = 4, family = font_family)
    }
  }

  # ----------------------------------------
  # Theme and labels (no x-axis title or ticks; category names on the axis
  # text are enough to identify each bar)
  # ----------------------------------------
  # Either fully removed (matches make_truncated_histogram, show_ticks =
  # FALSE) or the original visible y-axis ticks (show_ticks = TRUE, default).
  ticks_theme <- if (show_ticks) {
    theme(
      axis.ticks.x      = element_blank(),
      axis.ticks.y      = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.length = unit(3, "pt")
    )
  } else {
    theme(axis.ticks = element_blank())
  }

  p <- p +
    labs(
      x = NULL,
      y = "Percent"
    ) +
    scale_y_continuous(labels = comma, expand = expansion(mult = c(0, y_expand))) +
    theme_minimal(base_family = font_family, base_size = base_size) +
    theme(
      legend.position    = if (!is.null(group_var)) "bottom" else "none",
      legend.text        = element_text(size = 13),
      axis.title.x       = element_blank(),
      axis.title.y       = element_text(size = axis_title_y_size),
      axis.text.x        = element_text(size = axis_text_x_size),
      axis.text.y        = element_text(size = axis_text_y_size),
      axis.line          = element_line(colour = "black", linewidth = 0.4),
      panel.grid.major.x = element_blank(),
      panel.grid.minor   = element_blank(),
      panel.grid.major.y = element_line(colour = "grey85", linewidth = 0.3)
    ) +
    ticks_theme

  # ----------------------------------------
  # Save to PDF
  # ----------------------------------------
  ggsave(output_path, plot = p, width = width, height = height, device = "pdf")

  p
}
