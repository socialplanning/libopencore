def limit_cookie(cookie_path, proxied_base, frontend_base):
    """

    Any cookie set for a path which precedes the proxied base 
    should be restricted to the frontend base URL:

    >>> print limit_cookie("/", "/lists/", "/projects/occupy-data/list/")
    /projects/occupy-data/list/

    >>> print limit_cookie("/lists", "/lists/", "/projects/occupy-data/list/")
    /projects/occupy-data/list/
    
    >>> print limit_cookie("/lists/", "/lists/", "/projects/occupy-data/list/")
    /projects/occupy-data/list/

    >>> print limit_cookie("/lists", "/lists", "/projects/occupy-data/list/")
    /projects/occupy-data/list/

    >>> print limit_cookie("/lists", "/lists", "/projects/occupy-data/list")
    /projects/occupy-data/list

    >>> print limit_cookie("/lists", "/lists/", "/projects/occupy-data/list")
    /projects/occupy-data/list

    >>> print limit_cookie("/lists/", "/lists/", "/projects/occupy-data/list")
    /projects/occupy-data/list

    But a cookie set for a path which does not overlap the proxied base
    should be removed entirely:

    >>> print limit_cookie("/groups", "/lists/", "/projects/occupy-data/list/")
    None

    >>> print limit_cookie("/groups/two/", "/lists/", "/projects/occupy-data/list/")
    None

    >>> print limit_cookie("/groups", "/lists/", "/projects/occupy-data/list/")
    None

    >>> print limit_cookie("/lists-and-more", "/lists/", "/projects/occupy-data/list/")
    None

    >>> print limit_cookie("/lists-and-more", "/lists", "/projects/occupy-data/list/")
    None

    A cookie set for a subpath of the proxied base should be rewritten
    to be prefixed by the frontend base URL:

    >>> print limit_cookie("/lists/arc/occupydata", "/lists/", "/projects/occupy-data/list/")
    /projects/occupy-data/list/arc/occupydata

    >>> print limit_cookie("/lists/arc/occupydata/", "/lists/", "/projects/occupy-data/list/")
    /projects/occupy-data/list/arc/occupydata/

    >>> print limit_cookie("/lists/", "/lists", "/projects/occupy-data/list")
    /projects/occupy-data/list/

    >>> print limit_cookie("/lists/", "/lists", "/projects/occupy-data/list/")
    /projects/occupy-data/list/

    """
    
    def split(path):
        return path.strip("/").split("/")

    def orthogonal(path, proxy):
        path = split(path)
        proxy = split(proxy)
        if len(path) == 1 and path[0] == '':
            return False
        for a, b in zip(path, proxy):
            if a != b:
                return True
    if orthogonal(cookie_path, proxied_base):
        return None
    
    def precedes(string_path, string_proxy):
        path = split(string_path)
        proxy = split(string_proxy)
        if len(path) == 1 and path[0] == '':
            return True
        if len(path) > len(proxy):
            return False
        for a, b in zip(path, proxy):
            if a != b:
                assert 1 == 0
                return False
        if string_path.endswith("/") and not string_proxy.endswith("/"):
            return False
        return True
    if precedes(cookie_path, proxied_base):
        return frontend_base

    def strip_prefix(path, proxy):
        if len(path) <= len(proxy):
            assert 1 == 0
            return None
        if path[:len(proxy)] != proxy:
            assert 1 == 0
            return None
        return path[len(proxy):]

    return '%s/%s' % (
        frontend_base.rstrip("/"), 
        strip_prefix(cookie_path, proxied_base).lstrip("/"))

if __name__ == '__main__':
    import doctest
    doctest.testmod()
