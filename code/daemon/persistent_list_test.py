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
        if os.path.exists("persistent_list.db"):
            os.remove("persistent_list.db")


    def testEmpty(self):
        pl = PersistentList(self.table)
        self.assertEqual(0, len(pl))

    
    def testBasicUsage(self):
        pl = PersistentList(self.table)
        items = ["abc", 99, "xyz", 123]
        received_items = []
    
        # Add the items to the persistent list.
        for item in items:
            pl.append(item)
        self.assertEqual(len(items), len(pl), "The size of the original list matches the size of the persistent list.")

        # Ensure persistency is really working, by deleting the PersistentList
        # and then loading it again.
        del pl
        pl = PersistentList(self.table)

        # Get the items from the persistent list.
        for i in range(0, len(pl)):
            item = pl[i]
            received_items.append(item)
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the persistent list are equal")

        # Verify that the index() function is working.
        for item in pl:
            self.assertEqual(items.index(item), pl.index(item))

        # A second persistent list that uses the same table should get the
        # same data.
        pl2 = PersistentList(self.table)
        for i in range(0, len(pl2)):
            self.assertEqual(pl[i], pl2[i])
        del pl2

        # Remove items from the persistent list.
        for i in range(len(pl) - 1, -1, -1):
            len_before = len(pl)
            del pl[i]
            len_after = len(pl)
            self.assertEqual(len_before - 1, len_after, "removing")
        self.assertEqual(0, len(pl), "The persistent list is empty.")


if __name__ == "__main__":
    unittest.main()
