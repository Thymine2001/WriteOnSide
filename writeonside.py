import sys

from writeonside_app import WriteOnSideApp
from writeonside_app.platform import SingleInstanceGuard, enable_per_monitor_dpi, register_file_open_support
from writeonside_app.text_files import EDITABLE_TEXT_SUFFIXES, requested_file_from_args


if __name__ == "__main__":
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
        finally:
            instance.close()
