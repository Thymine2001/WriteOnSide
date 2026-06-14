from writeonside_app import WriteOnSideApp
from writeonside_app.platform import SingleInstanceGuard


if __name__ == "__main__":
    instance = SingleInstanceGuard()
    if not instance.is_primary:
        instance.signal_existing()
        instance.close()
    else:
        try:
            WriteOnSideApp(instance_guard=instance).run()
        finally:
            instance.close()