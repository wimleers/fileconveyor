"""pathscanner.py Scans paths and stores them in a sqlite3 database

You can use PathScanner to detect changes in a directory structure. For
efficiency, only creations, deletions and modifications are detected, not
moves.

Modified files are detected by looking at the mtime.

Instructions:
- Use initial_scan() to build the fill the database.
- Use scan() afterwards, to get the changes.
- Use remove() to remove all the metadata for a path from the database.

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
    def __init__(self, dbcon, table="pathscanner", commit_interval=50):
        self.dbcon = dbcon
        self.dbcur = dbcon.cursor()
        self.table = table
        self.commit_interval = commit_interval
        self.__prepare_db()
        

    def __prepare_db(self):
        """prepare the database (create the table structure)"""
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(path text, filename text, mtime integer)" % (self.table))
        self.dbcon.commit()


    def __walktree(self, path):
        rows = []
        for path, filename, mtime, is_dir in self.__listdir(path):
            if not is_dir:
                rows.append((path, filename, mtime))
            else:
                for childrows in self.__walktree(os.path.join(path, filename)):
                    yield childrows
        yield rows


    def __listdir(self, path):
        """list all the files in a directory
        
        Returns (path, filename, mtime, is_dir) tuples.
        """

        filenames = os.listdir(path)
        for filename in filenames:
            try:
                st = os.stat(os.path.join(path, filename))
                mtime = st[stat.ST_MTIME]
                is_dir = stat.S_ISDIR(st.st_mode)
                row = (path, filename, mtime, is_dir)
            except os.error:
                continue
            yield row


    def initial_scan(self, path):
        """perform the initial scan
        
        Returns False if there is already data available for this path.
        """

        # Check if there really isn't any data available for this path.
        self.dbcur.execute("SELECT COUNT(filename) FROM %s WHERE path=?" % (self.table), (path,))
        if self.dbcur.fetchone()[0] > 0:
            return False
        
        # Commit to the database in batches, to reduce concurrency: collect
        # self.commit_interval rows, then commit.
        num_uncommitted_rows = 0
        for files in scanner.__walktree(path):
            if len(files):
                for row in files:
                    # Save the metadata for each found file to the DB.
                    self.dbcur.execute("INSERT INTO %s VALUES(?, ?, ?)" % (self.table), row)
                    num_uncommitted_rows += 1
                    if (num_uncommitted_rows == self.commit_interval):
                        self.dbcon.commit()
                        num_uncommitted_rows = 0
        # Commit the remaining rows.
        self.dbcon.commit()


    def scan(self, path):
        """scan a directory (without recursion!) for changes
        
        The database is also updated to reflect the new situation, of course.
        """

        # Fetch the old metadata from the DB.
        self.dbcur.execute("SELECT filename, mtime FROM %s WHERE path=?" % (self.table), (path, ))
        old_files = {}
        for filename, mtime in self.dbcur.fetchall():
            old_files[filename] = (filename, mtime)

        # Get the current metadata.
        new_files = {}
        for path, filename, mtime, is_dir in scanner.__listdir(path):
            if not is_dir:
                new_files[filename] = (filename, mtime)

        scan_result = self.__scanhelper(old_files, new_files)

        # Add the created files to the DB.
        for filename in scan_result["created"]:
            (filename, mtime) = new_files[filename]
            self.dbcur.execute("INSERT INTO %s VALUES(?, ?, ?)" % (self.table), (path, filename, mtime))
        self.dbcon.commit()
        # Update the modified files in the DB.
        for filename in scan_result["modified"]:
            (filename, mtime) = new_files[filename]
            self.dbcur.execute("UPDATE %s SET mtime=? WHERE path=? AND filename=?" % (self.table), (mtime, path, filename))
        self.dbcon.commit()
        # Remove the deleted files from the DB.
        for filename in scan_result["deleted"]:
            self.dbcur.execute("DELETE FROM %s WHERE path=? AND filename=?" % (self.table), (path, filename))
        self.dbcon.commit()

        return scan_result


    def remove(self, path):
        """remove the metadata for a given path and all its subdirectories"""
        self.dbcur.execute("DELETE FROM %s WHERE path LIKE ?" % (self.table), (path + "%",))
        self.dbcon.commit()


    def __scanhelper(self, old_files, new_files):
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
        return result


if __name__ == "__main__":
    # Sample usage
    path = "/Users/wimleers/Downloads"
    db = sqlite3.connect("pathscanner.db")
    scanner = PathScanner(db)
    # Force a rescan
    #scanner.remove(path)
    scanner.initial_scan(path)
    print scanner.scan(path)
