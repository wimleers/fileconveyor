"""persistent_queue.py An infinite persistent queue that uses sqlite for storage and Queue for an in-memory cache"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sqlite3
import cPickle
import Queue


# Define exceptions.
class PersistentQueueError(Exception): pass
class Empty(PersistentQueueError): pass


class PersistentQueue(object):
    """docstring for PersistentQueue"""

    def __init__(self, dbfile="persistent_queue.db", table="persistent_queue", max_in_memory=100, min_in_memory=50):
        self.size = 0

        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory queue.
        self.max_in_memory = max_in_memory
        self.min_in_memory = min_in_memory
        self.memory_queue = Queue.Queue(self.max_in_memory)
        self.highest_id_in_queue = 0

        # Update the size property.
        self.dbcur.execute("SELECT COUNT(id) FROM persistent_queue")
        self.size = self.dbcur.fetchone()[0]


    def __prepare_db(self, dbfile):
        sqlite3.register_converter("pickle", cPickle.loads)
        self.dbcon = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle)" % (self.table))
        self.dbcon.commit()

        
    def qsize(self):
        return self.size


    def empty(self):
        return self.size == 0


    def full(self):
        # We've got infinite storage.
        return False


    def put(self, item):
        # Insert the item into the database.
        self.dbcur.execute("INSERT INTO %s (item) VALUES(?)" % (self.table), (cPickle.dumps(item), ))
        self.dbcon.commit()
        id = self.dbcur.lastrowid
        self.size += 1


    def get(self):
        if self.empty():
            raise Empty
        else:
            # If the memory queue is too small, update it using the database.
            if self.memory_queue.qsize() < self.min_in_memory:
                self.dbcur.execute("SELECT id, item FROM %s WHERE id > ? ORDER BY id ASC LIMIT 0,%d " % (self.table, self.max_in_memory - self.memory_queue.qsize()), (self.highest_id_in_queue, ))
                resultList = self.dbcur.fetchall()
                for id, item in resultList:
                    self.memory_queue.put((id, item))
                    self.highest_id_in_queue = id

            # Get the item from the memory queue and immediately delete it
            # from the database.
            (id, return_value) = self.memory_queue.get()
            self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()

            # Update the size.
            self.size -= 1

            return return_value
