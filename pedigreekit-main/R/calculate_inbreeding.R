calculate_inbreeding <- function(progeny = NULL,
                                 sire = NULL,
                                 dam = NULL,
                                 sex = NULL,
                                 birthdate = NULL,
                                 missing = c("0", "na", "NA", "", " "),
                                 quiet = FALSE,
                                 file = NULL,
                                 sep = " ",
                                 progress = NULL) {
  if (is.null(progress)) progress <- !quiet
  pb <- ped_progress_start(progress)
  on.exit(pb$finish(), add = TRUE)
  pb$update(3)
  ensure_pedigree_native_loaded()
  pb$update(10)

  pick_column <- function(ped, selected, preferred, index) {
    if (!is.null(selected) && is.character(selected) && length(selected) == 1 &&
        selected %in% names(ped)) {
      ped[[selected]]
    } else if (preferred %in% names(ped)) {
      ped[[preferred]]
    } else {
      ped[[index]]
    }
  }

  if (!is.null(file)) {
    if (!is.character(file) || length(file) != 1) {
      stop("file must be a single file path.")
    }
    ped <- read.table(file, header = TRUE, sep = sep, stringsAsFactors = FALSE)
    progeny <- pick_column(ped, progeny, "progeny", 1)
    sire <- pick_column(ped, sire, "sire", 2)
    dam <- pick_column(ped, dam, "dam", 3)
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  } else if (is.character(progeny) && length(progeny) == 1 &&
             missing(sire) && missing(dam) && file.exists(progeny)) {
    ped <- read.table(progeny, header = TRUE, sep = sep, stringsAsFactors = FALSE)
    progeny <- pick_column(ped, NULL, "progeny", 1)
    sire <- pick_column(ped, NULL, "sire", 2)
    dam <- pick_column(ped, NULL, "dam", 3)
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  } else if (is.data.frame(progeny) && missing(sire) && missing(dam)) {
    ped <- progeny
    if (!all(c("progeny", "sire", "dam") %in% names(ped))) {
      progeny <- ped[[1]]
      sire <- ped[[2]]
      dam <- ped[[3]]
    } else {
      progeny <- ped$progeny
      sire <- ped$sire
      dam <- ped$dam
    }
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  }
  pb$update(20)

  if (missing(progeny) || is.null(progeny) ||
      missing(sire) || is.null(sire) ||
      missing(dam) || is.null(dam)) {
    stop("progeny, sire, and dam are required.")
  }
  if (length(progeny) != length(sire) || length(progeny) != length(dam)) {
    stop("Length mismatch: progeny, sire, and dam must have same length.")
  }
  if (!is.null(sex) && length(sex) != length(progeny)) {
    stop("Length mismatch: sex must have the same length as progeny.")
  }
  if (!is.null(birthdate) && length(birthdate) != length(progeny)) {
    stop("Length mismatch: birthdate must have the same length as progeny.")
  }
  pb$update(28)

  fixed <- fix_pedigree(
    progeny = progeny,
    sire = sire,
    dam = dam,
    sex = sex,
    birthdate = birthdate,
    missing = missing,
    quiet = TRUE,
    progress = FALSE
  )
  pb$update(88)

  F <- fast_inbreeding_cpp(fixed$progeny, fixed$sire, fixed$dam) # nolint
  pb$update(94)
  inb <- data.frame(
    id = names(F),
    inbreeding = as.numeric(F),
    stringsAsFactors = FALSE
  )

  inb_vals <- inb$inbreeding
  inb_vals <- inb_vals[is.finite(inb_vals)]
  n_all <- length(inb_vals)
  if (n_all == 0) {
    pb$finish()
    if (!quiet) {
      message("Inbreeding summary:")
      message("No valid inbreeding values.")
    }
    return(inb)
  }
  pb$update(97)

  stats_all <- c(
    total = n_all,
    min = min(inb_vals),
    max = max(inb_vals),
    mean = mean(inb_vals),
    sd = sd(inb_vals)
  )

  inbred_vals <- inb_vals[inb_vals > 0]
  stats_inbred <- c(
    total = length(inbred_vals),
    min = if (length(inbred_vals) > 0) min(inbred_vals) else NA_real_,
    max = if (length(inbred_vals) > 0) max(inbred_vals) else NA_real_,
    mean = if (length(inbred_vals) > 0) mean(inbred_vals) else NA_real_,
    sd = if (length(inbred_vals) > 0) sd(inbred_vals) else NA_real_
  )

  breaks <- c(0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
              0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)
  labels <- c("0.00 < F <= 0.05", "0.05 < F <= 0.10", "0.10 < F <= 0.15",
              "0.15 < F <= 0.20", "0.20 < F <= 0.25", "0.25 < F <= 0.30",
              "0.30 < F <= 0.35", "0.35 < F <= 0.40", "0.40 < F <= 0.45",
              "0.45 < F <= 0.50", "0.50 < F <= 0.55", "0.55 < F <= 0.60",
              "0.60 < F <= 0.65", "0.65 < F <= 0.70", "0.70 < F <= 0.75",
              "0.75 < F <= 0.80", "0.80 < F <= 0.85", "0.85 < F <= 0.90",
              "0.90 < F <= 0.95", "0.95 < F <= 1.00")
  f_zero <- sum(inb_vals == 0, na.rm = TRUE)
  f_numeric_pos <- inb_vals[inb_vals > 0]
  f_cut <- cut(f_numeric_pos, breaks = breaks, labels = labels, include.lowest = FALSE)
  f_table <- table(f_cut)
  pb$finish()

  if (!quiet) {
    old_opt <- options(scipen = 6)
    on.exit(options(old_opt), add = TRUE)
    message("Inbreeding summary (all individuals):")
    stats_all_print <- stats_all
    stats_all_print["total"] <- format(as.integer(stats_all["total"]), big.mark = ",")
    print(stats_all_print)
    message("Inbreeding summary (inbred individuals, F > 0):")
    stats_inbred_print <- stats_inbred
    stats_inbred_print["total"] <- format(as.integer(stats_inbred["total"]), big.mark = ",")
    print(stats_inbred_print)
    message("Inbreeding distribution:")
    cat("-----------------------------------------------------------\n")
    cat(sprintf("%30s %20s\n", "F = 0", format(f_zero, big.mark = ",")))
    for (i in seq_along(labels)) {
      count <- if (labels[i] %in% names(f_table)) f_table[labels[i]] else 0
      cat(sprintf("%30s %20s\n", labels[i], format(count, big.mark = ",")))
    }
    cat("-----------------------------------------------------------\n")
  }

  inb
}
