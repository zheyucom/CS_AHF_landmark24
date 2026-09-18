#!/usr/bin/env Rscript

# Nested, deployment-compatible MICE sensitivity for the v3.3 Fine-Gray input.
# MICE is fitted only on each outer training fold. Validation-fold missing values
# are PMM-imputed from that fold's completed training donors, never from outcome
# data or other validation patients' outcome information.

suppressPackageStartupMessages({
  library(cmprsk)
  library(data.table)
  library(mice)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1L) stop("Run with Rscript so the project root can be resolved.")
script_path <- normalizePath(sub("^--file=", "", script_arg))
project_root <- normalizePath(file.path(dirname(script_path), ".."))

`%||%` <- function(x, y) if (is.null(x)) y else x

parse_args <- function(args) {
  out <- list()
  for (arg in args) {
    pair <- strsplit(sub("^--", "", arg), "=", fixed = TRUE)[[1]]
    if (!startsWith(arg, "--") || length(pair) != 2L) {
      stop("Arguments must use --name=value: ", arg)
    }
    out[[pair[1]]] <- pair[2]
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
input_csv <- args$input %||% file.path(
  project_root, "project_control/runs/20260828_v3_3_compact_features/data/090C_finegray_input_v33.csv"
)
manifest_csv <- args$manifest %||% file.path(
  project_root, "project_control/runs/20260828_v3_3_compact_features/reports/090_predictor_manifest.csv"
)
output_dir <- args$output %||% file.path(project_root, "project_control/runs/20260904_finegray_mice_sensitivity_v33")
folds <- as.integer(args$folds %||% "5")
m <- as.integer(args$m %||% "20")
maxit <- as.integer(args$maxit %||% "10")
seed <- as.integer(args$seed %||% "20260904")
horizon_hours <- as.numeric(args$horizon_hours %||% "48")

if (!file.exists(input_csv) || !file.exists(manifest_csv)) stop("Input CSV or manifest is missing.")
if (is.na(folds) || folds < 2L || is.na(m) || m < 2L || is.na(maxit) || maxit < 1L) {
  stop("--folds >=2, --m >=2 and --maxit >=1 are required.")
}
dir.create(file.path(output_dir, "data"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "reports"), recursive = TRUE, showWarnings = FALSE)

write_csv <- function(x, path) data.table::fwrite(data.table::as.data.table(x), path, na = "")

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

step_cif_at <- function(prediction_matrix, horizon) {
  position <- findInterval(horizon, prediction_matrix[, 1])
  if (position == 0L) return(rep(0, ncol(prediction_matrix) - 1L))
  as.numeric(prediction_matrix[position, -1, drop = TRUE])
}

scale_from_train <- function(train, test, predictors) {
  train_matrix <- matrix(NA_real_, nrow(train), length(predictors), dimnames = list(NULL, predictors))
  test_matrix <- matrix(NA_real_, nrow(test), length(predictors), dimnames = list(NULL, predictors))
  transforms <- vector("list", length(predictors))
  names(transforms) <- predictors
  for (predictor in predictors) {
    train_values <- as.numeric(train[[predictor]])
    test_values <- as.numeric(test[[predictor]])
    binary <- all(unique(train_values) %in% c(0, 1))
    center <- if (binary) 0 else mean(train_values)
    scale <- if (binary) 1 else stats::sd(train_values)
    if (!is.finite(scale) || scale == 0) scale <- 1
    train_matrix[, predictor] <- (train_values - center) / scale
    test_matrix[, predictor] <- (test_values - center) / scale
    transforms[[predictor]] <- data.frame(predictor, center, scale, binary, stringsAsFactors = FALSE)
  }
  list(train = train_matrix, test = test_matrix, transforms = rbindlist(transforms))
}

# Create M completed training data sets using predictors only. Excluding outcome
# fields makes the validation transformation available at prospective use time.
fit_training_mice <- function(train, predictors, m, maxit, seed) {
  train_predictors <- as.data.frame(train[, predictors, drop = FALSE])
  method <- vapply(train_predictors, function(x) if (anyNA(x)) "pmm" else "", character(1))
  predictor_matrix <- matrix(1L, nrow = length(predictors), ncol = length(predictors),
                             dimnames = list(predictors, predictors))
  diag(predictor_matrix) <- 0L
  mice_fit <- mice::mice(
    data = train_predictors,
    m = m,
    maxit = maxit,
    method = method,
    predictorMatrix = predictor_matrix,
    printFlag = FALSE,
    seed = seed,
    remove.collinear = FALSE,
    remove.constant = TRUE
  )
  list(
    completed = lapply(seq_len(m), function(index) mice::complete(mice_fit, index)),
    logged_events = mice_fit$loggedEvents,
    method = method
  )
}

# Apply one completed training data set to validation data. Initial medians only
# seed the PMM covariates; every originally missing validation value is then
# selected from completed *training* donors.
transform_validation_pmm <- function(completed_train, test, predictors, cycles = 3L, seed) {
  set.seed(seed)
  original_test <- as.data.frame(test[, predictors, drop = FALSE])
  test_work <- original_test
  missing_map <- lapply(predictors, function(p) is.na(original_test[[p]]))
  names(missing_map) <- predictors

  for (predictor in predictors) {
    missing <- missing_map[[predictor]]
    if (any(missing)) {
      test_work[[predictor]][missing] <- stats::median(completed_train[[predictor]], na.rm = TRUE)
    }
  }

  for (cycle in seq_len(cycles)) {
    for (predictor in predictors) {
      missing <- missing_map[[predictor]]
      if (!any(missing)) next
      other_predictors <- setdiff(predictors, predictor)
      train_n <- nrow(completed_train)
      y <- c(as.numeric(completed_train[[predictor]]), as.numeric(test_work[[predictor]]))
      y[train_n + which(missing)] <- NA_real_
      imputed <- mice::mice.impute.pmm(
        y = y,
        ry = c(rep(TRUE, train_n), rep(FALSE, nrow(test_work))),
        x = rbind(
          as.matrix(completed_train[, other_predictors, drop = FALSE]),
          as.matrix(test_work[, other_predictors, drop = FALSE])
        ),
        wy = c(rep(FALSE, train_n), missing),
        donors = 5
      )
      test_work[[predictor]][missing] <- imputed
    }
  }
  if (anyNA(test_work)) stop("Validation PMM transformation left missing predictor values.")
  test_work
}

add_missing_indicators <- function(train_matrix, test_matrix, train_original, test_original, indicator_vars) {
  retained <- list()
  for (predictor in indicator_vars) {
    train_indicator <- as.numeric(is.na(train_original[[predictor]]))
    test_indicator <- as.numeric(is.na(test_original[[predictor]]))
    if (length(unique(train_indicator)) < 2L ||
        any(vapply(retained, identical, logical(1), train_indicator))) next
    name <- paste0(predictor, "__missing")
    train_matrix <- cbind(train_matrix, setNames(data.frame(train_indicator), name))
    test_matrix <- cbind(test_matrix, setNames(data.frame(test_indicator), name))
    retained[[name]] <- train_indicator
  }
  list(train = as.matrix(train_matrix), test = as.matrix(test_matrix), included = names(retained))
}

model_data <- data.table::fread(input_csv, data.table = FALSE)
manifest <- data.table::fread(manifest_csv, data.table = FALSE)
predictors <- manifest$predictor_name[manifest$primary_model_flag == 1]
required <- c("stay_id", "followup_hours_from_landmark", "fg_status_code", "early_sepsis12_main_flag", predictors)
if (length(setdiff(required, names(model_data))) > 0L || anyDuplicated(model_data$stay_id)) {
  stop("Fine-Gray input must contain each required column and one row per stay.")
}
if (length(predictors) != 45L || !all(model_data$fg_status_code %in% c(0, 1, 2))) {
  stop("Expected the frozen 45 predictors and three-state Fine-Gray status coding.")
}

indicator_vars <- c("lactate_max", "ph_min", "baseexcess_min", "inr_max")
fold_id <- make_stratified_folds(model_data$fg_status_code, model_data$early_sepsis12_main_flag, folds, seed)
predictions <- matrix(NA_real_, nrow(model_data), 2L,
                      dimnames = list(NULL, c("mice_only", "mice_missingness_indicator")))
fold_rows <- list()
imputation_rows <- list()

for (fold in seq_len(folds)) {
  message("Running nested MICE fold ", fold, " of ", folds, "...")
  train_index <- fold_id != fold
  test_index <- fold_id == fold
  train <- model_data[train_index, , drop = FALSE]
  test <- model_data[test_index, , drop = FALSE]
  mice_result <- fit_training_mice(train, predictors, m, maxit, seed + fold)
  fold_predictions <- matrix(NA_real_, nrow(test), m, dimnames = list(NULL, seq_len(m)))
  fold_indicator_predictions <- matrix(NA_real_, nrow(test), m, dimnames = list(NULL, seq_len(m)))

  for (imputation in seq_len(m)) {
    completed_train <- mice_result$completed[[imputation]]
    completed_test <- transform_validation_pmm(
      completed_train, test, predictors, cycles = 3L, seed = seed + fold * 1000L + imputation
    )
    scaled <- scale_from_train(completed_train, completed_test, predictors)
    model_fit <- cmprsk::crr(
      ftime = train$followup_hours_from_landmark,
      fstatus = train$fg_status_code,
      cov1 = scaled$train,
      failcode = 1,
      cencode = 0,
      maxiter = 100
    )
    fold_predictions[, imputation] <- step_cif_at(
      predict(model_fit, cov1 = scaled$test), horizon_hours
    )
    augmented <- add_missing_indicators(
      scaled$train, scaled$test, train, test, indicator_vars
    )
    indicator_fit <- cmprsk::crr(
      ftime = train$followup_hours_from_landmark,
      fstatus = train$fg_status_code,
      cov1 = augmented$train,
      failcode = 1,
      cencode = 0,
      maxiter = 100
    )
    fold_indicator_predictions[, imputation] <- step_cif_at(
      predict(indicator_fit, cov1 = augmented$test), horizon_hours
    )
  }

  predictions[test_index, "mice_only"] <- rowMeans(fold_predictions)
  predictions[test_index, "mice_missingness_indicator"] <- rowMeans(fold_indicator_predictions)
  fold_rows[[fold]] <- data.frame(
    fold = fold,
    n_train = sum(train_index), n_test = sum(test_index),
    n_event_train = sum(train$fg_status_code == 1), n_event_test = sum(test$fg_status_code == 1),
    n_compete_train = sum(train$fg_status_code == 2), n_compete_test = sum(test$fg_status_code == 2),
    n_censor_train = sum(train$fg_status_code == 0), n_censor_test = sum(test$fg_status_code == 0),
    stringsAsFactors = FALSE
  )
  imputation_rows[[fold]] <- data.frame(
    fold = fold, m = m, maxit = maxit,
    mice_logged_events = if (is.null(mice_result$logged_events)) 0L else nrow(mice_result$logged_events),
    n_indicator_predictors = length(add_missing_indicators(
      matrix(0, nrow(train), 0), matrix(0, nrow(test), 0), train, test, indicator_vars
    )$included),
    stringsAsFactors = FALSE
  )
}

if (anyNA(predictions) || any(predictions < 0 | predictions > 1)) stop("Invalid nested-MICE OOF predictions.")
oof <- data.frame(
  stay_id = model_data$stay_id,
  followup_hours_from_landmark = model_data$followup_hours_from_landmark,
  fg_status_code = model_data$fg_status_code,
  early_sepsis12_main_flag = model_data$early_sepsis12_main_flag,
  fold = fold_id,
  cif48_mice_only = predictions[, "mice_only"],
  cif48_mice_missingness_indicator = predictions[, "mice_missingness_indicator"],
  stringsAsFactors = FALSE
)
write_csv(oof, file.path(output_dir, "data/094_finegray_mice_oof_predictions.csv"))
write_csv(rbindlist(fold_rows), file.path(output_dir, "reports/094_finegray_mice_fold_counts.csv"))
write_csv(rbindlist(imputation_rows), file.path(output_dir, "reports/094_finegray_mice_audit.csv"))
write_csv(data.frame(
  input_csv = normalizePath(input_csv), manifest_csv = normalizePath(manifest_csv),
  n_stays = nrow(model_data), n_events = sum(model_data$fg_status_code == 1),
  folds = folds, m = m, maxit = maxit, seed = seed, horizon_hours = horizon_hours,
  stringsAsFactors = FALSE
), file.path(output_dir, "reports/094_finegray_mice_run_summary.csv"))
file.copy(script_path, file.path(output_dir, "094_finegray_mice_sensitivity_v33.R"), overwrite = TRUE)
writeLines(capture.output(sessionInfo()), file.path(output_dir, "sessionInfo.txt"))
message("Completed nested MICE Fine-Gray sensitivity run: ", output_dir)
