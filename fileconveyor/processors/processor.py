__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


# Define exceptions.
class ProcessorError(Exception): pass
class InvalidCallbackError(ProcessorError): pass
class FileIOError(ProcessorError): pass
class RequestToRequeueException(ProcessorError): pass
class DocumentRootAndBasePathRequiredException(ProcessorError): pass


import threading
import os
import os.path
import logging
import copy
import subprocess


class Processor(object):
    """base class for file processors"""


    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        self.input_file         = input_file
        self.original_file      = original_file
        self.document_root      = document_root
        self.base_path          = base_path
        self.process_for_server = process_for_server
        self.working_dir        = working_dir
        self.parent_logger      = parent_logger

        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        # The file will end up in the working directory, in its relative path.
        # It doesn't hurt to have empty directory trees, so create this
        # already here to simplify the processors themselves.
        output_file_path = os.path.join(self.working_dir, path)
        if not os.path.exists(output_file_path):
            os.makedirs(output_file_path)

        # Set the default output file: the input file's base name.
        self.set_output_file_basename(basename)

        # Calculate the path to the processors in the Processor class so
        # subclasses don't have to.
        self.processors_path = os.path.dirname(os.path.realpath(__file__))


    def run(self):
        raise NotImplemented


    def get_path_parts(self, path):
        """get the different parts of the file's path"""

        (path, basename) = os.path.split(path)
        (name, extension) = os.path.splitext(basename)

        # Return the original relative path instead of the absolute path,
        # which may be inside the working directory because the file has been
        # processed by one processor already.
        if path.startswith(self.working_dir):
            path = path[len(self.working_dir):]

        # Ensure no absolute path is returned, which would make os.path.join()
        # fail.
        path = path.lstrip(os.sep)

        return (path, basename, name, extension)


    def would_process_input_file(cls, input_file):
        """check if a given input file would be processed by this processor"""

        (path, extension) = os.path.splitext(input_file)

        # Get some variables "as if it were magic", i.e., from subclasses of
        # this class.
        valid_extensions = getattr(cls, "valid_extensions", ())

        # Does the input file have one of the valid extensions?
        if len(valid_extensions) > 0 and extension.lower() not in valid_extensions:
            return False

        return True
    would_process_input_file = classmethod(would_process_input_file)


    def validate_settings(self):
        """validate the input file and its extensions"""

        if not os.path.exists(self.input_file):
            return False
        if not self.__class__.would_process_input_file(self.input_file):
            return False
        return True


    def run_command(self, command):
        """run a command and get (stdout, stderr) back"""

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        (stdout, stderr) = (stdout.rstrip(), stderr.rstrip())
        return (stdout, stderr)


    def set_output_file_basename(self, output_file_basename):
        """set the output file's basename (changing the path is not allowed)"""

        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.input_file)

        self.output_file = os.path.join(self.working_dir, path, output_file_basename)


class ProcessorChain(threading.Thread):
    """chains the given file processors (runs them in sequence)"""


    def __init__(self, processors, input_file, document_root, base_path, process_for_server, callback, error_callback, parent_logger, working_dir="/tmp"):
        if not callable(callback):
            raise InvalidCallbackError("callback function is not callable")
        if not callable(error_callback):
            raise InvalidCallbackError("error_callback function is not callable")

        self.processors         = processors
        self.input_file         = input_file
        self.output_file        = None
        self.document_root      = document_root
        self.base_path          = base_path
        self.process_for_server = process_for_server
        self.callback           = callback
        self.error_callback     = error_callback
        self.working_dir        = working_dir
        self.logger             = logging.getLogger(".".join([parent_logger, "ProcessorChain"]))

        self.parent_logger_for_processor = ".".join([parent_logger, "ProcessorChain"]);

        threading.Thread.__init__(self, name="ProcessorChainThread")


    def run(self):
        self.output_file = self.input_file

        # Run all processors in the chain.
        while len(self.processors):
            # Get next processor.
            processor_classname = self.processors.pop(0)

            # Get a reference to that class.
            (modulename, classname) = processor_classname.rsplit(".", 1)
            module = __import__(modulename, globals(), locals(), [classname])
            processor_class = getattr(module, classname)

            # Run the processor.
            old_output_file = self.output_file
            processor = processor_class(            
                input_file         = self.output_file,
                original_file      = self.input_file,
                document_root      = self.document_root,
                base_path          = self.base_path,
                process_for_server = self.process_for_server,
                parent_logger      = self.parent_logger_for_processor,
                working_dir        = self.working_dir,
            )
            if processor.validate_settings():
                self.logger.debug("Running the processor '%s' on the file '%s'." % (processor_classname, self.output_file))
                try:
                    self.output_file = processor.run()
                except RequestToRequeueException, e:
                    self.logger.warning("The processor '%s' has requested to requeue the file '%s'. Message: %s." % (processor_classname, self.input_file, e))
                    self.error_callback(self.input_file)
                    return
                except DocumentRootAndBasePathRequiredException, e:
                    self.logger.warning("The processor '%s' has skipped processing the file '%s' because the document root and/or base path are not set for the source associated with the file." % (processor_classname, self.input_file))
                except Exception, e:
                    self.logger.error("The processsor '%s' has failed while processing the file '%s'. Exception class: %s. Message: %s." % (processor_classname, self.input_file, e.__class__, e))
                    self.error_callback(self.input_file)
                    return
                else:
                    self.logger.debug("The processor '%s' has finished processing the file '%s', the output file is '%s'." % (processor_classname, self.input_file, self.output_file))

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


    def make_chain_for(self, input_file, processors, document_root, base_path, process_for_server, callback, error_callback):
        return ProcessorChain(copy.copy(processors), input_file, document_root, base_path, process_for_server, callback, error_callback, self.parent_logger, self.working_dir)
