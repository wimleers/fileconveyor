from transporter import *
from storages.backends.ftp import FTPStorage


TRANSPORTER_CLASS = "TransporterFTP"


class TransporterFTP(Transporter):


    name              = 'FTP'
    valid_settings    = ImmutableSet(["host", "username", "password", "url", "port", "path"])
    required_settings = ImmutableSet(["host", "username", "password", "url"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Fill out defaults if necessary.
        configured_settings = Set(self.settings.keys())
        if not "port" in configured_settings:
            self.settings["port"] = 21
        if not "path" in configured_settings:
            self.settings["path"] = ""

        # Map the settings to the format expected by FTPStorage.
        location = "ftp://" + self.settings["username"] + ":" + self.settings["password"] + "@" + self.settings["host"] + ":" + str(self.settings["port"]) + self.settings["path"]
        self.storage = FTPStorage(location, self.settings["url"])
        try:
            self.storage._start_connection()
        except Exception, e:            
            raise ConnectionError(e)
