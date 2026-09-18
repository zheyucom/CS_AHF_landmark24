#!/usr/bin/env Rscript

# Supplementary one-hour landmark survival model for v3.3.
# A multinomial discrete-time hazard model estimates event, competing
# discharge, and no transition at each hourly interval. OOF 48 h CIFs
# are then obtained by recursive state-transition multiplication.

suppressPackageStartupMessages({
  library(data.table)
  library(glmnet)
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
feature_csv <- args$features %||%
  file.path(
    project_root,
    "project_control/runs/20260828_v3_3_compact_features/data/090C_finegray_input_v33.csv"
  )
person_period_csv <- args$person_period %||%
  file.path(
    project_root,
    "project_control/runs/20260827_v3_3_person_period_reconciled/data/097_person_period_v33_v2.csv"
  )
output_dir <- args$output %||%
  file.path(project_root, "project_control/runs/20260827_person_period_model_v33")
folds <- as.integer(args$folds %||% "5")
seed <- as.integer(args$seed %||% "20260827")
alpha <- as.numeric(args$alpha %||% "0.5")
inner_folds <- as.integer(args$inner_folds %||% "3")

if (!file.exists(feature_csv) || !file.exists(person_period_csv)) {
  stop("Feature or person-period input is missing.")
}
if (is.na(folds) || folds < 2L) {
  stop("--folds must be an integer >= 2.")
}
if (is.na(seed) || is.na(alpha) || alpha < 0 || alpha > 1 ||
    is.na(inner_folds) || inner_folds < 2L) {
  stop("--seed must be valid, --alpha must be in [0, 1], and --inner_folds >= 2.")
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "data"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "reports"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(output_dir, "models"), recursive = TRUE, showWarnings = FALSE)

write_csv <- function(x, path) {
  data.table::fwrite(as.data.table(x), path, na = "")
}

feature_data <- utils::read.csv(feature_csv, check.names = FALSE)
person_period <- utils::read.csv(person_period_csv, check.names = FALSE)

manifest_csv <- file.path(
  project_root,
  "project_control/runs/20260828_v3_3_compact_features/reports/090_predictor_manifest.csv"
)
manifest <- utils::read.csv(manifest_csv, check.names = FALSE)
predictors <- manifest$predictor_name[manifest$primary_model_flag == 1]
if (length(predictors) != 45L) {
  stop("Expected exactly 45 frozen predictors; found ", length(predictors), ".")
}

required_feature_columns <- c("stay_id", "early_sepsis12_main_flag", predictors)
required_pp_columns <- c(
  "stay_id", "period_index", "period_status", "event_period_flag",
  "compete_period_flag", "censor_period_flag", "period_duration_hours"
)
missing_feature_columns <- setdiff(required_feature_columns, names(feature_data))
missing_pp_columns <- setdiff(required_pp_columns, names(person_period))
if (length(missing_feature_columns) > 0L || length(missing_pp_columns) > 0L) {
  stop(
    "Missing required columns. feature=",
    paste(missing_feature_columns, collapse = ", "),
    "; person_period=",
    paste(missing_pp_columns, collapse = ", ")
  )
}
if (anyDuplicated(feature_data$stay_id)) {
  stop("Feature input has duplicate stays.")
}

feature_data <- feature_data[, unique(c(
  required_feature_columns,
  "fg_status_code",
  "followup_hours_from_landmark"
)), drop = FALSE]
person_period <- person_period[, required_pp_columns, drop = FALSE]
person_period <- merge(
  person_period,
  feature_data,
  by = "stay_id",
  all.x = FALSE,
  all.y = FALSE,
  sort = FALSE
)
if (nrow(person_period) == 0L || anyNA(person_period$stay_id)) {
  stop("Feature/person-period join produced no usable rows.")
}

stay_level <- unique(feature_data[, c("stay_id", "early_sepsis12_main_flag")])
if (nrow(stay_level) != 5555L) {
  stop("Expected 5,555 unique stays; found ", nrow(stay_level), ".")
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

feature_matrix_with_imputation <- function(train_data, test_data, predictors) {
  train_matrix <- matrix(
    NA_real_, nrow = nrow(train_data), ncol = length(predictors),
    dimnames = list(as.character(train_data$stay_id), predictors)
  )
  test_matrix <- matrix(
    NA_real_, nrow = nrow(test_data), ncol = length(predictors),
    dimnames = list(as.character(test_data$stay_id), predictors)
  )
  transforms <- vector("list", length(predictors))
  names(transforms) <- predictors

  for (predictor in predictors) {
    train_values <- as.numeric(train_data[[predictor]])
    test_values <- as.numeric(test_data[[predictor]])
    if (all(is.na(train_values))) {
      stop("Predictor is completely missing in training data: ", predictor)
    }
    impute_value <- median(train_values, na.rm = TRUE)
    train_values[is.na(train_values)] <- impute_value
    test_values[is.na(test_values)] <- impute_value
    center <- mean(train_values)
    scale_value <- stats::sd(train_values)
    if (!is.finite(scale_value) || scale_value == 0) {
      scale_value <- 1
    }
    train_matrix[, predictor] <- (train_values - center) / scale_value
    test_matrix[, predictor] <- (test_values - center) / scale_value
    transforms[[predictor]] <- data.frame(
      predictor = predictor,
      train_median = impute_value,
      train_missing_fraction = mean(is.na(as.numeric(train_data[[predictor]]))),
      center = center,
      scale = scale_value,
      stringsAsFactors = FALSE
    )
  }

  list(
    train_matrix = train_matrix,
    test_matrix = test_matrix,
    transforms = data.table::rbindlist(transforms)
  )
}

make_design_matrix <- function(period_index, feature_matrix, predictors) {
  period_factor <- factor(period_index, levels = 0:47)
  period_matrix <- stats::model.matrix(~ period_factor)[, -1, drop = FALSE]
  colnames(period_matrix) <- paste0("period_", 1:47)
  cbind(period_matrix, feature_matrix[, predictors, drop = FALSE])
}

fit_multinomial_hazard <- function(train_rows, train_feature_matrix, predictors,
                                    alpha_value, seed_value, inner_folds_value) {
  set.seed(seed_value)
  response <- factor(
    ifelse(train_rows$event_period_flag == 1, "event",
      ifelse(train_rows$compete_period_flag == 1, "compete", "none")
    ),
    levels = c("none", "event", "compete")
  )
  row_feature_matrix <- train_feature_matrix[
    match(train_rows$stay_id, rownames(train_feature_matrix)),
    predictors,
    drop = FALSE
  ]
  if (anyNA(row_feature_matrix)) {
    stop("Could not map stay-level features to person-period rows.")
  }
  design <- make_design_matrix(
    train_rows$period_index,
    row_feature_matrix,
    predictors
  )
  if (anyNA(design) || anyNA(response)) {
    stop("NA detected in multinomial design or response.")
  }
  cv_fit <- glmnet::cv.glmnet(
    x = design,
    y = response,
    family = "multinomial",
    alpha = alpha_value,
    nfolds = inner_folds_value,
    nlambda = 30,
    type.measure = "deviance",
    grouped = FALSE,
    standardize = FALSE,
    parallel = FALSE
  )
  list(
    fit = cv_fit,
    lambda = cv_fit$lambda.min,
    design_columns = colnames(design)
  )
}

predict_cif <- function(model_fit, feature_matrix, predictors) {
  n_stays <- nrow(feature_matrix)
  event_cif <- numeric(n_stays)
  compete_cif <- numeric(n_stays)
  survival <- rep(1, n_stays)
  period_rows <- vector("list", 48L)

  for (period in 0:47) {
    period_design <- make_design_matrix(
      rep(period, n_stays),
      feature_matrix,
      predictors
    )
    probabilities <- predict(
      model_fit$fit,
      newx = period_design,
      s = model_fit$lambda,
      type = "response"
    )
    probability_matrix <- probabilities[, , 1, drop = TRUE]
    if (is.null(dim(probability_matrix))) {
      probability_matrix <- matrix(
        probability_matrix,
        nrow = n_stays,
        dimnames = list(NULL, dimnames(probabilities)[[2]])
      )
    }
    if (is.null(colnames(probability_matrix))) {
      colnames(probability_matrix) <- dimnames(probabilities)[[2]]
    }
    event_probability <- probability_matrix[, "event"]
    compete_probability <- probability_matrix[, "compete"]
    none_probability <- probability_matrix[, "none"]
    event_cif <- event_cif + survival * event_probability
    compete_cif <- compete_cif + survival * compete_probability
    survival <- survival * none_probability
    period_rows[[period + 1L]] <- data.frame(
      period_index = period,
      mean_event_hazard = mean(event_probability),
      mean_compete_hazard = mean(compete_probability),
      mean_none_probability = mean(none_probability),
      mean_survival = mean(survival),
      stringsAsFactors = FALSE
    )
  }
  list(
    event_cif = event_cif,
    compete_cif = compete_cif,
    survival_48h = survival,
    period_summary = data.table::rbindlist(period_rows)
  )
}

event_status <- unique(feature_data[, c(
  "stay_id", "fg_status_code", "followup_hours_from_landmark",
  "early_sepsis12_main_flag"
)])
if (nrow(event_status) != nrow(feature_data)) {
  stop("Could not establish one label row per stay from feature input.")
}

fold_id <- make_stratified_folds(
  event_status$fg_status_code,
  event_status$early_sepsis12_main_flag,
  folds,
  seed
)
event_status$fold <- fold_id
person_period <- merge(
  person_period,
  event_status[, c("stay_id", "fold")],
  by = "stay_id",
  all.x = FALSE,
  all.y = FALSE,
  sort = FALSE
)

oof <- event_status[, c(
  "stay_id", "fg_status_code", "followup_hours_from_landmark",
  "early_sepsis12_main_flag", "fold"
)]
oof$cif48_person_period <- NA_real_
oof$compete48_person_period <- NA_real_
oof$survival48_person_period <- NA_real_
fold_summary <- list()
transform_summary <- list()
period_summary <- list()

for (fold in seq_len(folds)) {
  train_stays <- event_status$stay_id[event_status$fold != fold]
  test_stays <- event_status$stay_id[event_status$fold == fold]
  train_features <- feature_data[feature_data$stay_id %in% train_stays, ]
  test_features <- feature_data[feature_data$stay_id %in% test_stays, ]
  train_rows <- person_period[person_period$stay_id %in% train_stays, ]

  preprocessing <- feature_matrix_with_imputation(
    train_features,
    test_features,
    predictors
  )
  model_fit <- fit_multinomial_hazard(
    train_rows,
    preprocessing$train_matrix,
    predictors,
    alpha,
    seed + fold,
    inner_folds
  )
  predictions <- predict_cif(
    model_fit,
    preprocessing$test_matrix,
    predictors
  )
  test_index <- match(test_stays, oof$stay_id)
  oof$cif48_person_period[test_index] <- predictions$event_cif
  oof$compete48_person_period[test_index] <- predictions$compete_cif
  oof$survival48_person_period[test_index] <- predictions$survival_48h

  fold_summary[[fold]] <- data.frame(
    fold = fold,
    n_train_stays = length(train_stays),
    n_test_stays = length(test_stays),
    n_train_rows = nrow(train_rows),
    n_train_events = sum(train_rows$event_period_flag),
    n_train_competes = sum(train_rows$compete_period_flag),
    lambda_min = model_fit$lambda,
  alpha = alpha,
    inner_folds = inner_folds,
    stringsAsFactors = FALSE
  )
  transform_summary[[fold]] <- cbind(
    preprocessing$transforms,
    data.frame(fold = fold, stringsAsFactors = FALSE)
  )
  period_summary[[fold]] <- cbind(
    predictions$period_summary,
    data.frame(fold = fold, stringsAsFactors = FALSE)
  )
}

if (any(!is.finite(oof$cif48_person_period)) ||
    any(!is.finite(oof$compete48_person_period)) ||
    any(!is.finite(oof$survival48_person_period))) {
  stop("OOF prediction contains non-finite values.")
}
if (any(oof$cif48_person_period < 0 | oof$cif48_person_period > 1) ||
    any(oof$compete48_person_period < 0 | oof$compete48_person_period > 1) ||
    any(oof$survival48_person_period < 0 | oof$survival48_person_period > 1)) {
  stop("OOF prediction is outside [0, 1].")
}
if (any(abs(
  oof$cif48_person_period +
    oof$compete48_person_period +
    oof$survival48_person_period - 1
) > 1e-8)) {
  stop("Recursive state probabilities do not sum to one.")
}

full_features <- feature_data
full_pp <- person_period
full_preprocessing <- feature_matrix_with_imputation(
  full_features,
  full_features,
  predictors
)
full_model <- fit_multinomial_hazard(
  full_pp,
  full_preprocessing$train_matrix,
  predictors,
  alpha,
  seed,
  inner_folds
)
saveRDS(
  list(
    model = full_model,
    predictors = predictors,
    preprocessing = full_preprocessing$transforms,
    alpha = alpha,
    inner_folds = inner_folds,
    seed = seed
  ),
  file.path(output_dir, "models/092_person_period_multistate_full_model.rds")
)

write_csv(oof, file.path(output_dir, "data/092_person_period_oof_predictions.csv"))
write_csv(
  data.table::rbindlist(fold_summary),
  file.path(output_dir, "reports/092_person_period_fold_summary.csv")
)
write_csv(
  data.table::rbindlist(transform_summary),
  file.path(output_dir, "reports/092_person_period_fold_preprocessing.csv")
)
write_csv(
  data.table::rbindlist(period_summary),
  file.path(output_dir, "reports/092_person_period_hazard_summary.csv")
)
write_csv(
  data.frame(
    input_features = feature_csv,
    input_person_period = person_period_csv,
    n_stays = nrow(event_status),
    n_person_period_rows = nrow(person_period),
    n_events = sum(event_status$fg_status_code == 1),
    n_competing = sum(event_status$fg_status_code == 2),
    n_censor = sum(event_status$fg_status_code == 0),
    predictors = length(predictors),
    folds = folds,
    seed = seed,
    alpha = alpha,
    stringsAsFactors = FALSE
  ),
  file.path(output_dir, "reports/092_person_period_run_summary.csv")
)
writeLines(
  capture.output(sessionInfo()),
  file.path(output_dir, "reports/092_sessionInfo.txt")
)

message("Completed one-hour person-period model: ", output_dir)
