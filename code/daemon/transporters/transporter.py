"""transporter.py Transporter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from django.core.files.storage import Storage
from django.core.files import File


# Define exceptions.
class TransporterError(Exception): pass
class InvalidSettingError(TransporterError): pass
class MissingSettingError(TransporterError): pass
class InvalidCallbackError(TransporterError): pass
class ConnectionError(TransporterError): pass
class InvalidActionError(TransporterError): pass


import threading
import Queue
import time
import os.path
from sets import Set, ImmutableSet


class Transporter(threading.Thread):
    """threaded abstraction around a Django Storage subclass"""


    ACTIONS = {
        "ADD_MODIFY" : 0x00000001,
        "DELETE"     : 0x00000002,
    }


    def __init__(self, settings, callback):
        if not callable(callback):
            raise InvalidCallbackError

        self.settings = settings
        self.storage = False
        self.ready = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
        self.callback = callback
        self.die = False
        threading.Thread.__init__(self)


    def run(self):
        while not self.die:
            # Sleep a little bit if there's no work.
            if self.queue.qsize() == 0:
                self.ready = True
                time.sleep(0.5)
            else:
                self.ready = False

                self.lock.acquire()
                (src, dst, action, callback) = self.queue.get_nowait()
                self.lock.release()

                try:
                    # Sync the file: either add/modify it, or delete it.
                    if action == Transporter.ADD_MODIFY:
                        # Sync the file.
                        f = File(open(src, "rb"))
                        if self.storage.exists(dst):
                            self.storage.delete(dst)
                        self.storage.save(dst, f)
                        f.close()
                        # Calculate the URL.
                        url = self.storage.url(dst)
                        url = self.alter_url(url)
                    else:
                        if self.storage.exists(dst):
                            self.storage.delete(dst)
                        url = None

                    # Call the callback function. Use the callback function
                    # defined for this Transporter (self.callback), unless
                    # an alternative one was defined for this file (callback).
                    if not callback is None:
                        callback(src, dst, url, action)
                    else:
                        self.callback(src, dst, url, action)

                except Exception, e:
                    raise ConnectionError(e)


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
            raise MissingSettingError


    def sync_file(self, src, dst=None, action=None, callback=None):
        # Set the default value here because Python won't allow it sooner.
        if dst is None:
            dst = src
        if action is None:
            action = Transporter.ADD_MODIFY
        elif action not in Transporter.ACTIONS.values():
            raise InvalidActionError

        # If dst is relative to the root, strip the leading slash.
        if dst.startswith("/"):
            dst = dst[1:]

        self.lock.acquire()
        self.queue.put((src, dst, action, callback))
        self.lock.release()


    def is_ready(self):
        return self.ready


# Make EVENTS' members directly accessible through the class dictionary.
for name, mask in Transporter.ACTIONS.iteritems():
    setattr(Transporter, name, mask)
