\name{check_pedigree_structure}
\alias{check_pedigree_structure}
\alias{print.pedigree_structure}
\title{Pedigree structure summary}
\usage{
check_pedigree_structure(progeny = NULL, sire = NULL, dam = NULL, sex = NULL,
  birthdate = NULL, missing = c("0", "na", "NA", "", " "),
  quiet = FALSE, file = NULL, sep = " ", lap_max_depth = 20L,
  lap_sample_size = 10000L, descendant_max_depth = 10L, top_n = 10L,
  progress = NULL)

\method{print}{pedigree_structure}(x, ...)
}
\description{
Summarises pedigree structure and returns a structured object that can be saved,
for example \code{ped_str <- check_pedigree_structure()}.
}
\arguments{
\item{progeny}{Progeny IDs, or a data.frame when \code{sire} and \code{dam} are omitted.}
\item{sire}{Sire IDs.}
\item{dam}{Dam IDs.}
\item{sex}{Optional sex vector.}
\item{birthdate}{Optional birth date vector.}
\item{missing}{Values treated as missing parent.}
\item{quiet}{If TRUE, do not print summary.}
\item{file}{Path to pedigree file (optional).}
\item{sep}{Field separator when reading file.}
\item{lap_max_depth}{Maximum depth bins used for LAP distribution.}
\item{lap_sample_size}{Compatibility argument recorded in output; LAP distribution is derived from full \code{lap_depths}.}
\item{descendant_max_depth}{Maximum depth used for descendant summaries.}
\item{top_n}{Number of top sire/dam parents shown in printed output.}
\item{progress}{Show progress bar. Default is \code{!quiet}.}
\item{x}{A \code{pedigree_structure} object.}
\item{...}{Unused.}
}
\value{
A list with class \code{pedigree_structure}, including:
\itemize{
  \item \code{generated_at}: report timestamp.
  \item \code{basic_stats}, \code{parent_stats}, \code{founder_stats}, \code{non_founder_stats}.
  \item \code{full_sib_groups}: full-sib group summary.
  \item \code{inbreeding}: full inbreeding summary, distribution, and per-individual values.
  \item \code{summary_stats}: A/B/C/D/E/G/H/I/J summary block.
  \item \code{lap}: LAP distribution, mean depth, and per-individual depths.
  \item \code{descendants}: sire/dam descendant summaries and top tables.
  \item \code{loops}: detected loop cycles.
  \item \code{fixed_pedigree}: cleaned pedigree used for the structure analysis.
}
}
\details{
The workflow is two-stage and consistent with \code{calculate_inbreeding()}:
first repair pedigree relationships, then compute structure statistics.

If no input is supplied, the function first tries a data.frame named
\code{ped} in the calling environment, then tries \code{ped.csv} in the
current working directory.
}
\examples{
\dontrun{
ped_str <- check_pedigree_structure(
  file = "/Applications/pedigreekit/tests/pedigree_data.txt",
  sep = " "
)
ped_str
str(ped_str$summary_stats)
}
}
