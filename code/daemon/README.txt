Addressing Processors
---------------------
You can address a specific processor by first specifying its Processor module
and then the exact Processor name (which is its class name):
  ProcessorModuleName.ProcessorName
E.g.:
- unique_filename.MD5
- image_optimizer.KeepMetadata


Processor module: unique_filename
---------------------------------
Available Processors:
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
changes their filename. This means they have to be stored

Available Processors:
1) Max
   optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)
2) KeepMetadata
   same as Max, but keeps JPEG metadata
3) KeepFilename
   same as Max, but keeps the original filename (no GIF optimization)
4) KeepMetadataAndFilename
   same as Max, but keeps JPEG metadata and the original filename (no GIF optimization)


Transporter: CloudFront - Creating a CloudFront distribution
------------------------------------------------------------

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
