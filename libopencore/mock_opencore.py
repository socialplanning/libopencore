def app_factory(global_conf, **kw):
    return MockOpencore(**kw)

from webob import Request, Response
from libopencore.auth import *
from tempita import Template

class MockOpencore(object):
    def __init__(self, secret):
        self.secret = secret

    def __call__(self, environ, start_response):
        req = Request(environ)

        path = req.path_info_peek()

        if path == "theme.html":
            return self.theme(environ, start_response)

        if path == "login":
            return self.login(environ, start_response)
        if path == "logout":
            if '__ac' in req.cookies:
                res = Response()
                res.status = 304
                res.location = "/"
                res.delete_cookie("__ac")
                return res(environ, start_response)
                
        if path == "projects":
            req.path_info_pop()
            project = req.path_info_pop()
            path = req.path_info_peek()

            if path == "info.xml":
                return Response("""
<info>
<policy>medium_policy</policy>
 <featurelets> 
  <featurelet>blog</featurelet> 
  <featurelet>wikis</featurelet> 
  <featurelet>tasks</featurelet> 
  <featurelet>listen</featurelet> 
 </featurelets> 
</info>""", content_type="application/xml")(environ, start_response)
            if path == "members.xml":
                return Response("""
<members> 
 <member> 
  <id>ejucovy</id> 
  <role>ProjectAdmin</role> 
 </member> 
</members>""", content_type="application/xml")(environ, start_response)

        return Response(req.path_info_peek(), content_type='text/plain')(environ, start_response)

    def theme(self, environ, start_response):
        req = Request(environ)
        try:
            username = authenticate_from_cookie(req.cookies['__ac'], get_secret(self.secret))[0]
        except:
            username = None
        res = Template("""
<html>
<body>
<div style="background-color: gray">Welcome {{username}}!</div>
<div id="oc-content-container">
</div>
</body>
</html>""")
        res = res.substitute(username=username or "AnonymousUser")
        return Response(res)(environ, start_response)

    def login(self, environ, start_response):
        req = Request(environ)
        if req.method == "GET":
            return Response("""
<form method="POST">
Username: <input type="text" name="username" />
<input type="submit" />
</form>""")(environ, start_response)
        username = req.POST['username']
        val = generate_cookie_value(username, get_secret(self.secret))
        res = Response()
        res.status = 304
        res.location = "/"
        res.set_cookie("__ac", val)
        return res(environ, start_response)
