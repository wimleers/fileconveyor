if __name__ == "__main__":
    import sys
    import os
    import os.path
    sys.path.append(os.path.abspath('../dependencies'))


from transporter import *
from storages.FTPStorage import *


TRANSPORTER_CLASS = "TransporterFTP"


class TransporterFTP(Transporter):


    valid_settings = ImmutableSet(["host", "username", "password", "url", "port", "path"])
    required_settings = ImmutableSet(["host", "username", "password", "url"])


    def __init__(self, settings, callback):
        Transporter.__init__(self, settings, callback)

        # Validate settings.
        configured_settings = Set(self.settings.keys())
        Transporter.validate_settings(self, self.__class__.valid_settings, self.__class__.required_settings, configured_settings)

        # Fill out defaults if necessary.
        if not "port" in configured_settings:
            self.settings["port"] = 21
        if not "path" in configured_settings:
            self.settings["path"] = ""

        # Map the settings to the format expected by FTPStorage.
        location = "ftp://" + self.settings["username"] + ":" + self.settings["password"] + "@" + self.settings["host"] + ":" + str(self.settings["port"]) + self.settings["path"]
        self.storage = FTPStorage(location, self.settings["url"])


if __name__ == "__main__":
    import time
    import sys
    import os
    sys.path.append(os.path.abspath('../dependencies'))

    def callbackfunc(src, dst, url, action):
        print "CALLBACK FIRED:\n\tsrc='%s'\n\tdst='%s'\n\turl='%s'\n\taction=%d" % (src, dst, url, action)

    settings = {
        "host"     : "your ftp host",
        "username" : "your username",
        "password" : "your password",
        "url"      : "your base URL"
    }
    ftp = TransporterFTP(settings, callbackfunc)
    ftp.start()
    ftp.sync_file("transporter.py")
    ftp.sync_file("drupal-5-6.png")
    ftp.sync_file("subdir/bmi-chart.png")
    ftp.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
    time.sleep(5)
    ftp.stop()
