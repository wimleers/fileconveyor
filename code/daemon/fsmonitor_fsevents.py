"""fsmonitor_fsevents.py FSMonitor subclass for FSEvents on Mac OS X >= 10.5

Always works in persistent mode by (FSEvent's) design.

TODO:
- threading (CFRunLoopRun() blocks everything else, so move it to a separate thread)
- 
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
    latency = 3.0
    sinceWhen = kFSEventStreamEventIdSinceNow
    flags = kFSEventStreamCreateFlagWatchRoot


    def __init__(self, callback, dbfile="fsmonitor.db"):
        FSMonitor.__init__(self, callback, True, dbfile)
        self.latest_event_id = None


    def add_dir(self, path, event_mask):
        """override of FSMonitor.add_dir()"""
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
        FSEventStreamShow(streamRef)

        if streamRef is None:
            raise MonitorError, "Could not monitor %s" % path
            return None
        else:
            # Schedule stream on a loop.
            FSEventStreamScheduleWithRunLoop(streamRef, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode)

            # Register with the FS Events service to receive events.
            started = FSEventStreamStart(streamRef)
            if not started:
                raise CouldNotStartError

            # Store it as a MonitoredPath.
            self.monitored_paths[path] = MonitoredPath(path, event_mask, streamRef)

            return self.monitored_paths[path]


    def remove_dir(self, path):
        """override of FSMonitor.remove_dir()"""
        if path in self.streamRefs.keys():
            streamRef = self.monitored_paths[path].data
            # Stop, unschedule, invalidate and release the stream refs.
            FSEventStreamStop(streamRef)
            # We don't use FSEventStreamUnscheduleFromRunLoop prior to
            # invalidating the stream, because invalidating the stream
            # automatically unschedules the stream from all run loops.
            FSEventStreamInvalidate(streamRef)
            FSEventStreamRelease(streamRef)


    def generate_missed_events(self):
        # TODO: use FSEventsGetLastEventIdForDeviceBeforeTime()
        pass


    def start(self):
        """override of FSMonitor.start()"""
        CFRunLoopRun()


    def stop(self):
        """override of FSMonitor.stop()"""
        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            remove_dir(path)
        # Store the latest event ID so we know where we left off.
        # TODO: separate table in DB to store this?


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
        for filename in result["created"]:
            FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.CREATED)
        for filename in result["modified"]:
            FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.MODIFIED)                
        for filename in result["deleted"]:
            FSMonitor.trigger_event(self, monitored_path, os.path.join(event_path, filename), FSMonitor.DELETED)
