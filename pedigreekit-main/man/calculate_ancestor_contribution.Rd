\name{calculate_ancestor_contribution}
\alias{calculate_ancestor_contribution}
\title{Ancestor contribution to inbreeding}
\usage{
calculate_ancestor_contribution(progeny = NULL, sire = NULL, dam = NULL,
  sex = NULL, birthdate = NULL, missing = c("0", "na", "NA", "", " "),
  quiet = FALSE, file = NULL, sep = " ", top_k = 5, max_depth = 6,
  format = c("ratio", "matrix"), target_animal = NULL,
  matrix_block_size = 2000L, progress = NULL)
}
\description{
Computes ancestor contributions to individual inbreeding (F).
Only inbred individuals (F > 0) are included in the result.
Use format \"ratio\" for a data frame (id, anc_1, anc_1_contribution, ...)
or \"matrix\" for a sparse matrix.
}
\arguments{
\item{progeny}{Progeny IDs.}
\item{sire}{Sire IDs.}
\item{dam}{Dam IDs.}
\item{sex}{Optional sex.}
\item{birthdate}{Optional birth date.}
\item{missing}{Values treated as missing.}
\item{quiet}{If TRUE, do not print.}
\item{file}{Path to pedigree file (optional).}
\item{sep}{Field separator when reading file.}
\item{top_k}{Number of top ancestors per individual.}
\item{max_depth}{Max depth for path enumeration.}
\item{format}{\"ratio\" (data frame) or \"matrix\".}
\item{target_animal}{Optional IDs to restrict output.}
\item{matrix_block_size}{Block size for matrix format.}
\item{progress}{Show progress bar. Default is \code{!quiet}.}
}
