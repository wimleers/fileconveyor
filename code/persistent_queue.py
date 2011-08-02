"""persistent_queue.py Infinite persistent queue with in-place updates.

An infinite persistent queue that uses SQLite for storage and a in-memory list
for a partial in-memory cache (to allow for peeking).

Each item in the queue is assigned a key of your choosing (if none is given,
the item itself becomes the key). By using this key, one can then later update
the item in the queue (i.e. without changing the order of the queue).

This class is thread-safe.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sqlite3
import cPickle
import hashlib
import types
import threading


# Define exceptions.
class PersistentQueueError(Exception): pass
class Empty(PersistentQueueError): pass
class AlreadyExists(PersistentQueueError): pass
class UpdateForNonExistingKey(PersistentQueueError): pass


class PersistentQueue(object):
    """a persistent queue with sqlite back-end designed for infinite queues"""

    def __init__(self, table, dbfile="persistent_queue.db", max_in_memory=100, min_in_memory=50):
        self.size = 0

        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory queue.
        self.max_in_memory = max_in_memory
        self.min_in_memory = min_in_memory
        self.memory_queue = []
        self.lowest_id_in_queue  = 0
        self.highest_id_in_queue = 0
        self.has_new_data = False

        # Locking is necessary to prevent a get() or peek() while an update()
        # is in progress.
        self.lock = threading.Lock()

        # Update the size property.
        self.dbcur.execute("SELECT COUNT(id) FROM %s" % (self.table))
        self.size = self.dbcur.fetchone()[0]


    def __prepare_db(self, dbfile):
        sqlite3.register_converter("pickle", cPickle.loads)
        self.dbcon = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle, key CHAR(32))" % (self.table))
        self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_key ON %s (key)" % (self.table))
        self.dbcon.commit()


    def __contains__(self, item):
        return self.dbcur.execute("SELECT COUNT(item) FROM %s WHERE item=?" % (self.table), (cPickle.dumps(item), )).fetchone()[0]


    def qsize(self):
        return self.size


    def empty(self):
        return self.size == 0


    def full(self):
        # We've got infinite storage.
        return False


    def put(self, item, key=None):
        # If no key is given, default to the item itself.
        if key is None:
            key = item

        # Insert the item into the database.
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        try:
            self.dbcur.execute("INSERT INTO %s (item, key) VALUES(?, ?)" % (self.table), (cPickle.dumps(item), md5))
        except sqlite3.IntegrityError:
            self.lock.release()
            raise AlreadyExists
        self.dbcon.commit()
        self.size += 1

        self.has_new_data = True

        self.lock.release()


    def peek(self):
        self.lock.acquire()
        if self.empty():
            self.lock.release()
            raise Empty
        else:
            self.__update_memory_queue()
            (id, item) = self.memory_queue[0]

            self.lock.release()

            return item


    def get(self):
        self.lock.acquire()
        
        if self.empty():
            self.lock.release()
            raise Empty
        else:
            self.__update_memory_queue()
            # Get the item from the memory queue and immediately delete it
            # from the database.
            (id, item) = self.memory_queue.pop(0)
            self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()
            self.size -= 1

            self.lock.release()

            return item


    def update(self, item, key):
        self.lock.acquire()

        # Update the item in the queue
        md5 = PersistentQueue.__hash_key(key)

        self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
        result = self.dbcur.fetchone()

        if result is None:
            self.lock.release()
            raise UpdateForNonExistingKey
        else:
            id = result[0]
            self.dbcur.execute("UPDATE %s SET item = ? WHERE key = ?" % (self.table), (cPickle.dumps(item), md5))
            self.dbcon.commit()

        if result is not None and id >= self.lowest_id_in_queue and id <= self.highest_id_in_queue:
            # Refresh the memory queue, because the updated item was in the
            # memory queue.
            self.__update_memory_queue(refresh=True)

        self.lock.release()


    @classmethod
    def __hash_key(cls, key):
        """calculate the md5 hash of the key"""
        if not isinstance(key, types.StringTypes):
            key = str(key)
        md5 = hashlib.md5(key).hexdigest()
        return md5


    def __update_memory_queue(self, refresh=False):
        if refresh:
            del self.memory_queue[:]

        # If the memory queue is too small, update it using the database.
        if self.has_new_data or len(self.memory_queue) < self.min_in_memory:
            # Store the lowest id that's in the memory queue (i.e. the id of
            # the first item). This is needed to be able to do refreshes.
            if len(self.memory_queue) == 0:
                self.lowest_id_in_queue = -1
            else:
                self.lowest_id_in_queue = self.memory_queue[0][0]

            # By default, we try to fetch additional items. If refresh=True,
            # however, we simply rebuild the memory queue as it was (possibly
            # with some additional items).
            if not refresh:
                min_id = self.highest_id_in_queue
            else:
                min_id = self.lowest_id_in_queue - 1

            # Do the actual update.
            self.dbcur.execute("SELECT id, item FROM %s WHERE id > ? ORDER BY id ASC LIMIT 0,%d " % (self.table, self.max_in_memory - len(self.memory_queue)), (min_id, ))
            resultList = self.dbcur.fetchall()
            for id, item in resultList:
                self.memory_queue.append((id, item))
                self.highest_id_in_queue = id

        # Now that we've updated, it's impossible that we've missed new data.
        self.has_new_data = False


class PersistentDataManager(object):
    def __init__(self, dbfile="persistent_queue.db"):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.__prepare_db(dbfile)


    def __prepare_db(self, dbfile):
        self.dbcon = sqlite3.connect(dbfile)
        self.dbcur = self.dbcon.cursor()


    def list(self, table):
        self.dbcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (table, ))
        resultList = self.dbcur.fetchall()
        tables = []
        for row in resultList:
            tables.append(row[0])
        return tables


    def delete(self, table):
        self.dbcur.execute("DROP TABLE '%s'" % (table))
        self.dbcon.commit()
