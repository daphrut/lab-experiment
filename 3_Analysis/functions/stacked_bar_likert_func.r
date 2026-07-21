# ============================================================
# make_stacked_bar()
#
# A flexible, reusable stacked horizontal bar chart for ggplot2,
# for showing the response composition of a set of related
# categorical items (e.g. checklist questions), one bar per item.
#
# Re-implements, in ggplot2 with the project's Okabe-Ito-style
# conventions, the stacked bar chart used for attitude questions
# in 3_Analysis/3_Descriptives/3_3_attitudes.ipynb.
# ============================================================

library(ggplot2)
library(dplyr)
library(scales)

make_stacked_bar <- function(
  df,
  item_cols,
  item_labels = NULL,
  response_order,
  output_file = NULL,
  colors = NULL,
  x_label = "Share of labs (%)",
  font_family = "",
  output_dir = "."
) {

  # ----------------------------------------
  # Output filename
  # ----------------------------------------
  if (is.null(output_file)) {
    output_file <- "stacked_bar.pdf"
  }
  output_path <- file.path(output_dir, output_file)

  # ----------------------------------------
  # Default colors (sequential, low->high agreement, Okabe-Ito derived)
  # ----------------------------------------
  if (is.null(colors)) {
    n_resp <- length(response_order)
    colors <- colorRampPalette(c("#D55E00", "#F0E442", "#0072B2"))(n_resp)
  }

  # ----------------------------------------
  # Compute % of non-missing responses per item, per category
  # (base R stand-in for tidyr::pivot_longer + complete, to avoid
  # adding a dependency not already used elsewhere in the project)
  # ----------------------------------------
  long_list <- lapply(item_cols, function(col) {
    data.frame(item = col, response = df[[col]], stringsAsFactors = FALSE)
  })
  long_df <- do.call(rbind, long_list) |>
    filter(!is.na(response), response %in% response_order)

  plot_data <- long_df |>
    count(item, response, name = "n") |>
    group_by(item) |>
    mutate(pct = n / sum(n) * 100) |>
    ungroup()

  # Ensure every item x response combination exists (fill missing with 0)
  full_grid <- expand.grid(item = item_cols, response = response_order,
                            stringsAsFactors = FALSE)
  plot_data <- full_grid |>
    left_join(plot_data, by = c("item", "response")) |>
    mutate(pct = ifelse(is.na(pct), 0, pct)) |>
    mutate(response = factor(response, levels = response_order))

  # ----------------------------------------
  # Item labels and ordering (first item at top)
  # ----------------------------------------
  item_labels_use <- if (!is.null(item_labels)) unlist(item_labels)[item_cols] else item_cols
  plot_data$item <- factor(plot_data$item, levels = rev(item_cols), labels = rev(item_labels_use))

  # ----------------------------------------
  # Build plot
  # ----------------------------------------
  p <- ggplot(plot_data, aes(x = item, y = pct, fill = response)) +
    geom_col(position = "stack", colour = "black", linewidth = 0.2, width = 0.7) +
    scale_fill_manual(values = colors, name = NULL, breaks = response_order) +
    coord_flip() +
    labs(x = NULL, y = x_label) +
    scale_y_continuous(labels = comma, limits = c(0, 100), expand = c(0, 0)) +
    theme_minimal(base_family = font_family, base_size = 14) +
    theme(
      legend.position    = "top",
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
  plot_height <- max(4, 0.35 * length(item_cols) + 1.5)
  ggsave(output_path, plot = p, width = 8, height = plot_height, device = "pdf")

  p
}
