check_pedigree_structure <- function(progeny = NULL,
                                     sire = NULL,
                                     dam = NULL,
                                     sex = NULL,
                                     birthdate = NULL,
                                     missing = c("0", "na", "NA", "", " "),
                                     quiet = FALSE,
                                     file = NULL,
                                     sep = " ",
                                     lap_max_depth = 20L,
                                     lap_sample_size = 10000L,
                                     descendant_max_depth = 10L,
                                     top_n = 10L,
                                     progress = NULL) {
  if (is.null(progress)) progress <- !quiet
  pb <- ped_progress_start(progress)
  on.exit(pb$finish(), add = TRUE)
  pb$update(2)
  ensure_pedigree_native_loaded()
  pb$update(8)

  progeny_missing <- missing(progeny)
  sire_missing <- missing(sire)
  dam_missing <- missing(dam)

  pick_column <- function(ped, selected, preferred, index) {
    if (!is.null(selected) && is.character(selected) && length(selected) == 1 && selected %in% names(ped)) {
      ped[[selected]]
    } else if (preferred %in% names(ped)) {
      ped[[preferred]]
    } else {
      ped[[index]]
    }
  }

  if (is.null(file) &&
      (progeny_missing || is.null(progeny)) &&
      (sire_missing || is.null(sire)) &&
      (dam_missing || is.null(dam))) {
    if (exists("ped", inherits = TRUE) && is.data.frame(get("ped", inherits = TRUE))) {
      progeny <- get("ped", inherits = TRUE)
      progeny_missing <- FALSE
    } else if (file.exists("ped.csv")) {
      file <- "ped.csv"
      if (identical(sep, " ")) sep <- ","
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
  } else if (is.character(progeny) &&
             length(progeny) == 1 &&
             sire_missing &&
             dam_missing &&
             file.exists(progeny)) {
    ped <- read.table(progeny, header = TRUE, sep = sep, stringsAsFactors = FALSE)
    progeny <- pick_column(ped, NULL, "progeny", 1)
    sire <- pick_column(ped, NULL, "sire", 2)
    dam <- pick_column(ped, NULL, "dam", 3)
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  } else if (is.data.frame(progeny) && sire_missing && dam_missing) {
    ped <- progeny
    if (all(c("progeny", "sire", "dam") %in% names(ped))) {
      progeny <- ped$progeny
      sire <- ped$sire
      dam <- ped$dam
    } else {
      progeny <- ped[[1]]
      sire <- ped[[2]]
      dam <- ped[[3]]
    }
    if (is.null(sex) && "sex" %in% names(ped)) sex <- ped$sex
    if (is.null(birthdate) && "birthdate" %in% names(ped)) birthdate <- ped$birthdate
  }
  pb$update(18)

  if (is.null(progeny) || is.null(sire) || is.null(dam)) {
    stop("progeny, sire, and dam are required. You can pass vectors/data.frame/file,\n",
         "or run from a directory containing ped.csv.")
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
  pb$update(25)

  lap_max_depth <- as.integer(lap_max_depth)
  lap_sample_size <- as.integer(lap_sample_size)
  descendant_max_depth <- as.integer(descendant_max_depth)
  top_n <- as.integer(top_n)
  if (!is.finite(lap_max_depth) || lap_max_depth <= 0L) {
    stop("lap_max_depth must be a positive integer.")
  }
  if (!is.finite(lap_sample_size) || lap_sample_size <= 0L) {
    stop("lap_sample_size must be a positive integer.")
  }
  if (!is.finite(descendant_max_depth) || descendant_max_depth <= 0L) {
    stop("descendant_max_depth must be a positive integer.")
  }
  if (!is.finite(top_n) || top_n <= 0L) {
    stop("top_n must be a positive integer.")
  }

  # Keep consistency with calculate_inbreeding(): fix pedigree first, then compute stats.
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
  pb$update(38)

  ids <- as.character(fixed$progeny)
  sires <- as.character(fixed$sire)
  dams <- as.character(fixed$dam)
  n <- length(ids)

  empty <- list(
    generated_at = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    input = list(file = file, sep = sep, rows = length(progeny)),
    pipeline = list(step_1 = "fix_pedigree", step_2 = "fast_structure_statistics"),
    basic_stats = list(),
    parent_stats = list(),
    founder_stats = list(),
    non_founder_stats = list(),
    full_sib_groups = list(),
    inbreeding = list(values = data.frame(id = character(0), inbreeding = numeric(0), stringsAsFactors = FALSE)),
    lap = list(depths = integer(0), distribution = integer(0)),
    descendants = list(),
    summary_stats = list(),
    loops = list(),
    fixed_pedigree = fixed
  )
  class(empty) <- "pedigree_structure"
  if (n == 0L) {
    pb$finish()
    if (!quiet) print(empty)
    return(empty)
  }

  is_known_parent <- function(x) {
    x_chr <- as.character(x)
    x_trim <- trimws(x_chr)
    !is.na(x_chr) & x_trim != "" & x_trim != "0" & toupper(x_trim) != "NA"
  }

  qc <- fast_pedigree_qc(ids, sires, dams)
  pb$update(48)
  loops <- fast_detect_loops(ids, sires, dams)
  pb$update(54)
  deepest <- fast_find_deepest_ancestor(ids, sires, dams, sample_size = min(200L, n))
  pb$update(60)

  lap_depths <- as.integer(fast_lap_depths(ids, sires, dams))
  lap_depths_non_na <- lap_depths[is.finite(lap_depths) & lap_depths >= 0L]
  if (length(lap_depths_non_na) > 0L) {
    lap_bins <- pmin(as.integer(lap_depths_non_na), lap_max_depth - 1L)
    lap_distribution <- tabulate(lap_bins + 1L, nbins = lap_max_depth)
  } else {
    lap_distribution <- integer(lap_max_depth)
  }
  names(lap_distribution) <- as.character(seq.int(0L, lap_max_depth - 1L))
  pb$update(68)

  sire_desc <- fast_descendant_summary(ids, sires, max_depth = descendant_max_depth)
  dam_desc <- fast_descendant_summary(ids, dams, max_depth = descendant_max_depth)
  pb$update(76)

  get_top_desc <- function(desc_res, n_top) {
    parents <- as.character(desc_res$parents)
    totals <- as.integer(desc_res$totals)
    if (length(parents) == 0L) {
      return(data.frame(parent = character(0), total_descendants = integer(0), stringsAsFactors = FALSE))
    }
    ord <- order(totals, decreasing = TRUE, na.last = TRUE)
    ord <- ord[seq_len(min(n_top, length(ord)))]
    data.frame(parent = parents[ord], total_descendants = totals[ord], stringsAsFactors = FALSE)
  }

  known_sire <- is_known_parent(sires)
  known_dam <- is_known_parent(dams)
  known_both <- known_sire & known_dam

  pair_key <- ifelse(known_both, paste(sires, dams, sep = "|"), NA_character_)
  pair_tab <- table(pair_key[!is.na(pair_key)])
  full_sib_sizes <- as.integer(pair_tab[pair_tab >= 2L])
  full_sib_group_count <- length(full_sib_sizes)
  full_sib_avg <- if (full_sib_group_count > 0L) mean(full_sib_sizes) else NA_real_
  full_sib_max <- if (full_sib_group_count > 0L) max(full_sib_sizes) else NA_integer_
  full_sib_min <- if (full_sib_group_count > 0L) min(full_sib_sizes) else NA_integer_

  F_vec <- fast_inbreeding_cpp(ids, sires, dams)
  pb$update(86)
  inb <- data.frame(
    id = names(F_vec),
    inbreeding = as.numeric(F_vec),
    stringsAsFactors = FALSE
  )
  inb_vals <- inb$inbreeding
  inb_vals <- inb_vals[is.finite(inb_vals)]

  n_eval <- length(inb_vals)
  n_inbred <- sum(inb_vals > 0, na.rm = TRUE)
  mean_all <- if (n_eval > 0L) mean(inb_vals) else NA_real_
  min_all <- if (n_eval > 0L) min(inb_vals) else NA_real_
  max_all <- if (n_eval > 0L) max(inb_vals) else NA_real_

  inbred_vals <- inb_vals[inb_vals > 0]
  mean_inbred <- if (length(inbred_vals) > 0L) mean(inbred_vals) else NA_real_

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
  f_pos <- inb_vals[inb_vals > 0]
  f_cut <- cut(f_pos, breaks = breaks, labels = labels, include.lowest = FALSE)
  f_table <- table(f_cut)
  dist_counts <- c(`F = 0` = as.integer(f_zero))
  for (lb in labels) {
    dist_counts[lb] <- if (lb %in% names(f_table)) as.integer(f_table[[lb]]) else 0L
  }
  pb$update(92)

  non_founders <- qc$total - qc$founders
  deepest_id <- if (length(deepest$id) > 0L) as.character(deepest$id) else NA_character_
  if (length(deepest_id) == 0L) deepest_id <- NA_character_
  lap_mean <- if (length(lap_depths_non_na) > 0L) mean(lap_depths_non_na) else NA_real_

  out <- list(
    generated_at = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    input = list(file = file, sep = sep, rows = length(progeny)),
    pipeline = list(step_1 = "fix_pedigree", step_2 = "fast_structure_statistics"),
    basic_stats = list(
      individuals_total = qc$total,
      founders = qc$founders,
      non_founders = non_founders,
      with_both_parents = qc$with_both_parents,
      only_known_sire = qc$only_sire,
      only_known_dam = qc$only_dam
    ),
    parent_stats = list(
      sires_total = qc$unique_sires,
      sire_progeny = qc$total_sire_progeny,
      dams_total = qc$unique_dams,
      dam_progeny = qc$total_dam_progeny,
      individuals_with_progeny = qc$individuals_with_progeny,
      individuals_without_progeny = qc$individuals_without_progeny
    ),
    founder_stats = list(
      founders = qc$founders,
      progeny = qc$founder_total_progeny,
      sires = qc$founder_sires,
      sire_progeny = qc$founder_sire_progeny,
      dams = qc$founder_dams,
      dam_progeny = qc$founder_dam_progeny,
      with_no_progeny = qc$founder_no_progeny
    ),
    non_founder_stats = list(
      non_founders = non_founders,
      sires = qc$non_founder_sires,
      sire_progeny = qc$non_founder_sire_progeny,
      dams = qc$non_founder_dams,
      dam_progeny = qc$non_founder_dam_progeny,
      only_known_sire = qc$only_sire,
      only_known_dam = qc$only_dam,
      with_known_sire_and_dam = qc$with_both_parents
    ),
    full_sib_groups = list(
      groups = full_sib_group_count,
      average_family_size = full_sib_avg,
      max_family_size = full_sib_max,
      min_family_size = full_sib_min,
      family_sizes = full_sib_sizes
    ),
    inbreeding = list(
      evaluated_individuals = n_eval,
      inbreds_total = n_inbred,
      inbreds_in_evaluated = n_inbred,
      distribution = dist_counts,
      mean_all = mean_all,
      mean_inbreds = mean_inbred,
      max = max_all,
      min = min_all,
      values = inb
    ),
    summary_stats = list(
      A_number_of_individuals = qc$total,
      B_number_of_inbreds = n_inbred,
      C_number_of_founders = qc$founders,
      D_number_with_both_known_parents = qc$with_both_parents,
      E_number_with_no_progeny = qc$individuals_without_progeny,
      G_average_inbreeding_coefficients = mean_all,
      H_average_inbreeding_in_inbreds = mean_inbred,
      I_max_inbreeding = max_all,
      J_min_inbreeding = min_all
    ),
    lap = list(
      distribution = lap_distribution,
      mean_generation_depth = lap_mean,
      deepest_sampled_individual = deepest_id,
      deepest_sampled_depth = as.integer(deepest$depth),
      depths = lap_depths,
      max_depth = lap_max_depth,
      sample_size = lap_sample_size
    ),
    descendants = list(
      sire = sire_desc,
      dam = dam_desc,
      top_sire = get_top_desc(sire_desc, top_n),
      top_dam = get_top_desc(dam_desc, top_n)
    ),
    loops = loops$cycles,
    fixed_pedigree = fixed
  )
  class(out) <- "pedigree_structure"
  pb$update(97)
  pb$finish()

  if (!quiet) print(out)
  out
}

print.pedigree_structure <- function(x, ...) {
  fmt_int <- function(v) format(as.integer(v), big.mark = ",", scientific = FALSE, trim = TRUE)
  fmt_num <- function(v, digits = 6L) format(round(as.numeric(v), digits), trim = TRUE, nsmall = digits)

  cat("========================================\n")
  cat("PEDIGREE STRUCTURE REPORT\n")
  cat("Generated:", x$generated_at, "\n")
  cat("========================================\n\n")

  cat("--- BASIC STATISTICS ---\n")
  cat("Individuals in total:", fmt_int(x$basic_stats$individuals_total), "\n")
  cat("Founders:", fmt_int(x$basic_stats$founders), "\n")
  cat("Non-founders:", fmt_int(x$basic_stats$non_founders), "\n")
  cat("With both parents:", fmt_int(x$basic_stats$with_both_parents), "\n")
  cat("Only with known sire:", fmt_int(x$basic_stats$only_known_sire), "\n")
  cat("Only with known dam:", fmt_int(x$basic_stats$only_known_dam), "\n\n")

  cat("--- PARENT STATISTICS ---\n")
  cat("Sires in total:", fmt_int(x$parent_stats$sires_total), "\n")
  cat("   -Progeny:", fmt_int(x$parent_stats$sire_progeny), "\n")
  cat("Dams in total:", fmt_int(x$parent_stats$dams_total), "\n")
  cat("   -Progeny:", fmt_int(x$parent_stats$dam_progeny), "\n")
  cat("Individuals with progeny:", fmt_int(x$parent_stats$individuals_with_progeny), "\n")
  cat("Individuals with no progeny:", fmt_int(x$parent_stats$individuals_without_progeny), "\n\n")

  cat("--- FOUNDER STATISTICS ---\n")
  cat("Founders:", fmt_int(x$founder_stats$founders), "\n")
  cat("   -Progeny:", fmt_int(x$founder_stats$progeny), "\n")
  cat("   -Sires:", fmt_int(x$founder_stats$sires), "\n")
  cat("       -Progeny:", fmt_int(x$founder_stats$sire_progeny), "\n")
  cat("   -Dams:", fmt_int(x$founder_stats$dams), "\n")
  cat("       -Progeny:", fmt_int(x$founder_stats$dam_progeny), "\n")
  cat("   -With no progeny:", fmt_int(x$founder_stats$with_no_progeny), "\n\n")

  cat("--- NON-FOUNDER STATISTICS ---\n")
  cat("Non-founders:", fmt_int(x$non_founder_stats$non_founders), "\n")
  cat("   -Sires:", fmt_int(x$non_founder_stats$sires), "\n")
  cat("       -Progeny:", fmt_int(x$non_founder_stats$sire_progeny), "\n")
  cat("   -Dams:", fmt_int(x$non_founder_stats$dams), "\n")
  cat("       -Progeny:", fmt_int(x$non_founder_stats$dam_progeny), "\n")
  cat("   -Only with known sire:", fmt_int(x$non_founder_stats$only_known_sire), "\n")
  cat("   -Only with known dam:", fmt_int(x$non_founder_stats$only_known_dam), "\n")
  cat("   -With known sire and dam:", fmt_int(x$non_founder_stats$with_known_sire_and_dam), "\n\n")

  cat("--- FULL-SIB GROUPS ---\n")
  cat("Full-sib groups:", fmt_int(x$full_sib_groups$groups), "\n")
  cat("   -Average family size:", fmt_num(x$full_sib_groups$average_family_size, digits = 3L), "\n")
  cat("       -Maximum:", fmt_int(x$full_sib_groups$max_family_size), "\n")
  cat("       -Minimum:", fmt_int(x$full_sib_groups$min_family_size), "\n\n")

  cat("--- INBREEDING STATISTICS ---\n")
  cat("Evaluated individuals:", fmt_int(x$inbreeding$evaluated_individuals), "\n")
  cat("Inbreds in total:", fmt_int(x$inbreeding$inbreds_total), "\n")
  cat("Inbreds in evaluated:", fmt_int(x$inbreeding$inbreds_in_evaluated), "\n\n")
  cat("Distribution of inbreeding coefficients\n")
  cat("-----------------------------------------------------------\n")
  dist_names <- names(x$inbreeding$distribution)
  dist_vals <- as.integer(x$inbreeding$distribution)
  for (i in seq_along(dist_names)) {
    cat(sprintf("%30s %20s\n", dist_names[i], format(dist_vals[i], big.mark = ",")))
  }
  cat("-----------------------------------------------------------\n\n")

  cat("--- SUMMARY STATISTICS ---\n")
  cat("A: Number of individuals:", fmt_int(x$summary_stats$A_number_of_individuals), "\n")
  cat("B: Number of inbreds:", fmt_int(x$summary_stats$B_number_of_inbreds), "\n")
  cat("C: Number of founders:", fmt_int(x$summary_stats$C_number_of_founders), "\n")
  cat("D: Number of individuals with both known parents:", fmt_int(x$summary_stats$D_number_with_both_known_parents), "\n")
  cat("E: Number of individuals with no progeny:", fmt_int(x$summary_stats$E_number_with_no_progeny), "\n\n")
  cat("G: Average inbreeding coefficients:", fmt_num(x$summary_stats$G_average_inbreeding_coefficients, digits = 8L), "\n")
  cat("H: Average inbreeding coefficients in the inbreds:", fmt_num(x$summary_stats$H_average_inbreeding_in_inbreds, digits = 8L), "\n")
  cat("I: Maximum of inbreeding coefficients:", fmt_num(x$summary_stats$I_max_inbreeding, digits = 7L), "\n")
  cat("J: Minimum of inbreeding coefficients:", fmt_num(x$summary_stats$J_min_inbreeding, digits = 7L), "\n\n")

  cat("--- LONGEST ANCESTRAL PATH (LAP) ---\n")
  lap_vals <- as.integer(x$lap$distribution)
  lap_names <- names(x$lap$distribution)
  nz <- which(lap_vals > 0L)
  if (length(nz) == 0L) {
    cat(sprintf("%20s %20s\n", "0", "0"))
  } else {
    for (i in nz) {
      cat(sprintf("%20s %20s\n", lap_names[i], format(lap_vals[i], big.mark = ",")))
    }
  }
  cat("\nMean generation depth:", format(round(as.numeric(x$lap$mean_generation_depth), 3L), nsmall = 3L), "\n")

  invisible(x)
}
