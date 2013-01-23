from transporter import *
from storages.backends.s3boto import S3BotoStorage


TRANSPORTER_CLASS = "TransporterS3"


class TransporterS3(Transporter):


    name              = 'S3'
    valid_settings    = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "bucket_prefix",
                                      "use_signed_urls", "use_secure_urls", "set_url_expiration"])
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

        # Continue default behavior of S3BotoStorage
        # if the user has not defined these in the
        # configuration file.
        if not "use_signed_urls" in configured_settings:
            self.settings["use_signed_urls"] = "true"

        if not "use_secure_urls" in configured_settings:
            self.settings["use_secure_urls"] = "true"

        if not "set_url_expiration" in configured_settings:
            self.settings["set_url_expiration"] = 3600

        # set_url_expiration must be an integer, if it is not, set to default.
        if not isinstance(self.settings["set_url_expiration"], int):
            self.settings["set_url_expiration"] = 3600

        if self.settings["use_signed_urls"].lower() == "true":
            USE_QUERYSTRING_AUTH=True
        else:
            USE_QUERYSTRING_AUTH=False

        if self.settings["use_secure_urls"].lower() == "true":
            USE_SECURE_URLS=True
            USE_URL_PROTOCOL="https"
        else:
            USE_SECURE_URLS=False
            USE_URL_PROTOCOL="http"

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = S3BotoStorage(
                self.settings["bucket_name"].encode('utf-8'), 
                self.settings["access_key_id"].encode('utf-8'),
                self.settings["secret_access_key"].encode('utf-8'),
                "public-read",
                "public-read",
                self.__class__.headers,
                querystring_auth=USE_QUERYSTRING_AUTH,
                querystring_expire=self.settings["set_url_expiration"],
                secure_urls=USE_SECURE_URLS,
                url_protocol=USE_URL_PROTOCOL
            )
        except Exception, e:            
            raise ConnectionError(e)
