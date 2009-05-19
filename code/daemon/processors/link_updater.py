__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path
import cssutils
import logging
import sys
import sqlite3
from urlparse import urljoin
from settings import SYNCED_FILES_DB


class CSSURLUpdater(Processor):
    """replaces URLs in .css files with their counterparts on the CDN"""


    valid_extensions = (".css")


    def run(self):
        # Step 0: ensure that the document_root and base_path variables are
        # set. If the file that's being processed was inside a source that has
        # either one or both not set, then this processor can't run.
        if self.document_root is None or self.base_path is None:
            raise DocumentRootAndBasePathRequiredException

        # We don't rename the file, so we can use the default output file.

        cssutils.log.setLog(logging.getLogger(".".join([self.parent_logger, "CSSURLUpdater"])))
        parser = cssutils.CSSParser()
        sheet = parser.parseFile(self.input_file)

        # Step 1: ensure the file has URLs. If it doesn't, we can stop the
        # processing.
        url_count = 0
        for url in cssutils.getUrls(sheet):
            url_count +=1
            break
        if url_count == 0:
            return self.input_file

        # Step 2: resolve the relative URLs to absolute paths.
        cssutils.replaceUrls(sheet, self.resolveToAbsolutePath)

        # Step 3: verify that each of these files has been synced.
        synced_files_db = urljoin(sys.path[0] + os.sep, SYNCED_FILES_DB)
        self.dbcon = sqlite3.connect(synced_files_db)
        self.dbcur = self.dbcon.cursor()
        all_synced = True
        for urlstring in cssutils.getUrls(sheet):
            # Skip absolute URLs.
            if urlstring.startswith("http://") or urlstring.startswith("https://"):
                continue

            # Skip broken references in the CSS file. This would otherwise
            # prevent this CSS file from ever passing through this processor.
            if not os.path.exists(urlstring):
                continue

            # Get the CDN URL for the given absolute path.
            self.dbcur.execute("SELECT url FROM synced_files WHERE input_file=?", (urlstring, ))
            result = self.dbcur.fetchone()

            if result == None:
                raise RequestToRequeueException("The file '%s' has not yet been synced." % (urlstring))
            else:
                cdn_url = result[0]

        # Step 4: resolve the absolute paths to CDN URLs.
        cssutils.replaceUrls(sheet, self.resolveToCDNURL)

        # Step 5: write the updated CSS to the output file.
        f = open(self.output_file, 'w')
        f.write(sheet.cssText)
        f.close()

        return self.output_file


    def resolveToAbsolutePath(self, urlstring):
        """rewrite relative URLs (which are also relative paths, relative to
        the CSS file's path or to the document root) to absolute paths.
        Absolute URLs are returned unchanged."""

        # Skip absolute URLs.
        if urlstring.startswith("http://") or urlstring.startswith("https://"):
            return urlstring

        # Resolve paths that are relative to the document root.
        if urlstring.startswith(self.base_path):
            # Strip the leading slash.
            relative_path = urlstring[1:]
            # Prepend the document root.
            return os.path.join(self.document_root, relative_path)

        # Resolve paths that are relative to the CSS file's path.
        return urljoin(self.original_file, urlstring)


    def resolveToCDNURL(self, urlstring):
        """rewrite absolute paths to CDN URLs"""
        
        # Skip broken references in the CSS file. This would otherwise
        # prevent this CSS file from ever passing through this processor.
        if not os.path.exists(urlstring):
            return urlstring

        # Get the CDN URL for the given absolute file path.
        self.dbcur.execute("SELECT url FROM synced_files WHERE input_file=?", (urlstring, ))
        return self.dbcur.fetchone()[0]


if __name__ == "__main__":
    p = CSSURLUpdater("test.css")
    print p.run()
