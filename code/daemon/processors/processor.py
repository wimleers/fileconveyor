__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


# Define exceptions.
class ProcessorError(Exception): pass
class InvalidCallbackError(ProcessorError): pass
class FileIOError(ProcessorError): pass


import threading
import os.path


class Processor(threading.Thread):
    """Base class for threaded file processors"""


    def __init__(self, input_file, callback, working_dir="/tmp"):
        if not callable(callback):
            raise InvalidCallbackError
        self.input_file  = input_file
        self.output_file = None
        self.callback    = callback
        self.working_dir = working_dir
        threading.Thread.__init__(self)


    def run(self):
        raise NotImplemented


    def get_path_parts(self, path):
        """get the different parts of the file's path"""
        (path, filename) = os.path.split(path)
        (name, extension) = os.path.splitext(filename)
        return (path, filename, name, extension)


    def validate(self, valid_extensions=()):
        (path, filename, name, extension) = self.get_path_parts(self.input_file)

        # Does the input file exist?
        if not os.path.exists(self.input_file):
            return False
        
        # Does the input file have one of the valid extensions?
        if len(valid_extensions) > 0 and extension.lower() not in valid_extensions:
            return False

        return True
