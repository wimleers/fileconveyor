"""persistent_queue.py Infinite persistent queue with in-place updates.

An infinite persistent queue that uses SQLite for storage and a in-memory list
for a partial in-memory cache (to allow for peeking).

Each item in the queue is assigned a key of your choosing (if none is given,
the item itself becomes the key). By using this key, one can then later update
the item in the queue (i.e. without changing the order of the queue), remove
the item from the queue, or even just get the item from the queue to perform
"smart" updates (i.e. based on the current value of the item corresponding to
the key).

This class is thread-safe.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import cPickle
import hashlib
import types
import threading
import logging
import base64
import uuid
import unicodedata

try:
    import MySQLdb
except ImportError:
    pass
    
try:
    import sqlite3
except ImportError:
    pass

# Define exceptions.
class PersistentQueueError(Exception): pass
class Empty(PersistentQueueError): pass
class AlreadyExists(PersistentQueueError): pass
class UpdateForNonExistingKey(PersistentQueueError): pass


class PersistentQueue(object):
    """a persistent queue with sqlite back-end designed for infinite queues"""

    def __init__(self, table, dbfile=("sqlite", "persistent_queue.db", '', '', '', ''), max_in_memory=100, min_in_memory=50):
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
        
        self.logger = logging.getLogger("Arbitrator")


    def __prepare_db(self, dbfile):
        (DB_SOURCE, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE) = dbfile
        self.DB_SOURCE = DB_SOURCE
                
        if DB_SOURCE == 'sqlite':
            self.IntegrityError = sqlite3.IntegrityError
            sqlite3.register_converter("pickle", cPickle.loads)
            self.dbcon = sqlite3.connect(DB_HOST, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle, item_key CHAR(32))" % (self.table))
            self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_key ON %s (item_key)" % (self.table))
        elif DB_SOURCE == 'mysql':
            self.IntegrityError = MySQLdb.IntegrityError
            self.dbcon = MySQLdb.connect(host=DB_HOST, port=DB_PORT, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_DATABASE, charset='utf8')
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INT NOT NULL AUTO_INCREMENT, item TEXT, item_key VARCHAR(32), PRIMARY KEY (id), UNIQUE INDEX unique_key (item_key))" % (self.table))
        else:
            self.logger.error("Invalid DB_SOURCE detected")
            
        self.dbcon.commit()


    def __contains__(self, item):
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            stmt = "SELECT COUNT(item) FROM %s" % self.table
            self.dbcur.execute(stmt + " WHERE item = %s", (base64.encodestring(cPickle.dumps(item)), ))
            result = self.dbcur.fetchone()
            if result is None:
                return None
            else:
                return result[0]
        elif self.DB_SOURCE == 'sqlite':
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
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            self.dbcon.ping(True)
            if self.DB_SOURCE == 'mysql':
                stmt = "INSERT INTO %s (item, item_key)" % self.table
                self.dbcur.execute(stmt + " VALUES(%s, %s)", (base64.encodestring(pickled_item), md5))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("INSERT INTO %s (item, item_key) VALUES(?, ?)" % (self.table), (sqlite3.Binary(pickled_item), md5))
        except self.IntegrityError:
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
            self.dbcon.ping(True)
            if self.DB_SOURCE == 'mysql':
                stmt = "DELETE FROM %s" % self.table
                self.dbcur.execute(stmt + " WHERE id = %s", (id, ))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()
            self.size -= 1

            self.lock.release()
            return item


    def get_item_for_key(self, key):
        """necessary to be able to do smart update()s"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            stmt = "SELECT item FROM %s" % self.table
            self.dbcur.execute(stmt + " WHERE item_key = %s", (md5, ))
        elif self.DB_SOURCE == 'sqlite':
            self.dbcur.execute("SELECT item FROM %s WHERE item_key = ?" % (self.table), (md5, ))
        self.lock.release()
        
        result = self.dbcur.fetchone()
        if result is None:
            return None
        else:
            if self.DB_SOURCE == 'mysql':
                data = base64.decodestring(result[0])
                item = cPickle.loads(data)
                return item
            else:
                return result[0]


    def remove_item_for_key(self, key):
        """necessary to be able to do smart update()s"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            stmt = "SELECT id FROM %s" % self.table
            self.dbcur.execute(stmt + " WHERE item_key = %s", (md5, ))
        elif self.DB_SOURCE == 'sqlite':
            self.dbcur.execute("SELECT id FROM %s WHERE item_key = ?" % (self.table), (md5, ))
        result = self.dbcur.fetchone()
        if result is None:
            self.lock.release()
        else:
            id = result[0]
            if self.DB_SOURCE == 'mysql':
                stmt = "DELETE FROM %s" % self.table
                self.dbcur.execute(stmt + " WHERE item_key = %s", (md5, ))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("DELETE FROM %s WHERE item_key = ?" % (self.table), (md5, ))
            self.dbcon.commit()
            self.size -= 1
            if id >= self.lowest_id_in_queue and id <= self.highest_id_in_queue:
                # Refresh the memory queue, because the updated item was in the
                # memory queue.
                self.__update_memory_queue(refresh=True)
            self.lock.release()


    def update(self, item, key):
        """update an item in the queue"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            stmt = "SELECT id FROM %s" % self.table
            self.dbcur.execute(stmt + " WHERE item_key = %s", (md5, ))
        elif self.DB_SOURCE == 'sqlite':
            self.dbcur.execute("SELECT id FROM %s WHERE item_key = ?" % (self.table), (md5, ))
        result = self.dbcur.fetchone()

        if result is None:
            self.lock.release()
            raise UpdateForNonExistingKey
        else:
            id = result[0]
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            if self.DB_SOURCE == 'mysql':
                stmt = "UPDATE %s" % self.table
                self.dbcur.execute(stmt + " SET item = %s WHERE item_key = %s", (base64.encodestring(pickled_item), md5))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("UPDATE %s SET item = ? WHERE item_key = ?" % (self.table), (sqlite3.Binary(pickled_item), md5))
            self.dbcon.commit()

        if result is not None and id >= self.lowest_id_in_queue and id <= self.highest_id_in_queue:
            # Refresh the memory queue, because the updated item was in the
            # memory queue.
            self.__update_memory_queue(refresh=True)

        self.lock.release()


    @classmethod
    def __hash_key(cls, key):
        """generate a uuid key based on the key"""
        if not isinstance(key, types.StringTypes):
            key = str(key)
        
        key = unicodedata.normalize('NFKD', key).encode('ascii', 'ignore')
        ret = uuid.uuid5(uuid.NAMESPACE_URL, key)
        return str(ret)


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
            upper_limit = self.max_in_memory - len(self.memory_queue)
            self.dbcon.ping(True)
            if self.DB_SOURCE == 'mysql':
                stmt = "SELECT id, item FROM %s" % self.table
                self.dbcur.execute(stmt + " WHERE id > %s ORDER BY id ASC LIMIT 0,%s", (min_id, upper_limit))
            elif self.DB_SOURCE == 'sqlite':
                self.dbcur.execute("SELECT id, item FROM %s WHERE id > %s ORDER BY id ASC LIMIT 0,%s " % (self.table), (min_id, upper_limit))
            resultList = self.dbcur.fetchall()
            for id, item in resultList:
                if self.DB_SOURCE == 'mysql':
                    data = base64.decodestring(item)
                    item = cPickle.loads(data)
                self.memory_queue.append((id, item))
                self.highest_id_in_queue = id

        # Now that we've updated, it's impossible that we've missed new data.
        self.has_new_data = False


class PersistentDataManager(object):
    def __init__(self, dbfile=("sqlite", "persistent_queue.db", '', '', '', '')):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.__prepare_db(dbfile)


    def __prepare_db(self, dbfile):
        (DB_SOURCE, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE) = dbfile
        self.DB_SOURCE = DB_SOURCE
                
        if DB_SOURCE == 'sqlite':
            self.dbcon = sqlite3.connect(DB_HOST, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
            self.dbcur = self.dbcon.cursor()
        elif DB_SOURCE == 'mysql':
            self.dbcon = MySQLdb.connect(host=DB_HOST, port=DB_PORT, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_DATABASE, charset='utf8')
            self.dbcur = self.dbcon.cursor()
        else:
            self.logger.error("Invalid DB_SOURCE detected")
        


    def list(self, table):
        self.dbcon.ping(True)
        if self.DB_SOURCE == 'mysql':
            self.dbcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE %s", (table, ))
        elif self.DB_SOURCE == 'sqlite':
            self.dbcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (table, ))
        resultList = self.dbcur.fetchall()
        tables = []
        for row in resultList:
            tables.append(row[0])
        return tables


    def delete(self, table):
        self.dbcon.ping(True)
        self.dbcur.execute("DROP TABLE '%s'" % (table))
        self.dbcon.commit()
