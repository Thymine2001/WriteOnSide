# Benchmark: pedigreekit vs pedigreeTools, pedigree, nadiv
# Compares speed and inbreeding coefficient (F) results.
# All packages use the SAME pedigree: fixed by pedigreekit (fix_pedigree).
#
# Usage (from package root):
#   source("tests/bench_inbreeding.R")
# Or with limits:
#   N_MAX=5000 source("tests/bench_inbreeding.R")
#   PED_FILE=/path/to/ped.txt source("tests/bench_inbreeding.R")

# -----------------------------------------------------------------------------
# Install other packages if missing
# ------------------------------------------------------------------------------
for (pkg in c("pedigreeTools", "pedigree", "nadiv")) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message("Installing ", pkg, " ...")
    install.packages(pkg, repos = "https://cloud.r-project.org", quiet = TRUE)
  }
}

# -----------------------------------------------------------------------------
# Setup: load pedigreekit and load raw pedigree
# ------------------------------------------------------------------------------
if (!requireNamespace("pedigreekit", quietly = TRUE)) {
  if (file.exists("DESCRIPTION")) devtools::load_all(".") else stop("Run from pedigreekit root or install pedigreekit.")
}
library(pedigreekit)

PED_FILE <- Sys.getenv("PED_FILE", "tests/pedigree_data.txt")
N_MAX    <- as.integer(Sys.getenv("N_MAX", "0"))  # 0 = use all rows
SEP      <- " "

if (!file.exists(PED_FILE)) {
  message("Pedigree file not found, using small built-in example.")
  id_raw   <- c("1", "2", "3", "4", "5", "6")
  sire_raw <- c(NA, NA, "1", "1", "4", "5")
  dam_raw  <- c(NA, NA, "2", NA, "3", "2")
} else {
  message("Loading pedigree: ", PED_FILE)
  raw <- read.table(PED_FILE, header = TRUE, sep = SEP, stringsAsFactors = FALSE,
                    nrows = if (N_MAX > 0) N_MAX else -1)
  nm <- tolower(names(raw))
  if ("product_id" %in% nm) raw$id <- raw[[which(nm == "product_id")]]
  if (!"id" %in% names(raw)) raw$id <- raw[[1]]
  if (!"sire" %in% names(raw)) raw$sire <- raw[[2]]
  if (!"dam" %in% names(raw)) raw$dam <- raw[[3]]
  id_raw   <- as.character(raw$id)
  sire_raw <- as.character(raw$sire)
  dam_raw  <- as.character(raw$dam)
  sire_raw[sire_raw %in% c("0", "NA", "", " ")] <- NA_character_
  dam_raw[dam_raw %in% c("0", "NA", "", " ")]   <- NA_character_
}

# -----------------------------------------------------------------------------
# Fix pedigree with pedigreekit; all packages use this fixed pedigree
# ------------------------------------------------------------------------------
message("Fixing pedigree with pedigreekit::fix_pedigree() ...")
fixed <- pedigreekit::fix_pedigree(
  progeny = id_raw, sire = sire_raw, dam = dam_raw, quiet = TRUE
)
id   <- as.character(fixed$progeny)
sire <- as.character(fixed$sire)
dam  <- as.character(fixed$dam)
n    <- length(id)
message("N = ", n, " individuals (after fix)")

tm_pt <- tm_ped <- tm_nadiv <- c(elapsed = NA_real_)

# -----------------------------------------------------------------------------
# 1) pedigreekit (C++ only: fair comparison with other packages' core)
# ------------------------------------------------------------------------------
sire_0 <- replace(sire, is.na(sire), "0")
dam_0  <- replace(dam, is.na(dam), "0")
message("\n--- pedigreekit (C++ only) ---")
tm_pk_cpp <- system.time({
  F_vec <- pedigreekit:::fast_inbreeding_cpp(id, sire_0, dam_0)
})
F_pk <- setNames(as.numeric(F_vec), names(F_vec))
message("Time: ", round(tm_pk_cpp["elapsed"], 3), " s")

# -----------------------------------------------------------------------------
# 1b) pedigreekit (full R: fix logic + loop detection + C++)
# ------------------------------------------------------------------------------
message("\n--- pedigreekit (full R) ---")
tm_pk <- system.time({
  res_pk <- pedigreekit::calculate_inbreeding(
    progeny = id, sire = sire, dam = dam, quiet = TRUE
  )
})
message("Time: ", round(tm_pk["elapsed"], 3), " s")

# -----------------------------------------------------------------------------
# 2) pedigreeTools (needs pedigree object: sire, dam, label; NA for missing)
# Skips when duplicate ids or n > 50k: pedigreeTools has "factor level duplicated"
# error on large pedigrees (internal factor() handling). Use N_MAX=50000 or 30000
# to include pedigreeTools in the comparison.
# ------------------------------------------------------------------------------
if (requireNamespace("pedigreeTools", quietly = TRUE)) {
  message("\n--- pedigreeTools ---")
  pt_max_n <- 50000L  # pedigreeTools often fails with "factor level duplicated" above this
  skip_pt <- any(duplicated(id)) || n > pt_max_n
  if (skip_pt) {
    if (any(duplicated(id))) message("Skip: duplicate individual IDs.")
    else message("Skip: N > ", pt_max_n, " (pedigreeTools factor-level limit). Use N_MAX=", pt_max_n, " to compare.")
    F_pt <- NULL
    tm_pt <- c(elapsed = NA)
  } else {
  # pedigreeTools expects sire/dam to be values in label (id), not indices
  sire_pt <- sire
  dam_pt  <- dam
  sire_pt[!is.na(sire) & !(sire %in% id)] <- NA_character_
  dam_pt[!is.na(dam) & !(dam %in% id)]   <- NA_character_
  res_pt <- tryCatch({
    ped_pt <- pedigreeTools::pedigree(
      sire = as.character(sire_pt),
      dam = as.character(dam_pt),
      label = as.character(id)
    )
    tm_pt <- system.time(F_pt <- pedigreeTools::inbreeding(ped_pt))["elapsed"]
    names(F_pt) <- id
    list(F = F_pt, time = tm_pt)
  }, error = function(e) {
    message("pedigreeTools failed: ", conditionMessage(e))
    message("(Common with very large pedigrees; try smaller N_MAX.)")
    list(F = NULL, time = NA_real_)
  })
  F_pt <- res_pt$F
  tm_pt <- c(elapsed = res_pt$time)
  if (!is.null(F_pt)) {
    message("Time: ", round(tm_pt["elapsed"], 3), " s")
    ok <- !is.na(F_pk) & !is.na(F_pt)
    if (sum(ok) > 0) {
      message("Correlation with pedigreekit: ", round(cor(F_pk[ok], F_pt[ok]), 6))
      message("Max |diff|: ", max(abs(F_pk[ok] - F_pt[ok]), na.rm = TRUE))
    }
  }
  }
} else {
  message("\n--- pedigreeTools not installed, skip ---")
  F_pt <- NULL
  tm_pt <- c(elapsed = NA)
}

# -----------------------------------------------------------------------------
# 3) pedigree (CRAN): data.frame id, dam, sire; 0/NA missing; must be ordered
# ------------------------------------------------------------------------------
if (requireNamespace("pedigree", quietly = TRUE)) {
  message("\n--- pedigree ---")
  ped_df <- data.frame(
    id   = seq_len(n),
    dam  = match(dam, id, nomatch = 0),
    sire = match(sire, id, nomatch = 0)
  )
  ped_df$dam[ped_df$dam == 0]  <- NA_integer_
  ped_df$sire[ped_df$sire == 0] <- NA_integer_
  ord <- tryCatch(pedigree::orderPed(ped_df), error = function(e) NULL)
  if (!is.null(ord) && length(ord) == n) {
    ped_ord <- ped_df[order(ord), ]
    ped_ord$id <- seq_len(n)
    oo <- order(ord)
    ped_ord$sire <- match(sire[oo], id[oo], nomatch = NA_integer_)
    ped_ord$dam  <- match(dam[oo], id[oo], nomatch = NA_integer_)
    ped_ord$sire[is.na(ped_ord$sire)] <- NA_integer_
    ped_ord$dam[is.na(ped_ord$dam)]  <- NA_integer_
    tm_ped <- system.time({
      F_ped_raw <- pedigree::calcInbreeding(ped_ord)
    })
    F_ped <- numeric(n)
    F_ped[oo] <- F_ped_raw
    names(F_ped) <- id
    message("Time: ", round(tm_ped["elapsed"], 3), " s")
    ok <- !is.na(F_pk) & !is.na(F_ped)
    if (sum(ok) > 0) {
      message("Correlation with pedigreekit: ", round(cor(F_pk[ok], F_ped[ok]), 6))
      message("Max |diff|: ", max(abs(F_pk[ok] - F_ped[ok]), na.rm = TRUE))
    }
  } else {
    message("orderPed failed, skip pedigree package")
    F_ped <- NULL
    tm_ped <- c(elapsed = NA)
  }
} else {
  message("\n--- pedigree not installed, skip ---")
  F_ped <- NULL
  tm_ped <- c(elapsed = NA)
}

# -----------------------------------------------------------------------------
# 4) nadiv: numPed then makeA; F = diag(A) - 1 (memory-heavy for large n)
# ------------------------------------------------------------------------------
if (requireNamespace("nadiv", quietly = TRUE) && n <= 50000) {
  message("\n--- nadiv ---")
  # nadiv: columns ID, Dam, Sire; missing as 0, NA, or "*"
  ped_nadiv <- data.frame(
    id = id,
    dam = replace(dam, is.na(dam), "0"),
    sire = replace(sire, is.na(sire), "0")
  )
  nPed <- tryCatch(suppressWarnings(nadiv::numPed(ped_nadiv)), error = function(e) NULL)
  if (!is.null(nPed)) {
    tm_nadiv <- system.time({
      A <- nadiv::makeA(nPed)
    })
    F_nadiv <- diag(as.matrix(A)) - 1
    names(F_nadiv) <- id
    message("Time: ", round(tm_nadiv["elapsed"], 3), " s")
    ok <- !is.na(F_pk) & !is.na(F_nadiv)
    if (sum(ok) > 0) {
      message("Correlation with pedigreekit: ", round(cor(F_pk[ok], F_nadiv[ok]), 6))
      message("Max |diff|: ", max(abs(F_pk[ok] - F_nadiv[ok]), na.rm = TRUE))
    }
  } else {
    message("numPed failed, skip nadiv")
    F_nadiv <- NULL
    tm_nadiv <- c(elapsed = NA)
  }
} else {
  if (n > 50000) message("\n--- nadiv skipped (N > 50000, makeA too heavy) ---")
  else message("\n--- nadiv not installed, skip ---")
  F_nadiv <- NULL
  tm_nadiv <- c(elapsed = NA)
}

# -----------------------------------------------------------------------------
# Summary table (speed)
# ------------------------------------------------------------------------------
timings <- data.frame(
  package  = c("pedigreekit (C++ only)", "pedigreekit (full R)", "pedigreeTools", "pedigree", "nadiv"),
  time_sec = c(tm_pk_cpp["elapsed"], tm_pk["elapsed"], tm_pt["elapsed"], tm_ped["elapsed"], tm_nadiv["elapsed"])
)
timings <- timings[!is.na(timings$time_sec), ]
timings <- timings[order(timings$time_sec), ]
message("\n========== Speed summary (N = ", n, ") ==========")
print(timings)
message("\nNote: pedigreekit (full R) includes fix/loop/birthdate logic; (C++ only) is core vs core.")
message("Done.")
