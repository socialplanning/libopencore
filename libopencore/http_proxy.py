from wsgifilter import proxyapp

vhm_template = "/VirtualHostBase/%(wsgi.url_scheme)s/%(HTTP_HOST)s:%(frontend_port)s"

def app_factory(global_conf,
                remote_uri=None,
                is_opencore=False,
                is_twirlip=None,
                robots_uri=None,
                site_root=None,
                rewrite_links=False,
                **local_conf):
    assert remote_uri is not None
    if site_root is not None:
        assert is_opencore

    remote_uris = [i.strip() for i in remote_uri.split()
                   if i.strip()]
    
    app = RemoteProxy(remote_uris, is_opencore, 
                      robots_uri=robots_uri,
                      site_root=site_root, rewrite_links=rewrite_links)
    if is_twirlip is None:
        return app
    # if we're proxying to twirlip we need to wrap this in
    # eyvind's middleware which transforms REMOTE_USER 
    # into a signed HTTP header that can be passed to twirlip
    from eyvind.lib.authmiddleware import make_auth_middleware
    app = fixer(app)
    app = make_auth_middleware(app, local_conf)
    return app

class fixer(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        p = environ['PATH_INFO'] 
        p = p.lstrip('/')
        environ['PATH_INFO'] = p
        return self.app(environ, start_response)

from random import randint
class RemoteProxy(object):
    def __init__(self, remote_uris=None, is_opencore=False, 
                 robots_uri=None, site_root=None, rewrite_links=False):
        remote_uris = remote_uris or []

        # make sure there's no trailing slash
        self.remote_uris = [
            remote_uri.rstrip('/')
            for remote_uri in remote_uris
            ]
        
        self.is_opencore = is_opencore

        if site_root:
            site_root = '/%s/' % site_root.strip('/')
        self.site_root = site_root or "/openplans/"
        

        if robots_uri is not None:
            robots_uri = robots_uri.rstrip('/') + '/'
        self.robots_uri = robots_uri
        self.rewrite_links = rewrite_links

    robots = ["+http://www.exabot.com/go/robot",
              "+http://search.msn.com/msnbot.htm",
              "+http://www.google.com/bot.html",
              "+http://about.ask.com/en/docs/about/webmasters.shtml",
              "+http://yandex.com/bots",
              "+http://help.yahoo.com/help/us/ysearch/slurp",
              "+http://www.baidu.com/search/spider.htm",
              "+http://www.bing.com/bingbot.htm"
              ]

    def test_robots(self, environ):
        if not environ.has_key("HTTP_USER_AGENT"):
            return False
        agent = environ['HTTP_USER_AGENT'].lower()
        for robot in self.robots:
            if robot in agent:
                return True
        return False

    def pick_remote_uri(self, environ):
        if self.robots_uri is not None:            
            if self.test_robots(environ):
                return self.robots_uri
        i = randint(0, len(self.remote_uris)-1)
        return self.remote_uris[i]

    def __call__(self, environ, start_response):
        remote_uri = self.pick_remote_uri(environ)

        if self.is_opencore:
            environ_copy = environ.copy()

            # With varnish on port 80 proxying to the opencore stack entrypoint,
            # HTTP_HOST doesn't include the :80 bit. (I don't know about other
            # frontends.) Just to be safe, we'll decompose HTTP_HOST into its
            # parts, and if the port information is missing, we'll set port 80.
            #
            # The virtual host monster needs this information. If it's missing,
            # opencore will generate links with the port that Zope is served on.

            parts = environ['HTTP_HOST'].split(':')
            environ_copy['HTTP_HOST'] = parts[0]
            if len(parts) > 1:
                environ_copy['frontend_port'] = parts[1]
            else:
                environ_copy['frontend_port'] = '80'
            remote_uri = ''.join([
                remote_uri,
                (vhm_template % environ_copy),
                self.site_root,
                'VirtualHostRoot'])

        environ['HTTP_X_OPENPLANS_DOMAIN'] = environ['HTTP_HOST'].split(':')[0]

        app = proxyapp.ForcedProxy(
            remote=remote_uri,
            force_host=True)

        # work around bug in WSGIFilter
        environ_copy = environ.copy()
        
        from webob import Request
        request = Request(environ_copy)
        resp = request.get_response(app)

        if self.rewrite_links:
            resp = rewrite_links(
                Request(environ), resp,
                url_normalize(remote_uri),
                url_normalize(Request(environ).application_url),
                url_normalize('%s://%s%s' % (
                        request.scheme, 
                        request.host,
                        request.path_qs))
                )
        
        return resp(environ, start_response)

from deliverance.util.urlnormalize import url_normalize
import re
_cookie_domain_re = re.compile(r'(domain="?)([a-z0-9._-]*)("?)', re.I)
from lxml.html import document_fromstring, tostring
import urlparse

def rewrite_links(request, response,
                  proxied_base, orig_base,
                  proxied_url):

    exact_proxied_base = proxied_base
    if not proxied_base.endswith('/'):
        proxied_base += '/'
    exact_orig_base = orig_base
    if not orig_base.endswith('/'):
        orig_base += '/'
    assert (proxied_url.startswith(proxied_base) 
            or proxied_url.split('?', 1)[0] == proxied_base[:-1]), (
        "Unexpected proxied_url %r, doesn't start with proxied_base %r"
        % (proxied_url, proxied_base))
    assert (request.url.startswith(orig_base) 
            or request.url.split('?', 1)[0] == orig_base[:-1]), (
        "Unexpected request.url %r, doesn't start with orig_base %r"
        % (request.url, orig_base))

    def link_repl_func(link):
        """Rewrites a link to point to this proxy"""
        if link == exact_proxied_base:
            return exact_orig_base
        if not link.startswith(proxied_base):
            # External link, so we don't rewrite it
            return link
        new = orig_base + link[len(proxied_base):]
        return new
    if response.content_type != 'text/html' or len(response.body) == 0:
        pass
    else:
        if not response.charset:
            ## FIXME: maybe we should guess the encoding?
            body = response.body
        else:
            body = response.unicode_body
        body_doc = document_fromstring(body, base_url=proxied_url)
        body_doc.make_links_absolute()
        body_doc.rewrite_links(link_repl_func)
        response.body = tostring(body_doc)

    if response.location:
        ## FIXME: if you give a proxy like
        ## http://openplans.org, and it redirects to
        ## http://www.openplans.org, it won't be rewritten and
        ## that can be confusing -- it *shouldn't* be
        ## rewritten, but some better log message is required
        loc = urlparse.urljoin(proxied_url, response.location)
        loc = link_repl_func(loc)
        response.location = loc
        
    if 'set-cookie' in response.headers:
        cookies = response.headers.getall('set-cookie')
        del response.headers['set-cookie']
        for cook in cookies:
            old_domain = urlparse.urlsplit(proxied_url)[1].lower()
            new_domain = request.host.split(':', 1)[0].lower()
            def rewrite_domain(match):
                """Rewrites domains to point to this proxy"""
                domain = match.group(2)
                if domain == old_domain:
                    ## FIXME: doesn't catch wildcards and the sort
                    return match.group(1) + new_domain + match.group(3)
                else:
                    return match.group(0)
            cook = _cookie_domain_re.sub(rewrite_domain, cook)
            response.headers.add('set-cookie', cook)

    return response
