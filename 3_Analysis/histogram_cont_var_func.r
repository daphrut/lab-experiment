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

make_histogram <- function(
  df,
  variable,
  group_var = NULL,
  restriction = NULL,
  output_file = NULL,
  bins = 30,
  group_labels = NULL,
  title = NULL,
  x_label = NULL,
  output_dir = "."
) {

  # ----------------------------------------
  # Apply restriction (e.g. "survey == 'BL'")
  # ----------------------------------------
  if (!is.null(restriction)) {
    df <- df %>% filter(!!rlang::parse_expr(restriction))
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
      geom_histogram(bins = bins, fill = palette[1], alpha = 0.7, colour = "white")

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
      geom_histogram(bins = bins, alpha = 0.5, position = "identity", colour = "white") +
      scale_fill_manual(values = palette)
  }

  # ----------------------------------------
  # Theme and labels
  # ----------------------------------------
  p <- p +
    labs(
      title = title,
      x = x_label,
      y = "Count",
      fill = if (!is.null(group_var)) gsub("_", " ", group_var) else NULL
    ) +
    theme_minimal() +
    theme(
      legend.position = if (!is.null(group_var)) "top" else "none",
      plot.title = element_text(hjust = 0.5)
    )

  # ----------------------------------------
  # Save to PDF
  # ----------------------------------------
  ggsave(output_path, plot = p, width = 6, height = 4, device = "pdf")

  return(p)
}