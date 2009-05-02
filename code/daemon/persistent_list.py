"""persistent_list.py An infinite persistent list that uses sqlite for storage and a list for a complete in-memory cache"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sqlite3
import cPickle


# Define exceptions.
class PersistentListError(Exception): pass


class PersistentList(object):
    """a persistent queue with sqlite back-end designed for finite lists"""

    def __init__(self, table, dbfile="persistent_list.db"):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory list: load its contents from the database.
        self.memory_list = []
        self.dbcur.execute("SELECT item FROM %s" % (self.table))
        resultList = self.dbcur.fetchall()
        for row in resultList:
            item = row[0]
            self.memory_list.append(item)


    def __prepare_db(self, dbfile):
        sqlite3.register_converter("pickle", cPickle.loads)
        self.dbcon = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(item pickle)" % (self.table))
        self.dbcon.commit()


    def __contains__(self, item):
        return item in self.memory_list


    def __len__(self):
        return len(self.memory_list)


    def append(self, item):
        # Insert the item into the database.
        self.dbcur.execute("INSERT INTO %s (item) VALUES(?)" % (self.table), (cPickle.dumps(item), ))
        self.dbcon.commit()
        # Insert the item into the in-memory list.
        self.memory_list.append(item)


    def index(self, item):
        return self.memory_list.index(item)


    def __getitem__(self, index):
        return self.memory_list[index]


    def __delitem__(self, index):
        # Delete from the database.
        item = self.memory_list[index]
        self.dbcur.execute("DELETE FROM %s WHERE item = ?" % (self.table), (cPickle.dumps(item), ))
        self.dbcon.commit()        
        # Delete from the in-memory list.
        del self.memory_list[index]
