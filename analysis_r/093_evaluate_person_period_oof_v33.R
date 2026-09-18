#!/usr/bin/env Rscript

# Evaluate OOF 48 h CIF predictions from the supplementary one-hour model.

suppressPackageStartupMessages({
  library(cmprsk)
  library(data.table)
  library(riskRegression)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1L) {
  stop("Run this file with Rscript so the project root can be resolved.")
}
script_path <- normalizePath(sub("^--file=", "", script_arg))
project_root <- normalizePath(file.path(dirname(script_path), ".."))

run_dir <- file.path(project_root, "project_control/runs/20260827_person_period_model_v33")
input_csv <- file.path(run_dir, "data/092_person_period_oof_predictions.csv")
if (!file.exists(input_csv)) {
  stop("Person-period OOF prediction file is missing: ", input_csv)
}

write_csv <- function(x, path) {
  data.table::fwrite(as.data.table(x), path, na = "")
}

observed_cif_at <- function(time, status, horizon) {
  estimate <- cmprsk::cuminc(ftime = time, fstatus = status, cencode = 0)
  cause_name <- grep("^1( |$)", names(estimate), value = TRUE)[1]
  if (is.na(cause_name)) return(0)
  curve <- estimate[[cause_name]]
  position <- findInterval(horizon, curve$time)
  if (position == 0L) 0 else as.numeric(curve$est[position])
}

oof <- utils::read.csv(input_csv, check.names = FALSE)
required_columns <- c(
  "stay_id", "followup_hours_from_landmark", "fg_status_code",
  "cif48_person_period"
)
missing_columns <- setdiff(required_columns, names(oof))
if (length(missing_columns) > 0L || anyDuplicated(oof$stay_id)) {
  stop("OOF prediction file is missing required columns or has duplicate stays.")
}
risk <- as.numeric(oof$cif48_person_period)
if (any(!is.finite(risk) | risk < 0 | risk > 1)) {
  stop("Person-period OOF CIF is non-finite or outside [0, 1].")
}

score_object <- riskRegression::Score(
  object = list(person_period = risk),
  formula = Hist(time, status) ~ 1,
  data = data.frame(
    time = as.numeric(oof$followup_hours_from_landmark),
    status = as.integer(oof$fg_status_code)
  ),
  cause = 1,
  times = 48,
  metrics = c("auc", "brier"),
  plots = "calibration",
  summary = "risks",
  null.model = TRUE,
  conf.int = FALSE,
  se.fit = FALSE,
  verbose = 0
)

breaks <- unique(stats::quantile(risk, probs = seq(0, 1, by = 0.1)))
if (length(breaks) < 3L) stop("Insufficient risk variation for calibration grouping.")
groups <- cut(risk, breaks = breaks, include.lowest = TRUE, labels = FALSE)
calibration <- rbindlist(lapply(sort(unique(groups)), function(group) {
  rows <- groups == group
  data.frame(
    model = "person_period",
    risk_group = group,
    n = sum(rows),
    mean_predicted_cif = mean(risk[rows]),
    observed_cif = observed_cif_at(
      oof$followup_hours_from_landmark[rows],
      oof$fg_status_code[rows],
      48
    ),
    stringsAsFactors = FALSE
  )
}))

report_dir <- file.path(run_dir, "reports")
write_csv(score_object$AUC$score, file.path(report_dir, "093_person_period_auc_48h.csv"))
write_csv(score_object$Brier$score, file.path(report_dir, "093_person_period_brier_48h.csv"))
write_csv(calibration, file.path(report_dir, "093_person_period_calibration_deciles_48h.csv"))
write_csv(
  score_object$Calibration$plotframe,
  file.path(report_dir, "093_person_period_calibration_plot_data_48h.csv")
)
writeLines(capture.output(sessionInfo()), file.path(report_dir, "093_sessionInfo.txt"))
message("Completed person-period OOF evaluation: ", run_dir)
