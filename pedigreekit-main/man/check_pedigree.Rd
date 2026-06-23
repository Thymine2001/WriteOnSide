\name{check_pedigree}
\alias{check_pedigree}
\title{Pedigree quality control}
\usage{
check_pedigree(progeny = NULL, sire = NULL, dam = NULL, sex = NULL,
  birthdate = NULL, missing = c("0", "na", "NA", "", " "),
  quiet = FALSE, file = NULL, sep = " ", progress = NULL)
}
\description{
Runs pedigree QC: duplicate IDs, missing parents, self-parent,
dual-role, sex mismatch, birth order, and loops.
Returns meta counts and a list of errors.
}
\arguments{
\item{progeny}{Progeny (individual) IDs.}
\item{sire}{Sire IDs.}
\item{dam}{Dam IDs.}
\item{sex}{Optional sex.}
\item{birthdate}{Optional birth date.}
\item{missing}{Values treated as missing (for progeny and parents).}
\item{quiet}{If TRUE, do not print.}
\item{file}{Path to pedigree file (optional).}
\item{sep}{Field separator when reading file.}
\item{progress}{Show progress bar. Default is \code{!quiet}.}
}
