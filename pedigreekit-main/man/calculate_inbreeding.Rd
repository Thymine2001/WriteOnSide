\name{calculate_inbreeding}
\alias{calculate_inbreeding}
\title{Inbreeding coefficients}
\usage{
calculate_inbreeding(progeny = NULL, sire = NULL, dam = NULL,
  sex = NULL, birthdate = NULL, missing = c("0", "na", "NA", "", " "),
  quiet = FALSE, file = NULL, sep = " ", progress = NULL)
}
\description{
Computes inbreeding coefficient (F) for each individual.
Uses internal fix logic then fast C++ implementation.
Returns a data frame with id and inbreeding.
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
