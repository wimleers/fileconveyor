"""fsmonitor_inotify.py FSMonitor subclass for inotify on Linux kernel >= 2.6.13"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
import pyinotify
from pyinotify import WatchManager, \
                      ThreadedNotifier, \
                      ProcessEvent
import time
import os



# Define exceptions.
class FSMonitorInotifyError(FSMonitorError): pass


class FSMonitorInotify(FSMonitor):
    """inotify support for FSMonitor"""


    EVENTMAPPING = {
        FSMonitor.CREATED             : pyinotify.EventsCodes.IN_CREATE,
        FSMonitor.MODIFIED            : pyinotify.EventsCodes.IN_MODIFY | pyinotify.EventsCodes.IN_ATTRIB,
        FSMonitor.DELETED             : pyinotify.EventsCodes.IN_DELETE,
        FSMonitor.MONITORED_DIR_MOVED : pyinotify.EventsCodes.IN_MOVE_SELF,
        FSMonitor.DROPPED_EVENTS      : pyinotify.EventsCodes.IN_Q_OVERFLOW,
    }


    def __init__(self, callback, persistent=False, trigger_events_for_initial_scan=False, ignored_dirs=[], dbfile="fsmonitor.db"):
        FSMonitor.__init__(self, callback, persistent, trigger_events_for_initial_scan, ignored_dirs, dbfile)
        self.wm = None
        self.notifier = None


    def __fsmonitor_event_to_inotify_event(self, event_mask):
        """map an FSMonitor event to an inotify event"""
        inotify_event_mask = 0
        for fsmonitor_event_mask in self.__class__.EVENTMAPPING.keys():
            if event_mask & fsmonitor_event_mask:
                inotify_event_mask = inotify_event_mask | self.__class__.EVENTMAPPING[fsmonitor_event_mask]
        return inotify_event_mask


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""
        # Perform an initial scan of the directory structure. If this has
        # already been done, then it will return immediately.
        if self.persistent:
            if self.trigger_events_for_initial_scan:
                FSMonitor.generate_missed_events(self, path, event_mask)
            else:
                self.pathscanner.initial_scan(path)

        event_mask_inotify = self.__fsmonitor_event_to_inotify_event(event_mask)

        # Use the inotify API to monitor a directory.
        wdd = self.wm.add_watch(path, event_mask_inotify, proc_fun=self.process_event, rec=True, auto_add=True)

        if wdd is None:
            raise MonitorError, "Could not monitor %s" % path
            return None
        else:
            self.monitored_paths[path] = MonitoredPath(path, event_mask, wdd)
            self.monitored_paths[path].monitoring = True

            # Generate the missed events.
            if self.persistent:
                FSMonitor.generate_missed_events(self, path)
            
            return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            wd = self.monitored_paths[path].fsmonitor_ref
            # TODO: figure out why this won't work, it seems this fails due to
            # a bug in pyinotify?
            #self.wm.rm_watch(wd, rec=True, quiet=True)

            del self.monitored_paths[path]


    def run(self):
        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.process_event = FSMonitorInotifyProcessEvent(self)
        self.lock.release()

        # Set up inotify.
        self.wm = WatchManager()
        self.notifier = ThreadedNotifier(self.wm, self.process_event)

        self.notifier.start()

        while not self.die:
            self.__process_queues()
            time.sleep(0.5)

        self.notifier.stop()


    def stop(self):
        """override of FSMonitor.stop()"""

        # Let the thread know it should die.
        self.lock.acquire()
        self.die = True
        self.lock.release()

        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            self.__remove_dir(path)


    def __process_queues(self):
        # Process add queue.
        self.lock.acquire()
        if not self.add_queue.empty():
            (path, event_mask) = self.add_queue.get()
            self.lock.release()
            self.__add_dir(path, event_mask)
        else:
            self.lock.release()

        # Process remove queue.
        self.lock.acquire()
        if not self.remove_queue.empty():
            path = self.add_queue.get()
            self.lock.release()
            self.__remove_dir(path)
        else:
            self.lock.release()


class FSMonitorInotifyProcessEvent(ProcessEvent):
    def __init__(self, fsmonitor):
        ProcessEvent.__init__(self)
        self.fsmonitor_ref = fsmonitor

    def process_IN_CREATE(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.CREATED)

    def process_IN_DELETE(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.DELETED)

    def process_IN_MODIFY(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.MODIFIED)

    def process_IN_ATTRIB(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.MODIFIED)

    def process_IN_MOVE_SELF(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.MONITORED_DIR_MOVED)

    def process_IN_Q_OVERFLOW(self, event):
        if FSMonitor.is_in_ignored_directory(self, event.path):
            return
        FSMonitor.trigger_event(self.fsmonitor_ref, event.path, event.pathname, FSMonitor.DROPPED_EVENTS)

    def process_default(self, event):
        # Event not supported!
        pass
        
