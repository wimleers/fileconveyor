""" See COPYING for license information. """

import re
from urlparse  import urlparse
from errors    import InvalidUrl
from consts    import object_name_limit

def parse_url(url):
    """
    Given a URL, returns a 4-tuple containing the hostname, port,
    a path relative to root (if any), and a boolean representing 
    whether the connection should use SSL or not.
    """
    (scheme, netloc, path, params, query, frag) = urlparse(url)

    # We only support web services
    if not scheme in ('http', 'https'):
        raise InvalidUrl('Scheme must be one of http or https')

    is_ssl = scheme == 'https' and True or False

    # Verify hostnames are valid and parse a port spec (if any)
    match = re.match('([a-zA-Z0-9\-\.]+):?([0-9]{2,5})?', netloc)

    if match:
        (host, port) = match.groups()
        if not port:
            port = is_ssl and '443' or '80'
    else:
        raise InvalidUrl('Invalid host and/or port: %s' % netloc)

    return (host, int(port), path.strip('/'), is_ssl)

def requires_name(exc_class):
    """Decorator to guard against invalid or unset names."""
    def wrapper(f):
        def decorator(*args, **kwargs):
            if not hasattr(args[0], 'name'):
                raise exc_class('')
            if not args[0].name:
                raise exc_class(args[0].name)
            return f(*args, **kwargs)
        decorator.__name__ = f.__name__
        decorator.__doc__ = f.__doc__
        decorator.parent_func = f
        return decorator
    return wrapper
