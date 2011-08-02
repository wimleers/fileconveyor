"""pathscanner.py Scans paths and stores them in a sqlite3 database

You can use PathScanner to detect changes in a directory structure. For
efficiency, only creations, deletions and modifications are detected, not
moves.

Modified files are detected by looking at the mtime.

Instructions:
- Use initial_scan() to build the initial database.
- Use scan() afterwards, to get the changes.
- Use scan_tree() (which uses scan()) to get the changes in an entire
  directory structure.
- Use purge_path() to purge all the metadata for a path from the database.
- Use (add|update|remove)_files() to add/update/remove files manually (useful
  when your application has more/faster knowledge of changes)

TODO: unit tests (with *many* mock functions). Stable enough without them.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import stat
import sqlite3
from sets import Set


class PathScanner(object):
    """scan paths for changes, persistent storage using SQLite"""
    def __init__(self, dbcon, ignored_dirs=[], table="pathscanner", commit_interval=50):
        self.dbcon                  = dbcon
        self.dbcur                  = dbcon.cursor()
        self.ignored_dirs           = ignored_dirs
        self.table                  = table
        self.uncommitted_statements = 0
        self.commit_interval        = commit_interval
        self.__prepare_db()


    def __prepare_db(self):
        """prepare the database (create the table structure)"""

        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(path text, filename text, mtime integer)" % (self.table))
        self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS file_unique_per_path ON %s (path, filename)" % (self.table))
        self.dbcon.commit()


    def __walktree(self, path):
        rows = []
        for path, filename, mtime, is_dir in self.__listdir(path):
            rows.append((path, filename, mtime if not is_dir else -1))
            if is_dir:
                for childrows in self.__walktree(os.path.join(path, filename)):
                    yield childrows
        yield rows


    def __listdir(self, path):
        """list all the files in a directory
        
        Returns (path, filename, mtime, is_dir) tuples.
        """

        try:
            filenames = os.listdir(path)
        except os.error:
            return

        for filename in filenames:
            try:
                path_to_file = os.path.join(path, filename)
                st = os.stat(path_to_file)
                mtime = st[stat.ST_MTIME]
                if stat.S_ISDIR(st.st_mode):
                    # If this is one of the ignored directories, skip it.
                    if filename in self.ignored_dirs:
                        continue
                    # This is not an ignored directory, but if it's a symlink,
                    # we will prevent walking the directory tree below it by
                    # pretending it's just a file.
                    else:
                        is_dir = not os.path.islink(path_to_file)
                else:
                    is_dir = False
                row = (path, filename, mtime, is_dir)
            except os.error:
                continue
            yield row


    def initial_scan(self, path):
        """perform the initial scan
        
        Returns False if there is already data available for this path.
        """
        path = path.decode('utf-8')

        # Check if there really isn't any data available for this path.
        self.dbcur.execute("SELECT COUNT(filename) FROM %s WHERE path=?" % (self.table), (path,))
        if self.dbcur.fetchone()[0] > 0:
            return False
        
        for files in self.__walktree(path):
            self.add_files(files)


    def purge_path(self, path):
        """purge the metadata for a given path and all its subdirectories"""
        path = path.decode('utf-8')

        self.dbcur.execute("DELETE FROM %s WHERE path LIKE ?" % (self.table), (path + "%",))
        self.dbcur.execute("VACUUM %s" % (self.table))
        self.dbcon.commit()


    def add_files(self, files):
        """add file metadata to the database
        
        Expected format: a set of (path, filename, mtime) tuples.
        """
        self.update_files(files)


    def update_files(self, files):
        """update file metadata in the database

        Expected format: a set of (path, filename, mtime) tuples.
        """

        for row in files:
            # Use INSERT OR REPLACE to let the OS's native file system monitor
            # (inotify on Linux, FSEvents on OS X) run *while* missed events
            # are being generated.
            # See https://github.com/wimleers/fileconveyor/issues/69.
            self.dbcur.execute("INSERT OR REPLACE INTO %s VALUES(?, ?, ?)" % (self.table), row)
            self.__db_batched_commit()
        # Commit the remaining rows.
        self.__db_batched_commit(True)


    def delete_files(self, files):
        """delete file metadata from the database

        Expected format: a set of (path, filename) tuples.
        """

        for row in files:
            self.dbcur.execute("DELETE FROM %s WHERE path=? AND filename=?" % (self.table), row)
            self.__db_batched_commit()
        # Commit the remaining rows.
        self.__db_batched_commit(True)


    def __db_batched_commit(self, force=False):
        """docstring for __db_commit"""
        # Commit to the database in batches, to reduce concurrency: collect
        # self.commit_interval rows, then commit.
        
        self.uncommitted_statements += 1
        if force == True or self.uncommitted_statements == self.commit_interval:
            self.dbcon.commit()
            self.uncommitted_rows = 0
            

    def scan(self, path):
        """scan a directory (without recursion!) for changes
        
        The database is also updated to reflect the new situation, of course.

        By design, so that this function can be used by scan_tree():
        - Cannot detect newly created directory trees.
        - Can detect deleted directory trees.
        """

        path = path.decode('utf-8')
        # Fetch the old metadata from the DB.
        self.dbcur.execute("SELECT filename, mtime FROM %s WHERE path=?" % (self.table), (path, ))
        old_files = {}
        for filename, mtime in self.dbcur.fetchall():
            old_files[filename] = (filename, mtime)

        # Get the current metadata.
        new_files = {}
        for path, filename, mtime, is_dir in self.__listdir(path):
            new_files[filename] = (filename, mtime if not is_dir else -1)

        scan_result = self.__scanhelper(path, old_files, new_files)

        # Add the created files to the DB.
        files = Set()
        for filename in scan_result["created"]:
            (filename, mtime) = new_files[filename]
            files.add((path, filename, mtime))
        self.add_files(files)
        # Update the modified files in the DB.
        files = Set()
        for filename in scan_result["modified"]:
            (filename, mtime) = new_files[filename]
            files.add((path, filename, mtime))
        self.update_files(files)
        # Remove the deleted files from the DB.
        files = Set()
        for filename in scan_result["deleted"]:
            if len(os.path.dirname(filename)):
                realpath = path + os.sep + os.path.dirname(filename)
            else:
                realpath = path
            realfilename = os.path.basename(filename)
            files.add((realpath, realfilename))
        self.delete_files(files)

        return scan_result


    def scan_tree(self, path):
        """scan a directory tree for changes"""
        path = path.decode('utf-8')

        # Scan the current directory for changes.
        result = self.scan(path)

        # Prepend the current path.
        for key in result.keys():
            tmp = Set()
            for filename in result[key]:
                tmp.add(path + os.sep + filename)
            result[key] = tmp
        yield (path, result)

        # Also scan each subdirectory.
        for path, filename, mtime, is_dir in self.__listdir(path):
            if is_dir:
                for subpath, subresult in self.scan_tree(os.path.join(path, filename)):
                    yield (subpath, subresult)


    def __scanhelper(self, path, old_files, new_files):
        """helper function for scan()

        old_files and new_files should be dictionaries of (filename, mtime)
        tuples, keyed by filename

        Returns a dictionary of sets of filenames with the keys "created",
        "deleted" and "modified".
        """

        # The dictionary that will be returned.
        result = {}
        result["created"] = Set()
        result["deleted"] = Set()
        result["modified"] = Set()

        # Create some sets that will make our work easier.
        old_filenames = Set(old_files.keys())
        new_filenames = Set(new_files.keys())

        # Step 1: find newly created files.
        result["created"] = new_filenames.difference(old_filenames)

        # Step 2: find deleted files.
        result["deleted"] = old_filenames.difference(new_filenames)

        # Step 3: find modified files.
        # Only files that are not created and not deleted can be modified!
        possibly_modified_files = new_filenames.union(old_filenames)
        possibly_modified_files = possibly_modified_files.symmetric_difference(result["created"])
        possibly_modified_files = possibly_modified_files.symmetric_difference(result["deleted"])
        for filename in possibly_modified_files:
            (filename, old_mtime) = old_files[filename]
            (filename, new_mtime) = new_files[filename]
            if old_mtime != new_mtime:
                result["modified"].add(filename)

        # Step 4
        # If a directory was deleted, we also need to retrieve the filenames
        # and paths of the files within that subtree.
        deleted_tree = Set()
        for deleted_file in result["deleted"]:
            (filename, mtime) = old_files[deleted_file]
            # An mtime of -1 means that this is a directory.
            if mtime == -1:
                dirpath = path + os.sep + filename
                self.dbcur.execute("SELECT * FROM %s WHERE path LIKE ?" % (self.table), (dirpath + "%",))
                files_in_dir = self.dbcur.fetchall()
                # Mark all files below the deleted directory also as deleted.
                for (subpath, subfilename, submtime) in files_in_dir:
                    deleted_tree.add(os.path.join(subpath, subfilename)[len(path) + 1:])
        result["deleted"] = result["deleted"].union(deleted_tree)
        
        return result


if __name__ == "__main__":
    # Sample usage
    path = "/Users/wimleers/Downloads"
    db = sqlite3.connect("pathscanner.db")
    ignored_dirs = ["CVS", ".svn"]
    scanner = PathScanner(db, ignored_dirs)
    # Force a rescan
    #scanner.purge_path(path)
    scanner.initial_scan(path)

    # Detect changes in a single directory
    #print scanner.scan(path)

    # Detect changes in the entire tree
    report = {}
    report["created"] = Set()
    report["deleted"] = Set()
    report["modified"] = Set()
    for path, result in scanner.scan_tree(path):
        report["created"] = report["created"].union(result["created"])
        report["deleted"] = report["deleted"].union(result["deleted"])
        report["modified"] = report["modified"].union(result["modified"])
    print report