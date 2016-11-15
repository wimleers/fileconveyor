from transporter import *
from storages.backends.s3boto import S3BotoStorage


TRANSPORTER_CLASS = "TransporterS3"


class TransporterS3(Transporter):


    name              = 'S3'
    valid_settings    = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "bucket_prefix", "bucket_access"])
    required_settings = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name"])
    headers = {
        'Expires':       'Tue, 20 Jan 2037 03:00:00 GMT', # UNIX timestamps will stop working somewhere in 2038.
        'Cache-Control': 'max-age=315360000',             # Cache for 10 years.
        'Vary' :         'Accept-Encoding',               # Ensure S3 content can be accessed from behind proxies.
    }


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Fill out defaults if necessary.
        configured_settings = Set(self.settings.keys())
        if not "bucket_prefix" in configured_settings:
            self.settings["bucket_prefix"] = ""

        if not "bucket_access" in configured_settings:
            self.settings["bucket_access"] = "private"

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = S3BotoStorage(
                self.settings["bucket_name"].encode('utf-8'),
                self.settings["access_key_id"].encode('utf-8'),
                self.settings["secret_access_key"].encode('utf-8'),
                self.settings["bucket_access"].encode('utf-8'),
                self.settings["bucket_access"].encode('utf-8'),
                self.__class__.headers
            )
        except Exception, e:
            raise ConnectionError(e)
