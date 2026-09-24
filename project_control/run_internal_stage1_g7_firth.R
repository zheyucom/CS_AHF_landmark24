#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly=TRUE)
input_path <- args[1]
out_path <- args[2]
d <- read.csv(input_path, fileEncoding='UTF-8-BOM', stringsAsFactors=FALSE, check.names=FALSE)
d$age_num <- as.numeric(d$age)
d$male <- ifelse(d$sex == '男', 1, 0)
d$emergency_num <- as.numeric(d$emergency)
d$y <- as.numeric(d$hospital_death)

fit_firth <- function(dat, label) {
  dat <- dat[complete.cases(dat[, c('age_num','male','emergency_num','y')]), ]
  age_center <- median(dat$age_num)
  x <- cbind(Intercept=1, age_c=dat$age_num - age_center, male=dat$male, emergency=dat$emergency_num)
  y <- dat$y
  if (length(unique(y)) < 2) stop(paste('single outcome class in', label))
  beta <- rep(0, ncol(x))
  converged <- FALSE
  iter_used <- NA
  for (iter in 1:200) {
    eta <- as.vector(x %*% beta)
    mu <- plogis(eta)
    w <- pmax(mu * (1 - mu), 1e-10)
    info <- crossprod(x, sweep(x, 1, w, '*'))
    info_inv <- tryCatch(solve(info), error=function(e) NULL)
    if (is.null(info_inv)) stop(paste('singular information in', label))
    h <- rowSums((x %*% info_inv) * x) * w
    z <- eta + (y - mu + h * (0.5 - mu)) / w
    beta_new <- as.vector(info_inv %*% crossprod(x, w * z))
    if (max(abs(beta_new - beta)) < 1e-9) {
      beta <- beta_new
      converged <- TRUE
      iter_used <- iter
      break
    }
    beta <- beta_new
  }
  eta <- as.vector(x %*% beta)
  mu <- plogis(eta)
  w <- pmax(mu * (1 - mu), 1e-10)
  info <- crossprod(x, sweep(x, 1, w, '*'))
  info_inv <- solve(info)
  se <- sqrt(pmax(diag(info_inv), 0))
  zcrit <- qnorm(0.975)
  data.frame(
    analysis=label,
    term=colnames(x),
    beta=beta,
    odds_ratio=exp(beta),
    se=se,
    ci_low=exp(beta - zcrit * se),
    ci_high=exp(beta + zcrit * se),
    n=nrow(dat),
    events=sum(y),
    non_events=sum(1-y),
    age_center=age_center,
    converged=converged,
    iterations=iter_used,
    stringsAsFactors=FALSE
  )
}

# Numerical smoke test on a separated toy dataset.
toy <- data.frame(age_num=c(40,41,42,70,71,72), male=c(0,1,0,1,0,1), emergency_num=c(0,0,1,1,1,0), y=c(0,0,0,1,1,1))
toy_result <- fit_firth(toy, 'toy_smoke_test')
if (any(!is.finite(toy_result$beta))) stop('toy smoke test failed')

analyses <- list(
  main_ABC = d,
  strict_objective = d[d$strict_objective_flag == '1', ],
  exclude_2024 = d[d$calendar_2024_incomplete_flag != '1', ]
)
all_results <- do.call(rbind, lapply(names(analyses), function(nm) fit_firth(analyses[[nm]], nm)))
write.csv(all_results, out_path, row.names=FALSE, fileEncoding='UTF-8')
cat('wrote', out_path, '\n')
print(all_results)
