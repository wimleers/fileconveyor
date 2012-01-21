Description
-----------
This daemon (a good name is yet to be found) is designed to discover new,
changed and deleted files via the operating system's built-in file system
monitor. After discovering the files, they can be optionally be processed by
a chain of processors – you can easily write new ones yourself. After files
have been processed, they can also optionally be transported to a server.

Discovery happens through inotify on Linux (with kernel >= 2.6.13), through
FSEvents on Mac OS X (>= 10.5) and through polling on other operating systems.

Processors are simple Python scripts that can change the file's base name (it
is impossible to change the path) and apply any sort of processing to the
file's contents. Examples are image optimization and video transcoding.

Transporters are simple threaded abstractions around Django storage systems.

For a detailed description of the innards of the daemon, see my bachelor
thesis text (find it via http://wimleers.com/tags/bachelor-thesis).

This application was written as part of the bachelor thesis [1] of Wim Leers
at Hasselt University [2].


[1] http://wimleers.com/tags/bachelor-thesis
[2] http://uhasselt.be/


<BLINK>IMPORTANT WARNING</BLINK>
--------------------------------
I've attempted to provide a solid enough README to get you started, but I'm
well aware that it isn't superb. But as this is just a bachelor thesis, time
was fairly limited. I've opted to create a solid basis instead of an extremely
rigourously documented piece of software. If you cannot find the answer in the
README.txt, nor the INSTALL.txt, nor the API.txt files, then please look at
my bachelor thesis text instead. If neither of that is sufficient, then please
contact me.


Upgrading
---------
If you're upgrading from a previous version of File Conveyor, please run
upgrade.py.



==============================================================================
| The basics                                                                 |
==============================================================================

Configuring the daemon
----------------------
The sample configuration file (config.sample.xml) should be self explanatory.
Copy this file to config.xml, which is the file the daemon will look for, and
edit it to suit your needs.
For a detailed description, see my bachelor thesis text (look for the
"Configuration file design" section).

Each rule consists of 3 components:
- filter
- processorChain
- destinations

A rule can also be configured to delete source files after they have been
synced to the destination(s).

The filter and processorChain components are optional. You must have at least
one destination.
If you want to use the daemon to process files locally, i.e. without
transporting them to a server, then use the Symlink or Copy transporter (see
below).


Starting the daemon
-------------------
The daemon must be started by starting its arbitrator (which links everything
together; it controls the file system monitor, the processor chains, the
transporters and so on). You can start the arbitrator like this:
  python /path/to/daemon/arbitrator.py


Stopping the daemon
-------------------
The daemon listens to standard signals to know when it should end, like the
Apache HTTP server does too. Send the TERMinate signal to terminate it:
  kill -TERM `cat ~/.fileconveyor.pid`

You can configure File Conveyor to store the PID file in the more typical
/var/run location on *nix:
* You can change the PID_FILE setting in settings.py to 
/var/run/fileconveyor.pid. However, this requires File Conveyor to be run with
root permissions (/var/run requires root permissions).
* Alternatively, you can create a new directory in /var/run which then no
longer requires root permissions. This can be achieved through these commands:
 1. sudo mkdir /var/run/fileconveyor`
 2. sudo chown fileconveyor-user /var/run/fileconveyor
 3. sudo chown 700 /var/run/fileconveyor
Then, you can change the PID_FILE setting in settings.py to
/var/run/fileconveyor/fileconveyor.pid, and you won't need to run File 
Conveyor with root permissions anymore.


The daemon's behavior
---------------------
Upon startup, the daemon starts the file system monitor and then performs a
"manual" scan to detect changes since the last time it ran. If you've got a
lot of files, this may take a while.

Just for fun, type the following while the daemon is syncing:
  killall -9 python
Now the daemon is dead. Upon starting it again, you should see something like:
  2009-05-17 03:52:13,454 - Arbitrator                - WARNING  - Setup: initialized 'pipeline' persistent queue, contains 2259 items.
  2009-05-17 03:52:13,455 - Arbitrator                - WARNING  - Setup: initialized 'files_in_pipeline' persistent list, contains 47 items.
  2009-05-17 03:52:13,455 - Arbitrator                - WARNING  - Setup: initialized 'failed_files' persistent list, contains 0 items.
  2009-05-17 03:52:13,671 - Arbitrator                - WARNING  - Setup: moved 47 items from the 'files_in_pipeline' persistent list into the 'pipeline' persistent queue.
  2009-05-17 03:52:13,672 - Arbitrator                - WARNING  - Setup: moved 0 items from the 'failed_files' persistent list into the 'pipeline' persistent queue.
As you can see, 47 items were still in the pipeline when the daemon was
killed. They're now simply added to the pipeline queue again and they will be
processed once again.


The initial sync
----------------
To get a feeling of the daemon's speed, you may want to run it in the console
and look at its output.


Verifying the synced files
--------------------------
Running the verify.py script will open the synced files database and verify
that each synced file actually exists.




==============================================================================
| Processors                                                                 |
==============================================================================

Addressing processors
---------------------

You can address a specific processor by first specifying its processor module
and then the exact processor name (which is its class name):
- unique_filename.MD5
- image_optimizer.KeepMetadata
- yui_compressor.YUICompressor
- link_updater.CSSURLUpdater

But, it works with third-party processors too! Just make sure the third-party
package is in the Python path and then you can just use this in config.xml:
- MyProcessorPackage.SomeProcessorClass


Processor module: filename
--------------------------
Available processors:
1) SpacesToUnderscores
   Changes a filename; replaces spaces by underscores. E.g.:
     this is a test.txt --> this_is_a_test.txt
2) SpacesToDashes
Changes a filename; replaces spaces by dashes. E.g.:
  this is a test.txt --> this-is-a-test.txt


Processor module: unique_filename
---------------------------------
Available processors:
1) Mtime
   Changes a filename based on the file's mtime. E.g.:
     logo.gif --> logo_1240668971.gif
2) MD5
   Changes a filename based on the file's MD5 hash. E.g.:
     logo.gif --> logo_2f0342a2b9aaf48f9e75aa7ed1d58c48.gif


Processor module: image_optimizer
---------------------------------
It's important to note that all metadata is stripped from JPEG images, as that
is the most effective way to reduce the image size. However, this might also
strip copyright information, i.e. this can also have legal consequences.
Choose one of the "keep metadata" classes if you want to avoid this.
When optimizing GIF images, they are converted to the PNG format, which also
changes their filename.

Available processors:
1) Max
   optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)
2) KeepMetadata
   same as Max, but keeps JPEG metadata
3) KeepFilename
   same as Max, but keeps the original filename (no GIF optimization)
4) KeepMetadataAndFilename
   same as Max, but keeps JPEG metadata and the original filename (no GIF
   optimization)


Processor module: yui_compressor
--------------------------------
Warning: this processor is CPU-intensive! Since you typically don't get new
CSS and JS files all the time, it's still fine to use this. But the initial
sync may cause a lot of CSS and JS files to be processed and thereby cause a
lot of load!

Available processors:
1) YUICompressor
   Compresses .css and .js files with the YUI Compressor


Processor module: google_closure_compiler
-----------------------------------------
Warning: this processor is CPU-intensive! Since you typically don't get new
JS files all the time, it's still fine to use this. But the initial sync may
cause a lot of JS files to be processed and thereby cause a lot of load!

Available processors:
1) GoogleClosureCompiler
   Compresses .js files with the Google Closure Compiler


Processor module: link_updater
------------------------------
Warning: this processor is CPU-intensive! Since you typically don't get new
CSS files all the time, it's still fine to use this. But the initial sync may
cause a lot of CSS files to be processed and thereby cause a lot of load! Note
that this processor will skip processing a CSS file if not all files that are
referenced from it, have been synced to the CDN yet. Which means the CSS files
may need to parsed over and over again until the images have been synced.

It seems this processor is suited for optimization. It uses the cssutils
Python module, which validates every CSS property. This is an enormous slow-
down: on a 2.66 GHz Core 2 Duo, it causes 100% CPU usage every time it runs.
This module also seems to suffer from rather massive memory leaks. Memory
usage can easily top 30 MB on Mac OS X where it would never go over 17 MB
without this processor!

This processor will replace all URLs in CSS files with references to their
counterparts on the CDN. There are a couple of important gotchas to use this
processor module:
 - absolute URLs (http://, https://) are ignored, only relative URLs are
   processed
 - if a referenced file doesn't exist, its URL will remain unchanged
 - if one of the referenced images or fonts is changed and therefor resynced,
   and if it is configured to have a unique filename, the CDN URL referenced
   from the updated CSS file will no longer be valid. Therefor, when you
   update an image file or font file that is referenced by CSS files, you
   should modify the CSS files as well. Just modifying the mtime (by using the
   touch command) is sufficient.
 - it requires the referenced files to be synced to the same server the CSS
   file is being synced to. This implies that all the references files must
   also be synced to the same server, or the file will never get synced!

Available processors:
1) CSSURLUpdater
   Replaces URLs in .css files with their counterparts on the CDN




==============================================================================
| Transporters                                                               |
==============================================================================

Addressing transporters
-----------------------

You can address a specific transporter by only specifying its module:
- cf
- ftp
- mosso
- s3
- sftp
- symlink_or_copy

But, it works with third-party transporters too! Just make sure the
third-party package is in the Python path and then you can just use this in
config.xml:
- MyTransporterPackage


Transporter: FTP (ftp)
----------------------
Value to enter: "ftp".

Available settings:
- host
- username
- password
- url
- port
- path
- key


Transporter: SFTP (sftp)
------------------------
Value to enter: "sftp".

Available settings:
- host
- username
- password
- url
- port
- path


Transporter: Amazon S3
----------------------
Value to enter: "s3".

Available settings:
- access_key_id
- secret_access_key
- bucket_name
- bucket_prefix

More than 4 concurrent connections doesn't show a significant speedup.


Transporter: Amazon CloudFront
------------------------------
Value to enter: "cf".

Available settings:
- access_key_id
- secret_access_key
- bucket_name
- bucket_prefix
- distro_domain_name



Transporter: Mosso CloudFiles
---------------------------------
Value to enter: "mosso".

Available settings:
- username
- api_key
- container


Transporter: Symlink or Copy
----------------------------
Value to enter: "symlink_or_copy".

Available settings:
- location
- url


Transporter: Amazon CloudFront - Creating a CloudFront distribution
-------------------------------------------------------------------
You can either use the S3Fox Firefox add-on to create a distribution or use
the included Python function to do so. In the latter case, do the following:

>>> import sys
>>> sys.path.append('/path/to/daemon/transporters')
>>> sys.path.append('/path/to/daemon/dependencies')
>>> from transporter_cf import create_distribution
>>> create_distribution("access_key_id", "secret_access_key", "bucketname.s3.amazonaws.com")
Created distribution
    - domain name: dqz4yxndo4z5z.cloudfront.net
    - origin: bucketname.s3.amazonaws.com
    - status: InProgress
    - comment: 
    - id: E3FERS845MCNLE

    Over the next few minutes, the distribution will become active. This
    function will keep running until that happens.
    ............................
    The distribution has been deployed!




==============================================================================
| The advanced stuff                                                         |
==============================================================================

Constants in Arbitrator.py
--------------------------
The following constants can be tweaked to change where the daemon stores its
files, or to change its behavior.

RESTART_AFTER_UNHANDLED_EXCEPTION = True
  Whether File Conveyor should restart itself after it encountered an
  unhandled exception (i.e., a bug).
RESTART_INTERVAL = 10
  After how much time File Conveyor should restart itself, after it has
  encountered an unhandled exception. Thus, this setting only has an effect
  when RESTART_AFTER_UNHANDLED_EXCEPTION == True.
LOG_FILE = './daemon.log'
  The log file.
PERSISTENT_DATA_DB = './persistent_data.db'
  Where to store persistent data (pipeline queue, 'files in pipeline' list and
  'failed files' list).
SYNCED_FILES_DB = './synced_files.db'
  Where to store the input_file, transported_file_basename, url and server for
  each synced file.
WORKING_DIR = '/tmp/daemon'
  The working directory.
MAX_FILES_IN_PIPELINE = 50
  The maximum number of files in the pipeline. Should be high enough in order
  to prevent transporters from idling too long.
MAX_SIMULTANEOUS_PROCESSORCHAINS = 1
  The maximum number of processor chains that may be executed simultaneously.
  If you've got CPU intensive processors and if you're running the daemon on
  the web server, you'll want to keep this very low, probably at 1.
MAX_SIMULTANEOUS_TRANSPORTERS = 10
  The maximum number of transporters that may be running simultaneously. This
  effectively caps the number of simultaneous connections. It can also be used
  to have some -- although limited -- control on the throughput consumed by
  the transporters.
MAX_TRANSPORTER_QUEUE_SIZE = 1
  The maximum of files queued for each transporters. It's recommended to keep
  this low enough to ensure files are not unnecessarily waiting. If you set
  this too high, no new transporters will be spawned, because all files will
  be queued on the existing transporters. Setting this to 0 can only be
  recommended in environments with a continuous stream of files that need
  syncing. The default of 1 is to ensure each transporter is idling as little
  as possible.
QUEUE_PROCESS_BATCH_SIZE = 20
  The number of files that will be processed when processing one of the many
  queues. Setting this too low will cause overhead. Setting this too high will
  cause delays for files that are ready to be processed or transported. See
  the "Pipeline design pattern" section in my bachelor thesis text.
CALLBACKS_CONSOLE_OUTPUT = False
  Controls whether output will be generated for each callback. (There are
  callbacks for the file system monitor, processor chains and transporters.)
CONSOLE_LOGGER_LEVEL = logging.WARNING
  Controls the output level of the logging to the console. For a full list of
  possibilities, see http://docs.python.org/release/2.6/library/logging.html#logging-levels.
FILE_LOGGER_LEVEL = logging.DEBUG
  Controls the output level of the logging to the console. For a full list of
  possibilities, see http://docs.python.org/release/2.6/library/logging.html#logging-levels.
RETRY_INTERVAL = 30
  Sets the interval in which the 'failed files' list is appended to the
  pipeline queue, to retry to sync these failed files.


Understanding persistent_data.db
--------------------------------
We'll go through this by using a sample database I created. You should be able
to reproduce similar output on your persistent_data.db file using the exact
same commands.
Access the database, by using the SQLite console application.
  $ sqlite3 persistent_data.db
  SQLite version 3.6.11
  Enter ".help" for instructions
  Enter SQL statements terminated with a ";"
  sqlite>

As you can see, there are three tables in the database, one for every
persistent data structure:
  sqlite> .table
  failed_files_list  pipeline_list      pipeline_queue

Simple count queries show how many items there are in each persistent data
structure. In this case for example, there are 2560 files waiting to enter the
pipeline, 50 were in the pipeline at the time of stopping the daemon (these
will be added to the queue again once we restart the daemon) and 0 files are
in the list of failed files. Files end up in there when their processor chain
or (one of) their transporters fails.
  sqlite> SELECT COUNT(*) FROM pipeline_queue;
  2560
  sqlite> SELECT COUNT(*) FROM pipeline_list;
  50
  sqlite> SELECT COUNT(*) FROM failed_files_list;
  0

You can also look at the database schemas of these tables:
  sqlite> .schema pipeline_queue
  CREATE TABLE pipeline_queue(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle);
  sqlite> .schema pipeline_list
  CREATE TABLE pipeline_list(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle);
  sqlite> .schema failed_files_list
  CREATE TABLE failed_files_list(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle);

As you can see, the three tables have identical schemas. the type for the
stored item is 'pickle', which means that you can store any Python object in
there as long as it can be "pickled", which means as much as "convertable to
a string representation". "Serialization" is the term PHP developers have
given to this, although pickling is much more advanced.
The Python object stored in there is the same for all three tables: a tuple of
the filename (as a string) and the event (as an integer). The event is one of
FSMonitor.CREATED, FSMonitor.MODIFIED, FSMonitor.DELETED.

This file is what tracks the curent state of the daemon. Thanks to this file,
it is possible for the daemon to crash and not lose any data.
Deleting this file would cause the daemon to lose all of its current work.
Only new (as in: after the file was deleted) changes in the file system would
be picked up. Changes that still had to be synced, would be forgotten.


Understanding fsmonitor.db
--------------------------
This database has a single table: pathscanner (which is inherited from the
pathscanner module around which the fsmonitor module is built). Its schema is:

  sqlite> .schema pathscanner
  CREATE TABLE pathscanner(path text, filename text, mtime integer);

This file is what tracks the current state of the directory tree associated
with each source. When an operating system's file system monitor is used, this
database will be updated through its callbacks. When no such file system
monitor is available, it will be updated through polling.
Deleting this file would cause the daemon to have to sync all files again.


Understanding synced_files.db
-----------------------------
We'll go through this by using a sample database I created. You should be able
to reproduce similar output on your synced_files.db file using the exact
same commands.
Access the database, by using the SQLite console application.
  $ sqlite3 synced_files.db 
  SQLite version 3.6.11
  Enter ".help" for instructions
  Enter SQL statements terminated with a ";"
  sqlite>
  
As you can see, there's only one table: synced_files.
  sqlite> .table
  synced_files

Let's look at the schema. There are 4 fields: input_file,
transported_file_basename, url and server. input_file is the full path.
transported_file_basename is the base name of the file that was transported to
the server. This is stored because the filename might have been altered by the
processors that have been applied to it, but the path cannot change. I use
this to delete the previous version of a file if a file has been modified. The
url field is of course the URL to retrieve the file from the server. Finally,
the server field contains the name you've assigned to the server in the
configuration file. Each file may be synced to multiple servers and this
allows you to check if a file has been synchronized to a specific server.
  sqlite> .schema synced_files
  CREATE TABLE synced_files(input_file text, transported_file_basename text, url text, server text);

We can again use simple count queries to learn more about the synced files. As
you can see, 845 files have been synced, of which 602 have been synced to a
the server that was named "origin pull cdn" and 243 to the server that was
named "ftp push cdn".
  sqlite> SELECT COUNT(*) FROM synced_files;
  845
  sqlite> SELECT COUNT(*) FROM synced_files WHERE server="origin pull cdn";
  602
  sqlite> SELECT COUNT(*) FROM synced_files WHERE server="ftp push cdn";
  243


License
-------
This application is dual-licensed under the GPL and the UNLICENSE.

This application depends on various pieces of 3rd party code:
- parts of Django (dependencies/django). Django is released under the modified
  BSD license, which is GPL-compatible.
- boto (dependencies/boto). boto is released under the MIT license, which is
  GPL-compatible.
- django-storages (dependencies/storages). django-storages is released under
  the modified BSD license, which is GPL-compatible.
- python-cloudfiles (dependencies/cloudfiles). python-cloudfiles is released
  under the MIT license, which is GPL-compatible.
  
Hence it made sense to initially release the source code under the GPL.
Clearly, the 3rd party code is not UNLICENSEd; only the newly written code is.


Author
------
Wim Leers ~ http://wimleers.com/

This application was written as part of the bachelor thesis of Wim Leers at
Hasselt University.
