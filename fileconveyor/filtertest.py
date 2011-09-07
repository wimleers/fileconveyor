"""Unit test for filter.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from filter import *
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.filter = Filter()

    def testNoConditions(self):
        """Filter should fail when no settings are provided"""
        self.assertRaises(MissingConditionError, self.filter.set_conditions, {})

    def testMinimumConditions(self):
        """Filter should work with at least one condition"""
        self.assertTrue(self.filter.set_conditions, {"paths" : "foo/bar:baz"})
        self.assertTrue(self.filter.set_conditions, {"extensions" : "gif:png"})
        self.assertTrue(self.filter.set_conditions, {"ignoredDirs" : "CVS:.svn"})
        self.assertTrue(self.filter.set_conditions, {"size" : {"treshold" : 1000000}})
        self.assertTrue(self.filter.set_conditions, {"pattern" : "foo/bar"})

    def testInvalidConditions(self):
        """Filter should fail when there is an invalid setting"""
        self.assertRaises(InvalidConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "invalid" : "invalid"})

    def testValidConditions(self):
        """setting filter conditions should return true when all required and no invalid conditions are specified"""
        # The minimal valid filter conditions.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz"}))
        # The maximal valid filter conditions.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS", "pattern" : "foo/bar", "size" : { "conditionType" : "minimum", "treshold" : 1000000}}))

    def testInvalidPathsCondition(self):
        """Filter should fail when setting an invalid paths filter condition"""
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo:baz>"})
        # Special: / is allowed
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz>"})
        # Special: \ is allowed
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo\\bar:baz>"})

    def testInvalidExtensionsCondition(self):
        """Filter should fail when setting an invalid extensions filter condition"""
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "<gif:png", "paths" : "foo/bar:baz"})
        # Special: . is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : ".gif:png", "paths" : "foo/bar:baz"})
        # Special: / is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "/gif:png", "paths" : "foo/bar:baz"})
        # Special: \ is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "\\gif:png", "paths" : "foo/bar:baz"})
        
    def testInvalidIgnoredDirsCondition(self):
        """Filter should fail when setting an invalid ignoredDirs filter condition"""
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS/"})
        # Special: / is disallowed
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS/"})
        # Special: \ is disallowed
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:\\CVS"})

    def testInvalidPatternCondition(self):
        """Filter should fail when setting an invalid pattern filter condition"""
        self.assertRaises(InvalidPatternConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "pattern" : "foo(bar"})
        self.assertRaises(InvalidPatternConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "pattern" : None})

    def testInvalidSizeCondition(self):
        """Filter should fail when setting an invalid size filter condition"""
        # Missing conditionType
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"treshold" : 1000000}})
        # Missing treshold
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"conditionType" : "minimum"}})
        # Invalid conditionType
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"treshold" : 1000000, "conditionType" : "this is in an invalid condition type"}})
        # Invalid treshold
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"conditionType" : "minimum", "treshold" : "this is not numeric and therefor invalid"}})

    def testValidSizeCondition(self):
        """'maximum' and 'minimum' are the allowed conditionTypes for the size condition"""
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "minimum", "treshold" : 1000000}}))
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "maximum", "treshold" : 1000000}}))
        # Strings should also work and should be converted to integers automatically.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "maximum", "treshold" : "1000000"}}))


class TestMatching(unittest.TestCase):
    def testWithoutConditions(self):
        """Ensure matching works properly even when no conditions are set"""
        filter = Filter()
        self.assertFalse(filter.matches('whatever'))

    def testPathsMatches(self):
        """Ensure paths matching works properly"""
        conditions = {
            "paths" : "foo/bar:baz"
        }
        filter = Filter(conditions)
        # Invalid paths.
        self.assertFalse(filter.matches('/a/b/c/d.gif'))
        self.assertFalse(filter.matches('/a/foo/bar.gif'))
        # Valid paths.
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))

    def testExtensionsMatches(self):
        """Ensure extensions matching works properly"""
        conditions = {
            "extensions" : "gif:png",
        }
        filter = Filter(conditions)
        # Invalid extensions.
        self.assertFalse(filter.matches('/a/foo/bar/b.mov'))
        self.assertFalse(filter.matches('/a/baz/c/d/e/f.txt'))
        # Valid extensions.
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))

    def testSimpleMatches(self):
        """Ensure paths/extensions matching works properly"""
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz"
        }
        filter = Filter(conditions)
        # Invalid extensions, valid paths
        self.assertFalse(filter.matches('/a/foo/bar/b.mov'))
        self.assertFalse(filter.matches('/a/baz/c/d/e/f.txt'))
        # Invalid paths, valid extensions
        self.assertFalse(filter.matches('/a/b.png'))
        self.assertFalse(filter.matches('/a/b/c/d/e/f.gif'))
        # Both invalid extensions and paths
        self.assertFalse(filter.matches('/a/b.rar'))
        self.assertFalse(filter.matches('/a/b/c/d/e/f.avi'))
        # Both valid extensions and paths
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))
        # Tricky one: the path seems to match, but is part of the filename and
        # therefor it doesn't match!
        self.assertFalse(filter.matches('foo/bar.gif'))
        self.assertFalse(filter.matches('baz.png'))

    def testIgnoredDirsMatches(self):
        """Ensure ignoredDirs matching works properly"""
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz",
            "ignoredDirs" : ".svn:CVS",
        }
        filter = Filter(conditions)
        # Contains ignored dirs
        self.assertFalse(filter.matches('/a/foo/bar/.svn/b.gif'))
        self.assertFalse(filter.matches('/a/baz/CVS/d/e/f.png'))
        # Doesn't contain ignored dirs
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))
    
    def testPatternMatches(self):
        """Ensure pattern matching works properly"""
        conditions = {
            "paths" : "foo/bar:baz",
            "pattern" : ".*/([a-zA-Z_])+\.[a-zA-Z0-9]{3}$",
        }
        filter = Filter(conditions)
        # Does not match pattern
        self.assertFalse(filter.matches('/a/foo/bar/.svn/b9.gif'))
        self.assertFalse(filter.matches('/a/f.png'))
        # Matches pattern
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/this_one_has_underscores.gif'))
        self.assertTrue(filter.matches('/a/and_this_one_too/baz/c.png'))
    
    def testSizeMatches(self):
        """Ensure size validation works properly"""

        # The matches function only looks at ST_SIZE, which is in the 7th
        # position in the tuple. This lambda function simplifies the rest of
        # this test case.
        fakestatfunc = lambda filesize: (1, 2, 3, 4, 5, 6, filesize)
        # We always use the same filepath.
        filepath = '/a/baz/c.png'

        # Minimum size
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz",
            "ignoredDirs" : ".svn:CVS",
            "size" : {
                "conditionType" : "minimum",
                "treshold" : 500
            }
        }
        filter = Filter(conditions)
        # Meets minimum size
        statfunc = lambda filepath: fakestatfunc(501L)
        self.assertTrue(filter.matches(filepath, statfunc))
        # Does not meet minimum size
        statfunc = lambda filepath: fakestatfunc(499L)
        self.assertFalse(filter.matches(filepath, statfunc))

        # Maximium size
        conditions["size"]["conditionType"] = "maximum"
        filter.set_conditions(conditions)
        # Meets maximum size
        statfunc = lambda filepath: fakestatfunc(499L)
        self.assertTrue(filter.matches(filepath, statfunc))
        # Does not meet maximum size
        statfunc = lambda filepath: fakestatfunc(500L)
        self.assertFalse(filter.matches(filepath, statfunc))

        # Minimium size
        conditions["size"]["conditionType"] = "minimum"
        filter.set_conditions(conditions)
        # File doesn't exist anymore: size check should be skipped.
        statfunc = lambda filepath: fakestatfunc(0)
        self.assertTrue(filter.matches(filepath, statfunc, True))


if __name__ == "__main__":
    unittest.main()
