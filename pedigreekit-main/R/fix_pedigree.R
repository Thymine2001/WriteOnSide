fix_pedigree <- function(progeny = NULL,
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
             missing(sire) && missing(dam)) {
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
  pb$update(22)

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
  pb$update(30)

  parse_birthdate_numeric <- function(x) {
    if (is.null(x)) return(NULL)
    if (inherits(x, "Date") || inherits(x, "POSIXct")) {
      return(as.numeric(x))
    }
    if (is.character(x)) {
      return(vapply(x, function(v) {
        if (is.na(v)) return(NA_real_)
        v_trim <- trimws(v)
        if (v_trim == "" || toupper(v_trim) == "NA" || grepl("1900-01-00", v_trim, fixed = TRUE)) {
          return(NA_real_)
        }
        suppressWarnings(as.numeric(as.Date(v_trim)))
      }, numeric(1)))
    }
    suppressWarnings(as.numeric(x))
  }

  birth_num <- parse_birthdate_numeric(birthdate)
  pb$update(38)

  fixed_cpp <- fast_fix_pedigree_cpp( # nolint: object_usage_linter
    progeny = as.character(progeny),
    sires = as.character(sire),
    dams = as.character(dam),
    sex = if (is.null(sex)) NULL else as.character(sex),
    birthdate = birth_num,
    missing = as.character(missing)
  )
  pb$update(86)

  fixed_summary <- list()
  fix_log <- fixed_cpp$fix_log
  if (!is.null(fix_log) && nrow(fix_log) > 0L) {
    log_type <- as.character(fix_log$type)
    log_old <- as.character(fix_log$old)
    n_missing_ids <- sum(log_type == "missing_progeny", na.rm = TRUE)
    n_dups <- sum(log_type == "duplicate_id", na.rm = TRUE)
    n_self <- sum(log_type == "self_parent", na.rm = TRUE)
    n_dual <- sum(log_type == "dual_role_parent", na.rm = TRUE)
    n_sex <- sum(log_type == "sex_mismatch", na.rm = TRUE)
    n_loops <- sum(log_type == "loop_break", na.rm = TRUE)
    n_birth <- sum(log_type == "birthdate_invalid", na.rm = TRUE)

    founder_old <- log_old[log_type == "missing_parent_founder"]
    founder_old <- founder_old[!is.na(founder_old) & founder_old != "" & founder_old != "NA"]
    n_founders <- length(unique(founder_old))

    if (n_missing_ids > 0L) {
      fixed_summary$missing_ids <- paste0("Removed ", n_missing_ids, " row(s) with missing or empty ID")
    }
    if (n_dups > 0L) {
      fixed_summary$duplicates <- paste0("Removed ", n_dups, " duplicate record(s); kept the most complete record per ID")
    }
    if (n_self > 0L) {
      fixed_summary$self_parenting <- paste0("Fixed ", n_self, " self-parenting case(s)")
    }
    if (n_founders > 0L) {
      fixed_summary$missing_parents <- paste0(
        "Added ", n_founders, " missing parent ID(s) as founder record(s) with sire=0 and dam=0"
      )
    }
    if (n_dual > 0L) {
      fixed_summary$dual_parent_role <- paste0("Set ", n_dual, " dual-role parent reference(s) to NA")
    }
    if (n_sex > 0L) {
      fixed_summary$sex_mismatch <- paste0("Set ", n_sex, " parent reference(s) with sex mismatch to NA")
    }
    if (n_birth > 0L) {
      fixed_summary$birth_date_order <- paste0("Set ", n_birth, " invalid birth date(s) to 0")
    }
    if (n_loops > 0L) {
      fixed_summary$loops <- paste0("Broke ", n_loops, " circular reference(s)")
    }
  }

  ped_out <- data.frame(
    progeny = as.character(fixed_cpp$progeny),
    sire = as.character(fixed_cpp$sire),
    dam = as.character(fixed_cpp$dam),
    stringsAsFactors = FALSE
  )

  if (!is.null(fixed_cpp$sex)) {
    ped_out$sex <- as.character(fixed_cpp$sex)
  }

  if (!is.null(birthdate) && !is.null(fixed_cpp$birthdate)) {
    birth_out <- as.numeric(fixed_cpp$birthdate)
    if (inherits(birthdate, "Date") || inherits(birthdate, "POSIXct") || is.character(birthdate)) {
      birth_chr <- rep(NA_character_, length(birth_out))
      keep_date <- !is.na(birth_out) & birth_out != 0
      birth_chr[keep_date] <- as.character(as.Date(birth_out[keep_date], origin = "1970-01-01"))
      birth_chr[!is.na(birth_out) & birth_out == 0] <- "0"
      ped_out$birthdate <- birth_chr
    } else {
      ped_out$birthdate <- birth_out
    }
  }
  pb$update(92)

  pb$update(98)
  pb$finish()
  if (!quiet) {
    message("Fix log:")
    print(fixed_summary)
  }

  ped_out
}
