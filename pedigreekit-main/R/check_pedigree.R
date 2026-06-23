ensure_pedigree_native_loaded <- function() {
  needed <- c(
    "_pedigreekit_fast_pedigree_qc",
    "_pedigreekit_fast_pedigree_qc_sex",
    "_pedigreekit_fast_detect_loops",
    "_pedigreekit_check_birth_date_order",
    "_pedigreekit_fast_fix_pedigree_cpp",
    "_pedigreekit_fast_inbreeding_cpp",
    "_pedigreekit_fast_top_contrib_cpp",
    "_pedigreekit_fast_ancestor_contribution_bulk_cpp",
    "_pedigreekit_fast_ancestor_contribution_triplet_cpp"
  )
  if (!all(vapply(needed, is.loaded, logical(1)))) {
    stop(
      "Native C++ routines are not loaded. Install/reinstall 'pedigreekit', ",
      "or in development use pkgload::load_all(compile = TRUE).",
      call. = FALSE
    )
  }
  invisible(TRUE)
}

check_pedigree <- function(progeny = NULL,
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
      stop("data.frame must contain columns: progeny, sire, dam.")
    }
    progeny <- ped$progeny
    sire <- ped$sire
    dam <- ped$dam
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  }
  pb$update(25)

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
  n <- length(progeny)
  if (n == 0) {
    result <- list(
      meta = list(total = 0),
      errors = list()
    )
    pb$finish()
    if (!quiet) print(result$meta)
    return(result)
  }
  pb$update(35)

  normalize_missing <- function(x, missing_tokens) {
    x_chr <- as.character(x)
    x_trim <- trimws(x_chr)
    x_low <- tolower(x_trim)
    missing_low <- unique(tolower(as.character(missing_tokens)))
    is_missing <- is.na(x_chr) | x_trim == "" | x_low %in% missing_low
    x_trim[is_missing] <- "0"
    x_trim
  }

  progeny_chr_raw <- as.character(progeny)
  progeny_chr <- trimws(progeny_chr_raw)
  missing_low <- unique(tolower(trimws(as.character(missing))))
  missing_progeny <- is.na(progeny_chr_raw) | progeny_chr == "" | tolower(progeny_chr) %in% missing_low
  missing_progeny_ids <- progeny_chr[missing_progeny]
  if (any(missing_progeny)) {
    keep <- !missing_progeny
    progeny_chr <- progeny_chr[keep]
    sire <- sire[keep]
    dam <- dam[keep]
    if (!is.null(sex)) sex <- sex[keep]
    if (!is.null(birthdate)) birthdate <- birthdate[keep]
  }

  sire_chr <- normalize_missing(sire, missing)
  dam_chr <- normalize_missing(dam, missing)
  pb$update(45)

  self_parent_ids <- progeny_chr[
    (sire_chr == progeny_chr & sire_chr != "0") |
      (dam_chr == progeny_chr & dam_chr != "0")
  ]

  qc <- fast_pedigree_qc(progeny_chr, sire_chr, dam_chr) # nolint
  pb$update(60)

  errors <- list(
    duplicate_ids = qc$duplicate_ids,
    missing_sires = qc$missing_sires,
    missing_dams = qc$missing_dams,
    dual_role_ids = qc$dual_role_ids,
    self_parent_ids = unique(self_parent_ids),
    missing_progeny_ids = missing_progeny_ids
  )

  meta <- list(
    total = qc$total,
    founders = qc$founders,
    with_both_parents = qc$with_both_parents,
    only_sire = qc$only_sire,
    only_dam = qc$only_dam,
    self_parent_count = length(unique(self_parent_ids)),
    duplicate_count = length(qc$duplicate_ids),
    missing_sires_count = length(qc$missing_sires),
    missing_dams_count = length(qc$missing_dams),
    dual_role_count = length(qc$dual_role_ids),
    checked_sex = FALSE,
    checked_birthdate = FALSE,
    checked_loops = TRUE,
    missing_progeny_count = length(missing_progeny_ids)
  )

  if (!is.null(sex)) {
    qc_sex <- fast_pedigree_qc_sex(progeny_chr, sire_chr, dam_chr, sex) # nolint
    errors$sex_mismatch_sire_ids <- qc_sex$sex_mismatch_sire_ids
    errors$sex_mismatch_dam_ids <- qc_sex$sex_mismatch_dam_ids
    meta$sex_mismatch_sire_count <- qc_sex$sex_mismatch_sire_count
    meta$sex_mismatch_dam_count <- qc_sex$sex_mismatch_dam_count
    meta$checked_sex <- TRUE
  }
  pb$update(72)

  if (!is.null(birthdate)) {
    birth_res <- check_birth_date_order( # nolint
      progeny_chr,
      sire_chr,
      dam_chr,
      as.numeric(birthdate)
    )
    errors$birthdate_invalid_offspring_ids <- birth_res$invalid_offspring_ids
    errors$birthdate_invalid_sire_ids <- birth_res$invalid_sire_ids
    errors$birthdate_invalid_dam_ids <- birth_res$invalid_dam_ids
    meta$birthdate_invalid_count <- birth_res$count
    meta$checked_birthdate <- TRUE
  }
  pb$update(84)

  loops <- fast_detect_loops(progeny_chr, sire_chr, dam_chr) # nolint
  errors$loop_cycles <- loops$cycles
  meta$loop_count <- loops$count

  result <- list(meta = meta, errors = errors)
  pb$update(96)
  pb$finish()
  if (!quiet) print(result$meta)
  result
}
