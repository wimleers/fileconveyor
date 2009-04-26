__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os.path
import stat
import shutil


class UniqueFilenameMtime(Processor):
    """gives the file a unique filename based on its mtime"""


    def __init__(self, input_file, callback, working_dir="/tmp"):
        Processor.__init__(self, input_file, callback, working_dir="/tmp")


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self):
            return self.callback(self.input_file, self.input_file)

        mtime = os.stat(self.input_file)[stat.ST_MTIME]
        self.output_file = os.path.join(self.working_dir, name + "_" + str(mtime) + extension)

        shutil.copyfile(self.input_file, self.output_file)

        # We're done, perform the callback!
        self.callback(self.input_file, self.output_file)


if __name__ == "__main__":
    import time

    def callbackfunc(input_file, output_file):
        print "CALLBACK FIRED: intput_file=%s, output_file=%s" % (input_file, output_file)

    p = UniqueFilenameMtime("logo.gif", callbackfunc)
    p.run()
