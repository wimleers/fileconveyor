import StringIO
# FTP storage class for Django pluggable storage system.
# Author: Rafal Jonca <jonca.rafal@gmail.com>
# License: MIT
# Comes from http://www.djangosnippets.org/snippets/1269/
#
# Usage:
#
# Add below to settings.py:
# FTP_STORAGE_LOCATION = '[a]ftp://<user>:<pass>@<host>:<port>/[path]'
#
# In models.py you can write:
# from FTPStorage import FTPStorage
# fs = FTPStorage()
# class FTPTest(models.Model):
#     file = models.FileField(upload_to='a/b/c/', storage=fs)

import pprint
import os
import errno
import urlparse
import paramiko, base64
from paramiko.sftp import *
from binascii import hexlify

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured

# setup logging
paramiko.util.log_to_file('demo_sftp.log')


class SSFTPStorageException(Exception): pass

class SFTPStorage(Storage):
    """SFTP Storage class for Django pluggable storage system."""

    def __init__(self, location=settings.FTP_STORAGE_LOCATION, base_url=settings.MEDIA_URL, key=None):
        self._config = self._decode_location(location)
        self._config['key'] = key
        self._base_url = base_url
        self._connection = None

    def _decode_location(self, location):
        """Return splitted configuration data from location."""
        splitted_url = urlparse.urlparse(location)
        config = {}
        
        if splitted_url.scheme not in ('sftp'):
            raise ImproperlyConfigured('SFTPStorage works only with SFTP protocol!')
        if splitted_url.hostname == '':
            raise ImproperlyConfigured('You must at least provide hostname!')
        
        config['path'] = splitted_url.path
        config['host'] = splitted_url.hostname
        config['user'] = splitted_url.username
        config['passwd'] = splitted_url.password
        config['port'] = int(splitted_url.port)
        
        return config

    def _agent_auth(self,transport,username):
        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            try:
                transport.auth_publickey(username, key)
                # print "Using Key %s" % hexlify(key.get_fingerprint())
                return
            except paramiko.SSHException:
                # print "Error logging in with key %s" % hexlify(key.get_fingerprint())
                raise
            except paramiko.AuthenticationException:
                # print "Not Using Key %s" % hexlify(key.get_fingerprint())
                raise

    def _start_connection(self):
        # Check if connection is still alive and if not, drop it.
        if self._connection is not None:
            try:
                self._connection.getcwd()
            except paramiko.SSHException, e:
                self._connection = None
        
        # Real reconnect
        if self._connection is None:
            try:
                t = paramiko.Transport((self._config['host'], self._config['port']))
                t.start_client()
                self._agent_auth(t, self._config['user'])
                
                if not t.is_authenticated():
                    #Use password auth
                    t.connect(username=self._config['user'], password=self._config['passwd']) #,hostkey=hostkey

                sftp = paramiko.SFTPClient.from_transport(t)
                if self._config['path'] != '':
                    sftp.chdir(self._config['path'])

                self._connection = sftp
            except paramiko.SSHException, e:
                raise SSFTPStorageException('Connection or login error using data %s' % repr(self._config))

    def disconnect(self):
        self._connection.close()
        self._connection = None

    def _mkremdirs(self, path):
        pwd = self._connection.getcwd()
        path_splitted = path.split('/')
        for path_part in path_splitted:
            try:
                self._connection.chdir(path_part)
            except:
                try:
                    self._connection.mkdir(path_part)
                    self._connection.chdir(path_part)
                except paramiko.SSHException, e:
                    raise SFTPStorageException('Cannot create directory chain %s' % path)
        self._connection.chdir(pwd)
        return

    def _put_file(self, name, content):
        # Connection must be open!
        try:
            self._mkremdirs(os.path.dirname(name))
            pwd = self._connection.getcwd()
            self._connection.chdir(os.path.dirname(name))
            try:
                fr = self._connection.open(os.path.basename(name), 'wb')
                fr.write(content)
            finally:
                self._connection.chdir(pwd)
        except paramiko.SSHException, e:
            raise SFTPStorageException('Error writing file %s' % name)

    def _open(self, name, mode='rb'):
        remote_file = SFTPStorageFile(name, self, mode=mode)
        return remote_file

    def _read(self, name):
        memory_file = StringIO()
        try:
            pwd = self._connection.getcwd()
            self._connection.chdir(os.path.dirname(name))
            memory_file.write(self._connection.open(os.path.basename(name)).read())
            self._connection.chdir(pwd)
            return memory_file
        except paramiko.SSHException, e:
            raise SFTPStorageException('Error reading file %s' % name)
        
    def _save(self, name, content):
        content.open()
        self._start_connection()
        self._put_file(name, content.read())
        content.close()
        return name

    def _get_dir_details(self, path):
        # Connection must be open!
        try:
            lines = []
            lines = self._connection.listdir_attr(path)
            dirs = {}
            files = {}
            for line in lines:
                words = line.split()
                if len(words) < 6:
                    continue
                if words[-2] == '->':
                    continue
                if words[0][0] == 'd':
                    dirs[words[-1]] = 0;
                elif words[0][0] == '-':
                    files[words[-1]] = int(words[-5]);
            return dirs, files
        except paramiko.SSHException, msg:
            raise SFTPStorageException('Error getting listing for %s' % path)

    def listdir(self, path):
        self._start_connection()
        raise Error("listdir Not yet implemnted")
        try:
            dirs, files = self._get_dir_details(path)
            return dirs.keys(), files.keys()
        except SFTPStorageException, e:
            raise

    def delete(self, name):
        if not self.exists(name):
            return
        self._start_connection()
        try:
            self._connection.remove(name)
        except Error, e:
            raise SFTPStorageException('Error when removing %s' % name)

    def exists(self, name):
        self._start_connection()
        try:
            attr = self._connection.stat(name)
            if attr.attr == {}:
                return False
            return True
        except IOError as (code, strerror):
            if (code == errno.ENOENT):
                return False
        except SFTPError, e:
            raise SFTPStorageException('Error when testing existence of %s' % name)

    def size(self, name):
        raise Error("not yet implemeted")
        self._start_connection()
        try:
            dirs, files = self._get_dir_details(os.path.dirname(name))
            if os.path.basename(name) in files:
                return files[os.path.basename(name)]
            else:
                return 0
        except SFTPStorageException, e:
            return 0

    def url(self, name):
        if self._base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self._base_url, name).replace('\\', '/')

class SFTPStorageFile(File):
    def __init__(self, name, storage, mode):
        self._name = name
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self._is_read = False
    
    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        if not self._is_read:
            self._storage._start_connection()
            self.file = self._storage._read(self._name)
            self._storage._end_connection()
            self._is_read = True
            
        return self.file.read(num_bytes)

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True
        self._is_read = True

    def close(self):
        if self._is_dirty:
            self._storage._start_connection()
            self._storage._put_file(self._name, self.file.getvalue())
            self._storage._end_connection()
        self.file.close()