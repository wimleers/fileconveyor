if __name__ == "__main__":
    import sys
    import os
    import os.path
    sys.path.append(os.path.abspath('../dependencies'))


from transporter import *
from storages.S3BotoStorage import *


TRANSPORTER_CLASS = "TransporterS3"


class TransporterS3(Transporter):


    valid_settings    = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "bucket_prefix"])
    required_settings = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name"])
    headers = {
        'Expires': 'Tue, 20 Jan 2037 03:00:00 GMT', # UNIX timestamps will stop working somewhere in 2038.
        'Cache-Control': 'max-age=315360000',       # Cache for 10 years.
        'Vary' : 'Accept-Encoding',                 # Ensure S3 content can be accessed from behind proxies.
    }


    def __init__(self, settings, callback):
        Transporter.__init__(self, settings, callback)

        # Validate settings.
        configured_settings = Set(self.settings.keys())
        Transporter.validate_settings(self, self.__class__.valid_settings, self.__class__.required_settings, configured_settings)

        # Fill out defaults if necessary.
        if not "bucket_prefix" in configured_settings:
            self.settings["bucket_prefix"] = ""

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = S3BotoStorage(
                self.settings["bucket_name"],
                self.settings["bucket_prefix"],
                self.settings["access_key_id"],
                self.settings["secret_access_key"],
                "public-read",
                self.__class__.headers
            )
        except Exception, e:
            raise ConnectionError(e)


if __name__ == "__main__":
    import time
    import sys
    import os
    sys.path.append(os.path.abspath('../dependencies'))

    def callbackfunc(src, dst, url, action):
        print "CALLBACK FIRED:\n\tsrc='%s'\n\tdst='%s'\n\turl='%s'\n\taction=%d" % (src, dst, url, action)

    settings = {
        "access_key_id"      : "your access key id",
        "secret_access_key"  : "your secret access key",
        "bucket_name"        : "your bucket name",
    }
    s3 = TransporterS3(settings, callbackfunc)
    s3.start()
    s3.sync_file("transporter.py")
    s3.sync_file("drupal-5-6.png")
    s3.sync_file("subdir/bmi-chart.png")
    s3.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
    time.sleep(5)
    s3.stop()
