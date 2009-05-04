__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


# Define exceptions.
class ProcessorError(Exception): pass
class InvalidCallbackError(ProcessorError): pass
class FileIOError(ProcessorError): pass


import threading
import os
import os.path
import logging
import copy
from distutils.dir_util import mkpath


class Processor(object):
    """base class for file processors"""


    def __init__(self, input_file, working_dir="/tmp"):
        self.input_file  = input_file
        self.output_file = None
        self.working_dir = working_dir
        if not os.path.exists(self.working_dir):
            mkpath(self.working_dir)

        # Calculate the path to the processors in the Processor class so
        # subclasses don't have to.
        self.processors_path = os.path.dirname(os.path.realpath(__file__))


    def run(self):
        raise NotImplemented


    def get_path_parts(self, path):
        """get the different parts of the file's path"""
        (path, filename) = os.path.split(path)
        (name, extension) = os.path.splitext(filename)

        # Return the original relative path instead of the absolute path,
        # which may be inside the working directory because the file has been
        # processed by one processor already.
        if path.startswith(self.working_dir):
            path = path[len(self.working_dir):]

        # Ensure no absolute path is returned, which would make os.path.join()
        # fail.
        path = path.lstrip(os.sep)

        # The file will most likely end up in the working directory, in its
        # relative path. It doesn't hurt to have empty directory trees, so
        # create this already here to simplify the processors themselves.
        working_dir_plus_path = os.path.join(self.working_dir, path)
        if not os.path.exists(working_dir_plus_path):
            mkpath(working_dir_plus_path)

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


class ProcessorChain(threading.Thread):
    """chains the given file processors (runs them in sequence)"""


    def __init__(self, processors, input_file, callback, parent_logger, working_dir="/tmp"):
        if not callable(callback):
            raise InvalidCallbackError
        self.processors    = processors
        self.input_file    = input_file
        self.output_file   = None
        self.callback      = callback
        self.working_dir   = working_dir
        self.logger        = logging.getLogger(".".join([parent_logger, "ProcessorChain"]))
        threading.Thread.__init__(self)


    def run(self):
        self.output_file = self.input_file

        # Run all processors in the chain.
        while len(self.processors):
            # Get next processor.
            processor_classname = self.processors.pop(0)

            # Get a reference to that class.
            (modulename, classname) = processor_classname.split(".")
            module = __import__(modulename, globals(), locals(), [classname])
            processor_class = getattr(module, classname)

            # Run the processor.
            old_output_file = self.output_file
            processor = processor_class(self.output_file, self.working_dir)
            self.logger.info("Running the processor '%s' on the file '%s'." % (processor_classname, self.output_file))
            self.output_file = processor.run()
            self.logger.info("The processor '%s' has finished processing the file '%s', the output file is '%s'." % (processor_classname, self.output_file, self.output_file))

            # Delete the old output file if applicable. But never ever remove
            # the input file!
            if old_output_file != self.output_file and old_output_file != self.input_file:
                os.remove(old_output_file)

        # All done, call the callback!
        self.callback(self.input_file, self.output_file)


class ProcessorChainFactory(object):
    """produces ProcessorChain objects whenever requested"""


    def __init__(self, parent_logger, working_dir="/tmp"):
        self.parent_logger = parent_logger
        self.working_dir   = working_dir


    def make_chain_for(self, input_file, processors, callback):
        return ProcessorChain(copy.copy(processors), input_file, callback, self.parent_logger, self.working_dir)


if __name__ == '__main__':
    import time
    import logging.handlers

    def callbackfunc(input_file, output_file):
        print "CALLBACK FIRED, input_file='%s', output_file='%s'" % (input_file, output_file)

    # Set up logging.
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("processor.log")
    logger.addHandler(handler)

    # Use a ProcessorChainFactory.
    processors = [
        "image_optimizer.KeepFilename",
        "unique_filename.Mtime"
    ]
    factory = ProcessorChainFactory(processors, callbackfunc, "test")
    chain = factory.make_chain_for("test.jpg")
    chain.run()
    chain = factory.make_chain_for("test.png")
    chain.run()
    