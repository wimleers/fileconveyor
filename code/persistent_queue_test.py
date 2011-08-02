"""Unit test for persistent_queue.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from persistent_queue import *
import os
import os.path
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.table = "persistent_queue_test"
        self.db = "persistent_queue_test.db"
        if os.path.exists(self.db):
            os.remove(self.db)


    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)


    def testEmpty(self):
        pq = PersistentQueue(self.table, self.db)
        self.assertRaises(Empty, pq.get)


    def testBasicUsage(self):
        pq = PersistentQueue(self.table, self.db)
        items = ["abc", 99, "xyz", 123]
        received_items = []

        # Queue the items.
        for item in items:
            pq.put(item)
        self.assertEqual(len(items), pq.qsize(), "The size of the original list matches the size of the queue.")

        # Dequeue the items.
        while not pq.empty():
            item = pq.get()
            received_items.append(item)
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the queue are equal")


    def testAdvancedUsage(self):
        pq = PersistentQueue(self.table, self.db, max_in_memory=5, min_in_memory=2)
        items = range(1, 100)
        received_items = []

        # Queue the items.
        for item in items:
            pq.put(item)
        self.assertEqual(len(items), pq.qsize(), "The size of the original list matches the size of the queue.")

        # Peeking should not affect the queue.
        size_before = pq.qsize()
        first_item = pq.peek()
        self.assertEqual(first_item, items[0], "Peeking works correctly.")
        size_after = pq.qsize()
        self.assertEqual(size_before, size_after, "Peeking should not affect the queue.")

        # Dequeue the items.
        while not pq.empty():
            item = pq.get()
            received_items.append(item)
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the queue are equal")


    def testUniquenessAndUpdating(self):
        # Inserting the same item twice should not be allowed
        pq = PersistentQueue(self.table, self.db)
        item = "some item"
        pq.put(item)
        pq.put("some other item")
        self.assertRaises(AlreadyExists, pq.put, item)

        # Empty the queue again.
        while not pq.empty():
            pq.get()

        # Inserting the same item twice but with different keys should be
        # allowed.
        pq = PersistentQueue(self.table, self.db)
        pq.put(item, "some key")
        pq.put(item, "some other key")

        # It should be impossible to update when a non-existing key is given.
        self.assertRaises(UpdateForNonExistingKey, pq.update, "new value", "some key that does not exist")

        # It should be possible to update an item in the queue, given its
        # key.
        pq.update("yarhar", "some key")
        self.assertEquals(pq.qsize(), 2)
        self.assertEquals(pq.get(), "yarhar")
        self.assertEquals(pq.get(), item)


if __name__ == "__main__":
    unittest.main()
