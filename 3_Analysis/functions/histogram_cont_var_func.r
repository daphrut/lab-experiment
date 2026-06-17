# ============================================================
# make_histogram()
#
# A flexible, reusable histogram function for ggplot2,
# styled for use in applied micro papers.
#
# Produces a single PDF histogram of a continuous variable,
# optionally split by a grouping variable (e.g. treatment status,
# faculty).
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

# Drops zero-count bins before they reach the geom, preventing a coloured
# outline being drawn at y = 0 for empty bins.
# Source: https://stackoverflow.com/a/57140371 (Z.Lin, CC BY-SA 4.0)
StatBin2 <- ggproto( # nolint: object_usage_linter.
  "StatBin2",
  StatBin,
  compute_group = function(data, scales, binwidth = NULL, bins = NULL,
                           center = NULL, boundary = NULL,
                           closed = c("right", "left"), pad = FALSE,
                           breaks = NULL, origin = NULL, right = NULL,
                           drop = NULL, width = NULL) {
    if (!is.null(breaks)) {
      if (!scales$x$is_discrete()) breaks <- scales$x$transform(breaks)
      bins <- ggplot2:::bin_breaks(breaks, closed) # nolint: undesirable_operator_linter.
    } else if (!is.null(binwidth)) {
      if (is.function(binwidth)) binwidth <- binwidth(data$x)
      bins <- ggplot2:::bin_breaks_width( # nolint: undesirable_operator_linter.
        scales$x$dimension(), binwidth,
        center = center, boundary = boundary, closed = closed
      )
    } else {
      bins <- ggplot2:::bin_breaks_bins( # nolint: undesirable_operator_linter.
        scales$x$dimension(), bins,
        center = center, boundary = boundary, closed = closed
      )
    }
    res <- ggplot2:::bin_vector(data$x, bins, weight = data$weight, pad = pad) # nolint: undesirable_operator_linter.
    res[res$count > 0, ]
  }
)

make_histogram <- function(
  df,
  variable,
  group_var = NULL,
  restriction = NULL,
  output_file = NULL,
  bins = 30,
  binwidth = NULL,
  boundary = NULL,
  group_labels = NULL,
  show_median = FALSE,
  x_label = NULL,
  x_limits = NULL,
  x_breaks = NULL,
  median_digits = 0,
  font_family = "",
  output_dir = "."
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
    output_file <- paste0("hist_", variable, ".pdf")
  }
  output_path <- file.path(output_dir, output_file)

  # ----------------------------------------
  # Default x-axis label
  # ----------------------------------------
  if (is.null(x_label)) {
    x_label <- gsub("_", " ", variable)
  }

  # ----------------------------------------
  # Blue/red palette
  # ----------------------------------------
  palette <- c("#0072B2", "#D55E00")  # blue, vermillion (Okabe-Ito)

  # ----------------------------------------
  # Build plot
  # ----------------------------------------
  if (is.null(group_var)) {

    # Single histogram, no grouping
    p <- ggplot(df, aes(x = .data[[variable]])) +
      geom_histogram(
        aes(y = after_stat(count / ave(count, group, FUN = sum) * 100)), # nolint: object_usage_linter.
        stat = StatBin2,
        bins = bins, binwidth = binwidth, boundary = boundary,
        fill = palette[1], alpha = 0.8,
        colour = palette[1], linewidth = 0.3
      )

  } else {

    # Grouped, overlapping semi-transparent histograms
    df[[group_var]] <- as.factor(df[[group_var]])

    # Apply custom group labels if provided
    if (!is.null(group_labels)) {
      df[[group_var]] <- factor(
        df[[group_var]],
        levels = names(group_labels),
        labels = unlist(group_labels)
      )
    }

    p <- ggplot(df, aes(x = .data[[variable]], fill = .data[[group_var]])) +
      geom_histogram(
        aes(y = after_stat(count / ave(count, group, FUN = sum) * 100), # nolint: object_usage_linter.
            colour = .data[[group_var]]),
        stat = StatBin2,
        bins = bins, binwidth = binwidth, boundary = boundary,
        alpha = 0.5, position = "identity", linewidth = 0.3
      ) +
      scale_fill_manual(values = palette, name = NULL) +
      scale_colour_manual(values = palette, guide = "none")
  }

  # ----------------------------------------
  # Median lines
  # ----------------------------------------
  if (show_median) {
    if (is.null(group_var)) {
      med <- median(df[[variable]], na.rm = TRUE)
      p <- p +
        geom_vline(xintercept = med, colour = palette[1],
                   linetype = "dashed", linewidth = 0.6) +
        annotate("text", x = med, y = Inf,
                 label = paste0("Median = ", format(round(med, median_digits), scientific = FALSE, nsmall = median_digits)),
                 colour = palette[1], hjust = -0.1, vjust = 1.5,
                 size = 3, family = font_family)
    } else {
      medians <- df |>
        group_by(.data[[group_var]]) |>
        summarise(
          med = median(.data[[variable]], na.rm = TRUE),
          .groups = "drop"
        )
      group_levels <- levels(df[[group_var]])
      for (i in seq_along(group_levels)) {
        med_val <- medians$med[medians[[group_var]] == group_levels[i]]
        p <- p +
          geom_vline(xintercept = med_val, colour = palette[i],
                     linetype = "dashed", linewidth = 0.6) +
          annotate("text", x = med_val, y = Inf,
                   label = paste0(group_levels[i], " median = ",
                                  format(round(med_val, median_digits), scientific = FALSE, nsmall = median_digits)),
                   colour = palette[i], hjust = -0.1,
                   vjust = 1.5 + (i - 1) * 1.8,
                   size = 3, family = font_family)
      }
    }
  }

  # ----------------------------------------
  # Theme and labels
  # ----------------------------------------
  p <- p +
    labs(
      x = x_label,
      y = "Percent"
    ) +
    scale_x_continuous(labels = comma, breaks = x_breaks) +
    theme_minimal(base_family = font_family) +
    theme(
      legend.position    = if (!is.null(group_var)) "top" else "none",
      axis.line          = element_line(colour = "black", linewidth = 0.4),
      axis.ticks         = element_line(colour = "black", linewidth = 0.4),
      axis.ticks.length  = unit(3, "pt"),
      panel.grid.major.x = element_blank(),
      panel.grid.minor   = element_blank(),
      panel.grid.major.y = element_line(colour = "grey85", linewidth = 0.3)
    )

  if (!is.null(x_limits)) {
    p <- p + coord_cartesian(xlim = x_limits)
  }

  # ----------------------------------------
  # Save to PDF
  # ----------------------------------------
  ggsave(output_path, plot = p, width = 6, height = 4, device = "pdf")

  p
}