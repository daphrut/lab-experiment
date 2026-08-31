# ============================================================
# make_energy_share_bar()
#
# 100% stacked horizontal bar chart showing each equipment type's
# share of total energy use, one bar for "Overall" plus one bar
# per level of an optional grouping variable (e.g. faculty).
#
# Each bar's shares are the ratio of averages - mean energy use
# of that equipment type across labs (in the relevant group),
# divided by the sum of all types' means for that same group -
# not an average of each lab's own share. This matches "the
# average energy use of each equipment type" as a share of the
# average total, and is the same quantity whichever group a bar
# represents.
#
# Segments are ordered largest-to-smallest by the "Overall" bar
# and that order is kept fixed across every bar, so the same
# equipment type lines up in the same stacking position in every
# bar for direct comparison, and the legend reads in the same
# largest-to-smallest order.
#
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

make_energy_share_bar <- function(
  df,
  energy_cols,
  bar_var = NULL,
  bar_labels = NULL,
  legend_ncol = 4,
  label_min_pct = 5, # minimum segment share (%) for a label
  output_file = NULL,
  x_label = "Share of total energy use (%)",
  font_family = "",
  output_dir = "."
) {

  # ----------------------------------------
  # Output filename
  # ----------------------------------------
  if (is.null(output_file)) {
    output_file <- "energy_share_bar.pdf"
  }
  output_path <- file.path(output_dir, output_file)

  # ----------------------------------------
  # Share for one subset of rows: mean of each energy column,
  # each as a % of the sum of all those means. `energy_cols` is a
  # named vector, names(energy_cols) = column names in df,
  # energy_cols[[name]] = its display label - so this iterates the
  # names to look up each column, and keeps the result named by
  # column name (not by label) for use as a join key below.
  # ----------------------------------------
  compute_shares <- function(d) {
    means <- vapply(names(energy_cols), function(col) mean(d[[col]], na.rm = TRUE), numeric(1))
    names(means) <- names(energy_cols)
    means / sum(means) * 100
  }

  overall_share <- compute_shares(df)
  equip_order <- names(sort(overall_share, decreasing = TRUE))

  rows <- list(data.frame(
    bar = "Overall", equipment = names(overall_share),
    pct = as.numeric(overall_share), stringsAsFactors = FALSE
  ))

  bar_levels <- "Overall"
  if (!is.null(bar_var)) {
    df[[bar_var]] <- as.factor(df[[bar_var]])
    if (!is.null(bar_labels)) {
      df[[bar_var]] <- factor(df[[bar_var]], levels = names(bar_labels), labels = unlist(bar_labels))
    }
    group_levels <- levels(df[[bar_var]])
    bar_levels <- c(bar_levels, group_levels)
    for (g in group_levels) {
      share_g <- compute_shares(df[df[[bar_var]] == g, ])
      rows[[length(rows) + 1]] <- data.frame(
        bar = g, equipment = names(share_g), pct = as.numeric(share_g), stringsAsFactors = FALSE
      )
    }
  }

  plot_data <- do.call(rbind, rows)
  # Reversed so "Overall" plots at the top after coord_flip()
  plot_data$bar <- factor(plot_data$bar, levels = rev(bar_levels))
  plot_data$equipment <- factor(plot_data$equipment, levels = equip_order,
                                 labels = unname(energy_cols[equip_order]))

  # ----------------------------------------
  # Colours: a vivid qualitative palette (base R's built-in "Dark 3",
  # no extra dependency), prioritizing clear between-segment contrast
  # over a perceptual ordering - the largest-to-smallest ranking is
  # already conveyed by segment size and legend order.
  # ----------------------------------------
  n_equip <- length(equip_order)
  equip_labels_ordered <- unname(energy_cols[equip_order])
  equip_colors <- setNames(grDevices::hcl.colors(n_equip, palette = "Dark 3"), equip_labels_ordered)

  # ----------------------------------------
  # Build plot
  # ----------------------------------------
  # Only label segments with room for a legible number - a share below
  # `label_min_pct` renders as a sliver a few pixels wide, and a "2.1%"
  # label on it would overflow into neighbouring segments rather than
  # sitting inside its own. The unlabelled small segments are still
  # identified in the legend.
  plot_data$label <- ifelse(plot_data$pct >= label_min_pct,
                             sprintf("%.1f%%", plot_data$pct), "")

  p <- ggplot(plot_data, aes(x = bar, y = pct, fill = equipment)) +
    geom_col(position = position_stack(reverse = TRUE), colour = "black",
             linewidth = 0.2, width = 0.6) +
    geom_text(aes(label = label), position = position_stack(reverse = TRUE, vjust = 0.5),
              colour = "black", size = 3.6, family = font_family) +
    scale_fill_manual(values = equip_colors, name = NULL, breaks = equip_labels_ordered) +
    coord_flip() +
    labs(x = NULL, y = x_label) +
    # oob = squish clamps (rather than drops) cumulative stack values that
    # float-point drift pushes fractionally past 100 - see stacked_bar_likert_func.r
    scale_y_continuous(labels = comma, limits = c(0, 100),
                        expand = expansion(mult = c(0, 0.04)),
                        oob = scales::squish) +
    theme_minimal(base_family = font_family, base_size = 14) +
    theme(
      legend.position       = "bottom",
      legend.justification  = "center",
      legend.box.just       = "center",
      legend.text           = element_text(size = 10),
      axis.title            = element_text(size = 14),
      axis.text             = element_text(size = 13),
      axis.line.x           = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.x          = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.y          = element_blank(),
      axis.ticks.length     = unit(3, "pt"),
      panel.grid.major.y    = element_blank(),
      panel.grid.minor      = element_blank(),
      panel.grid.major.x    = element_line(colour = "grey85", linewidth = 0.3)
    ) +
    guides(fill = guide_legend(ncol = legend_ncol, byrow = TRUE))

  # ----------------------------------------
  # Save to PDF (scale height to number of bars, plus room for the
  # multi-row legend of equipment types)
  # ----------------------------------------
  n_legend_rows <- ceiling(n_equip / legend_ncol)
  plot_height <- max(4.5, 0.9 * length(bar_levels) + 1.3 + 0.4 * n_legend_rows)
  ggsave(output_path, plot = p, width = 10, height = plot_height, device = "pdf")

  p
}
