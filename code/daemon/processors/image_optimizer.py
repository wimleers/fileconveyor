__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os
import stat


COPY_METADATA_NONE = "none"
COPY_METADATA_ALL  = "all"
FILENAME_MUTABLE   = True
FILENAME_IMMUTABLE = False


class Base(Processor):
    """optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)"""


    valid_extensions = (".gif", ".png", ".jpg", ".jpeg")


    def __init__(self, input_file, working_dir="/tmp", copy_metadata=COPY_METADATA_NONE, filename_mutable=FILENAME_MUTABLE):
        Processor.__init__(self, input_file, working_dir)
        self.copy_metadata    = copy_metadata
        self.filename_mutable = filename_mutable
        self.devnull = open(os.devnull, 'w')


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self, self.__class__.valid_extensions):
            return self.input_file

        format = self.__identify_format(self.input_file)

        if format == "GIF":
            if self.filename_mutable == FILENAME_MUTABLE:
                tmp_file         = os.path.join(self.working_dir, name + ".tmp.png")
                self.output_file = os.path.join(self.working_dir, name + ".png")
                self.__optimize_GIF(self.input_file, tmp_file, self.output_file)

        elif format == "PNG":
            self.output_file = os.path.join(self.working_dir, filename)
            self.__optimize_PNG(self.input_file, self.output_file)

        elif format == "JPEG":
            self.output_file = os.path.join(self.working_dir, filename)
            self.__optimize_JPEG(self.input_file, self.output_file, self.copy_metadata)

        # Animated GIF
        elif len(format) >= 6 and format[0:6] == "GIFGIF":
            self.output_file = os.path.join(self.working_dir, filename)
            self.__optimize_animated_GIF(self.input_file, self.output_file)
        
        # Clean up things.
        self.devnull.close()

        return self.output_file


    def __identify_format(self, filename):
        p = subprocess.Popen("identify -format %%m %s" % (filename),
                             shell=True,
                             stdout=subprocess.PIPE
                             )
        return p.communicate()[0].rstrip()


    def __optimize_GIF(self, input_file, tmp_file, output_file):
        # Convert to temporary PNG.
        subprocess.call("convert %s %s" % (input_file, tmp_file),
                        shell=True,
                        stdout=subprocess.PIPE
                        )
        # Optimize temporary PNG.
        subprocess.call("pngcrush -rem alla -reduce %s %s" % (tmp_file, output_file),
                        shell=True,
                        stdout=subprocess.PIPE
                        )
        # Remove temporary PNG.
        os.remove(tmp_file)



    def __optimize_PNG(self, input_file, output_file):
        subprocess.call("pngcrush -rem alla -reduce %s %s" % (input_file, output_file),
                        shell=True,
                        stdout=subprocess.PIPE
                        )


    def __optimize_JPEG(self, input_file, output_file, copy_metadata):
        filesize = os.stat(input_file)[stat.ST_SIZE]
        # If the file is 10 KB or larger, JPEG's progressive mode
        # typically results in a higher compression ratio.
        if filesize < 10 * 1024:
            subprocess.call("jpegtran -copy %s -optimize %s > %s" % (copy_metadata, input_file, output_file),
                            shell=True,
                            stdout=subprocess.PIPE
                            )
        else:
            subprocess.call("jpegtran -copy %s -progressive -optimize %s > %s" % (copy_metadata, input_file, output_file),
                            shell=True,
                            stdout=subprocess.PIPE
                            )


    def __optimize_animated_GIF(self, input_file, output_file):
        subprocess.call("gifsicle -O2 %s > %s" % (input_file, output_file),
                        shell=True,
                        stdout=subprocess.PIPE
                        )


class Max(Base):
    """optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)"""

    def __init__(self, input_file, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      working_dir="/tmp",
                      copy_metadata=COPY_METADATA_NONE, # Don't keep metadata
                      filename_mutable=FILENAME_MUTABLE # Do change filenames
                      )


class KeepMetadata(Base):
    """same as Max, but keeps JPEG metadata"""

    def __init__(self, input_file, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      working_dir,
                      copy_metadata=COPY_METADATA_ALL,  # Do keep metadata
                      filename_mutable=FILENAME_MUTABLE # Don't change filenames
                      )


class KeepFilename(Base):
    """same as Max, but keeps the original filename (no GIF optimization)"""

    def __init__(self, input_file, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      working_dir,
                      copy_metadata=COPY_METADATA_NONE,   # Don't keep metadata
                      filename_mutable=FILENAME_IMMUTABLE # Do keep filenames
                      )


class KeepMetadataAndFilename(Base):
    """same as Max, but keeps JPEG metadata and the original filename (no GIF optimization)"""

    def __init__(self, input_file, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      working_dir,
                      copy_metadata=COPY_METADATA_ALL,    # Do keep metadata
                      filename_mutable=FILENAME_IMMUTABLE # Do keep filenames
                      )


if __name__ == "__main__":
    import time

    p = Max("logo.gif")
    print p.run()
    p = Max("test.png")
    print p.run()
    p = Max("test.jpg")
    print p.run()
    p = Max("animated.gif")
    print p.run()
    p = Max("processor.pyc")
    print p.run()

    # Should result in a JPEG file that contains all original metadata.
    p = KeepMetadata("test.jpg", "/tmp/KeepMetadata")
    print p.run()

    # Should keep the original GIF file, as the only possible optimizaton is
    # to convert it from GIF to PNG, but that would change the filename.
    p = KeepFilename("test.gif", "/tmp/KeepFilename")
    print p.run()

    # Should act as the combination of the two above
    p = KeepMetadataAndFilename("test.jpg", "/tmp/KeepMetadataAndFilename")
    print p.run()
    p = KeepMetadataAndFilename("test.gif", "/tmp/KeepMetadataAndFilename")
    print p.run()
