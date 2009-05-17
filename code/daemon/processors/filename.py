__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os.path
import shutil
import hashlib


class Base(Processor):
    """replaces one set of strings with another set"""


    valid_extensions = () # Any extension is valid.


    def __init__(self, input_file, working_dir="/tmp", search=[], replace=[]):
        Processor.__init__(self, input_file, working_dir)
        self.search  = search
        self.replace = replace


    def run(self):
        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.input_file)

        # Update the file's base name.
        new_filename = basename
        for i in range(0, len(self.search)):
            new_filename = new_filename.replace(self.search[i], self.replace[i])

        # Set the output file base name.
        self.set_output_file_basename(new_filename)

        # Copy the file.
        shutil.copyfile(self.input_file, self.output_file)

        return self.output_file


class SpacesToUnderscores(Base):
  """replaces spaces in the filename with underscores ("_")"""

  def __init__(self, input_file, working_dir="/tmp"):
      Base.__init__(self,
                    input_file,
                    working_dir,
                    [" "],
                    ["_"]
                    )


class SpacesToDashes(Base):
    """replaces spaces in the filename with dashes ("-")"""

    def __init__(self, input_file, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      working_dir,
                      [" "],
                      ["-"]
                      )


if __name__ == "__main__":
    import time

    p = SpacesToUnderscores("test this.txt")
    print p.run()
    p = SpacesToDashes("test this.txt")
    print p.run()
