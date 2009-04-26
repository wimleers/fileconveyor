__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os
import stat


class ImageOptimizer(Processor):
    """optimizes image files losslessly (GIF, PNG, JPEG)"""


    valid_extensions = (".gif", ".png", ".jpg", ".jpeg")
    jpegtran_copy_metadata = "none"


    def __init__(self, input_file, callback, working_dir="/tmp"):
        Processor.__init__(self, input_file, callback, working_dir="/tmp")
        self.devnull = open(os.devnull, 'w')


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self, self.__class__.valid_extensions):
            return self.callback(self.input_file, self.input_file)

        # Identify the format.
        p = subprocess.Popen("identify -format %%m %s" % (self.input_file),
                             shell=True,
                             stdout=subprocess.PIPE,
                             )
        format = p.communicate()[0].rstrip()

        if format == "GIF":
            tmp_file = os.path.join(self.working_dir, name + ".tmp.png")
            self.output_file = os.path.join(self.working_dir, name + ".png")
            # Convert to temporary PNG.
            subprocess.call("convert %s %s" % (self.input_file, tmp_file), shell=True, stdout=subprocess.PIPE)
            # Optimize temporary PNG.
            subprocess.call("pngcrush -rem alla -reduce %s %s" % (tmp_file, self.output_file), shell=True, stdout=subprocess.PIPE)
            # Remove temporary PNG.
            os.remove(tmp_file)

        elif format == "PNG":
            self.output_file = os.path.join(self.working_dir, filename)
            subprocess.call("pngcrush -rem alla -reduce %s %s" % (self.input_file, self.output_file), shell=True, stdout=subprocess.PIPE)

        elif format == "JPEG":
            self.output_file = os.path.join(self.working_dir, filename)
            filesize = os.stat(self.input_file)[stat.ST_SIZE]
            # If the file is 10 KB or larger, JPEG's progressive mode
            # typically results in a higher compression ratio.
            if filesize < 10 * 1024:
                subprocess.call("jpegtran -copy %s -optimize %s > %s" % (self.__class__.jpegtran_copy_metadata, self.input_file, self.output_file), shell=True, stdout=subprocess.PIPE)
            else:
                subprocess.call("jpegtran -copy %s -progressive -optimize %s > %s" % (self.__class__.jpegtran_copy_metadata, self.input_file, self.output_file), shell=True, stdout=subprocess.PIPE)

        # Animated GIF
        elif len(format) >= 6 and format[0:6] == "GIFGIF":
            self.output_file = os.path.join(self.working_dir, filename)
            subprocess.call("gifsicle -O2 %s > %s" % (self.input_file, self.output_file), shell=True, stdout=subprocess.PIPE)
        
        # Clean up things.
        self.devnull.close()

        # We're done, perform the callback!
        self.callback(self.input_file, self.output_file)


if __name__ == "__main__":
    import time

    def callbackfunc(input_file, output_file):
        print "CALLBACK FIRED: input_file=%s, output_file=%s" % (input_file, output_file)

    p = ImageOptimizer("logo.gif", callbackfunc)
    p.run()
    p = ImageOptimizer("test.png", callbackfunc)
    p.run()
    p = ImageOptimizer("test.jpg", callbackfunc)
    p.run()
    p = ImageOptimizer("animated.gif", callbackfunc)
    p.run()
    p = ImageOptimizer("processor.pyc", callbackfunc)
    p.run()
