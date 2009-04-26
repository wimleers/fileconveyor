__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os.path
import shutil
import hashlib


class UniqueFilenameMD5(Processor):
    """gives the file a unique filename based on its MD5 hash"""


    def __init__(self, input_file, callback, working_dir="/tmp"):
        Processor.__init__(self, input_file, callback, working_dir="/tmp")


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self):
            return self.callback(self.input_file, self.input_file)

        md5 = self.md5(self.input_file)
        self.output_file = os.path.join(self.working_dir, name + "_" + md5 + extension)

        shutil.copyfile(self.input_file, self.output_file)

        # We're done, perform the callback!
        self.callback(self.input_file, self.output_file)


    def md5(self, filename):
        """compute the md5 hash of the specified file"""
        m = hashlib.md5()
        try:
            f = open(filename, "rb")
        except IOError:
            print "Unable to open the file in readmode:", filename
            raise FileIOError

        line = f.readline()
        while line:
            m.update(line)
            line = f.readline()
        f.close()
        return m.hexdigest()


if __name__ == "__main__":
    import time

    def callbackfunc(input_file, output_file):
        print "CALLBACK FIRED: intput_file=%s, output_file=%s" % (input_file, output_file)

    p = UniqueFilenameMD5("logo.gif", callbackfunc)
    p.run()
