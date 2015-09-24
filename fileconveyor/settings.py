__author__ = "Wim Leers (work@wimleers.com), Christopher Blay (chris.b.blay@gmail.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"

import logging
 
RESTART_AFTER_UNHANDLED_EXCEPTION = True
RESTART_INTERVAL = 10
LOG_FILE = './fileconveyor.log'
PID_FILE = '~/.fileconveyor.pid'
PERSISTENT_DATA_DB = './persistent_data.db'
WORKING_DIR = '/tmp/fileconveyor'

SYNCED_FILES_BACKEND = 'sqlite'       # also could be 'mysql'
                                      # default is 'sqlite'
SYNCED_FILES_DB = './synced_files.db' # path to file if backend is 'sqlite'
                                      # name of database if backend is 'mysql'
                                      # default is './synced_files.db'
SYNCED_FILES_TABLE = 'synced_files'   # name of table in the database to use
                                      # default is 'synced_files'
SYNCED_FILES_HOST = 'localhost'       # only applicible if backend is 'mysql'
SYNCED_FILES_USER = 'username'        # only applicible if backend is 'mysql'
SYNCED_FILES_PASS = 'password'        # only applicible if backend is 'mysql'

MAX_FILES_IN_PIPELINE = 50
MAX_SIMULTANEOUS_PROCESSORCHAINS = 1
MAX_SIMULTANEOUS_TRANSPORTERS = 10

MAX_TRANSPORTER_QUEUE_SIZE = 1
QUEUE_PROCESS_BATCH_SIZE = 20
CALLBACKS_CONSOLE_OUTPUT = False
CONSOLE_LOGGER_LEVEL = logging.WARNING
FILE_LOGGER_LEVEL = logging.INFO
RETRY_INTERVAL = 30
