"""fsmonitor_polling.py FSMonitor subclass that uses polling

Always works in persistent mode by design.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
import time
import os



# Define exceptions.
class FSMonitorPollingError(FSMonitorError): pass


class FSMonitorPolling(FSMonitor):
    """polling support for FSMonitor"""


    interval = 30


    def __init__(self, callback, dbfile="fsmonitor.db"):
        FSMonitor.__init__(self, callback, True, dbfile)
        self.die = False


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""
        # Perform an initial scan of the directory structure. If this has
        # already been done, then it will return immediately.
        if self.persistent:
            self.pathscanner.initial_scan(path)

        self.monitored_paths[path] = MonitoredPath(path, event_mask, None)
        self.monitored_paths[path].monitoring = True
        return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            del self.monitored_paths[path]


    def generate_missed_events(self):
        # TODO: use PathScanner()
        pass


    def run(self):
        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.lock.release()

        while not self.die:
            self.__process_queues()
            # Sleep some time.
            # TODO: make this configurable!
            time.sleep(self.__class__.interval)
            


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
        # Die when asked to.
        self.lock.acquire()
        if self.die:
            self.notifier.stop()
        self.lock.release()

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

        # Scan all paths.
        for monitored_path in self.monitored_paths.keys():
            for path, result in self.pathscanner.scan_tree(monitored_path):
                self.__trigger_events_for_pathscanner_result(monitored_path, monitored_path, result)


    def __trigger_events_for_pathscanner_result(self, monitored_path, event_path, result):
        """trigger events for pathscanner result"""
        event_mask = self.monitored_paths[monitored_path].event_mask
        if event_mask & FSMonitor.CREATED:
            for filename in result["created"]:
                FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.CREATED)
        if event_mask & FSMonitor.MODIFIED:
            for filename in result["modified"]:
                FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.MODIFIED)                
        if event_mask & FSMonitor.DELETED:
            for filename in result["deleted"]:
                FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.DELETED)
