"""fsmonitor_fsevents.py FSMonitor subclass for FSEvents on Mac OS X >= 10.5

Always works in persistent mode by (FSEvent's) design.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
from FSEvents import kCFAllocatorDefault, \
                     CFRunLoopGetCurrent, \
                     kCFRunLoopDefaultMode, \
                     CFRunLoopRun, \
                     CFRunLoopStop, \
                     CFRunLoopAddTimer, \
                     CFRunLoopTimerCreate, \
                     CFAbsoluteTimeGetCurrent, \
                     NSAutoreleasePool, \
                     kFSEventStreamEventIdSinceNow, \
                     kFSEventStreamCreateFlagWatchRoot, \
                     kFSEventStreamEventFlagMustScanSubDirs, \
                     kFSEventStreamEventFlagUserDropped, \
                     kFSEventStreamEventFlagKernelDropped, \
                     kFSEventStreamEventFlagRootChanged, \
                     FSEventStreamScheduleWithRunLoop, \
                     FSEventStreamCreate, \
                     FSEventStreamStart, \
                     FSEventStreamStop, \
                     FSEventStreamInvalidate, \
                     FSEventStreamRelease, \
                     FSEventStreamShow
import os


# Define exceptions.
class FSMonitorFSEventsError(FSMonitorError): pass
class MonitorError(FSMonitorFSEventsError): pass
class CouldNotStartError(FSMonitorFSEventsError): pass


class FSMonitorFSEvents(FSMonitor):
    """FSEvents support for FSMonitor"""


    # These 3 settings are hardcoded. See FSMonitor's documentation for an
    # explanation.
    latency = 1.0
    sinceWhen = kFSEventStreamEventIdSinceNow
    flags = kFSEventStreamCreateFlagWatchRoot


    def __init__(self, callback, dbfile="fsmonitor.db"):
        FSMonitor.__init__(self, callback, True, dbfile)
        self.latest_event_id = None
        self.die = False
        self.auto_release_pool = None


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""
        # Perform an initial scan of the directory structure. If this has
        # already been done, then it will return immediately.
        self.pathscanner.initial_scan(path)

        # Use the FSEvents API to monitor a directory.
        streamRef = FSEventStreamCreate(kCFAllocatorDefault,
                                        self.__fsevents_callback,
                                        path,
                                        [path],
                                        self.__class__.sinceWhen,
                                        self.__class__.latency,
                                        self.__class__.flags)
        # Debug output.
        #FSEventStreamShow(streamRef)

        if streamRef is None:
            raise MonitorError, "Could not monitor %s" % path
            return None
        else:
            self.monitored_paths[path] = MonitoredPath(path, event_mask, streamRef)
            return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            streamRef = self.monitored_paths[path].fsmonitor_ref
            # Stop, unschedule, invalidate and release the stream refs.
            FSEventStreamStop(streamRef)
            # We don't use FSEventStreamUnscheduleFromRunLoop prior to
            # invalidating the stream, because invalidating the stream
            # automatically unschedules the stream from all run loops.
            FSEventStreamInvalidate(streamRef)
            FSEventStreamRelease(streamRef)

            del self.monitored_paths[path]


    def generate_missed_events(self):
        # TODO: use FSEventsGetLastEventIdForDeviceBeforeTime()
        pass


    def run(self):
        # Necessary because we're using PyObjC in a thread other than the main
        # thread.
        self.auto_release_pool = NSAutoreleasePool.alloc().init()

        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.lock.release()

        # Set up a callback to a function that process the queues frequently.
        CFRunLoopAddTimer(
           CFRunLoopGetCurrent(),
           CFRunLoopTimerCreate(None, CFAbsoluteTimeGetCurrent(), 0.5, 0, 0, self.__process_queues, None),
           kCFRunLoopDefaultMode
        )

        # Start the run loop.
        CFRunLoopRun()


    def stop(self):
        """override of FSMonitor.stop()"""

        # Let the thread know it should die.
        self.lock.acquire()
        self.die = True
        self.lock.release()

        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            self.__remove_dir(path)

        # Store the latest event ID so we know where we left off.
        # TODO: separate table in DB to store this?

        # Delete the auto release pool.
        del self.auto_release_pool


    def __process_queues(self, timer, context):
        # Die when asked to.
        self.lock.acquire()
        if self.die:
            CFRunLoopStop(CFRunLoopGetCurrent())
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

        # Ensure all monitored paths are actually being monitored. If they're
        # not yet being monitored, start doing so.
        for path in self.monitored_paths.keys():
            if self.monitored_paths[path].monitoring:
                continue
            streamRef = self.monitored_paths[path].fsmonitor_ref
            
            # Schedule stream on a loop.
            FSEventStreamScheduleWithRunLoop(streamRef, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode)

            # Register with the FS Events service to receive events.
            started = FSEventStreamStart(streamRef)
            if not started:
                raise CouldNotStartError
            else:
                self.monitored_paths[path].monitoring = True


    def __fsevents_callback(self, streamRef, clientCallBackInfo, numEvents, eventPaths, eventFlags, eventIDs):
        """private callback function for use with FSEventStreamCreate"""
        # Details of the used flags can be found in FSEvents.h.
        monitored_path = clientCallBackInfo

        for i in range(numEvents):
            event_path = eventPaths[i]
            self.latest_event_id = eventIDs[i]

            # Strip trailing slash
            if event_path[-1] == '/':
                event_path = event_path[:-1]

            # Trigger the appropriate events.
            if eventFlags[i] & kFSEventStreamEventFlagUserDropped:
                FSMonitor.trigger_event(self, monitored_path, None, FSMonitor.DROPPED_EVENTS)

            elif eventFlags[i] & kFSEventStreamEventFlagKernelDropped:
                FSMonitor.trigger_event(self, monitored_path, None, FSMonitor.DROPPED_EVENTS)

            elif eventFlags[i] & kFSEventStreamEventFlagRootChanged:
                FSMonitor.trigger_event(self, monitored_path, event_path, FSMonitor.MONITORED_DIR_MOVED)

            elif eventFlags[i] & kFSEventStreamEventFlagMustScanSubDirs:
                result = self.pathscanner.scan_tree(event_path)
                self.__trigger_events_for_pathscanner_result(monitored_path, event_path, result)
            else:
                result = self.pathscanner.scan(event_path)
                self.__trigger_events_for_pathscanner_result(monitored_path, event_path, result)


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
