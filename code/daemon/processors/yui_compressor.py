__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os.path


class YUICompressor(Processor):
    """compresses .css and .js files with the YUI Compressor"""


    valid_extensions = (".css", ".js")


    def __init__(self, input_file, working_dir="/tmp", search=[], replace=[]):
        Processor.__init__(self, input_file, working_dir)
        self.yuicompressor_path = os.path.join(self.processors_path, "yuicompressor.jar")


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self):
            return self.input_file

        self.output_file = os.path.join(self.working_dir, path, filename)        
        p = subprocess.Popen("java -jar %s %s -o %s" % (self.yuicompressor_path, self.input_file, self.output_file),
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             )

        # Raise an exception if an error occurred.
        error = p.communicate()[1].rstrip()
        if not error == "":
            raise Exception(error)

        return self.output_file
