import logging
import logging.handlers
import Queue
import os
import stat
import threading
import time
import signal
import sys


sys.path.append(os.path.abspath('dependencies'))


from config import *
from persistent_queue import *
from persistent_list import *
from fsmonitor import *
from filter import *
from processors.processor import *
from transporters.transporter import *


LOG_FILE = './daemon.log'
PERSISTENT_DATA_FILE = './persistent_data.db'
WORKING_DIR = '/tmp/test'
MAX_SIMULTANEOUS_PROCESSORCHAINS = 20
MAX_SIMULTANEOUS_TRANSPORTERS = 10


# Copied from django.utils.functional
def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args+moreargs), **dict(kwargs, **morekwargs))
    return _curried


class Arbitrator(threading.Thread):
    """docstring for arbitrator"""


    def __init__(self, configfile="config.xml"):
        threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.die = False
        self.processorchains_running = 0
        self.transporters_running = 0

        # Set up logger.
        self.logger = logging.getLogger("Arbitrator")
        self.logger.setLevel(logging.DEBUG)
        # Handlers.
        fileHandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=5242880, backupCount=5)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.ERROR)
        # Formatters.
        formatter = logging.Formatter("%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s")
        fileHandler.setFormatter(formatter)
        consoleHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        self.logger.addHandler(consoleHandler)
        self.logger.info("Arbitrator is initializing.")

        # Load config file.
        self.configfile = configfile
        self.logger.info("Loading config file.")
        self.config = Config("Arbitrator")
        self.config_errors = self.config.load(self.configfile)
        self.logger.info("Loaded config file.")
        if self.config_errors > 0:
            self.logger.error("Cannot continue, please fix the errors in the config file first.")
            return

        # TRICKY: set the "symlinkWithin" setting for "none" transporters
        # First calculate the value for the "symlinkWithin" setting.
        source_paths = []
        for (name, path) in self.config.sources.items():
            source_paths.append(path)
        symlinkWithin = ":".join(source_paths)
        # Then set it for every server that uses the "none" transporter.
        for name in self.config.servers.keys():
            if self.config.servers[name]["transporter"] == "none":
                self.config.servers[name]["settings"]["symlinkWithin"] = symlinkWithin


    def setup(self):
        self.processor_chain_factory = ProcessorChainFactory("Arbitrator", WORKING_DIR)

        # Create transporter (cfr. worker thread) pools for each server.
        # Create one initial transporter per pool, possible other transporters
        # will be created on-demand.
        self.transporters = {}
        for server in self.config.servers.keys():
            self.transporters[server] = []
            self.logger.info("Created transporter pool for the '%s' server." % (server))
            self.__create_transporter(server)

        # Create objects associated with each rule.
        self.rules = []
        self.logger.info("Creating objects associated with each rule.")
        for (name, path) in self.config.sources.items():
            if self.config.rules.has_key(name):
                root_path = self.config.sources[name]
                for rule in self.config.rules[name]:
                    prepend_root_path = lambda path: os.path.join(root_path, path)
                    paths = map(prepend_root_path, rule["filterConditions"]["paths"].split(":"))
                    rule["filterConditions"]["paths"] = ":".join(paths)
                    self.rules.append({
                        "source"         : name,
                        "label"          : rule["label"],
                        "filter"         : Filter(rule["filterConditions"]),
                        "processorChain" : rule["processorChain"],
                        "destination"    : rule["destination"],
                    })
                    self.logger.info("Created objects for rule '%s' for source '%s'." % (rule["label"], name))

        # Initialize the FSMonitor.
        fsmonitor_class = get_fsmonitor()
        self.logger.info("Using the %s FSMonitor class." % (fsmonitor_class))
        self.fsmonitor = fsmonitor_class(self.fsmonitor_callback, True)
        self.logger.info("Initialized FSMonitor.")

        # Initialize the persistent queues, thread-crossing queues and
        # persistent lists..
        # TRICKY: we don't use Python's shelve module because it's loaded into
        # memory in its entirety. In the case of a huge backlag of files that
        # still have to be filtered, processed or transported, say, 1 million
        # files, this would result in hundreds of megabytes of memory usage.
        # Persistent queues.
        self.filter_queue    = PersistentQueue("filter_queue", PERSISTENT_DATA_FILE)
        self.logger.info("Initialized 'filter' persistent queue, contains %d items." % (self.filter_queue.qsize()))
        self.process_queue   = PersistentQueue("process_queue", PERSISTENT_DATA_FILE)
        self.logger.info("Initialized 'process' persistent queue, contains %d items." % (self.process_queue.qsize()))
        self.transport_queue = {}
        for server in self.config.servers.keys():
            self.transport_queue[server] = PersistentQueue("transport_queue_%s" % (server), PERSISTENT_DATA_FILE)
            self.logger.info("Initialized 'transport' persistent queue for the '%s' server, contains %d items." % (server, self.transport_queue[server].qsize()))
        self.db_queue        = PersistentQueue("process_queue", PERSISTENT_DATA_FILE)
        self.logger.info("Initialized 'db' persistent queue, contains %d items." % (self.db_queue.qsize()))
        # Thread-crossing queues.
        self.filter_thread_queue    = Queue.Queue()
        self.process_thread_queue   = Queue.Queue()
        self.transport_thread_queue = {}
        for server in self.config.servers.keys():
            self.transport_thread_queue[server] = Queue.Queue()
        self.db_thread_queue        = Queue.Queue()
        self.logger.info("Initialized thread-crossing queues.")
        # Persistent lists.
        self.filtering_list    =  PersistentList("filtering_list", PERSISTENT_DATA_FILE)
        self.processing_list   =  PersistentList("processing_list", PERSISTENT_DATA_FILE)
        self.transporting_list =  PersistentList("transporting_list", PERSISTENT_DATA_FILE)
        self.logger.info("Initialized 'filtering' persistent list, contains %d items." % (len(self.filtering_list)))
        self.logger.info("Initialized 'transporting' persistent list, contains %d items." % (len(self.processing_list)))
        self.logger.info("Initialized 'processing' persistent list, contains %d items." % (len(self.transporting_list)))

        # Delete unused 'transport' persistent queues.
        pdm = PersistentDataManager(PERSISTENT_DATA_FILE)
        tables = pdm.list('transport_queue_%')
        for table in tables:
            server = table.split('transport_queue_')[1]
            if not server in self.config.servers.keys():
                pdm.delete(table)
                self.logger.info("Deleted the 'transport' persistent queue for the '%s' server, as it is no longer in use." % (server))

        # Monitor all source paths.
        for (name, path) in self.config.sources.items():
            self.logger.info("Monitoring '%s' (%s)." % (path, name))
            self.fsmonitor.add_dir(path, FSMonitor.CREATED | FSMonitor.MODIFIED | FSMonitor.DELETED)


    def run(self):
        if self.config_errors > 0:
            return

        # Do all setup within the run() method to ensure all thread-bound
        # objects are created in the right thread.
        self.setup()

        # Start the FS monitor.
        self.fsmonitor.start()

        while not self.die:
            #self.logger.info("%d threads are running" % (threading.activeCount()))
            self.__sync_queues()
            self.__process_filter_queue()
            self.__process_process_queue()
            self.__process_transport_queues()
            self.__process_db_queue()

            # Syncing the queues 10 times per second is more than sufficient,
            # because files are modified, processed and transported much
            # slower than that.
            time.sleep(0.1)

        self.logger.info("Stopping.")

        # Stop the FSMonitor and wait for its thread to end.
        self.fsmonitor.stop()
        self.fsmonitor.join()
        self.logger.info("Stopped FSMonitor.")

        # Stop the transporters and wait for their threads to end.
        for server in self.transporters.keys():
            for transporter in self.transporters[server]:
                transporter.stop()
                transporter.join()
            self.logger.info("Stopped transporters for the '%s' server." % (server))


    def __sync_queues(self):
        """move data from the thread-crossing (memory) queues to their
        corresponding persistent queues and remove the data from the
        persistent lists"""

        # 'filter' queue
        self.lock.acquire()
        while self.filter_thread_queue.qsize() > 0:
            (monitored_path, event_path, event) = self.filter_thread_queue.get()
            self.filter_queue.put((monitored_path, event_path, event))
            self.logger.info("Syncing: added ('%s', '%s', %d) to the 'filter' persistent queue." % (monitored_path, event_path, event))
        self.lock.release()

        # 'process' queue
        self.lock.acquire()
        while self.process_thread_queue.qsize() > 0:
            (input_file, rule) = self.process_thread_queue.get()
            self.process_queue.put((input_file, rule))
            self.logger.info("Syncing: added '%s' and its processor chain to the 'process' persistent queue." % (input_file))
        self.lock.release()

        # 'transport' queues
        self.lock.acquire()
        for server in self.config.servers.keys():
            while self.transport_thread_queue[server].qsize() > 0:
                (input_file, output_file, action, rule) = self.transport_thread_queue[server].get()

                # Remove the file from the "processing" list. This is only
                # necessary if the file was previously being processed. It's
                # possible that the file didn't need processing, in which
                # case it doesn't have to be removed from any list.
                try:
                    index = self.processing_list.index((input_file, rule))
                    del self.processing_list[index]
                except ValueError:
                    pass

                # Add the file to the "transport" persistent queue for the
                # appropriate server.
                self.transport_queue[server].put((input_file, output_file, action, rule))                

                self.logger.info("Syncing: added '%s' (original file: '%s') and its server '%s' to the 'transport' persistent queue." % (output_file, input_file, server))
        self.lock.release()

        # 'db' queue
        self.lock.acquire()
        while self.db_thread_queue.qsize() > 0:
            (src, dst, url, action, input_file, rule) = self.db_thread_queue.get()
            
            # Remove the file from the "transporting" list. This is only
            # necessary if the file was previously being processed. It's
            # possible that the file didn't need processing, in which case it
            # doesn't have to be removed from any list.
            try:
                index = self.transporting_list.index((input_file, rule))
                del self.transporting_list[index]
            except ValueError:
                pass

            # Add the file to the "db" persistent queue.
            self.db_queue.put((src, dst, url, action, input_file, rule))

            self.logger.info("Syncing: added the synced file '%s' (url: '%s') to the 'db' persistent queue." % (src, rule))
        self.lock.release()


    def __process_filter_queue(self):
        # Process items in the 'filter' queue.
        while self.filter_queue.qsize() > 0:
            # Get the first item from the queue and stored in the persistent
            # 'filtering' list so the data can never get lost.
            self.lock.acquire()
            (monitored_path, event_path, event) = self.filter_queue.get()
            self.filtering_list.append((monitored_path, event_path, event))
            self.lock.release()

            # Find all rules that apply to the detected file event.
            match_found = False
            for rule in self.rules:
                # Try to find a rule that matches the file.
                if rule["filter"].matches(event_path):
                    match_found = True
                    input_file = event_path
                    server     = rule["destination"]["server"]
                    self.logger.info("Filtering: '%s' matches the '%s' rule for the '%s' source!" % (input_file, rule["label"], rule["source"]))
                    # If the file was deleted, also delete the file on all
                    # servers.
                    self.lock.acquire()
                    if event == FSMonitor.DELETED:
                        src = input_file
                        dst = self.__calculate_transporter_dst(src)
                        self.transport_queue[server].put((src, dst, Transporter.DELETE, rule))
                        self.logger.info("Filtering: queued transporter to server '%s' for file '%s' to delete it ('%s' rule)." % (server, input_file, rule["label"]))
                    else:
                        # If a processor chain is configured, queue the file to
                        # be processed. Otherwise, immediately queue the file
                        # to be transported 
                        if not rule["processorChain"] is None:
                            self.process_queue.put((input_file, rule))
                            processor_chain_string = "->".join(rule["processorChain"])
                            self.logger.info("Filtering: queued processor chain '%s' for file '%s' ('%s' rule)." % (processor_chain_string, input_file, rule["label"]))
                        else:
                            src = input_file
                            dst = self.__calculate_transporter_dst(src)
                            self.transport_queue[server].put((src, dst, Transporter.ADD_MODIFY, rule))
                            self.logger.info("Filtering: ueued transporter to server '%s' for file '%s' ('%s' rule)." % (server, input_file, rule["label"]))
                    self.lock.release()

            # Log the lack of matches.
            if not match_found:
                self.logger.info("Filtering: '%s' matches no rules. Discarding this file." % (event_path))

            # Remove the file from the "filtering" list.
            self.lock.acquire()
            index = self.filtering_list.index((monitored_path, event_path, event))
            del self.filtering_list[index]
            self.lock.release()


    def __process_process_queue(self):
        while self.process_queue.qsize() > 0 and self.processorchains_running < MAX_SIMULTANEOUS_PROCESSORCHAINS:
            # Get the first item from the queue and stored in the persistent
            # 'processing' list so the data can never get lost.
            self.lock.acquire()
            (input_file, rule) = self.process_queue.get()
            self.processing_list.append((input_file, rule))
            self.lock.release()

            # Create a curried callback so we can pass the rule metadata to
            # the processor chain callback without passing it to the processor
            # chain (which cannot handle sending additional metadata to its
            # callback function).
            curried_callback = curry(self.processor_chain_callback, rule=rule)

            # Start the processor chain.
            processor_chain = self.processor_chain_factory.make_chain_for(input_file, rule["processorChain"], curried_callback)
            processor_chain.start()

            # Log.
            processor_chain_string = "->".join(rule["processorChain"])
            self.logger.info("Processing: started the '%s' processor chain for the file '%s'." % (processor_chain_string, input_file))


    def __process_transport_queues(self):
        # Don't run more than the allowed number of simultaneous transporters.
        if not self.transporters_running < MAX_SIMULTANEOUS_TRANSPORTERS:
            return

        # Process each server's transport queue.
        for server in self.config.servers.keys():
            while self.transport_queue[server].qsize() > 0:
                # Peek at the first item from the queue
                self.lock.acquire()
                (input_file, output_file, action, rule) = self.transport_queue[server].peek()
                self.lock.release()

                # Get the additional settings from the rule.
                parent_path = ""
                if rule["destination"]["settings"].has_key("path"):
                    parent_path = rule["destination"]["settings"]["path"]

                (id, transporter) = self.__get_transporter(server)
                if not transporter is None:
                    # Get the first item from the queue and stored in the persistent
                    # 'transporting' list so the data can never get lost.
                    self.lock.acquire()
                    (input_file, output_file, action, rule) = self.transport_queue[server].get()
                    self.transporting_list.append((input_file, output_file, action, rule))
                    self.lock.release()

                    # Create a curried callback so we can pass the rule
                    # metadata to the transporter callback without passing it
                    # to the transporter (which cannot handle sending
                    # additional metadata to its callback function).
                    curried_callback = curry(self.transporter_callback,
                                            input_file=input_file,
                                            rule=rule
                                            )

                    # Calculate src and dst for the file, then queue it to be
                    # transported.
                    src = output_file
                    dst = self.__calculate_transporter_dst(src, parent_path)
                    transporter.sync_file(src, dst, action, curried_callback)
                    self.logger.info("Transporting: queued '%s' to transfer to server '%s' with transporter #%d (of %d)." % (output_file, server, id + 1, len(self.transporters[server])))
                else:
                    self.logger.info("Transporting: no more transporters are available for server '%s'." % (server))
                    break

    def __process_db_queue(self):
        # Process items in the 'db' queue.
        while self.db_queue.qsize() > 0:
            self.lock.acquire()
            (src, dst, url, action, input_file, rule) = self.db_queue.get()
            self.lock.release()

            # TODO
            print "Finalizing: storing in DB:", (src, dst, url, action, input_file, rule)


    def __get_transporter(self, server):
        # Try to find a running transporter that is ready for new work.
        for id in range(0, len(self.transporters[server])):
            transporter = self.transporters[server][id]
            if transporter.is_ready():
                return (id, transporter)

        # Since we didn't find any ready transporter, check if we can create
        # a new one.
        if self.config.servers[server]["maxConnections"] < len(self.transporters[server]):
            id          = len(self.transporters[server]) - 1
            transporter = self.__create_transporter(server)
            return (id, transporter)
        else:
            return None


    def __create_transporter(self, server):
        transporter_name = self.config.servers[server]["transporter"]
        settings = self.config.servers[server]["settings"]

        # Determine which class to import.
        transporter_modulename = "transporters.transporter_" + transporter_name
        _temp = __import__(transporter_modulename, globals(), locals(), ["TRANSPORTER_CLASS"], -1)
        transporter_classname = _temp.TRANSPORTER_CLASS

        # Get a reference to that class.
        module = __import__(transporter_modulename, globals(), locals(), [transporter_classname])
        transporter_class = getattr(module, transporter_classname)

        # Create an instance of the transporter and add it to the pool.
        transporter = transporter_class(settings, self.transporter_callback)
        transporter.start()
        self.transporters[server].append(transporter)

        self.transporters_running += 1
        self.logger.info("Created '%s' transporter for the '%s' server." % (transporter_name, server))

        return transporter


    def __calculate_transporter_dst(self, src, parent_path=None):
        dst = src

        # Strip off the working directory.
        if dst.startswith(WORKING_DIR):
            dst = dst[len(WORKING_DIR):]

        # Prepend any possible parent path.
        if not parent_path is None:
            dst = os.path.join(parent_path, dst)

        return dst


    def fsmonitor_callback(self, monitored_path, event_path, event):
        print "FSMONITOR CALLBACK FIRED:\n\tmonitored_path='%s'\n\tevent_path='%s'\n\tevent=%d" % (monitored_path, event_path, event)
        # Ignore directories.
        if not stat.S_ISDIR(os.stat(event_path)[stat.ST_MODE]):
            self.lock.acquire()
            self.filter_thread_queue.put((monitored_path, event_path, event))
            self.lock.release()


    def processor_chain_callback(self, input_file, output_file, rule):
        print "PROCESSOR CHAIN CALLBACK FIRED\n\tinput_file='%s'\n\toutput_file='%s'" % (input_file, output_file)

        # We need to know to which server this file should be transported to
        # in order to know in which queue to put the file.
        server = rule["destination"]["server"]

        # Queue the file to the thread-crossing "transport" queue.
        self.lock.acquire()
        self.transport_thread_queue[server].put((input_file, output_file, Transporter.ADD_MODIFY, rule))
        self.lock.release()


    def transporter_callback(self, src, dst, url, action, input_file, rule):
        print "TRANSPORTER CALLBACK FIRED:\n\tsrc='%s'\n\tdst='%s'\n\turl='%s'\n\taction=%d\n\t(curried): input_file='%s'" % (src, dst, url, action, input_file)

        # Queue the file to the thread-crossing "db" queue.
        self.lock.acquire()
        self.db_thread_queue.put((src, dst, url, action, input_file, rule))
        self.lock.release()


    def stop(self):
        self.logger.info("Signaling to stop.")
        self.lock.acquire()
        self.die = True
        self.lock.release()


if __name__ == '__main__':
    arbitrator = Arbitrator("config.sample.xml")
    arbitrator.start()
    if arbitrator.isAlive():
        time.sleep(30)
        arbitrator.stop()
        arbitrator.join()
    

    # def handleKeyboardInterrupt(signalNumber, frame):
    #     print "stopping"
    #     arbitrator.stop()
    #     print "stopped!"
    # 
    # try :
    #     # Register a signal handler for ctrl-C, control-z
    #     signal.signal(signal.SIGINT, handleKeyboardInterrupt)
    #     signal.signal(signal.SIGTSTP, handleKeyboardInterrupt)
    # 
    #     # Signal doesn't work.
    #     arbitrator.start()
    # 
    #     # Signal works (because no separate thread is started).
    #     #arbitrator.run()
    # finally:
    #     pass
