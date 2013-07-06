"""
Integration with http://sci-hub.org/
"""

import requests
from HTMLParser import HTMLParser
from urlparse import urlparse
import itertools
import urllib
import base64
import os

scihub_cookie = os.environ.get("SCIHUB_PASSWORD", None)

if scihub_cookie == None:
    raise Exception("need SCIHUB_PASSWORD set")

def libgen(url, doi, **kwargs):
    auth_ = requests.auth.HTTPBasicAuth("genesis", "upload")
    re = requests.get(url, **kwargs)
    payload = "data:application/pdf;base64," + base64.b64encode(re.content)
    re = requests.get("http://libgen.org/scimag/librarian/form.php", auth = auth_,
       files = {"uploadedfile":("derp.pdf", payload)}, data = {"doi": doi})
    formp = []
    class FormP(HTMLParser):
        def handle_starttag(self, tag, attr):
            if tag == "input":
                d = dict(attr); form.append((d[name], d[value]))
    re = requests.get("http://libgen.org/scimag/librarian/register.php", data = dict(formp), auth = auth_)
    return "http://libgen.org/scimag5/" + doi

def scihubber(url, **kwargs):
    """
    Takes user url and traverses sci-hub proxy system until pdf is found.
    When successful, returns either sci-hub pdfcache or libgen pdf url
    """
    # include a cookie for sci-hub.org access
    if "cookies" not in kwargs.keys():
        kwargs["cookies"] = {scihub_cookie: ""}

    a = urlparse(url)
    geturl = "http://%s.sci-hub.org/%s?%s" % (a.hostname, a.path, a.query)
    def _go(_url, _doi = None):
        _as = []
        _frames = []
        just = []
        justdoi = []

        class MaybeDOI(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "meta":
                    d = dict(attrs)
                    if str.find(d.get("name","").encode("utf8"), "doi") != -1:
                        v = d.get("content","").encode("utf8")
                        ix = str.find(v, "10.")
                        if ix != -1: justdoi.append(v[ix:])
                if tag == "a":
                    d = dict(attrs)
                    v = d.get("href","").encode("utf8")
                    if str.find(v, "doi") != -1:
                        ix = str.find(v, "10.")
                        if ix != -1: justdoi.append(urllib.unquote(v[ix:]))

        class MaybeTail(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "frame":
                    d = dict(attrs)
                    if d.get("name","").encode("utf8") == "_pdf": just.append(d.get("src", None))

        class Derper(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "a": _as.append(dict(attrs))
                elif tag == "frame" or tag == "iframe": _frames.append(dict(attrs))

        re = requests.get(_url, **kwargs).text.encode("utf8")
        if not _doi:
            MaybeDOI().feed(re)
            if justdoi: _doi = justdoi[0]
        MaybeTail().feed(re)
        if just: return (just[0], _doi)
        Derper().feed(re)
        qq = filter(lambda x: str.find(x.get("href","").encode("utf8"), "pdf") != -1, _as)
        qq += filter(lambda x: str.find(x.get("src","").encode("utf8"), "pdf") != -1, _frames)
        qq = filter(None, map(lambda x: x.get("href", x.get("src", None)), qq))
        it = itertools.ifilter(None,
            itertools.imap(lambda x: _go("http://%s.sci-hub.org/%s" % (a.hostname, x), _doi), qq))
        try: return it.next()
        except StopIteration: return None
    ret = _go(geturl)
    if ret: return ret
    else: return (None, None)
