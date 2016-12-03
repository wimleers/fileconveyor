"""persistent_list.py An infinite persistent list that uses sqlite for storage and a list for a complete in-memory cache"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import cPickle
import base64

# Define exceptions.
class PersistentListError(Exception): pass


class PersistentList(object):
    """a persistent queue with sqlite back-end designed for finite lists"""

    def __init__(self, table, dbfile=("sqlite", "persistent_queue.db")):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory list: load its contents from the database.
        self.memory_list = {}
        self.dbcur.execute("SELECT id, item FROM %s ORDER BY id ASC" % (self.table))
        resultList = self.dbcur.fetchall()
        for id, item in resultList:
            self.memory_list[item] = id


    def __prepare_db(self, dbfile):
        (DB_SOURCE, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE) = dbfile
        self.DB_SOURCE = DB_SOURCE
        
        if DB_SOURCE == 'sqlite':
            import sqlite3
            from sqlite3 import IntegrityError
            sqlite3.register_converter("pickle", cPickle.loads)
            self.dbcon = sqlite3.connect(DB_HOST, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle)" % (self.table))        
            self.dbcon.commit()
        elif DB_SOURCE == 'mysql':
            import MySQLdb
            from MySQLdb import IntegrityError
            self.dbcon = MySQLdb.connect(host=DB_HOST, port=DB_PORT, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_DATABASE)
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INT NOT NULL AUTO_INCREMENT, item TEXT, PRIMARY KEY (id))" % (self.table))        
            self.dbcon.commit()
        else:
            self.logger.error("Invalid DB_SOURCE detected")
            
        


    def __contains__(self, item):
        return item in self.memory_list.keys()


    def __iter__(self):
        return self.memory_list.__iter__()


    def __len__(self):
        return len(self.memory_list)


    def __getitem__(self, index):
        keys = self.memory_list.keys()
        return keys[index]


    def append(self, item):
        # Insert the item into the database.
        pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            stmt = "INSERT INTO %s (item)" % self.table
            self.dbcur.execute(stmt + " VALUES(%s)", (base64.encodestring(pickled_item), ))
        elif self.DB_SOURCE == 'sqlite':
            self.dbcur.execute("INSERT INTO %s (item) VALUES(?)" % (self.table), (sqlite3.Binary(pickled_item), ))
        self.dbcon.commit()
        id = self.dbcur.lastrowid
        # Insert the item into the in-memory list.
        self.memory_list[item] = id


    def remove(self, item):
        # Delete from the database.
        if self.memory_list.has_key(item):
            id = self.memory_list[item]
            self.dbcon.ping(True)
            if self.DB_SOURCE == 'mysql':
                stmt = "DELETE FROM %s" % self.table
                self.dbcur.execute(stmt + " WHERE id = %s", (id, ))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()        
            # Delete from the in-memory list.
            del self.memory_list[item]
