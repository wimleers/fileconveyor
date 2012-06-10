from transporter import *
from cumulus.storage import CloudFilesStorage


TRANSPORTER_CLASS = "TransporterCumulus"


class TransporterCumulus (Transporter):

    name              = 'cumulus'
    valid_settings    = ImmutableSet(["username", "api_key", "container"])
    required_settings = ImmutableSet(["username", "api_key", "container"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Raise exception when required settings have not been configured.
        configured_settings = Set(self.settings.keys())
        if not "username" in configured_settings:
            raise ImpropertlyConfigured, "username not set" 
        if not "api_key" in configured_settings:
            raise ImpropertlyConfigured, "api_key not set" 
        if not "container" in configured_settings:
            raise ImpropertlyConfigured, "container not set" 

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = CloudFilesStorage(
            self.settings["username"],
            self.settings["api_key"],
            self.settings["container"]
            )
        except Exception, e:
            if e.__class__ == cloudfiles.errors.AuthenticationFailed:
                raise ConnectionError, "Authentication failed"
            else:
                raise ConnectionError(e)
