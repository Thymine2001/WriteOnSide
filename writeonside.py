import sys
from tkinter import messagebox

from writeonside_app import WriteOnSideApp
from writeonside_app.diagnostics import (
    configure_logging,
    install_exception_hooks,
    log_exception,
    log_startup,
    write_startup_failure_report,
)
from writeonside_app.platform import SingleInstanceGuard, enable_per_monitor_dpi, register_file_open_support
from writeonside_app.text_files import EDITABLE_TEXT_SUFFIXES, requested_file_from_args


if __name__ == "__main__":
    configure_logging()
    install_exception_hooks()
    log_startup(sys.argv)
    enable_per_monitor_dpi()
    requested_file = requested_file_from_args(sys.argv[1:])
    instance = SingleInstanceGuard()
    if not instance.is_primary:
        instance.signal_existing(requested_file)
        instance.close()
    else:
        try:
            register_file_open_support(EDITABLE_TEXT_SUFFIXES)
            WriteOnSideApp(instance_guard=instance, initial_file=requested_file).run()
        except Exception as exc:
            failure_path = write_startup_failure_report(type(exc), exc, exc.__traceback__)
            log_exception("Startup failure", type(exc), exc, exc.__traceback__)
            try:
                messagebox.showerror(
                    "WriteOnSide startup failed",
                    f"WriteOnSide failed to start.\n\nA diagnostic report was written to:\n{failure_path}",
                )
            except Exception:
                pass
            raise
        finally:
            instance.close()
