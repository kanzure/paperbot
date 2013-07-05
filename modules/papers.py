"""
Fetches papers.
"""
import re
import os
import json
import random
import requests
import lxml.etree
from StringIO import StringIO

import pdfparanoia

from HTMLParser import HTMLParser
from urlparse import urlparse
import itertools

def scihubber(url, **kwargs):
    """
    Takes user url and traverses sci-hub proxy system until pdf is found.
    When successful, returns either sci-hub pdfcache or libgen pdf url
    """
    a = urlparse(url)
    geturl = "http://%s.sci-hub.org/%s?%s" % (a.hostname, a.path, a.query)
    def _go(_url):
        _as = []
        _frames = []
        just = []
        class MaybeTail(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "frame":
                    d = dict(attrs)
                    if d.get("name","").encode("utf8") == "_pdf": just.append(d.get("src", None))
        class Derper(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "a": _as.append(dict(attrs))
                elif tag == "frame": _frames.append(dict(attrs))
        re = requests.get(_url, **kwargs).text.encode("utf8")
        MaybeTail().feed(re)
        if just: return just[0]
        Derper().feed(re)
        qq = filter(lambda x: str.find(x.get("href","").encode("utf8"), "pdf") != -1, _as)
        qq += filter(lambda x: str.find(x.get("src","").encode("utf8"), "pdf") != -1, _frames)
        qq = filter(lambda x: x, map(lambda x: x.get("href", x.get("src", None)), qq))
        it = itertools.ifilter(lambda x:x,
            itertools.imap(lambda x: _go("http://%s.sci-hub.org/%s" % (a.hostname, x)), qq))
        try: return it.next()
        except StopIteration: return None
    return _go(geturl)

def download(phenny, input, verbose=True):
    """
    Downloads a paper.
    """
    # only accept requests in a channel
    if not input.sender.startswith('#'):
        # unless the user is an admin, of course
        if not input.admin:
            phenny.say("i only take requests in the ##hplusroadmap channel.")
            return
        else:
            # just give a warning message to the admin.. not a big deal.
            phenny.say("okay i'll try, but please send me requests in ##hplusroadmap in the future.")

    # get the input
    line = input.group()

    # was this an explicit command?
    explicit = False
    if line.startswith(phenny.nick):
        explicit = True
        line = line[len(phenny.nick):]

        if line.startswith(",") or line.startswith(":"):
            line = line[1:]

    if line.startswith(" "):
        line = line.strip()

    # don't bother if there's nothing there
    if len(line) < 5 or (not "http://" in line and not "https://" in line) or not line.startswith("http"):
        return
    for line in re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line):
        line = filter_fix(line)

        # fix for login.jsp links to ieee xplore
        line = fix_ieee_login_urls(line)
        line = fix_jstor_pdf_urls(line)

        translation_url = "http://localhost:1969/web"

        headers = {
            "Content-Type": "application/json",
        }

        data = {
            "url": line,
            "sessionid": "what"
        }

        data = json.dumps(data)

        response = requests.post(translation_url, data=data, headers=headers)

        if response.status_code == 200 and response.content != "[]":
            # see if there are any attachments
            content = json.loads(response.content)
            item = content[0]
            title = item["title"]

            if item.has_key("attachments"):
                pdf_url = None
                for attachment in item["attachments"]:
                    if attachment.has_key("mimeType") and "application/pdf" in attachment["mimeType"]:
                        pdf_url = attachment["url"]
                        break

                if pdf_url:
                    user_agent = "Mozilla/5.0 (X11; Linux i686 (x86_64)) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11"

                    headers = {
                        "User-Agent": user_agent,
                    }

                    response = None
                    if pdf_url.startswith("https://"):
                        response = requests.get(pdf_url, headers=headers, verify=False)
                    else:
                        response = requests.get(pdf_url, headers=headers)

                    # detect failure
                    if response.status_code == 401:
                        phenny.say("HTTP 401 unauthorized " + str(pdf_url))
                        continue
                    elif response.status_code != 200:
                        phenny.say("HTTP " + str(response.status_code) + " " + str(pdf_url))
                        continue

                    data = response.content

                    if "pdf" in response.headers["content-type"]:
                        try:
                            data = pdfparanoia.scrub(StringIO(data))
                        except:
                            # this is to avoid a PDFNotImplementedError
                            pass

                    # grr..
                    title = title.encode("ascii", "ignore")

                    path = os.path.join("/home/bryan/public_html/papers2/paperbot/", title + ".pdf")

                    file_handler = open(path, "w")
                    file_handler.write(data)
                    file_handler.close()

                    filename = requests.utils.quote(title)

                    # Remove an ending period, which sometimes happens when the
                    # title of the paper has a period at the end.
                    if filename[-1] == ".":
                        filename = filename[:-1]

                    url = "http://diyhpl.us/~bryan/papers2/paperbot/" + filename + ".pdf"

                    phenny.say(url)
                    continue
                elif verbose and explicit:
                    phenny.say(download_url(line))
                    continue
            elif verbose and explicit:
                phenny.say(download_url(line))
                continue
        elif verbose and explicit:
            if response.status_code == 501:
                if verbose:
                    phenny.say("no translator available, raw dump: " + download_url(line))
                    continue
            else:
                if verbose:
                    phenny.say("error: HTTP " + str(response.status_code) + " " + download_url(line))
                    continue
        else:
            continue
    return
download.commands = ["fetch", "get", "download"]
download.priority = "high"
download.rule = r'(.*)'

def download_ieee(url):
    """
    Downloads an IEEE paper. The Zotero translator requires frames/windows to
    be available. Eventually translation-server will be fixed, but until then
    it might be nice to have an IEEE workaround.
    """
    # url = "http://ieeexplore.ieee.org:80/xpl/freeabs_all.jsp?reload=true&arnumber=901261"
    # url = "http://ieeexplore.ieee.org/iel5/27/19498/00901261.pdf?arnumber=901261"
    raise NotImplementedError

def download_url(url):
    response = requests.get(url, headers={"User-Agent": "origami-pdf"})
    content = response.content

    # just make up a default filename
    title = "%0.2x" % random.getrandbits(128)

    # default extension
    extension = ".txt"

    if "pdf" in response.headers["content-type"]:
        extension = ".pdf"
    elif check_if_html(response):
        # parse the html string with lxml.etree
        tree = parse_html(content)

        # extract some metadata with xpaths
        citation_pdf_url = find_citation_pdf_url(tree, url)
        citation_title = find_citation_title(tree)

        # aip.org sucks, citation_pdf_url is wrong
        if citation_pdf_url and "link.aip.org/" in citation_pdf_url:
            citation_pdf_url = None

        if citation_pdf_url and "ieeexplore.ieee.org" in citation_pdf_url:
            content = requests.get(citation_pdf_url).content
            tree = parse_html(content)
            # citation_title = ...

        # wow, this seriously needs to be cleaned up
        if citation_pdf_url and citation_title and not "ieeexplore.ieee.org" in citation_pdf_url:
            citation_title = citation_title.encode("ascii", "ignore")
            response = requests.get(citation_pdf_url, headers={"User-Agent": "pdf-defense-force"})
            content = response.content
            if "pdf" in response.headers["content-type"]:
                extension = ".pdf"
                title = citation_title
        else:
            if "sciencedirect.com" in url and not "ShoppingCart" in url:
                try:
                    title = tree.xpath("//h1[@class='svTitle']")[0].text
                    pdf_url = tree.xpath("//a[@id='pdfLink']/@href")[0]
                    new_response = requests.get(pdf_url, headers={"User-Agent": "sdf-macross"})
                    new_content = new_response.content
                    if "pdf" in new_response.headers["content-type"]:
                        extension = ".pdf"
                except Exception:
                    pass
                else:
                    content = new_content
                    response = new_response
            elif "jstor.org/" in url:
                # clean up the url
                if "?" in url:
                    url = url[0:url.find("?")]

                # not all pages have the <input type="hidden" name="ppv-title"> element
                try:
                    title = tree.xpath("//div[@class='hd title']")[0].text
                except Exception:
                    try:
                        title = tree.xpath("//input[@name='ppv-title']/@value")[0]
                    except Exception:
                        pass

                # get the document id
                document_id = None
                if url[-1] != "/":
                    #if "stable/" in url:
                    #elif "discover/" in url:
                    #elif "action/showShelf?candidate=" in url:
                    #elif "pss/" in url:
                    document_id = url.split("/")[-1]

                if document_id.isdigit():
                    try:
                        pdf_url = "http://www.jstor.org/stable/pdfplus/" + document_id + ".pdf?acceptTC=true"
                        new_response = requests.get(pdf_url, headers={"User-Agent": "time-machine/1.1"})
                        new_content = new_response.content
                        if "pdf" in new_response.headers["content-type"]:
                            extension = ".pdf"
                    except Exception:
                        pass
                    else:
                        content = new_content
                        response = new_response
            elif ".aip.org/" in url:
                try:
                    title = tree.xpath("//title/text()")[0].split(" | ")[0]
                    pdf_url = [link for link in tree.xpath("//a/@href") if "getpdf" in link][0]
                    new_response = requests.get(pdf_url, headers={"User-Agent": "time-machine/1.0"})
                    new_content = new_response.content
                    if "pdf" in new_response.headers["content-type"]:
                        extension = ".pdf"
                except Exception:
                    pass
                else:
                    content = new_content
                    response = new_response
            elif "ieeexplore.ieee.org" in url:
                try:
                    pdf_url = [url for url in tree.xpath("//frame/@src") if "pdf" in url][0]
                    new_response = requests.get(pdf_url, headers={"User-Agent": "time-machine/2.0"})
                    new_content = new_response.content
                    if "pdf" in new_response.headers["content-type"]:
                        extension = ".pdf"
                except Exception:
                    pass
                else:
                    content = new_content
                    response = new_response
            elif "h1 class=\"articleTitle" in content:
                try:
                    title = tree.xpath("//h1[@class='articleTitle']")[0].text
                    title = title.encode("ascii", "ignore")
                    pdf_url = tree.xpath("//a[@title='View the Full Text PDF']/@href")[0]
                except:
                    pass
                else:
                    if pdf_url.startswith("/"):
                        url_start = url[:url.find("/",8)]
                        pdf_url = url_start + pdf_url
                    response = requests.get(pdf_url, headers={"User-Agent": "pdf-teapot"})
                    content = response.content
                    if "pdf" in response.headers["content-type"]:
                        extension = ".pdf"
            # raise Exception("problem with citation_pdf_url or citation_title")
            # well, at least save the contents from the original url
            pass

    # make the title again just in case
    if not title:
        title = "%0.2x" % random.getrandbits(128)

    # can't create directories
    title = title.replace("/", "_")

    path = os.path.join("/home/bryan/public_html/papers2/paperbot/", title + extension)

    if extension in [".pdf", "pdf"]:
        try:
            content = pdfparanoia.scrub(StringIO(content))
        except:
            # this is to avoid a PDFNotImplementedError
            pass

    file_handler = open(path, "w")
    file_handler.write(content)
    file_handler.close()

    title = title.encode("ascii", "ignore")
    url = "http://diyhpl.us/~bryan/papers2/paperbot/" + requests.utils.quote(title) + extension

    return url

def parse_html(content):
    if not isinstance(content, StringIO):
        content = StringIO(content)
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.parse(content, parser)
    return tree

def check_if_html(response):
    return "text/html" in response.headers["content-type"]

def find_citation_pdf_url(tree, url):
    """
    Returns the <meta name="citation_pdf_url"> content attribute.
    """
    citation_pdf_url = extract_meta_content(tree, "citation_pdf_url")
    if citation_pdf_url and  not citation_pdf_url.startswith("http"):
        if citation_pdf_url.startswith("/"):
            url_start = url[:url.find("/",8)]
            citation_pdf_url = url_start + citation_pdf_url
        else:
            raise Exception("unhandled situation (citation_pdf_url)")
    return citation_pdf_url

def find_citation_title(tree):
    """
    Returns the <meta name="citation_title"> content attribute.
    """
    citation_title = extract_meta_content(tree, "citation_title")
    return citation_title

def extract_meta_content(tree, meta_name):
    try:
        content = tree.xpath("//meta[@name='" + meta_name + "']/@content")[0]
    except:
        return None
    else:
        return content

def filter_fix(url):
    """
    Fixes some common problems in urls.
    """
    if ".proxy.lib.pdx.edu" in url:
        url = url.replace(".proxy.lib.pdx.edu", "")
    return url

def fix_ieee_login_urls(url):
    """
    Fixes urls point to login.jsp on IEEE Xplore. When someone browses to the
    abstracts page on IEEE Xplore, they are sometimes sent to the login.jsp
    page, and then this link is given to paperbot. The actual link is based on
    the arnumber.

    example:
    http://ieeexplore.ieee.org/xpl/login.jsp?tp=&arnumber=806324&url=http%3A%2F%2Fieeexplore.ieee.org%2Fxpls%2Fabs_all.jsp%3Farnumber%3D806324
    """
    if "ieeexplore.ieee.org/xpl/login.jsp" in url:
        if "arnumber=" in url:
            parts = url.split("arnumber=")

            # i guess the url might not look like the example in the docstring
            if "&" in parts[1]:
                arnumber = parts[1].split("&")[0]
            else:
                arnumber = parts[1]

            return "http://ieeexplore.ieee.org/xpl/articleDetails.jsp?arnumber=" + arnumber

    # default case when things go wrong
    return url

def fix_jstor_pdf_urls(url):
    """
    Fixes urls pointing to jstor pdfs.
    """
    if "jstor.org/" in url:
        if ".pdf" in url and not "?acceptTC=true" in url:
            url += "?acceptTC=true"
    return url

