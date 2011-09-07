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
import logging
from sets import Set, ImmutableSet


class Transporter(threading.Thread):
    """threaded abstraction around a Django Storage subclass"""


    ACTIONS = {
        "ADD_MODIFY" : 0x00000001,
        "DELETE"     : 0x00000002,
    }


    def __init__(self, settings, callback, error_callback, parent_logger):
        if not callable(callback):
            raise InvalidCallbackError("callback function is not callable")
        if not callable(error_callback):
            raise InvalidCallbackError("error_callback function is not callable")

        self.settings       = settings
        self.storage        = None
        self.lock           = threading.Lock()
        self.queue          = Queue.Queue()
        self.callback       = callback
        self.error_callback = error_callback
        self.logger         = logging.getLogger(".".join([parent_logger, "Transporter"]))
        self.die            = False

        # Validate settings.
        self.validate_settings()

        threading.Thread.__init__(self, name="TransporterThread")


    def run(self):
        while not self.die:
            # Sleep a little bit if there's no work.
            if self.queue.qsize() == 0:
                time.sleep(0.5)
            else:
                self.lock.acquire()
                (src, dst, action, callback, error_callback) = self.queue.get()
                self.lock.release()

                self.logger.debug("Running the transporter '%s' to sync '%s'." % (self.name, src))
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

                    self.logger.debug("The transporter '%s' has synced '%s'." % (self.name, src))

                    # Call the callback function. Use the callback function
                    # defined for this Transporter (self.callback), unless
                    # an alternative one was defined for this file (callback).
                    if not callback is None:
                        callback(src, dst, url, action)
                    else:
                        self.callback(src, dst, url, action)

                except Exception, e:
                    self.logger.error("The transporter '%s' has failed while transporting the file '%s' (action: %d). Error: '%s'." % (self.name, src, action, e))

                    # Call the error_callback function. Use the error_callback
                    # function defined for this Transporter
                    # (self.error_callback), unless an alternative one was
                    # defined for this file (error_callback).
                    if not callback is None:
                        error_callback(src, dst, action)
                    else:
                        self.error_callback(src, dst, action)


    def alter_url(self, url):
        """allow some classes to alter the generated URL"""
        return url


    def stop(self):
        self.lock.acquire()
        self.die = True
        self.lock.release()


    def validate_settings(self):
        # Get some variables "as if it were magic", i.e., from subclasses of
        # this class.
        valid_settings      = self.valid_settings
        required_settings   = self.required_settings
        configured_settings = Set(self.settings.keys())

        if len(configured_settings.difference(valid_settings)):
            raise InvalidSettingError

        if len(required_settings.difference(configured_settings)):
            raise MissingSettingError


    def sync_file(self, src, dst=None, action=None, callback=None, error_callback=None):
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
        self.queue.put((src, dst, action, callback, error_callback))
        self.lock.release()


    def qsize(self):
        self.lock.acquire()
        qsize = self.queue.qsize()
        self.lock.release()
        return qsize


# Make EVENTS' members directly accessible through the class dictionary.
for name, mask in Transporter.ACTIONS.iteritems():
    setattr(Transporter, name, mask)
