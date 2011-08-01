"""transporter.py Transporter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import os.path
import signal
import time


class DaemonThreadRunner(object):
    """runs a thread as a daemon and provides a PID file through which you can
    kill the daemon (kill -TERM `cat pidfile`)"""

    pidfile_check_interval = 60
    pidfile_permissions    = 0600

    def __init__(self, thread, pidfile):
        self.thread             = thread
        self.running            = False
        self.pidfile            = os.path.expanduser(pidfile)
        self.last_pidfile_check = 0

        # Configure signal handler.
        signal.signal(signal.SIGINT,  self.handle_interrupt)
        signal.signal(signal.SIGTSTP, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)


    def start(self):
        self.write_pid_file()

        # Start the daemon thread.
        self.running = True
        self.thread.setDaemon(True)
        self.thread.start()

        # While running, keep the PID file updated and sleep.
        while self.running:
            self.update_pid_file()
            time.sleep(1)

        # Remove the PID file.
        if os.path.isfile(self.pidfile):
            os.remove(self.pidfile)


    def handle_interrupt(self, signalNumber, frame):
        self.thread.stop()
        self.thread.join()
        self.running = False


    def write_pid_file(self):
        pid = os.getpid()
        open(self.pidfile, 'w+').write(str(pid))
        os.chmod(self.pidfile, self.pidfile_permissions)


    def update_pid_file(self):
        # Recreate the file when it is deleted.
        if not os.path.isfile(self.pidfile):
            self.write_pid_file()

        # Update the file every interval.
        if self.last_pidfile_check + self.pidfile_check_interval < time.time():
            self.write_pid_file()
            self.last_pidfile_check = time.time()
