\name{extract_sub_pedigree}
\alias{extract_sub_pedigree}
\title{Extract sub pedigree from target individuals}
\usage{
extract_sub_pedigree(progeny = NULL, sire = NULL, dam = NULL,
  target = NULL, target_column = NULL, generation = "All",
  siblings = "None", sublings = NULL,
  missing = c("0", "na", "NA", "", " "), file = NULL, sep = " ")
}
\description{
Extracts a sub pedigree containing target individuals and their direct ancestors
up to a specified number of generations. Optionally, siblings of target
individuals can be included.
}
\arguments{
\item{progeny}{Progeny IDs.}
\item{sire}{Sire IDs.}
\item{dam}{Dam IDs.}
\item{target}{Target IDs. Can be a single ID, an ID vector, or (for file/data.frame input) a column name containing target IDs.}
\item{target_column}{Optional column name in input data used as target IDs.}
\item{generation}{Number of generations to trace back, or \code{"All"} for all ancestors.}
\item{siblings}{Sibling inclusion mode. One of \code{"None"}, \code{"Full"}, \code{"Half"}, or \code{"All"}.
\code{"Full"} includes full siblings (same sire and same dam),
\code{"Half"} includes half siblings (share sire or dam, but not both as a target pair),
\code{"All"} includes both full and half siblings.
Logical values are kept for compatibility: \code{TRUE -> "All"}, \code{FALSE -> "None"}.}
\item{sublings}{Compatibility alias for \code{siblings}. If provided, this value is used.}
\item{missing}{Values treated as missing.}
\item{file}{Path to pedigree file (optional).}
\item{sep}{Field separator when reading file.}
}
\value{
A data.frame with \code{progeny}, \code{sire}, and \code{dam} for the extracted sub pedigree.
}
