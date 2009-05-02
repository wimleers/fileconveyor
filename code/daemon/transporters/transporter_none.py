from transporter import *
from storages.SymlinkOrCopyStorage import *


TRANSPORTER_CLASS = "TransporterNone"


class TransporterNone(Transporter):


    valid_settings    = ImmutableSet(["location", "url", "symlinkWithin"])
    required_settings = ImmutableSet(["location", "url", "symlinkWithin"])


    def __init__(self, settings, callback):
        Transporter.__init__(self, settings, callback)

        # Validate settings.
        configured_settings = Set(self.settings.keys())
        Transporter.validate_settings(self, self.__class__.valid_settings, self.__class__.required_settings, configured_settings)

        # Map the settings to the format expected by SymlinkStorage.
        self.storage = SymlinkOrCopyStorage(self.settings["location"],
                                            self.settings["url"],
                                            self.settings["symlinkWithin"]
                                            )


if __name__ == "__main__":
    import time
    import subprocess
    import tempfile
    import os.path
    import sys
    import os
    sys.path.append(os.path.abspath('../dependencies'))

    def callbackfunc(filepath, url):
        print "CALLBACK FIRED: filepath=%s, url=%s" % (filepath, url)

    settings = {
        "location"     : "/htdocs/static.example.com/",
        "url"          : "http://static.example.com/",
        "symlinkWithin": os.path.abspath('')
    }
    none = TransporterNone(settings, callbackfunc)
    none.start()
    none.sync_file("transporter.py")
    none.sync_file("drupal-5-6.png")
    none.sync_file("subdir/bmi-chart.png")
    subprocess.call("echo yarhar > $TMPDIR/foobar.txt", shell=True, stdout=subprocess.PIPE)
    none.sync_file(os.path.join(tempfile.gettempdir(), "foobar.txt"))
    time.sleep(5)
    none.stop()
