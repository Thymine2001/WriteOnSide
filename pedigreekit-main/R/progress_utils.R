ped_progress_start <- function(enabled = TRUE) {
  if (!isTRUE(enabled)) {
    return(list(
      update = function(...) invisible(NULL),
      finish = function(...) invisible(NULL)
    ))
  }

  pb <- utils::txtProgressBar(min = 0, max = 100, style = 3)
  state <- new.env(parent = emptyenv())
  state$current <- 0
  state$closed <- FALSE

  update <- function(pct) {
    if (state$closed) return(invisible(NULL))
    pct_num <- suppressWarnings(as.numeric(pct))
    if (!is.finite(pct_num)) return(invisible(NULL))
    pct_num <- max(0, min(100, pct_num))
    if (pct_num < state$current) pct_num <- state$current
    state$current <- pct_num
    utils::setTxtProgressBar(pb, state$current)
    invisible(NULL)
  }

  finish <- function() {
    if (state$closed) return(invisible(NULL))
    utils::setTxtProgressBar(pb, 100)
    close(pb)
    state$closed <- TRUE
    term <- Sys.getenv("TERM", unset = "")
    can_ansi <- isTRUE(base::isatty(stdout())) &&
      nzchar(term) &&
      !identical(tolower(term), "dumb")
    if (can_ansi) {
      # Move to previous line and clear completed progress bar line.
      cat("\033[1A\r\033[2K\r", sep = "")
    } else {
      cat("\n")
    }
    flush.console()
    invisible(NULL)
  }

  list(update = update, finish = finish)
}
