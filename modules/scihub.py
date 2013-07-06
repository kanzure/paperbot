"""
Integration with http://sci-hub.org/
"""

import requests
from HTMLParser import HTMLParser
from urlparse import urlparse
import itertools
from lxml import etree
from StringIO import StringIO
import urllib
import base64
import os

scihub_cookie = os.environ.get("SCIHUB_PASSWORD", None)

if scihub_cookie == None:
    raise Exception("need SCIHUB_PASSWORD set")

def libgen(url, doi, **kwargs):
    if "cookies" not in kwargs.keys():
        kwargs["cookies"] = {scihub_cookie: ""}
    auth_ = requests.auth.HTTPBasicAuth("genesis", "upload")
    re = requests.get(url, **kwargs)
    payload = "data:application/pdf;base64," + base64.b64encode(re.content)
    re = requests.post("http://libgen.org/scimag/librarian/form.php", auth = auth_,
       files = {"uploadedfile":("derp.pdf", re.content)}, data = {"doi": doi})
    shu = etree.parse(StringIO(re.text), etree.HTMLParser())
    formp = dict(map(lambda x: (x.get("name"), x.get("value")), tr.xpath("//input[@name]")))
    re = requests.get("http://libgen.org/scimag/librarian/register.php", data = formp, auth = auth_)
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
        shu = etree.parse(StringIO(re.text),etree.HTMLParser())
        if not _doi:
            metas = map(lambda x:x.get("content"), shu.xpath("//meta[contains(@name,'doi')]"))
            _as = map(lambda x:urllib.unquote(x.get("href")), shu.xpath("//a[contains(@href,'doi')]"))
            maybedoi = filter(lambda x:str.find(x, "10.") != -1, metas + _as)
            if maybedoi:
                ix = str.find(maybedoi[0],"10.")
                _doi = maybedoi[0][ix:]
        just = map(lambda x:x.get("src"), shu.xpath("//frame[@name='_pdf']"))
        if just: return (just[0], _doi)
        derp = map(lambda x:x.get("src"), shu.xpath("//frame | //iframe"))
        derp += map(lambda x:x.get("href"), shu.xpath("//a"))
        derp = filter(None,derp)
        it = itertools.ifilter(None,
            itertools.imap(lambda x: _go("http://%s.sci-hub.org/%s" % (a.hostname, x), _doi), derp))
        try: return it.next()
        except StopIteration: return None
    ret = _go(geturl)
    if ret: return ret
    else: return (None, None)
