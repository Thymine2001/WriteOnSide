from writeonside_app import WriteOnSideApp
from writeonside_app.platform import SingleInstanceGuard, enable_per_monitor_dpi


if __name__ == "__main__":
    enable_per_monitor_dpi()
    instance = SingleInstanceGuard()
    if not instance.is_primary:
        instance.signal_existing()
        instance.close()
    else:
        try:
            WriteOnSideApp(instance_guard=instance).run()
        finally:
            instance.close()