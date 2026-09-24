#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(survival)
  library(riskRegression)
  library(prodlim)
  library(cmprsk)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("usage: run_mimic_stage5_model.R INPUT_CSV OUTPUT_DIR")
}
input_csv <- args[[1]]
out_dir <- args[[2]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

features <- c(
  "age_years", "ntprobnp_log1p", "lactate_log1p_raw", "bun_log1p_blood_only",
  "creatinine_log1p", "ph_raw", "sodium_raw", "hemoglobin_raw", "wbc_log1p", "mbp_raw"
)

raw <- fread(input_csv, na.strings = c("", "NA", "NaN"))
stopifnot(all(features %in% names(raw)))
for (z in c("t0", "t12", "t60", "target_event_time", "competing_event_time", "observation_end")) {
  raw[[z]] <- as.POSIXct(raw[[z]], format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")
}

make_analysis <- function(d) {
  d <- copy(d)
  d[, `:=`(
    duration_h = fifelse(final_outcome_status == "target_event",
                         as.numeric(difftime(target_event_time, t12, units = "hours")),
                         fifelse(final_outcome_status == "competing_event",
                                 as.numeric(difftime(competing_event_time, t12, units = "hours")),
                                 as.numeric(difftime(observation_end, t12, units = "hours")))),
    status = fifelse(final_outcome_status == "target_event", 1L,
                     fifelse(final_outcome_status == "competing_event", 2L, 0L))
  )]
  bad <- d[is.na(duration_h) | duration_h < 0 | duration_h > 48.0001]
  if (nrow(bad)) stop("Invalid event/censor duration rows: ", nrow(bad))
  d[, duration_h := pmin(duration_h, 48)]
  d
}

median_impute_scale <- function(train, test = NULL) {
  med <- vapply(train[, ..features], function(x) median(x, na.rm = TRUE), numeric(1))
  if (any(!is.finite(med))) stop("A feature has no finite training median")
  mu <- vapply(train[, ..features], function(x) mean(x, na.rm = TRUE), numeric(1))
  sdv <- vapply(train[, ..features], function(x) sd(x, na.rm = TRUE), numeric(1))
  sdv[!is.finite(sdv) | sdv <= 0] <- 1
  transform_one <- function(x) {
    y <- copy(x)
    for (j in seq_along(features)) {
      f <- features[[j]]
      y[[f]][is.na(y[[f]])] <- med[[j]]
      y[[f]] <- (y[[f]] - mu[[j]]) / sdv[[j]]
    }
    y
  }
  list(train = transform_one(train), test = if (is.null(test)) NULL else transform_one(test),
       medians = med, means = mu, sds = sdv)
}

fit_fgr <- function(d) {
  # FGR uses cause 1 for target event; status 2 is competing event.
  riskRegression::FGR(Hist(duration_h, status) ~ age_years + ntprobnp_log1p + lactate_log1p_raw +
                        bun_log1p_blood_only + creatinine_log1p + ph_raw + sodium_raw +
                        hemoglobin_raw + wbc_log1p + mbp_raw,
                      data = d, cause = 1)
}

score_model <- function(model, d, label) {
  sc <- riskRegression::Score(list(fgr = model),
                              formula = Hist(duration_h, status) ~ 1,
                              data = d, cause = 1, times = 48,
                              metrics = c("AUC", "Brier"),
                              summary = "risk", conf.int = FALSE)
  auc <- as.data.table(sc$AUC$score)
  brier <- as.data.table(sc$Brier$score)
  auc[, split := label]; brier[, split := label]
  list(auc = auc, brier = brier)
}

calibration_table <- function(d) {
  # Decile calibration at the prespecified 48-hour horizon. Observed risk is
  # the Aalen-Johansen cumulative incidence with status 2 as competing event.
  br <- quantile(d$pred_risk_48h, probs = seq(0, 1, by = .1), na.rm = TRUE,
                 names = FALSE, type = 8)
  br <- unique(br)
  if (length(br) < 3) stop("Insufficient unique prediction values for calibration")
  d[, calibration_group := cut(pred_risk_48h, breaks = br, include.lowest = TRUE,
                               labels = FALSE, duplicates = "drop")]
  d[, calibration_group := factor(calibration_group)]
  groups <- levels(d$calibration_group)
  fit <- prodlim(Hist(duration_h, status) ~ calibration_group, data = d)
  obs <- predict(fit, times = 48, cause = 1,
                 newdata = data.frame(calibration_group = factor(groups, levels = groups)))
  out <- d[, .(n = .N, target_events = sum(status == 1), competing_events = sum(status == 2),
               mean_predicted_risk = mean(pred_risk_48h)), by = calibration_group]
  out[, calibration_group := as.integer(as.character(calibration_group))]
  obs_dt <- data.table(calibration_group = as.integer(sub(".*=", "", names(obs))),
                       observed_cif_48h = as.numeric(obs))
  out <- merge(out, obs_dt, by = "calibration_group", sort = FALSE)
  setorder(out, calibration_group)
  out
}

fit_one <- function(d, label, boot_B = 200L) {
  x <- median_impute_scale(d)
  fit <- fit_fgr(x$train)
  pred <- as.numeric(predictRisk(fit, newdata = x$train, times = 48))
  pred <- pmin(pmax(pred, 1e-8), 1 - 1e-8)
  d_pred <- copy(x$train); d_pred[, pred_risk_48h := pred]
  fwrite(d_pred[, c("stay_id", "cohort_version", "duration_h", "status", "pred_risk_48h"), with = FALSE],
         file.path(out_dir, paste0("predictions_", label, "_full.csv")))
  fwrite(calibration_table(d_pred), file.path(out_dir, paste0("calibration_deciles_", label, ".csv")))
  prep <- data.table(feature = features, median = x$medians, mean = x$means, sd = x$sds,
                     cohort = label)
  fwrite(prep, file.path(out_dir, paste0("preprocessing_", label, ".csv")))
  sc <- score_model(fit, x$train, "apparent_full")

  # Bootstrap optimism correction: preprocessing is refit inside each bootstrap sample.
  set.seed(20260924)
  boot_rows <- vector("list", boot_B)
  n <- nrow(d)
  for (b in seq_len(boot_B)) {
    ii <- sample.int(n, n, replace = TRUE)
    tr <- d[ii]
    pp <- tryCatch(median_impute_scale(tr, d), error = function(e) NULL)
    if (is.null(pp)) next
    fm <- tryCatch(fit_fgr(pp$train), error = function(e) NULL)
    if (is.null(fm)) next
    s_tr <- tryCatch(score_model(fm, pp$train, "bootstrap_train"), error = function(e) NULL)
    s_te <- tryCatch(score_model(fm, pp$test, "bootstrap_test"), error = function(e) NULL)
    if (is.null(s_tr) || is.null(s_te)) next
    a1 <- s_tr$auc$AUC[1]
    a2 <- s_te$auc$AUC[1]
    b1 <- s_tr$brier$Brier[1]
    b2 <- s_te$brier$Brier[1]
    boot_rows[[b]] <- data.table(iteration = b, auc_train = a1, auc_test = a2,
                                  auc_optimism = a1 - a2, brier_train = b1, brier_test = b2,
                                  brier_optimism = b1 - b2)
  }
  bt <- rbindlist(boot_rows, fill = TRUE)
  fwrite(bt, file.path(out_dir, paste0("bootstrap_", label, ".csv")))
  summary <- data.table(
    cohort = label, n = nrow(d), target_events = sum(d$status == 1),
    competing_events = sum(d$status == 2), admin_censor = sum(d$status == 0),
    apparent_auc_48h = sc$auc$AUC[1],
    apparent_brier_48h = sc$brier$Brier[1],
    bootstrap_reps = nrow(bt),
    optimism_auc = mean(bt$auc_optimism, na.rm = TRUE),
    optimism_brier = mean(bt$brier_optimism, na.rm = TRUE),
    optimism_corrected_auc = sc$auc$AUC[1] - mean(bt$auc_optimism, na.rm = TRUE),
    optimism_corrected_brier = sc$brier$Brier[1] - mean(bt$brier_optimism, na.rm = TRUE)
  )
  list(model = fit, preproc = x, score = sc, summary = summary)
}

all_out <- list()
for (cohort in c("V4_main", "V3_strict_sensitivity")) {
  d <- make_analysis(raw[cohort_version == cohort])
  # V4 is the primary development model; V3 is prespecified sensitivity.
  fit <- fit_one(d, cohort, boot_B = if (cohort == "V4_main") 200L else 100L)
  all_out[[cohort]] <- fit$summary
  coef_tab <- as.data.table(summary(fit$model)$coef, keep.rownames = "term")
  coef_tab[, hazard_ratio := exp(coef)]
  coef_tab[, `:=`(hr_lower_95 = exp(coef - 1.96 * `se(coef)`),
                  hr_upper_95 = exp(coef + 1.96 * `se(coef)`))]
  fwrite(coef_tab, file.path(out_dir, paste0("coefficients_", cohort, ".csv")))
}

fwrite(rbindlist(all_out, fill = TRUE), file.path(out_dir, "model_performance_summary.csv"))
capture.output(sessionInfo(), file = file.path(out_dir, "sessionInfo.txt"))
cat("Completed Stage 5 model run.\n")
