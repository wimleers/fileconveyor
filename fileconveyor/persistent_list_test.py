"""Unit test for persistent_list.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from persistent_list import *
import os
import os.path
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.table = "persistent_list_test"
        self.db = "persistent_list_test.db"
        if os.path.exists(self.db):
            os.remove(self.db)


    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)


    def testEmpty(self):
        pl = PersistentList(self.table, self.db)
        self.assertEqual(0, len(pl))


    def testBasicUsage(self):
        pl = PersistentList(self.table, self.db)
        items = ["abc", 99, "xyz", 123]
        received_items = []
    
        # Add the items to the persistent list.
        for item in items:
            pl.append(item)
        self.assertEqual(len(items), len(pl), "The size of the original list matches the size of the persistent list.")

        # Ensure persistency is really working, by deleting the PersistentList
        # and then loading it again.
        del pl
        pl = PersistentList(self.table, self.db)

        # Get the items from the persistent list.
        for item in pl:
            received_items.append(item)
        # The order doesn't matter.
        items.sort()
        received_items.sort()
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the persistent list are equal")

        # A second persistent list that uses the same table should get the
        # same data.
        pl2 = PersistentList(self.table, self.db)
        for item in pl2:
            self.assertEqual(True, item in pl)
        del pl2

        # Remove items from the persistent list.
        for item in items:
            len_before = len(pl)
            pl.remove(item)
            len_after = len(pl)
            self.assertEqual(len_before - 1, len_after, "removing")
        self.assertEqual(0, len(pl), "The persistent list is empty.")


if __name__ == "__main__":
    unittest.main()
