__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path


class YUICompressor(Processor):
    """compresses .css and .js files with the YUI Compressor"""


    valid_extensions = (".css", ".js")


    def __init__(self, input_file, working_dir="/tmp"):
        Processor.__init__(self, input_file, working_dir)


    def run(self):
        # Return the input file if the file cannot be processed.
        if not Processor.validate(self):
            return self.input_file

        # We don't rename the file, so we can use the default output file.

        # Remove the output file if it already exists, otherwise YUI
        # Compressor will fail.
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

        # Run YUI Compressor on the file.
        yuicompressor_path = os.path.join(self.processors_path, "yuicompressor.jar")
        (stdout, stderr) = self.run_command("java -jar %s %s -o %s" % (yuicompressor_path, self.input_file, self.output_file))

        # Raise an exception if an error occurred.
        if not stderr == "":
            raise Exception(error)

        return self.output_file


if __name__ == "__main__":
    p = YUICompressor("test.css")
    print p.run()
    p = YUICompressor("test.js")
    print p.run()
