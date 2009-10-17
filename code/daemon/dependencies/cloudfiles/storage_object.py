"""
Object operations

An Object is analogous to a file on a conventional filesystem. You can
read data from, or write data to your Objects. You can also associate
arbitrary metadata with them.

See COPYING for license information.
"""

try:
	from hashlib import md5
except ImportError:
	from md5 import md5
import StringIO
import mimetypes
import os
import tempfile

from urllib  import quote
from errors  import ResponseError, NoSuchObject, \
                    InvalidObjectName, InvalidObjectSize, \
                    InvalidMetaName, InvalidMetaValue, \
                    IncompleteSend
from socket  import timeout
import consts
from utils   import requires_name

# Because HTTPResponse objects *have* to have read() called on them 
# before they can be used again ...
# pylint: disable-msg=W0612

class Object(object):
    """
    Storage data representing an object, (metadata and data).

    @undocumented: _make_headers
    @undocumented: _name_check
    @undocumented: _initialize
    @undocumented: compute_md5sum
    @undocumented: __get_conn_for_write
    @ivar name: the object's name (generally treat as read-only)
    @type name: str
    @ivar content_type: the object's content-type (set or read)
    @type content_type: str
    @ivar metadata: metadata associated with the object (set or read)
    @type metadata: dict
    @ivar size: the object's size (cached)
    @type size: number
    @ivar last_modified: date and time of last file modification (cached)
    @type last_modified: str
    @ivar container: the object's container (generally treat as read-only)
    @type container: L{Container}
    """
    # R/O support of the legacy objsum attr.
    objsum = property(lambda self: self._etag)

    def __set_etag(self, value):
        self._etag = value
        self._etag_override = True

    etag = property(lambda self: self._etag, __set_etag)

    def __init__(self, container, name=None, force_exists=False, object_record=None):
        """
        Storage objects rarely if ever need to be instantiated directly by the
        user.

        Instead, use the L{create_object<Container.create_object>},
        L{get_object<Container.get_object>},
        L{list_objects<Container.list_objects>} and other
        methods on its parent L{Container} object.
        """
        self.container = container
        self.last_modified = None
        self.metadata = {}
        if object_record:
            self.name = object_record['name']
            self.content_type = object_record['content_type']
            self.size = object_record['bytes']
            self.last_modified = object_record['last_modified']
            self._etag = object_record['hash']
            self._etag_override = False
        else:
            self.name = name
            self.content_type = None
            self.size = None
            self._etag = None
            self._etag_override = False
            if not self._initialize() and force_exists:
                raise NoSuchObject(self.name)

    @requires_name(InvalidObjectName)
    def read(self, size=-1, offset=0, hdrs=None, buffer=None, callback=None):
        """
        Read the content from the remote storage object.

        By default this method will buffer the response in memory and
        return it as a string. However, if a file-like object is passed
        in using the buffer keyword, the response will be written to it
        instead.

        A callback can be passed in for reporting on the progress of
        the download. The callback should accept two integers, the first
        will be for the amount of data written so far, the second for
        the total size of the transfer. Note: This option is only
        applicable when used in conjunction with the buffer option.

        >>> test_object.write('hello')
        >>> test_object.read()
        'hello'

        @param size: combined with offset, defines the length of data to be read
        @type size: number
        @param offset: combined with size, defines the start location to be read
        @type offset: number
        @param hdrs: an optional dict of headers to send with the request
        @type hdrs: dictionary
        @param buffer: an optional file-like object to write the content to
        @type buffer: file-like object
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        @rtype: str or None
        @return: a string of all data in the object, or None if a buffer is used
        """
        self._name_check()
        if size > 0:
            range = 'bytes=%d-%d' % (offset, (offset + size) - 1)
            if hdrs:
                hdrs['Range'] = range
            else:
                hdrs = {'Range': range}
        response = self.container.conn.make_request('GET',
                path = [self.container.name, self.name], hdrs = hdrs)
        if (response.status < 200) or (response.status > 299):
            buff = response.read()
            raise ResponseError(response.status, response.reason)

        if hasattr(buffer, 'write'):
            scratch = response.read(8192)
            transferred = 0

            while len(scratch) > 0:
                buffer.write(scratch)
                transferred += len(scratch)
                if callable(callback):
                    callback(transferred, self.size)
                scratch = response.read(8192)
            return None
        else:
            return response.read()

    def save_to_filename(self, filename, callback=None):
        """
        Save the contents of the object to filename.

        >>> container = connection['container1']
        >>> obj = container.get_object('backup_file')
        >>> obj.save_to_filename('./backup_file')

        @param filename: name of the file
        @type filename: str
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        try:
            fobj = open(filename, 'wb')
            self.read(buffer=fobj, callback=callback)
        finally:
            fobj.close()

    @requires_name(InvalidObjectName)
    def stream(self, chunksize=8192, hdrs=None):
        """
        Return a generator of the remote storage object's data.

        Warning: The HTTP response is only complete after this generator
        has raised a StopIteration. No other methods can be called until
        this has occurred.

        >>> test_object.write('hello')
        >>> test_object.stream()
        <generator object at 0xb77939cc>
        >>> '-'.join(test_object.stream(chunksize=1))
        'h-e-l-l-o'

        @param chunksize: size in bytes yielded by the generator
        @type chunksize: number
        @param hdrs: an optional dict of headers to send in the request
        @type hdrs: dict
        @rtype: str generator
        @return: a generator which yields strings as the object is downloaded
        """
        self._name_check()
        response = self.container.conn.make_request('GET',
                path = [self.container.name, self.name], hdrs = hdrs)
        if response.status < 200 or response.status > 299:
            buff = response.read()
            raise ResponseError(response.status, response.reason)
        buff = response.read(chunksize)
        while len(buff) > 0:
            yield buff
            buff = response.read(chunksize)
        # I hate you httplib
        buff = response.read()

    @requires_name(InvalidObjectName)
    def sync_metadata(self):
        """
        Commits the metadata to the remote storage system.

        >>> test_object = container['paradise_lost.pdf']
        >>> test_object.metadata = {'author': 'John Milton'}
        >>> test_object.sync_metadata()

        Object metadata can be set and retrieved through the object's
        .metadata attribute.
        """
        self._name_check()
        if self.metadata:
            headers = self._make_headers()
            headers['Content-Length'] = 0
            response = self.container.conn.make_request(
                'POST', [self.container.name, self.name], hdrs=headers, data=''
            )
            buff = response.read()
            if response.status != 202:
                raise ResponseError(response.status, response.reason)

    def __get_conn_for_write(self):
        headers = self._make_headers()

        headers['X-Auth-Token'] = self.container.conn.token

        path = "/%s/%s/%s" % (self.container.conn.uri.rstrip('/'), \
                quote(self.container.name), quote(self.name))

        # Requests are handled a little differently for writes ...
        http = self.container.conn.connection

        # TODO: more/better exception handling please
        http.putrequest('PUT', path)
        for hdr in headers:
            http.putheader(hdr, headers[hdr])
        http.putheader('User-Agent', consts.user_agent)
        http.endheaders()
        return http

    # pylint: disable-msg=W0622
    @requires_name(InvalidObjectName)
    def write(self, data='', verify=True, callback=None):
        """
        Write data to the remote storage system.

        By default, server-side verification is enabled, (verify=True), and
        end-to-end verification is performed using an md5 checksum. When
        verification is disabled, (verify=False), the etag attribute will
        be set to the value returned by the server, not one calculated
        locally. When disabling verification, there is no guarantee that
        what you think was uploaded matches what was actually stored. Use
        this optional carefully. You have been warned.

        A callback can be passed in for reporting on the progress of
        the upload. The callback should accept two integers, the first
        will be for the amount of data written so far, the second for
        the total size of the transfer.

        >>> test_object = container.create_object('file.txt')
        >>> test_object.content_type = 'text/plain'
        >>> fp = open('./file.txt')
        >>> test_object.write(fp)

        @param data: the data to be written
        @type data: str or file
        @param verify: enable/disable server-side checksum verification
        @type verify: boolean
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        self._name_check()
        if isinstance(data, file):
            # pylint: disable-msg=E1101
            try:
                data.flush()
            except IOError:
                pass # If the file descriptor is read-only this will fail
            self.size = int(os.fstat(data.fileno())[6])
        else:
            data = StringIO.StringIO(data)
            self.size = data.len

        # If override is set (and _etag is not None), then the etag has
        # been manually assigned and we will not calculate our own.

        if not self._etag_override:
            self._etag = None

        if not self.content_type:
            # pylint: disable-msg=E1101
            type = None
            if hasattr(data, 'name'):
                type = mimetypes.guess_type(data.name)[0]
            self.content_type = type and type or 'application/octet-stream'

        http = self.__get_conn_for_write()

        response = None
        transfered = 0
        running_checksum = md5()

        buff = data.read(4096)
        try:
            while len(buff) > 0:
                http.send(buff)
                if verify and not self._etag_override:
                    running_checksum.update(buff)
                buff = data.read(4096)
                transfered += len(buff)
                if callable(callback):
                    callback(transfered, self.size)
            response = http.getresponse()
            buff = response.read()
        except timeout, err:
            if response:
                # pylint: disable-msg=E1101
                buff = response.read()
            raise err
        else:
            if verify and not self._etag_override:
                self._etag = running_checksum.hexdigest()

        # ----------------------------------------------------------------

        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)

        # If verification has been disabled for this write, then set the 
        # instances etag attribute to what the server returns to us.
        if not verify:
            for hdr in response.getheaders():
                if hdr[0].lower() == 'etag':
                    self._etag = hdr[1]

    @requires_name(InvalidObjectName)
    def send(self, iterable):
        """
        Write potentially transient data to the remote storage system using a
        generator or stream.

        If the object's size is not set, chunked transfer encoding will be
        used to upload the file.

        If the object's size attribute is set, it will be used as the
        Content-Length.  If the generator raises StopIteration prior to yielding
        the right number of bytes, an IncompleteSend exception is raised.

        If the content_type attribute is not set then a value of
        application/octet-stream will be used.

        Server-side verification will be performed if an md5 checksum is
        assigned to the etag property before calling this method,
        otherwise no verification will be performed, (verification
        can be performed afterward though by using the etag attribute
        which is set to the value returned by the server).

        >>> test_object = container.create_object('backup.tar.gz')
        >>> pfd = os.popen('tar -czvf - ./data/', 'r')
        >>> test_object.send(pfd)

        @param iterable: stream or generator which yields the content to upload
        @type iterable: generator or stream
        """
        self._name_check()

        if hasattr(iterable, 'read'):
            def file_iterator(file):
                chunk = file.read(4095)
                while chunk:
                    yield chunk
                    chunk = file.read(4095)
                raise StopIteration()
            iterable = file_iterator(iterable)

        # This method implicitly diables verification
        if not self._etag_override:
            self._etag = None

        if not self.content_type:
            self.content_type = 'application/octet-stream'

        path = "/%s/%s/%s" % (self.container.conn.uri.rstrip('/'), \
                quote(self.container.name), quote(self.name))
        headers = self._make_headers()
        if self.size is None:
            del headers['Content-Length']
            headers['Transfer-Encoding'] = 'chunked'
        headers['X-Auth-Token'] = self.container.conn.token
        headers['User-Agent'] = consts.user_agent
        http = self.container.conn.connection
        http.putrequest('PUT', path)
        for key, value in headers.iteritems():
            http.putheader(key, value)
        http.endheaders()

        response = None
        transferred = 0
        try:
            for chunk in iterable:
                if self.size is None:
                    http.send("%X\r\n" % len(chunk))
                    http.send(chunk)
                    http.send("\r\n")
                else:
                    http.send(chunk)
                transferred += len(chunk)
            if self.size is None:
                http.send("0\r\n\r\n")
            # If the generator didn't yield enough data, stop, drop, and roll.
            elif transferred < self.size:
                raise IncompleteSend()
            response = http.getresponse()
            buff = response.read()
        except timeout, err:
            if response:
                # pylint: disable-msg=E1101
                buff = response.read()
            raise err

        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)

        for hdr in response.getheaders():
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]

    def load_from_filename(self, filename, verify=True, callback=None):
        """
        Put the contents of the named file into remote storage.

        >>> test_object = container.create_object('file.txt')
        >>> test_object.content_type = 'text/plain'
        >>> test_object.load_from_filename('./my_file.txt')

        @param filename: path to the file
        @type filename: str
        @param verify: enable/disable server-side checksum verification
        @type verify: boolean
        @param callback: function to be used as a progress callback
        @type callback: callable(transferred, size)
        """
        fobj = open(filename, 'rb')
        self.write(fobj, verify=verify, callback=callback)
        fobj.close()

    def _initialize(self):
        """
        Initialize the Object with values from the remote service (if any).
        """
        if not self.name:
            return False

        response = self.container.conn.make_request(
                'HEAD', [self.container.name, self.name]
        )
        buff = response.read()
        if response.status == 404:
            return False
        if (response.status < 200) or (response.status > 299):
            raise ResponseError(response.status, response.reason)
        for hdr in response.getheaders():
            if hdr[0].lower() == 'content-type':
                self.content_type = hdr[1]
            if hdr[0].lower().startswith('x-object-meta-'):
                self.metadata[hdr[0][14:]] = hdr[1]
            if hdr[0].lower() == 'etag':
                self._etag = hdr[1]
                self._etag_override = False
            if hdr[0].lower() == 'content-length':
                self.size = int(hdr[1])
            if hdr[0].lower() == 'last-modified':
                self.last_modified = hdr[1]
        return True

    def __str__(self):
        return self.name

    def _name_check(self):
        if len(self.name) > consts.object_name_limit:
            raise InvalidObjectName(self.name)

    def _make_headers(self):
        """
        Returns a dictionary representing http headers based on the
        respective instance attributes.
        """
        headers = {}
        headers['Content-Length'] = self.size and self.size or 0
        if self._etag: headers['ETag'] = self._etag

        if self.content_type: headers['Content-Type'] = self.content_type
        else: headers['Content-Type'] = 'application/octet-stream'

        for key in self.metadata:
            if len(key) > consts.meta_name_limit:
                raise(InvalidMetaName(key))
            if len(self.metadata[key]) > consts.meta_value_limit:
                raise(InvalidMetaValue(self.metadata[key]))
            headers['X-Object-Meta-'+key] = self.metadata[key]
        return headers

    @classmethod
    def compute_md5sum(cls, fobj):
        """
        Given an open file object, returns the md5 hexdigest of the data.
        """
        checksum = md5()
        buff = fobj.read(4096)
        while buff:
            checksum.update(buff)
            buff = fobj.read(4096)
        fobj.seek(0)
        return checksum.hexdigest()

    def public_uri(self):
        """
        Retrieve the URI for this object, if its container is public.

        >>> container1 = connection['container1']
        >>> container1.make_public()
        >>> container1.create_object('file.txt').write('testing')
        >>> container1['file.txt'].public_uri()
        'http://c00061.cdn.cloudfiles.rackspacecloud.com/file.txt'

        @return: the public URI for this object
        @rtype: str
        """
        return "%s/%s" % (self.container.public_uri().rstrip('/'),
                quote(self.name))

class ObjectResults(object):
    """
    An iterable results set object for Objects.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, container, objects=None):
        self._objects = objects and objects or list()
        self._names = [obj['name'] for obj in self._objects]
        self.container = container

    def __getitem__(self, key):
        return Object(self.container, object_record=self._objects[key])

    def __getslice__(self, i, j):
        return [Object(self.container, object_record=k) for k in self._objects[i:j]]

    def __contains__(self, item):
        return item in self._objects

    def __len__(self):
        return len(self._objects)

    def __repr__(self):
        return 'ObjectResults: %s objects' % len(self._objects)
    __str__ = __repr__

    def index(self, value, *args):
        """
        returns an integer for the first index of value
        """
        return self._names.index(value, *args)

    def count(self, value):
        """
        returns the number of occurrences of value
        """
        return self._names.count(value)

# vim:set ai sw=4 ts=4 tw=0 expandtab:
