"""transporter.py Transporter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sys
import os
sys.path.append(os.path.abspath('../dependencies'))

from django.core.files.storage import Storage
from django.core.files import File


# Define exceptions.
class TransporterError(Exception): pass
class InvalidSettingError(TransporterError): pass
class MissingSettingError(TransporterError): pass
class InvalidCallbackError(TransporterError): pass
class ConnectionError(TransporterError): pass


import threading
import Queue
import time
from sets import Set, ImmutableSet


class Transporter(threading.Thread):
    """threaded abstraction around a Django Storage subclass"""

    def __init__(self, settings, callback):
        if not callable(callback):
            raise InvalidCallbackError

        self.settings = settings
        self.storage = False
        self.is_ready = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.callback = callback
        self.die = False
        threading.Thread.__init__(self)


    def run(self):
        while not self.die:
            self.lock.acquire()
            try:
                (filepath, path) = self.queue.get_nowait()
                self.lock.release()

                # Sync the file.
                f = File(open(filepath, "rb"))
                target = os.path.join(path, filepath)
                if self.storage.exists(target):
                    self.storage.delete(target)
                self.storage.save(target, f)
                f.close()

                # Call the callback function.
                url = self.storage.url(filepath)
                url = self.alter_url(url)
                self.callback(filepath, url)

            except Exception, e:
                print e
                self.lock.release()

            # Sleep a little bit.
            time.sleep(0.1)


    def alter_url(self, url):
        """allow some classes to alter the generated URL"""
        return url


    def stop(self):
        self.lock.acquire()
        self.die = True
        self.lock.release()


    def validate_settings(self, valid_settings, required_settings, settings):
        if len(settings.difference(valid_settings)):
            raise InvalidSettingError

        if len(required_settings.difference(settings)):
            raise InvalidSettingError


    def sync_file(self, filepath, path=""):
        """sync a file"""
        self.lock.acquire()
        self.queue.put((filepath, path))
        self.lock.release()
