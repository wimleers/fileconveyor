__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path
import shutil


class YUICompressor(Processor):
    """compresses .css and .js files with YUI Compressor"""


    valid_extensions = (".css", ".js")


    def run(self):
        # We don't rename the file, so we can use the default output file.

        # The YUI Compressor crashes if the output file already exists.
        # Therefor, we're using a temporary output file and copying that to
        # the final output file afterwards.
        tmp_file = self.output_file + ".tmp"
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Run YUI Compressor on the file.
        yuicompressor_path = os.path.join(self.processors_path, "yuicompressor.jar")
        (stdout, stderr) = self.run_command("java -jar %s %s -o %s" % (yuicompressor_path, self.input_file, tmp_file))

        # Copy the temporary output file to the final output file and remove
        # the temporary output file.
        shutil.copy(tmp_file, self.output_file)
        os.remove(tmp_file)

        # Raise an exception if an error occurred.
        if not stderr == "":
            raise ProcessorError(stderr)

        return self.output_file


if __name__ == "__main__":
    p = YUICompressor("test.css")
    print p.run()
    p = YUICompressor("test.js")
    print p.run()
