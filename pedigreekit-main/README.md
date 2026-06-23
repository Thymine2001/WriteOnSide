## pedigreekit

`pedigreekit` is an R package for fast analysis of large pedigree data, providing:

- **Pedigree quality control**: duplicate IDs, missing parents, self-parenting, sex mismatch, birth-date order issues, loops
- **Pedigree fixing**: normalize missing values, drop problematic rows, add missing founder records, break loops
- **Inbreeding coefficients**: efficient C++ implementation of individual \(F\)
- **Ancestor contribution**: contribution of ancestors to individual inbreeding (wide table or sparse matrix)
- **Pedigree structure analysis**: LAP (longest ancestral path), descendants, full-sib family sizes, etc.
- **Sub pedigree extraction**: extract ancestors directly related to one or more targets with configurable tracing generations

All core computations are implemented in C++ and exposed via Rcpp, and are suitable for large pedigrees (tens of thousands of individuals or more).

---

## Installation

### From GitHub (recommended)

```r
install.packages("remotes")      # if not yet installed
remotes::install_github("Thymine2001/pedigreekit")

library(pedigreekit)
```

### From a local source checkout

If you have cloned the repository locally (for example `C:/Developing/pedigreekit`):

```r
install.packages("remotes")
remotes::install_local("C:/Developing/pedigreekit")

library(pedigreekit)
```

For development and debugging you can use:

```r
devtools::load_all("C:/Developing/pedigreekit")
```

---

## Input formats

`pedigreekit` supports three common ways to provide pedigree data:

- **Three vectors**: `progeny`, `sire`, `dam`
- **A `data.frame`**: containing `progeny/sire/dam` columns, or having these three columns as the first 3 columns
- **A file path**: passed to the `file` argument, or directly as `progeny = "path/to/file"`; when column names are not specified, the first 3 columns are used as progeny/sire/dam.

By default the following values are treated as missing: `c("0", "na", "NA", "", " ")`. You can override this with the `missing =` argument.

Example (data.frame):

```r
ped <- data.frame(
  progeny = c("D1", "D2", "D3"),
  sire    = c("S1", "S1", "0"),
  dam     = c("M1", "M2", "M1"),
  stringsAsFactors = FALSE
)
```

Example (file, first 3 columns are individual / parents):

```r
ped <- data.frame(
  ID    = c("D1", "D2", "D3"),
  DadID = c("S1", "S1", "0"),
  MaID  = c("M1", "M2", "M1")
)
write.table(ped, "ped.txt", row.names = FALSE, quote = FALSE)
```

---

## Core functions and examples

### 1. `check_pedigree()`: basic QC

**What it reports (without modifying your data):**

- Duplicate IDs
- Missing sires / dams
- Individuals used as their own parents
- Parents that appear both as sire and dam (“dual-role”)
- Sex mismatches (if `sex` is provided)
- Birth-date order issues (if `birthdate` is provided)
- Pedigree loops

**Example:**

```r
qc <- check_pedigree(
  file = "ped.txt",
  sep  = " ",
  quiet = FALSE
)

str(qc$meta)    # summary counts
str(qc$errors)  # lists of IDs with issues
```

You can also pass a `data.frame` or three vectors; the interface mirrors `fix_pedigree()`.

---
### 2. `fix_pedigree()`: clean and fix a pedigree

**What it does**: normalizes missing values, removes rows with missing/duplicate IDs, fixes self-parenting and loops, adds missing parents as founders, optionally fixes sex and birth-date issues.

**Typical usage:**

```r
library(pedigreekit)

# 1) Pass vectors explicitly
ped_fixed <- fix_pedigree(
  progeny = ped$ID,
  sire    = ped$DadID,
  dam     = ped$MaID
)

# 2) From a file (ID / DadID / MaID as the first 3 columns)
ped_fixed2 <- fix_pedigree(
  file = "ped.txt",
  sep  = " "
)

head(ped_fixed)
```

This returns a data.frame with `progeny/sire/dam` (and optionally `sex/birthdate`), and prints a short “fix log” to the console.

---
### 3. `calculate_inbreeding()`: inbreeding coefficient \(F\)

**What it does**: automatically calls `fix_pedigree()` to clean the pedigree, then uses a C++ algorithm to compute each individual’s inbreeding coefficient \(F\). It can print summary statistics and the distribution of inbreeding.

**Example:**

```r
inb <- calculate_inbreeding(
  file = "ped.txt",
  sep  = " ",
  quiet = TRUE          # return only the data.frame, no console summary
)

head(inb)
#   id inbreeding
#  D1 0.00
#  D2 0.25

# Enable console summary
calculate_inbreeding("ped.txt", sep = " ", quiet = FALSE)
```

The function returns a data.frame with `id` and `inbreeding` columns.

---

### 4. `calculate_ancestor_contribution()`: ancestor contributions

**What it does**: after fixing the pedigree and computing inbreeding, it evaluates how much each ancestor contributes to an individual’s inbreeding:

- `format = "ratio"` (default): returns a wide data.frame with `id + anc_k + anc_k_contribution`
- `format = "matrix"`: returns a `Matrix::sparseMatrix`

**Basic usage (ratio table):**

```r
CF <- calculate_ancestor_contribution(
  file = "ped.txt",
  sep  = " ",
  top_k = 5,          # keep the top 5 ancestors per individual
  max_depth = 6,      # maximum number of generations traced back
  format = "ratio",
  quiet = TRUE
)

head(CF)
```

**Matrix form:**

```r
CF_mat <- calculate_ancestor_contribution(
  file = "ped.txt",
  sep  = " ",
  top_k = 999,        # 999 = use a safe cap (up to 100)
  max_depth = 999,    # 999 = use pedigree depth with a safe cap (up to 30)
  format = "matrix",
  quiet = TRUE
)

CF_mat[1:5, 1:5]      # inspect the first 5×5 block
```

You can use `target_animal = c("D1","D2")` to restrict the output to specific individuals (columns).

---

### 5. `check_pedigree_structure()`: structural statistics and report

**What it does**: calls `fix_pedigree()` and then computes:

- Number of individuals, founders, and non-founders
- Number of individuals with/without known parents
- Parent roles and progeny counts (sires/dams)
- Founder vs non-founder parent structures
- Full-sib family counts and size distribution
- Inbreeding distribution and summary statistics
- LAP (longest ancestral path) distribution and mean depth
- Descendant distributions for each parent (sire/dam)

**Example:**

```r
report <- check_pedigree_structure(
  file = "ped.txt",
  sep  = " ",
  lap_max_depth       = 20,
  descendant_max_depth = 10,
  top_n               = 10,
  quiet = FALSE       # print a human-readable report
)

# You can continue to use the structured results programmatically:
str(report$basic_stats)
str(report$inbreeding$values)     # similar to calculate_inbreeding output
```

The print method `print.pedigree_structure()` is registered, so simply typing `report` will display a formatted textual report.

---

### 6. `extract_sub_pedigree()`: extract target-related ancestors

**What it does**: traces direct ancestral links from one or multiple targets and returns only the related records as a sub pedigree.

**Key arguments:**

- `target` supports:
  - single ID, e.g. `"D1"`
  - ID vector, e.g. `c("D1", "D2")`
  - column vector, e.g. `target <- col$id`
  - column name in pedigree data, e.g. `target = "id"`
- `generation` supports:
  - numeric depth (e.g. `1`, `2`, `3`)
  - `"All"` for full-depth tracing
- `siblings` supports:
  - `"None"` (default): do not expand sibling targets
  - `"Full"`: include full siblings (same sire and same dam)
  - `"Half"`: include half siblings (share sire or dam, but not both as a target pair)
  - `"All"`: include both full and half siblings

**Example (single target):**

```r
sub_1 <- extract_sub_pedigree(
  progeny = ped,
  target = "D1",
  generation = 2
)

sub_1
```

**Example (vector target, including `target <- col$id`):**

```r
col <- data.frame(id = c("D1", "D2"), stringsAsFactors = FALSE)
target <- col$id

sub_all <- extract_sub_pedigree(
  progeny = ped,
  target = target,
  generation = "All",
  siblings = "All"
)

sub_all
```

**Example (target as column name):**

```r
ped2 <- data.frame(
  id = c("D1", "D2", "D3"),
  sire = c("S1", "S1", "0"),
  dam = c("M1", "M2", "M1"),
  stringsAsFactors = FALSE
)

sub_col <- extract_sub_pedigree(
  progeny = ped2,
  target = "id",
  generation = "All"
)

sub_col
```

Core tracing in `extract_sub_pedigree()` is accelerated with **Rcpp**.

---

If you run into performance or result questions on your data, you may can start by running:

```r
check_pedigree("ped.txt", sep = " ")
check_pedigree_structure("ped.txt", sep = " ")
extract_sub_pedigree("ped.txt", target = c("D1", "D2"), generation = "All")
```
