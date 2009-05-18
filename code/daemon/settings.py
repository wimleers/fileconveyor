__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import logging


LOG_FILE = './daemon.log'
PERSISTENT_DATA_DB = './persistent_data.db'
SYNCED_FILES_DB = './synced_files.db'
WORKING_DIR = '/tmp/daemon'
MAX_FILES_IN_PIPELINE = 50
MAX_SIMULTANEOUS_PROCESSORCHAINS = 1
MAX_SIMULTANEOUS_TRANSPORTERS = 10
MAX_TRANSPORTER_QUEUE_SIZE = 1
QUEUE_PROCESS_BATCH_SIZE = 20
CALLBACKS_CONSOLE_OUTPUT = False
CONSOLE_LOGGER_LEVEL = logging.WARNING
FILE_LOGGER_LEVEL = logging.INFO
