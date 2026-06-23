\name{fix_pedigree}
\alias{fix_pedigree}
\title{Fix pedigree}
\usage{
fix_pedigree(progeny = NULL, sire = NULL, dam = NULL, sex = NULL,
  birthdate = NULL, missing = c("0", "na", "NA", "", " "),
  quiet = FALSE, file = NULL, sep = " ", progress = NULL)
}
\description{
Cleans pedigree: drop rows with missing progeny, resolve dual-role
and sex mismatch, remove self-parent, add missing parents as founders,
break loops,
normalize birthdates. Returns a data frame (progeny, sire, dam, ...).
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
\item{progress}{Show progress bar. Default is \code{!quiet}.}
}
