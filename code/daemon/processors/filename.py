__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import subprocess
import os.path
import shutil
import hashlib


class Base(Processor):
    """replaces one set of strings with another set"""


    def __init__(self, input_file, working_dir="/tmp", search=[], replace=[]):
        Processor.__init__(self, input_file, working_dir)
        self.search  = search
        self.replace = replace


    def run(self):
        (path, filename, name, extension) = Processor.get_path_parts(self, self.input_file)

        # Return the input file if the file cannot be processed.
        if not Processor.validate(self) or len(self.search) != len(self.replace):
            return self.input_file

        # Update the filename.
        new_filename = filename
        for i in range(0, len(self.search)):
            new_filename = new_filename.replace(self.search[i], self.replace[i])

        self.output_file = os.path.join(self.working_dir, path, new_filename)
        shutil.copyfile(self.input_file, self.output_file)

        return self.output_file


        def __init__(self, input_file, working_dir="/tmp"):
            Base.__init__(self,
                          input_file,
                          working_dir,
                          copy_metadata=COPY_METADATA_ALL,    # Do keep metadata
                          filename_mutable=FILENAME_IMMUTABLE # Do keep filenames
                          )


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
