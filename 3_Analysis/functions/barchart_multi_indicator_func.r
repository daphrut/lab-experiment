# ============================================================
# make_indicator_barchart()
#
# A flexible, reusable bar chart function for ggplot2, styled to
# match make_barchart() / make_histogram(), for plotting a SET of
# related 0/1 indicator variables side by side (e.g. one bar per
# equipment type showing the share of labs with that equipment),
# rather than one chart per variable.
#
# Produces a single PDF horizontal bar chart with one bar per item
# (the share, in %, of observations equal to `positive_value`),
# optionally split by a grouping variable (e.g. treatment status).
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

make_indicator_barchart <- function(
  df,
  item_cols,
  item_labels = NULL,
  group_var = NULL,
  group_labels = NULL,
  positive_value = 1,
  output_file = NULL,
  x_label = NULL,
  y_label = "Percent",
  show_pct_labels = TRUE,
  font_family = "",
  output_dir = "."
) {

  # ----------------------------------------
  # Output filename
  # ----------------------------------------
  if (is.null(output_file)) {
    output_file <- "bar_indicators.pdf"
  }
  output_path <- file.path(output_dir, output_file)

  # ----------------------------------------
  # Blue/red palette (matches make_histogram / make_barchart)
  # ----------------------------------------
  palette <- c("#0072B2", "#D55E00")  # blue, vermillion (Okabe-Ito)

  # ----------------------------------------
  # Item labels and ordering (reversed so item_cols order reads top-to-bottom
  # after coord_flip())
  # ----------------------------------------
  item_labels_use <- if (!is.null(item_labels)) unlist(item_labels)[item_cols] else item_cols
  item_levels <- rev(item_cols)
  item_labels_use <- rev(item_labels_use)

  # ----------------------------------------
  # Compute % positive per item, per group
  # ----------------------------------------
  if (is.null(group_var)) {

    pct_vals <- sapply(item_cols, function(col) {
      x <- df[[col]]
      x <- x[!is.na(x)]
      if (length(x) == 0) return(NA_real_)
      100 * mean(x == positive_value)
    })
    plot_data <- data.frame(item = item_cols, pct = pct_vals)
    plot_data$item <- factor(plot_data$item, levels = item_levels, labels = item_labels_use)

    p <- ggplot(plot_data, aes(x = item, y = pct)) +
      geom_col(fill = palette[1], colour = palette[1], alpha = 0.8, linewidth = 0.3)

  } else {

    df[[group_var]] <- as.factor(df[[group_var]])
    if (!is.null(group_labels)) {
      df[[group_var]] <- factor(
        df[[group_var]],
        levels = names(group_labels),
        labels = unlist(group_labels)
      )
    }
    group_levels <- levels(df[[group_var]])

    rows <- lapply(group_levels, function(g) {
      sub <- df[df[[group_var]] == g, ]
      pct_vals <- sapply(item_cols, function(col) {
        x <- sub[[col]]
        x <- x[!is.na(x)]
        if (length(x) == 0) return(NA_real_)
        100 * mean(x == positive_value)
      })
      data.frame(item = item_cols, group = g, pct = pct_vals)
    })
    plot_data <- do.call(rbind, rows)

    # Fill any item x group combination with no observations as 0, so
    # position_dodge() always splits the width the same way across items
    # (see make_barchart() for why this matters).
    plot_data$pct[is.na(plot_data$pct)] <- 0

    plot_data$item <- factor(plot_data$item, levels = item_levels, labels = item_labels_use)
    names(plot_data)[names(plot_data) == "group"] <- group_var
    plot_data[[group_var]] <- factor(plot_data[[group_var]], levels = group_levels)

    p <- ggplot(plot_data, aes(x = item, y = pct, fill = .data[[group_var]])) +
      geom_col(aes(colour = .data[[group_var]]),
               position = position_dodge(width = 0.8), width = 0.7,
               alpha = 0.8, linewidth = 0.3) +
      scale_fill_manual(values = palette, name = NULL) +
      scale_colour_manual(values = palette, guide = "none")
  }

  # ----------------------------------------
  # Percent labels beyond bar ends
  # ----------------------------------------
  if (show_pct_labels) {
    if (is.null(group_var)) {
      p <- p + geom_text(aes(label = paste0(round(pct), "%")),
                          hjust = -0.2, size = 4, family = font_family)
    } else {
      p <- p + geom_text(aes(label = paste0(round(pct), "%")),
                          position = position_dodge(width = 0.8),
                          hjust = -0.2, size = 4, family = font_family)
    }
  }

  # ----------------------------------------
  # Theme and labels (horizontal bars via coord_flip)
  # ----------------------------------------
  p <- p +
    coord_flip() +
    labs(
      x = x_label,
      y = y_label
    ) +
    scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.12))) +
    theme_minimal(base_family = font_family, base_size = 14) +
    theme(
      legend.position    = if (!is.null(group_var)) "top" else "none",
      legend.text        = element_text(size = 13),
      axis.title         = element_text(size = 14),
      axis.text          = element_text(size = 12),
      axis.line.x        = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.x       = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.y       = element_blank(),
      axis.ticks.length  = unit(3, "pt"),
      panel.grid.major.y = element_blank(),
      panel.grid.minor   = element_blank(),
      panel.grid.major.x = element_line(colour = "grey85", linewidth = 0.3)
    )

  # ----------------------------------------
  # Save to PDF (scale height to number of items)
  # ----------------------------------------
  plot_height <- max(4, 0.5 * length(item_cols) + 1.5)
  ggsave(output_path, plot = p, width = 7, height = plot_height, device = "pdf")

  p
}
