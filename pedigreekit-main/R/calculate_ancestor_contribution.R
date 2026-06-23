calculate_ancestor_contribution <- function(progeny = NULL,
                                            sire = NULL,
                                            dam = NULL,
                                            sex = NULL,
                                            birthdate = NULL,
                                            missing = c("0", "na", "NA", "", " "),
                                            quiet = FALSE,
                                            file = NULL,
                                            sep = " ",
                                            top_k = 5,
                                            max_depth = 6,
                                            # 999 = full population (safe cap: top_k=100, max_depth=30)
                                            format = c("ratio", "matrix"),
                                            target_animal = NULL,
                                            matrix_block_size = 2000L,
                                            progress = NULL) {
  if (is.null(progress)) progress <- !quiet
  pb <- ped_progress_start(progress)
  on.exit(pb$finish(), add = TRUE)
  pb$update(3)
  ensure_pedigree_native_loaded()
  pb$update(10)

  format <- match.arg(format)

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
  pb$update(22)

  if (missing(progeny) || is.null(progeny) ||
      missing(sire) || is.null(sire) ||
      missing(dam) || is.null(dam)) {
    stop("progeny, sire, and dam are required.")
  }
  if (length(progeny) != length(sire) || length(progeny) != length(dam)) {
    stop("Length mismatch: progeny, sire, and dam must have same length.")
  }
  pb$update(30)

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
  pb$update(45)

  ids <- as.character(fixed$progeny)
  sires <- as.character(fixed$sire)
  dams <- as.character(fixed$dam)
  F_vec <- fast_inbreeding_cpp(ids, sires, dams) # nolint
  pb$update(55)

  # User-defined missing values (same as fix_pedigree 'missing')
  miss <- missing

  # Pedigree depth: max generations from any individual to founder
  pedigree_depth <- function() {
    n <- length(ids)
    sire_idx <- match(sires, ids)
    dam_idx <- match(dams, ids)
    sire_idx[is.na(sires) | sires %in% miss] <- NA_integer_
    dam_idx[is.na(dams) | dams %in% miss] <- NA_integer_
    depth <- integer(n)
    repeat {
      changed <- FALSE
      for (i in seq_len(n)) {
        s <- sire_idx[i]
        d <- dam_idx[i]
        if (is.na(s) && is.na(d)) next
        new_d <- 1L + max(
          if (is.na(s)) 0L else depth[s],
          if (is.na(d)) 0L else depth[d]
        )
        if (new_d > depth[i]) {
          depth[i] <- new_d
          changed <- TRUE
        }
      }
      if (!changed) break
    }
    max(depth, 0L, na.rm = TRUE)
  }

  # 999 = full population: max_depth from pedigree depth (cap 30), top_k safe cap 100
  max_depth_cap <- 30L
  top_k_cap <- 100L
  top_k_use <- if (is.numeric(top_k) && length(top_k) == 1L && top_k == 999L) {
    top_k_cap
  } else {
    min(as.integer(top_k), top_k_cap)
  }
  max_depth_use <- if (is.numeric(max_depth) && length(max_depth) == 1L && max_depth == 999L) {
    min(pedigree_depth(), max_depth_cap)
  } else {
    min(as.integer(max_depth), max_depth_cap)
  }
  pb$update(62)
  if (!quiet) {
    tk <- is.numeric(top_k) && length(top_k) == 1L
    md <- is.numeric(max_depth) && length(max_depth) == 1L
    if ((tk && top_k != 999L && top_k > top_k_cap) || (md && max_depth != 999L && max_depth > max_depth_cap)) {
      warning("top_k / max_depth capped at ", top_k_cap, " / ", max_depth_cap,
              " for stability. Use 999 for full-population safe limits.")
    }
  }

  out <- fast_ancestor_contribution_bulk_cpp( # nolint
    ids, sires, dams,
    as.numeric(F_vec),
    top_k = top_k_use,
    max_depth = max_depth_use,
    return_ratio = (format == "ratio")
  )
  pb$update(72)
  out <- as.data.frame(out, stringsAsFactors = FALSE)

  show_empty_target_msg <- FALSE
  if (format == "ratio") {
    out <- out[!is.na(out$anc_1), , drop = FALSE]
    if (!is.null(target_animal)) {
      target_animal <- as.character(target_animal)
      out <- out[out$id %in% target_animal, , drop = FALSE]
      show_empty_target_msg <- (nrow(out) == 0L && !quiet)
    }
    anc_id_cols <- names(out)[grepl("^anc_[0-9]+$", names(out))]
    if (length(anc_id_cols) > 0L) {
      anc_nums <- as.integer(sub("^anc_", "", anc_id_cols))
      anc_id_cols <- anc_id_cols[order(anc_nums)]
      used <- which(vapply(anc_id_cols, function(col) any(!is.na(out[[col]])), logical(1L)))
      max_anc <- if (length(used) == 0L) 0L else max(anc_nums[used])
      if (max_anc >= 1L) {
        keep <- c("id", as.vector(rbind(
          paste0("anc_", seq_len(max_anc)),
          paste0("anc_", seq_len(max_anc), "_contribution")
        )))
        out <- out[, keep[keep %in% names(out)], drop = FALSE]
      }
    }
    pb$update(92)
  } else {
    if (!requireNamespace("Matrix", quietly = TRUE)) {
      stop("Package 'Matrix' is required for format = 'matrix'. Please install it.")
    }

    n <- length(ids)
    id_vec <- ids

    if (is.null(matrix_block_size) || !is.finite(matrix_block_size) || matrix_block_size <= 0) {
      matrix_block_size <- 2000L
    }
    matrix_block_size <- as.integer(matrix_block_size)

    if (!is.null(target_animal)) {
      target_animal <- as.character(target_animal)
      target_indices_all <- match(target_animal, id_vec)
      target_indices_all <- target_indices_all[!is.na(target_indices_all)]
    } else {
      target_indices_all <- seq_len(n)
    }

    all_i <- integer(0)
    all_j <- integer(0)
    all_x <- numeric(0)

    if (length(target_indices_all) > 0L) {
      n_blocks <- ceiling(length(target_indices_all) / matrix_block_size)
      block_id <- 0L
      for (start in seq(1L, length(target_indices_all), by = matrix_block_size)) {
        block_id <- block_id + 1L
        end <- min(length(target_indices_all), start + matrix_block_size - 1L)
        block_idx <- target_indices_all[start:end]

        trip <- fast_ancestor_contribution_triplet_cpp(
          ids = ids,
          sires = sires,
          dams = dams,
          F = as.numeric(F_vec),
          target_indices = block_idx,
          top_k = top_k_use,
          max_depth = max_depth_use,
          return_ratio = FALSE
        )

        if (length(trip$i) > 0L) {
          all_i <- c(all_i, as.integer(trip$i))
          all_j <- c(all_j, as.integer(trip$j))
          all_x <- c(all_x, as.numeric(trip$x))
        }
        pb$update(72 + (20 * block_id / n_blocks))
      }
    }

    mat <- Matrix::sparseMatrix(
      i = all_i,
      j = all_j,
      x = all_x,
      dims = c(n, n),
      dimnames = list(id_vec, id_vec),
      repr = "C"
    )

    show_empty_matrix_target_msg <- FALSE
    if (!is.null(target_animal)) {
      mat <- mat[, target_indices_all, drop = FALSE]
      show_empty_matrix_target_msg <- (ncol(mat) == 0L && !quiet)
    }
    pb$update(95)
    pb$finish()
    if (show_empty_matrix_target_msg) {
      message("No columns for target_animal in matrix output; check whether target IDs exist in pedigree.")
    }
    return(mat)
  }

  pb$finish()
  if (show_empty_target_msg) {
    message("No rows for target_animal: ancestor contribution only includes inbred individuals (F > 0). ",
            "Specified target(s) may have F = 0 or be absent from the pedigree.")
  }
  if (!quiet) {
    has_both <- (sires != "0" & sires != "" & !is.na(sires)) &
      (dams != "0" & dams != "" & !is.na(dams))
    F_numeric <- as.numeric(F_vec)
    n_inbred <- sum(has_both & (F_numeric > 0) & is.finite(F_numeric))
    message("Ancestor contribution (OpenMP): computed for ", n_inbred, " inbred individuals (F > 0); ",
            "top ", top_k, " ancestors per individual (max_depth = ", max_depth, ").")
  }

  out
}
