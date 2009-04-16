"""fsmonitor.py Cross-platform file system monitor

How it works:
- Uses inotify on Linux (kernel 2.6 and higher)
- Uses FileSystemWatcher on Windows (TODO)
- Uses FSEvents on Mac OS X (10.5 and higher)
- Falls back to polling

A persistent mode is also supported, in which all metadata is stored in a
database. This allows you to even track changes when your program wasn't
running.

Only FSEvents supports looking back in time. For Linux and Windows this means
that the manual scanning procedure will be used instead until we have caught
up.

To make this class work consistently, less critical features that are only
available for specific file system monitors are abstracted away. And other
features are emulated.
It comes down to the fact that FSMonitor's API is very simple to use and only
supports 5 different events: CREATED, MODIFIED, DELETED, MONITORED_DIR_MOVED
and DROPPED_EVENTS. The last 2 events are only triggered for inotify and
FSEvents.

This implies that the following features are not available through FSMonitor:
- inotify:
  * auto_add: is always assumed to be True (FSEvents has no setting for this)
  * recursive: is always assumed to be True (FSEvents has no setting for this)
  * IN_ACCESS, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE, IN_OPEN, IN_DELETE_SELF and
    IN_IGNORED event aren't supported (FSEvents doesn't support this)
  * IN_UNMOUNT is also not supported because FSEvents' equivalent
    (kFSEventStreamEventFlagUnmount) isn't supported in Python
- FSEvents:
  * sinceWhen: is always set to kFSEventStreamEventIdSinceNow (inotify has no
    setting for this)
  * kFSEventStreamEventFlagMount: is ignored (inotify doesn't support this)
And the following features are emulated:
- FSEvents:
  * inotify's mask, which allows you to listen only to certain events
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import platform
import sqlite3
import threading
import Queue
from pathscanner import PathScanner


# Define exceptions.
class FSMonitorError(Exception): pass


class FSMonitor(threading.Thread):
    """cross-platform file system monitor"""


    # Identifiers for each event.
    EVENTS = {
        "CREATED"             : 0x00000001,
        "MODIFIED"            : 0x00000002,
        "DELETED"             : 0x00000004,
        "MONITORED_DIR_MOVED" : 0x00000008,
        "DROPPED_EVENTS"      : 0x00000016,
    }


    def __init__(self, callback, persistent=False, dbfile="fsmonitor.db"):
        self.persistent = persistent
        self.monitored_paths = {}
        self.dbfile = dbfile
        self.dbcon = None
        self.dbcur = None
        self.pathscanner = None
        self.callback = callback
        self.lock = threading.Lock()
        self.add_queue = Queue.Queue(0)
        self.remove_queue = Queue.Queue(0)
        threading.Thread.__init__(self)


    def generate_missed_events(self):
        """generate the missed events for a persistent DB"""
        raise NotImplemented


    def run(self):
        """start the file system monitor (starts a separate thread)"""
        raise NotImplemented


    def add_dir(self, path, event_mask):
        """add a directory to monitor"""
        self.lock.acquire()
        self.add_queue.put((path, event_mask))
        self.lock.release()


    def __add_dir(self, path, event_mask):
        raise NotImplemented


    def remove_dir(self, path):
        """stop monitoring a directory"""
        self.lock.acquire()
        self.remove_queue.put(path)
        self.lock.release()


    def __remove_dir(self, path):
        raise NotImplemented


    def stop(self):
        """stop the file system monitor (stops the separate thread)"""
        raise NotImplemented


    def purge_dir(self, path):
        """purge the metadata for a monitored directory
        
        Only possible if this is a persistent DB.
        """
        if self.persistent:
            self.pathscanner.purge_path(path)

    def trigger_event(self, monitored_path, event_path, event):
        """trigger one of the standardized events"""
        if callable(self.callback):
            self.callback(monitored_path, event_path, event)


    def setup(self):
        """set up the database and pathscanner"""
        # Database.
        if self.dbcur is None:
            self.dbcon = sqlite3.connect(self.dbfile)
            self.dbcur = self.dbcon.cursor()
        # PathScanner.
        if self.persistent == True and self.dbcur is not None:
            self.pathscanner = PathScanner(self.dbcon, "pathscanner")
            

class MonitoredPath(object):
    """A simple container for all metadata related to a monitored path"""
    def __init__(self, path, event_mask, fsmonitor_ref=None):
        self.path = path
        self.event_mask = event_mask
        self.fsmonitor_ref = fsmonitor_ref
        self.monitoring = False


def __get_class_reference(modulename, classname):
    """get a reference to a class"""
    module = __import__(modulename, globals(), locals(), [classname])
    class_reference = getattr(module, classname)
    return class_reference


def get_fsmonitor():
    """get the FSMonitor for the current platform"""
    system = platform.system()
    if system == "Linux":
        kernel = platform.release().split(".")
        # Available in Linux kernel 2.6.13 and higher.
        if int(kernel[0]) == 2 and int(kernel[1]) == 6 and kernel[2][:2] >= 13:
            return __get_class_reference("fsmonitor_inotify", "FSMonitorInotify")
    elif system == "Windows":
        # See:
        # - http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
        # - http://code.activestate.com/recipes/156178/
        # - http://stackoverflow.com/questions/339776/asynchronous-readdirectorychangesw
        pass
    elif system == "Darwin":
        (release, version_info, machine) = platform.mac_ver()
        major = release.split(".")[1]
        # Available in Mac OS X 10.5 and higher.
        if (major >= 5):
            return __get_class_reference("fsmonitor_fsevents", "FSMonitorFSEvents")

    # Default to a polling mechanism
    return __get_class_reference("fsmonitor_polling", "FSMonitorPolling")


# Make EVENTS' members directly accessible through the class dictionary.
for name, mask in FSMonitor.EVENTS.iteritems():
    setattr(FSMonitor, name, mask)




if __name__ == "__main__":
    import time

    def callbackfunc(monitored_path, event_path, event):
        print "CALLBACK FIRED, params: monitored_path=%s', event_path='%s', event='%d'" % (monitored_path, event_path, event)

    fsmonitor_class = get_fsmonitor()
    print "Using class", fsmonitor_class
    fsmonitor = fsmonitor_class(callbackfunc)
    fsmonitor.start()
    fsmonitor.add_dir("/Users/wimleers/Downloads", FSMonitor.CREATED | FSMonitor.MODIFIED | FSMonitor.DELETED)
    time.sleep(30)
    fsmonitor.stop()
