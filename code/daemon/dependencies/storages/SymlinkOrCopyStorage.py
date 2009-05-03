import os
import os.path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class SymlinkOrCopyStorage(FileSystemStorage):
    """Stores symlinks to files instead of actual files whenever possible
    
    When a file that's being saved is currently stored in the symlinkWithin
    directory, then symlink the file. Otherwise, copy the file.
    """


    def __init__(self, location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL, symlinkWithin=None):
        FileSystemStorage.__init__(self, location, base_url)
        self.symlinkWithin = symlinkWithin.split(":")


    def _save(self, name, content):
        full_path_dst = self.path(name)

        directory = os.path.dirname(full_path_dst)
        if not os.path.exists(directory):
            os.makedirs(directory)
        elif not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        full_path_src = os.path.abspath(content.name)

        symlinked = False
        for path in self.symlinkWithin:
            if full_path_src.startswith(path):
                os.symlink(full_path_src, full_path_dst)
                symlinked = True
                break

        if not symlinked:
            FileSystemStorage._save(self, name, content)

        return name
