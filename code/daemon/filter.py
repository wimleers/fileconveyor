"""filter.py Filter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from sets import Set, ImmutableSet
import re
import types
import os
import os.path
import stat


# Define exceptions.
class FilterError(Exception): pass
class InvalidConditionError(FilterError): pass
class MissingConditionError(FilterError): pass
class InvalidPathsConditionError(InvalidConditionError): pass
class InvalidExtensionsConditionError(InvalidConditionError): pass
class InvalidIgnoredDirsConditionError(InvalidConditionError): pass
class InvalidPatternConditionError(InvalidConditionError): pass
class InvalidSizeConditionError(InvalidConditionError): pass
class MatchError(FilterError): pass


class Filter(object):
    """filter filepaths based on path, file extensions, ignored directories, file pattern and file size"""

    valid_conditions = ImmutableSet(["paths", "extensions", "ignoredDirs", "pattern", "size"])
    required_sizeconditions = ImmutableSet(["conditionType", "treshold"])
    # Prevent forbidden characters in filepaths!
    # - Mac OS X: :
    # - Linux: /
    # - Windows: * " / \ [ ] : ; | = , < >
    # It's clear that if your filepaths are valid on Windows, they're valid
    # anywhere. So we go with that.
    forbidden_characters = {
        "paths"       : '\*"\[\]:;\|=,<>',      # / and \ are allowed
        "extensions"  : '\*"/\\\[\]:;\|=,<>\.', # / and \ and . are disallowed
        "ignoredDirs" : '\*"/\\\[\]:;\|=,<>',   # / and \ are disallowed
    }
    patterns = {
        "paths"       : re.compile('^(?:([^' + forbidden_characters["paths"]       + ']+):)*[^' + forbidden_characters["paths"]       + ']+$'),
        "extensions"  : re.compile('^(?:([^' + forbidden_characters["extensions"]  + ']+):)*[^' + forbidden_characters["extensions"]  + ']+$'),
        "ignoredDirs" : re.compile('^(?:([^' + forbidden_characters["ignoredDirs"] + ']+):)*[^' + forbidden_characters["ignoredDirs"] + ']+$'),
    }


    def __init__(self, conditions = None):
        self.initialized = False
        self.conditions = {}
        self.pattern = None
        if conditions is not None:
            self.set_conditions(conditions)


    def set_conditions(self, conditions):
        """Validate and then set the conditions of this Filter"""
        present_conditions = Set(conditions.keys())

        # Ensure all required conditions are set.
        if not (conditions.has_key("paths") or conditions.has_key("extensions")):
            raise MissingConditionError("You must at least set a paths or extensions condition.")

        # Ensure only valid conditions are set.
        if len(present_conditions.difference(self.__class__.valid_conditions)):
            raise InvalidConditionError

        # Validate conditions. This may trigger exceptions, which should be
        # handled by the caller.
        self.__validate_conditions(conditions)
        
        # The conditions passed all validation tests: store it.
        self.conditions = conditions

        # Precompile the pattern condition, if there is one.
        if (self.conditions.has_key("pattern")):
            self.pattern = re.compile(self.conditions["pattern"])

        self.initialized = True

        return True


    def __validate_conditions(self, conditions):
        """Validate a given set of conditions"""

        # The paths condition must contain paths separated by colons.
        if conditions.has_key("paths"):
            if not self.__class__.patterns["paths"].match(conditions["paths"]):
                raise InvalidPathsConditionError

        # The extensions condition must contain extensions separated by colons.
        if conditions.has_key("extensions"):
            if not self.__class__.patterns["extensions"].match(conditions["extensions"]):
                raise InvalidExtensionsConditionError

        # The ignoredDirs condition must contain dirnames separated by colons.
        if conditions.has_key("ignoredDirs"):
            if not self.__class__.patterns["ignoredDirs"].match(conditions["ignoredDirs"]):
                raise InvalidIgnoredDirsConditionError

        # If a pattern condition is set, ensure that it's got a valid regular
        # expression.
        if conditions.has_key("pattern"):
            if conditions["pattern"] is None:
                raise InvalidPatternConditionError
            try:
                re.compile(conditions["pattern"])
            except re.error:
                raise InvalidPatternConditionError

        # If a size condition is set, ensure that it's got both a size
        # condition type and a treshold. And both of them must be valid.
        if conditions.has_key("size"):
            size = conditions["size"]
            if len(self.__class__.required_sizeconditions.difference(size.keys())):
                raise InvalidSizeConditionError, "The 'size' condition misses either of 'conditionType' and 'treshold'"
            if size["conditionType"] != "minimum" and size["conditionType"] != "maximum":
                raise InvalidSizeConditionError, "The 'size' condition has an invalid 'conditionType', valid values are 'maximum' and 'minimum'"
            try:
                size["treshold"] = int(size["treshold"])
            except ValueError:
                raise InvalidSizeConditionError, "The 'size' condition has an invalid 'treshold', only integer values are valid'"


    def matches(self, filepath, statfunc = os.stat, file_is_deleted = False):
        """Check if the given filepath matches the conditions of this Filter

        This function performs the different checks in an order that is
        optimized for speed: the conditions that are most likely to reduce
        the chance of a match are performed first.

        """

        if not self.initialized:
            return False

        match = True
        (root, ext) = os.path.splitext(filepath)

        # Step 1: apply the paths condition.
        if match and self.conditions.has_key("paths"):
            append_slash = lambda path: path + "/"
            paths = map(append_slash, self.conditions["paths"].split(":"))
            path_found = False
            for path in paths:
                if root.find(path) > -1:
                    path_found = True
                    break
            if not path_found:
                match = False
        
        # Step 2: apply the extensions condition.
        if match and self.conditions.has_key("extensions"):
            ext = ext.lstrip(".")
            if not ext in self.conditions["extensions"].split(":"):
                match = False

        # Step 3: apply the ignoredDirs condition.
        if match and self.conditions.has_key("ignoredDirs"):
            ignored_dirs = Set(self.conditions["ignoredDirs"].split(":"))
            dirs = Set(root.split(os.sep))
            if len(ignored_dirs.intersection(dirs)):
                match = False

        # Step 4: apply the pattern condition.
        if match and self.conditions.has_key("pattern"):
            if not self.pattern.match(filepath):
                match = False

        # Step 5: apply the size condition, except when file_is_deleted is
        # enabled.
        # (If a file is deleted, we can no longer check its size and therefor
        # we allow this to match.)
        if match and self.conditions.has_key("size") and not file_is_deleted:
            size = statfunc(filepath)[stat.ST_SIZE]
            condition_type = self.conditions["size"]["conditionType"]
            treshold       = self.conditions["size"]["treshold"]
            if condition_type == "minimum" and not treshold < size:
                match = False
            elif condition_type == "maximum" and not treshold > size:
                match = False

        return match
