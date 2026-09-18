#!/usr/bin/env Rscript

# v3.3 primary-model baseline: prespecified Fine-Gray model with external-style
# out-of-fold validation. The predictor list is frozen in the 090 manifest.

suppressPackageStartupMessages({
  library(cmprsk)
  library(data.table)
  library(prodlim)
  library(riskRegression)
  library(survival)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1L) {
  stop("Run this file with Rscript so the project root can be resolved.")
}
script_path <- normalizePath(sub("^--file=", "", script_arg))
project_root <- normalizePath(file.path(dirname(script_path), ".."))

`%||%` <- function(x, y) {
  if (is.null(x)) y else x
}

parse_args <- function(args) {
  out <- list()
  for (arg in args) {
    if (!startsWith(arg, "--")) {
      stop("Unexpected argument: ", arg)
    }
    pair <- strsplit(sub("^--", "", arg), "=", fixed = TRUE)[[1]]
    if (length(pair) != 2L || !nzchar(pair[1]) || !nzchar(pair[2])) {
      stop("Arguments must use --name=value: ", arg)
    }
    out[[pair[1]]] <- pair[2]
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
input_csv <- args$input %||%
  file.path(
    project_root,
    "project_control/runs/20260828_v3_3_compact_features/data/090C_finegray_input_v33.csv"
  )
manifest_csv <- args$manifest %||%
  file.path(
    project_root,
    "project_control/runs/20260828_v3_3_compact_features/reports/090_predictor_manifest.csv"
  )
output_dir <- args$output %||%
  file.path(project_root, "project_control/runs/20260827_finegray_baseline_v33")
folds <- as.integer(args$folds %||% "5")
seed <- as.integer(args$seed %||% "20260827")
horizon_hours <- as.numeric(args$horizon_hours %||% "48")

if (is.na(folds) || folds < 2L) {
  stop("--folds must be an integer >= 2.")
}
if (is.na(seed)) {
  stop("--seed must be an integer.")
}
if (is.na(horizon_hours) || horizon_hours <= 0) {
  stop("--horizon_hours must be > 0.")
}
if (!file.exists(input_csv) || !file.exists(manifest_csv)) {
  stop("Input CSV or predictor manifest is missing.")
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "data"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "reports"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "models"), recursive = TRUE, showWarnings = FALSE)

write_csv <- function(x, path) {
  data.table::fwrite(as.data.table(x), path, na = "")
}

step_cif_at <- function(prediction_matrix, horizon) {
  event_times <- prediction_matrix[, 1]
  position <- findInterval(horizon, event_times)
  if (position == 0L) {
    return(rep(0, ncol(prediction_matrix) - 1L))
  }
  as.numeric(prediction_matrix[position, -1, drop = TRUE])
}

observed_cif_at <- function(time, status, horizon) {
  estimate <- cmprsk::cuminc(ftime = time, fstatus = status, cencode = 0)
  cause_name <- grep("^1( |$)", names(estimate), value = TRUE)[1]
  if (is.na(cause_name)) {
    return(0)
  }
  curve <- estimate[[cause_name]]
  position <- findInterval(horizon, curve$time)
  if (position == 0L) 0 else as.numeric(curve$est[position])
}

make_stratified_folds <- function(status, sepsis, n_folds, seed_value) {
  set.seed(seed_value)
  stratum <- interaction(status, sepsis, drop = TRUE, lex.order = TRUE)
  fold_id <- integer(length(status))
  for (level in levels(stratum)) {
    index <- which(stratum == level)
    fold_id[index] <- sample(rep(seq_len(n_folds), length.out = length(index)))
  }
  fold_id
}

is_binary_training_column <- function(x) {
  observed <- unique(x[!is.na(x)])
  length(observed) > 0L && all(observed %in% c(0, 1))
}

fit_fold_preprocessor <- function(train_data, test_data, predictors, indicator_vars) {
  train_matrix <- matrix(NA_real_, nrow = nrow(train_data), ncol = length(predictors))
  test_matrix <- matrix(NA_real_, nrow = nrow(test_data), ncol = length(predictors))
  colnames(train_matrix) <- predictors
  colnames(test_matrix) <- predictors
  transform_rows <- list()
  indicator_rows <- list()

  for (predictor in predictors) {
    train_values <- as.numeric(train_data[[predictor]])
    test_values <- as.numeric(test_data[[predictor]])
    if (all(is.na(train_values))) {
      stop("Predictor is completely missing in the training fold: ", predictor)
    }

    train_median <- median(train_values, na.rm = TRUE)
    train_missing_fraction <- mean(is.na(train_values))
    binary_column <- is_binary_training_column(train_values)
    train_values[is.na(train_values)] <- train_median
    test_values[is.na(test_values)] <- train_median

    train_center <- if (binary_column) 0 else mean(train_values)
    train_scale <- if (binary_column) 1 else stats::sd(train_values)
    if (!is.finite(train_scale) || train_scale == 0) {
      train_scale <- 1
    }

    train_matrix[, predictor] <- (train_values - train_center) / train_scale
    test_matrix[, predictor] <- (test_values - train_center) / train_scale
    transform_rows[[predictor]] <- data.frame(
      predictor = predictor,
      train_median = train_median,
      train_missing_fraction = train_missing_fraction,
      center = train_center,
      scale = train_scale,
      binary_column = binary_column,
      stringsAsFactors = FALSE
    )
  }

  indicator_vars <- intersect(indicator_vars, predictors)
  if (length(indicator_vars) > 0L) {
    retained_indicator_patterns <- list()
    for (predictor in indicator_vars) {
      indicator_name <- paste0(predictor, "__missing")
      train_indicator <- as.numeric(is.na(train_data[[predictor]]))
      test_indicator <- as.numeric(is.na(test_data[[predictor]]))
      include_indicator <- length(unique(train_indicator)) > 1L &&
        !any(vapply(retained_indicator_patterns, identical, logical(1), train_indicator))
      exclusion_reason <- if (include_indicator) {
        ""
      } else if (length(unique(train_indicator)) <= 1L) {
        "constant_in_training_fold"
      } else {
        "duplicate_missingness_pattern_in_training_fold"
      }
      indicator_rows[[predictor]] <- data.frame(
        predictor = predictor,
        indicator_name = indicator_name,
        included = include_indicator,
        exclusion_reason = exclusion_reason,
        stringsAsFactors = FALSE
      )
      if (!include_indicator) {
        next
      }
      train_matrix <- cbind(
        train_matrix,
        setNames(data.frame(train_indicator), indicator_name)
      )
      test_matrix <- cbind(
        test_matrix,
        setNames(data.frame(test_indicator), indicator_name)
      )
      retained_indicator_patterns[[indicator_name]] <- train_indicator
    }
  }

  list(
    train_matrix = as.matrix(train_matrix),
    test_matrix = as.matrix(test_matrix),
    transformations = rbindlist(transform_rows),
    indicator_info = rbindlist(indicator_rows),
    indicator_vars = indicator_vars
  )
}

run_cv_specification <- function(data, predictors, fold_id, specification, indicator_vars) {
  predictions <- rep(NA_real_, nrow(data))
  coefficient_rows <- list()
  transformation_rows <- list()
  indicator_rows <- list()
  fold_rows <- list()

  for (fold in sort(unique(fold_id))) {
    train_index <- fold_id != fold
    test_index <- fold_id == fold
    preprocessing <- fit_fold_preprocessor(
      train_data = data[train_index, ],
      test_data = data[test_index, ],
      predictors = predictors,
      indicator_vars = indicator_vars
    )

    model_fit <- cmprsk::crr(
      ftime = data$followup_hours_from_landmark[train_index],
      fstatus = data$fg_status_code[train_index],
      cov1 = preprocessing$train_matrix,
      failcode = 1,
      cencode = 0,
      maxiter = 100
    )
    predicted_cif <- predict(
      model_fit,
      cov1 = preprocessing$test_matrix
    )
    predictions[test_index] <- step_cif_at(predicted_cif, horizon_hours)

    coefficient_rows[[as.character(fold)]] <- data.frame(
      specification = specification,
      fold = fold,
      predictor = names(model_fit$coef),
      coefficient = as.numeric(model_fit$coef),
      standard_error = sqrt(diag(model_fit$var)),
      stringsAsFactors = FALSE
    )
    transformations <- preprocessing$transformations
    transformations$specification <- specification
    transformations$fold <- fold
    transformation_rows[[as.character(fold)]] <- transformations
    indicator_info <- preprocessing$indicator_info
    if (nrow(indicator_info) > 0L) {
      indicator_info$specification <- specification
      indicator_info$fold <- fold
      indicator_rows[[as.character(fold)]] <- indicator_info
    }
    fold_rows[[as.character(fold)]] <- data.frame(
      specification = specification,
      fold = fold,
      n_train = sum(train_index),
      n_test = sum(test_index),
      n_event_train = sum(data$fg_status_code[train_index] == 1),
      n_event_test = sum(data$fg_status_code[test_index] == 1),
      n_compete_train = sum(data$fg_status_code[train_index] == 2),
      n_compete_test = sum(data$fg_status_code[test_index] == 2),
      n_censor_train = sum(data$fg_status_code[train_index] == 0),
      n_censor_test = sum(data$fg_status_code[test_index] == 0),
      converged = model_fit$converged,
      stringsAsFactors = FALSE
    )
  }

  list(
    predictions = predictions,
    coefficients = rbindlist(coefficient_rows),
    transformations = rbindlist(transformation_rows),
    indicators = if (length(indicator_rows) > 0L) rbindlist(indicator_rows) else data.table(),
    folds = rbindlist(fold_rows)
  )
}

model_data <- data.table::fread(input_csv, data.table = FALSE)
manifest <- data.table::fread(manifest_csv, data.table = FALSE)
predictors <- manifest$predictor_name[manifest$primary_model_flag == 1]

required_columns <- c(
  "stay_id",
  "followup_hours_from_landmark",
  "fg_status_code",
  "early_sepsis12_main_flag",
  predictors
)
missing_columns <- setdiff(required_columns, names(model_data))
if (length(missing_columns) > 0L) {
  stop("Required columns are missing: ", paste(missing_columns, collapse = ", "))
}
if (anyDuplicated(model_data$stay_id)) {
  stop("Each stay must have one row in the Fine-Gray input.")
}
if (!all(model_data$fg_status_code %in% c(0, 1, 2))) {
  stop("fg_status_code must use only 0=censor, 1=event, 2=competing event.")
}
if (any(model_data$followup_hours_from_landmark <= 0 |
        is.na(model_data$followup_hours_from_landmark))) {
  stop("Follow-up times must be positive and non-missing.")
}
if (length(predictors) != 45L) {
  stop("The current v3.3 main-model contract requires exactly 45 predictors; found ",
       length(predictors), ".")
}

# These sampled laboratory measures have >=25% missingness in the 090 QC.
# They are not added to the primary model because they increase its degrees of
# freedom; instead, they are tested in a preregistered missingness-aware sensitivity.
sampled_lab_indicator_vars <- c(
  "lactate_max",
  "baseexcess_min",
  "ph_min",
  "inr_max"
)
missingness <- data.frame(
  predictor = predictors,
  n_missing = vapply(predictors, function(x) sum(is.na(model_data[[x]])), integer(1)),
  stringsAsFactors = FALSE
)
missingness$pct_missing <- 100 * missingness$n_missing / nrow(model_data)

fold_id <- make_stratified_folds(
  status = model_data$fg_status_code,
  sepsis = model_data$early_sepsis12_main_flag,
  n_folds = folds,
  seed_value = seed
)
fold_assignment <- data.frame(
  stay_id = model_data$stay_id,
  fold = fold_id,
  fg_status_code = model_data$fg_status_code,
  early_sepsis12_main_flag = model_data$early_sepsis12_main_flag
)

specifications <- list(
  primary_prespecified = character(0),
  missingness_indicator_sensitivity = sampled_lab_indicator_vars
)
cv_results <- list()
for (specification in names(specifications)) {
  message("Running ", specification, "...")
  cv_results[[specification]] <- run_cv_specification(
    data = model_data,
    predictors = predictors,
    fold_id = fold_id,
    specification = specification,
    indicator_vars = specifications[[specification]]
  )
}

prediction_table <- data.frame(
  stay_id = model_data$stay_id,
  followup_hours_from_landmark = model_data$followup_hours_from_landmark,
  fg_status_code = model_data$fg_status_code,
  early_sepsis12_main_flag = model_data$early_sepsis12_main_flag,
  fold = fold_id,
  stringsAsFactors = FALSE
)
for (specification in names(cv_results)) {
  prediction_table[[paste0("cif", horizon_hours, "_", specification)]] <-
    cv_results[[specification]]$predictions
}
if (anyNA(prediction_table)) {
  stop("Out-of-fold prediction table contains missing values.")
}

write_csv(prediction_table, file.path(output_dir, "data/090_finegray_oof_predictions.csv"))

calibration_rows <- list()
for (specification in names(cv_results)) {
  risk_column <- paste0("cif", horizon_hours, "_", specification)
  risk <- prediction_table[[risk_column]]
  breaks <- unique(stats::quantile(risk, probs = seq(0, 1, by = 0.1), na.rm = TRUE))
  if (length(breaks) < 3L) {
    stop("Insufficient risk variation for calibration grouping: ", specification)
  }
  prediction_table$calibration_group <- cut(
    risk,
    breaks = breaks,
    include.lowest = TRUE,
    labels = FALSE
  )
  group_summary <- lapply(sort(unique(prediction_table$calibration_group)), function(group) {
    rows <- prediction_table$calibration_group == group
    data.frame(
      specification = specification,
      risk_group = group,
      n = sum(rows),
      mean_predicted_cif = mean(risk[rows]),
      observed_cif = observed_cif_at(
        prediction_table$followup_hours_from_landmark[rows],
        prediction_table$fg_status_code[rows],
        horizon_hours
      ),
      stringsAsFactors = FALSE
    )
  })
  calibration_rows[[specification]] <- rbindlist(group_summary)
}

# Fit the frozen primary model once on the complete development cohort. This
# object is for later lock-down/external validation; its apparent fit is not
# used as an internal-performance estimate.
full_preprocessing <- fit_fold_preprocessor(
  train_data = model_data,
  test_data = model_data,
  predictors = predictors,
  indicator_vars = character(0)
)
full_primary_model <- cmprsk::crr(
  ftime = model_data$followup_hours_from_landmark,
  fstatus = model_data$fg_status_code,
  cov1 = full_preprocessing$train_matrix,
  failcode = 1,
  cencode = 0,
  maxiter = 100
)

write_csv(fold_assignment, file.path(output_dir, "reports/090_finegray_fold_assignment.csv"))
write_csv(missingness, file.path(output_dir, "reports/090_finegray_missingness.csv"))
write_csv(
  rbindlist(lapply(cv_results, `[[`, "folds")),
  file.path(output_dir, "reports/090_finegray_fold_counts.csv")
)
write_csv(
  rbindlist(lapply(cv_results, `[[`, "coefficients")),
  file.path(output_dir, "reports/090_finegray_cv_coefficients.csv")
)
write_csv(
  rbindlist(lapply(cv_results, `[[`, "transformations")),
  file.path(output_dir, "reports/090_finegray_fold_preprocessing.csv")
)
write_csv(
  rbindlist(lapply(cv_results, `[[`, "indicators")),
  file.path(output_dir, "reports/090_finegray_missingness_indicator_audit.csv")
)
write_csv(
  rbindlist(calibration_rows),
  file.path(output_dir, "reports/090_finegray_calibration_deciles_48h.csv")
)
write_csv(
  data.frame(
    predictor = names(full_primary_model$coef),
    coefficient = as.numeric(full_primary_model$coef),
    standard_error = sqrt(diag(full_primary_model$var)),
    subdistribution_hazard_ratio = exp(as.numeric(full_primary_model$coef)),
    stringsAsFactors = FALSE
  ),
  file.path(output_dir, "reports/090_finegray_full_primary_coefficients.csv")
)
write_csv(
  full_preprocessing$transformations,
  file.path(output_dir, "reports/090_finegray_full_primary_preprocessing.csv")
)
write_csv(
  data.frame(
    input_csv = normalizePath(input_csv),
    manifest_csv = normalizePath(manifest_csv),
    n_stays = nrow(model_data),
    n_events = sum(model_data$fg_status_code == 1),
    n_competing_events = sum(model_data$fg_status_code == 2),
    n_administrative_censor = sum(model_data$fg_status_code == 0),
    n_primary_predictors = length(predictors),
    n_missingness_sensitivity_indicators = length(sampled_lab_indicator_vars),
    folds = folds,
    seed = seed,
    horizon_hours = horizon_hours,
    stringsAsFactors = FALSE
  ),
  file.path(output_dir, "reports/090_finegray_run_summary.csv")
)

saveRDS(
  list(
    model = full_primary_model,
    predictor_names = predictors,
    preprocessing = full_preprocessing$transformations,
    horizon_hours = horizon_hours,
    source_input = normalizePath(input_csv),
    source_manifest = normalizePath(manifest_csv)
  ),
  file.path(output_dir, "models/090_finegray_full_primary_model.rds")
)
file.copy(manifest_csv, file.path(output_dir, "reports/090_predictor_manifest.csv"), overwrite = TRUE)
file.copy(script_path, file.path(output_dir, "090_finegray_baseline_v33.R"), overwrite = TRUE)
writeLines(capture.output(sessionInfo()), file.path(output_dir, "sessionInfo.txt"))

message("Completed Fine-Gray baseline run: ", output_dir)
