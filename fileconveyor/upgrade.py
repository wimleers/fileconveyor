from settings import *
import sqlite3
import hashlib
import cPickle
import types

def upgrade_persistent_data_to_v10(db):
    sqlite3.register_converter("pickle", cPickle.loads)
    dbcon = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
    dbcur = dbcon.cursor()

    # Rename the table pipeline_queue to pipeline_queue_original.
    dbcur.execute("ALTER TABLE '%s' RENAME TO '%s'" % ("pipeline_queue", "pipeline_queue_original"))
    dbcon.commit()

    # Crete the table pipeline_queue according to the new schema.
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle, key CHAR(32))" % ("pipeline_queue"))
    dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_key ON %s (key)" % ("pipeline_queue"))
    dbcon.commit()

    # Provide Mock versions of FSMonitor and PersistentQueue.
    class FSMonitor(object):pass
    FSMonitor.EVENTS = {
        "CREATED"             : 0x00000001,
        "MODIFIED"            : 0x00000002,
        "DELETED"             : 0x00000004,
        "MONITORED_DIR_MOVED" : 0x00000008,
        "DROPPED_EVENTS"      : 0x00000016,
    }
    for name, mask in FSMonitor.EVENTS.iteritems():
        setattr(FSMonitor, name, mask)
    FSMonitor.MERGE_EVENTS = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.CREATED]   = FSMonitor.CREATED  #!
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.MODIFIED]  = FSMonitor.CREATED
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.DELETED]   = None
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.CREATED]  = FSMonitor.MODIFIED #!
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.MODIFIED] = FSMonitor.MODIFIED
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.DELETED]  = FSMonitor.DELETED
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.CREATED]   = FSMonitor.MODIFIED
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.MODIFIED]  = FSMonitor.MODIFIED #!
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.DELETED]   = FSMonitor.DELETED  #!

    class PersistentQueue(object):
        """Mock version of the real PersistentQueue class, to be able to reuse
        the same event merging code. This mock version only contains the
        essential code that's needed for this upgrade script.
        """
        def __init__(self, dbcon, dbcur):
            self.dbcon = dbcon
            self.dbcur = dbcur
            self.table = 'pipeline_queue'

        @classmethod
        def __hash_key(cls, key):
            if not isinstance(key, types.StringTypes):
                key = str(key)
            md5 = hashlib.md5(key.encode('utf-8')).hexdigest().decode('ascii')
            return md5

        def get_item_for_key(self, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT item FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is None:
                return None
            else:
                return result[0]

        def put(self, item, key=None):
            if key is None:
                key = item
            md5 = PersistentQueue.__hash_key(key)
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            self.dbcur.execute("INSERT INTO %s (item, key) VALUES(?, ?)" % (self.table), (sqlite3.Binary(pickled_item), md5))
            self.dbcon.commit()

        def remove_item_for_key(self, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is not None:
                id = result[0]
                self.dbcur.execute("DELETE FROM %s WHERE key = ?" % (self.table), (md5, ))
                self.dbcon.commit()

        def update(self, item, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is not None:
                id = result[0]
                pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
                self.dbcur.execute("UPDATE %s SET item = ? WHERE key = ?" % (self.table), (sqlite3.Binary(pickled_item), md5))
                self.dbcon.commit()


    # Get all items from the original pipeline queue. Insert these into the
    # pipeline queue that follows the new schema, and merge their events.
    pq = PersistentQueue(dbcon, dbcur)
    dbcur.execute("SELECT id, item FROM %s ORDER BY id ASC " % ("pipeline_queue_original"))
    resultList = dbcur.fetchall()
    for id, original_item in resultList:
        (input_file, event) = original_item
        item = pq.get_item_for_key(key=input_file)
        # If the file does not yet exist in the pipeline queue, put() it.
        if item is None:
            pq.put(item=(input_file, event), key=input_file)
        # Otherwise, merge the events, to prevent unnecessary actions.
        # See https://github.com/wimleers/fileconveyor/issues/68.
        else:
            old_event = item[1]
            merged_event = FSMonitor.MERGE_EVENTS[old_event][event]
            if merged_event is not None:
                pq.update(item=(input_file, merged_event), key=input_file)
            # The events being merged cancel each other out, thus remove
            # the file from the pipeline queue.
            else:
                pq.remove_item_for_key(key=input_file)

    # Finally, remove empty pages in the SQLite database.
    dbcon.execute("DROP TABLE %s" % ("pipeline_queue_original"))
    dbcon.execute("VACUUM")
    dbcon.close()


if __name__ == '__main__':
    # TODO: only run the necessary upgrades!

    # By default, PERSISTENT_DATA_DB is used, which is defined in settings.py.
    # You're free to change this to some other path, of course.
    upgrade_persistent_data_to_v10(PERSISTENT_DATA_DB)
