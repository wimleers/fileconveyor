import httplib
import urlparse
import sqlite3
import sys
from settings import *

num_files_checked = 0
num_files_invalid = 0

dbcon = sqlite3.connect(SYNCED_FILES_DB)
dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
dbcur = dbcon.cursor()
num_files = dbcur.execute("SELECT COUNT(*) FROM synced_files").fetchone()[0]
dbcur.execute("SELECT input_file, url, server FROM synced_files ORDER BY server")

for input_file, url, server in dbcur.fetchall():
    parsed = urlparse.urlparse(url)
    
    conn = httplib.HTTPConnection(parsed.netloc)
    conn.request("HEAD", parsed.path)
    response = conn.getresponse()
    
    if not (response.status == 200 and response.reason == 'OK'):
        print "Missing: %s, which should be available at %s (server: %s)" % (input_file, url, server)
        num_files_invalid += 1

    num_files_checked += 1

    sys.stdout.write("\r%3d%% (%d/%d)" % ((num_files_checked * 100.0 / num_files), num_files_checked, num_files))
    sys.stdout.flush()

print ""
print "Finished verifying synced files. Results:"
print " - Number of checked synced files: %d" % (num_files_checked)
print " - Number of invalid synced files: %d" % (num_files_invalid)
