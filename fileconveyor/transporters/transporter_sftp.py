from transporter import *
from customstorages.SFTPStorageFC import SFTPStorageFC


TRANSPORTER_CLASS = "TransporterSFTP"


class TransporterSFTP(Transporter):


    name              = 'SFTP'
    valid_settings    = ImmutableSet(["host", "username", "password", "root_path", "port", "timeout", "key_filename"])
    required_settings = ImmutableSet(["host", "username", "root_path"])

    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Raise exception when required settings have not been configured.
        configured_settings = Set(self.settings.keys())
        if not "username" in configured_settings:
            raise ImpropertlyConfigured, "username not set" 
        if not "host" in configured_settings:
            raise ImpropertlyConfigured, "host not set" 
        if not "root_path" in configured_settings:
            raise ImpropertlyConfigured, "path not set" 
        if not "timeout" in self.settings:
          self.settings["timeout"] = 30.0
        if not "port" in self.settings:
          self.settings["port"] = 22
        if not "password" in self.settings:
          self.settings["password"] = None 
        if not "key_filename" in self.settings:
          self.settings["key_filename"] = None 

        try:
          self.storage = SFTPStorageFC({'root_path':self.settings['root_path'],'host':self.settings['host'],'username':self.settings['username'],'password':self.settings['password'],'port':self.settings['port'],'timeout':self.settings['timeout'],'key_filename':self.settings['key_filename']})
        except Exception, e:
          raise Exception(e)

