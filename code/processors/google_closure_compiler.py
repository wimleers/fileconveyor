__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path


class GoogleClosureCompiler(Processor):
    """compresses .js files with Google Closure Compiler"""


    valid_extensions = (".js")


    def run(self):
        # We don't rename the file, so we can use the default output file.

        # Run Google Closure Compiler on the file.
        compiler_path = os.path.join(self.processors_path, "compiler.jar")
        (stdout, stderr) = self.run_command("java -jar %s --js %s --js_output_file %s" % (compiler_path, self.input_file, self.output_file))

        # Raise an exception if an error occurred.
        if not stderr == "":
            raise ProcessorError(stderr)

        return self.output_file
