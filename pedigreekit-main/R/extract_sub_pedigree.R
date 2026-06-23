extract_sub_pedigree <- function(progeny = NULL,
                                 sire = NULL,
                                 dam = NULL,
                                 target = NULL,
                                 target_column = NULL,
                                 generation = "All",
                                 siblings = "None",
                                 sublings = NULL,
                                 missing = c("0", "na", "NA", "", " "),
                                 file = NULL,
                                 sep = " ") {
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

  ped_source <- NULL
  if (!is.null(file)) {
    if (!is.character(file) || length(file) != 1) {
      stop("file must be a single file path.")
    }
    ped_source <- read.table(file, header = TRUE, sep = sep, stringsAsFactors = FALSE)
    progeny <- pick_column(ped_source, progeny, "progeny", 1)
    sire <- pick_column(ped_source, sire, "sire", 2)
    dam <- pick_column(ped_source, dam, "dam", 3)
  } else if (is.character(progeny) && length(progeny) == 1 &&
             missing(sire) && missing(dam) && file.exists(progeny)) {
    ped_source <- read.table(progeny, header = TRUE, sep = sep, stringsAsFactors = FALSE)
    progeny <- pick_column(ped_source, NULL, "progeny", 1)
    sire <- pick_column(ped_source, NULL, "sire", 2)
    dam <- pick_column(ped_source, NULL, "dam", 3)
  } else if (is.data.frame(progeny) && missing(sire) && missing(dam)) {
    ped_source <- progeny
    if (!all(c("progeny", "sire", "dam") %in% names(ped_source))) {
      progeny <- ped_source[[1]]
      sire <- ped_source[[2]]
      dam <- ped_source[[3]]
    } else {
      progeny <- ped_source$progeny
      sire <- ped_source$sire
      dam <- ped_source$dam
    }
  }

  if (missing(progeny) || is.null(progeny) ||
      missing(sire) || is.null(sire) ||
      missing(dam) || is.null(dam)) {
    stop("progeny, sire, and dam are required.")
  }

  if (length(progeny) != length(sire) || length(progeny) != length(dam)) {
    stop("Length mismatch: progeny, sire, and dam must have same length.")
  }

  all_generation <- is.character(generation) &&
    length(generation) == 1 &&
    !is.na(generation) &&
    tolower(trimws(generation)) == "all"

  if (!all_generation &&
      (!is.numeric(generation) || length(generation) != 1 || is.na(generation) ||
       generation < 0)) {
    stop("generation must be a single non-negative number or 'All'.")
  }

  if (!is.null(sublings)) {
    siblings <- sublings
  }

  if (is.logical(siblings)) {
    if (length(siblings) != 1 || is.na(siblings)) {
      stop("siblings must be a single logical value or one of: 'None', 'Full', 'Half', 'All'.")
    }
    siblings <- if (siblings) "All" else "None"
  }

  if (!is.character(siblings) || length(siblings) != 1 || is.na(siblings)) {
    stop("siblings must be one of: 'None', 'Full', 'Half', 'All'.")
  }

  siblings_mode <- tolower(trimws(siblings))
  if (!(siblings_mode %in% c("none", "full", "half", "all"))) {
    stop("siblings must be one of: 'None', 'Full', 'Half', 'All'.")
  }

  if (is.null(target)) {
    if (is.null(target_column)) {
      stop("Please provide target IDs using `target`, or provide `target_column`.")
    }
    if (is.null(ped_source)) {
      stop("target_column can only be used with `file` input or data.frame input.")
    }
    if (!is.character(target_column) || length(target_column) != 1 ||
        !(target_column %in% names(ped_source))) {
      stop("target_column must be one existing column name in the pedigree data.")
    }
    target <- ped_source[[target_column]]
  } else if (!is.null(ped_source) &&
             is.character(target) &&
             length(target) == 1 &&
             target %in% names(ped_source)) {
    target <- ped_source[[target]]
  }

  target <- as.character(target)
  target <- trimws(target)
  missing_low <- unique(tolower(trimws(as.character(missing))))
  target <- unique(target[!(is.na(target) | target == "" | tolower(target) %in% missing_low)])
  if (length(target) == 0L) {
    stop("No valid target IDs were found.")
  }

  ped_fixed <- fix_pedigree(
    progeny = as.character(progeny),
    sire = as.character(sire),
    dam = as.character(dam),
    missing = missing,
    quiet = TRUE,
    progress = FALSE
  )

  ids <- as.character(ped_fixed$progeny)

  target_existing <- target[target %in% ids]
  if (length(target_existing) == 0L) {
    stop("None of the target IDs are present in the pedigree.")
  }

  extract_targets <- target_existing

  if (siblings_mode != "none") {
    is_missing_parent <- function(x) {
      x <- trimws(as.character(x))
      is.na(x) | x == "" | tolower(x) %in% missing_low
    }

    sire_chr <- as.character(ped_fixed$sire)
    dam_chr <- as.character(ped_fixed$dam)

    valid_sire <- !is_missing_parent(sire_chr)
    valid_dam <- !is_missing_parent(dam_chr)
    valid_both <- valid_sire & valid_dam

    idx_target <- match(target_existing, ids)
    idx_target <- idx_target[!is.na(idx_target)]

    target_sire <- sire_chr[idx_target]
    target_dam <- dam_chr[idx_target]

    target_sire <- unique(target_sire[!is_missing_parent(target_sire)])
    target_dam <- unique(target_dam[!is_missing_parent(target_dam)])

    share_sire <- if (length(target_sire) > 0L) {
      valid_sire & sire_chr %in% target_sire
    } else {
      rep(FALSE, length(ids))
    }
    share_dam <- if (length(target_dam) > 0L) {
      valid_dam & dam_chr %in% target_dam
    } else {
      rep(FALSE, length(ids))
    }

    target_pair_key <- character(0)
    if (length(idx_target) > 0L) {
      target_valid_both <- valid_both[idx_target]
      if (any(target_valid_both)) {
        target_pair_key <- unique(paste(
          sire_chr[idx_target][target_valid_both],
          dam_chr[idx_target][target_valid_both],
          sep = "\r"
        ))
      }
    }

    is_full <- if (length(target_pair_key) > 0L) {
      valid_both & paste(sire_chr, dam_chr, sep = "\r") %in% target_pair_key
    } else {
      rep(FALSE, length(ids))
    }

    sibling_ids <- switch(
      siblings_mode,
      "all" = ids[share_sire | share_dam],
      "full" = ids[is_full],
      "half" = ids[(share_sire | share_dam) & !is_full],
      character(0)
    )

    if (length(sibling_ids) > 0L) {
      extract_targets <- unique(c(extract_targets, sibling_ids))
    }
  }

  max_depth <- if (all_generation) -1L else as.integer(generation)

  keep <- fast_extract_sub_pedigree_cpp(
    ids = ids,
    sires = as.character(ped_fixed$sire),
    dams = as.character(ped_fixed$dam),
    target_ids = extract_targets,
    max_depth = max_depth,
    missing = as.character(missing)
  )

  sub_pedigree <- ped_fixed[keep, , drop = FALSE]
  rownames(sub_pedigree) <- NULL
  sub_pedigree
}
