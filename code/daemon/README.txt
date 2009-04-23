Creating a CloudFront distribution
----------------------------------

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
