from transporter import *
from storages.backends.symlinkorcopy import SymlinkOrCopyStorage


TRANSPORTER_CLASS = "TransporterSymlinkOrCopy"


class TransporterSymlinkOrCopy(Transporter):


    name              = 'SYMLINK_OR_COPY'
    valid_settings    = ImmutableSet(["location", "url", "symlinkWithin"])
    required_settings = ImmutableSet(["location", "url", "symlinkWithin"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Map the settings to the format expected by SymlinkStorage.
        self.storage = SymlinkOrCopyStorage(self.settings["location"],
                                            self.settings["url"],
                                            self.settings["symlinkWithin"]
                                            )

