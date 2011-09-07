import sys
import os
import os.path
import time
import subprocess
import tempfile


from transporter_ftp import *
from transporter_s3 import *
from transporter_cf import *
from transporter_none import *


if __name__ == "__main__":
    # Set up logger.
    logger = logging.getLogger("Test")
    logger.setLevel(logging.DEBUG)
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)
    logger.addHandler(h)

    def callback(src, dst, url, action):
        print """CALLBACK FIRED:
                    src='%s'
                    dst='%s'
                    url='%s'
                    action=%d""" % (src, dst, url, action)

    def error_callback(src, dst, action):
        print """ERROR CALLBACK FIRED:
                    src='%s'
                    dst='%s'
                    action=%d""" % (src, dst, action)

    # FTP
    settings = {
        "host"     : "your ftp host",
        "username" : "your username",
        "password" : "your password",
        "url"      : "your base URL"
    }
    try:
        ftp = TransporterFTP(settings, callback, error_callback, "Test")
    except Exception, e:
        print "Error occurred in TransporterFTP:", e
    else:
        ftp.start()
        ftp.sync_file("transporter.py")
        ftp.sync_file("drupal-5-6.png")
        ftp.sync_file("subdir/bmi-chart.png")
        ftp.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        ftp.stop()


    # Amazon S3
    settings = {
        "access_key_id"      : "your access key id",
        "secret_access_key"  : "your secret access key",
        "bucket_name"        : "your bucket name",
    }
    try:
        s3 = TransporterS3(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterS3:", e
    else:
        s3.start()
        s3.sync_file("transporter.py")
        s3.sync_file("drupal-5-6.png")
        s3.sync_file("subdir/bmi-chart.png")
        s3.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        s3.stop()


    # Amazon CloudFront
    settings = {
        "access_key_id"      : "your access key id",
        "secret_access_key"  : "your secret access key",
        "bucket_name"        : "your bucket name",
        "distro_domain_name" : "your-distro-domain-name.cloudfront.net",
    }
    try:
        cf = TransporterCF(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterCF:", e
    else:
        cf.start()
        cf.sync_file("transporter.py")
        cf.sync_file("drupal-5-6.png")
        cf.sync_file("subdir/bmi-chart.png")
        cf.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        cf.stop()


    # None
    settings = {
        "location"     : "/htdocs/static.example.com/",
        "url"          : "http://static.example.com/",
        "symlinkWithin": os.path.abspath('')
    }
    try:
        none = TransporterNone(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterNone:", e
    else:
        none.start()
        none.sync_file("transporter.py")
        none.sync_file("drupal-5-6.png")
        none.sync_file("subdir/bmi-chart.png")
        subprocess.call("echo yarhar > $TMPDIR/foobar.txt", shell=True, stdout=subprocess.PIPE)
        none.sync_file(os.path.join(tempfile.gettempdir(), "foobar.txt"))
        none.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        none.stop()
