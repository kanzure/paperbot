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
import modules.scihub
import urllib
import traceback

import pdfparanoia

logchannel = os.environ.get("LOGGING", None)

PROXY = 'http://ec2-54-218-13-46.us-west-2.compute.amazonaws.com:8500/plsget'
USER_AGENT = 'Mozilla/5.0 (X11; Linux i686 (x86_64)) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11'

ARCHIVE_DIR = '/home/bryan/public_html/papers2/paperbot/'
ARCHIVE_BASE = 'http://diyhpl.us/~bryan/papers2/paperbot/'
IEEE_EXPLORE_BASE = 'http://ieeexplore.ieee.org/xpl/articleDetails.jsp?arnumber='

HEADERS_TM_1 = {"User-Agent": "time-machine/1.0"}
HEADERS_TM_11 = {"User-Agent": "time-machine/1.1"}
HEADERS_TM_2 = {"User-Agent": "time-machine/2.0"}
HEADERS_TEAPOT = {"User-Agent": "pdf-teapot"}
HEADERS_DEFENSE = {"User-Agent": "pdf-defense-force"}

LIBGEN_FORM = "http://libgen.info/scimag/librarian/form.php"

URL_REGEX = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

proxy_list = [
    {
        'proxy_url': None,
        'proxy_type': 'normal'},
#    {
#        'proxy_url': PROXY,
#        'proxy_type': 'custom_flask_json'
#    }
]


def nullLog(msg):
    pass


def make_jstor_url(document_id):
    """Return the url to a document from its ID."""
    PREFIX = 'http://www.jstor.org/stable/pdfplus/'
    SUFFIX = '.pdf?acceptTC=true'
    return PREFIX + document_id + SUFFIX


class paperbot_download_request(object):
    _log = nullLog

    def get(self, pdf_url, use_generator=False, **kwargs):
        proxies_left_to_try = len(proxy_list)
        extension = ".txt"
        request_iteration = 0
        proxy_url_index = 0
        user_agent = USER_AGENT
        headers = {
            "User-Agent": user_agent,
        }
        _log = self._log
        _log('paperbot_download_request pdf_url: %s' % pdf_url)
        while proxies_left_to_try:
            proxy_url = proxy_list[proxy_url_index]['proxy_url']
            proxy_type = proxy_list[proxy_url_index]['proxy_type']
            _log('proxies_left_to_try: %d proxy_url_index %d'
                 % (proxies_left_to_try, proxy_url_index))
            _log('request_iteration: %d' % request_iteration)
            # perform default behaviour if proxy is None
            if proxy_list[proxy_url_index]['proxy_url'] is None:
                if pdf_url.startswith("https://"):
                    response = requests.get(pdf_url,  verify=False, **kwargs)
                else:
                    response = requests.get(pdf_url, **kwargs)
            else:
                # check type of proxy
                if proxy_type == 'custom_flask_json':
                    data = {
                        'pdf_url': pdf_url,
                        'headers': kwargs.get('headers', None),
                        'request_iteration': request_iteration
                    }

                    headers["Content-Type"] = "application/json"

                    _log('trying custom_flask_json, proxy_url %s' % proxy_url)
                    response = requests.get(proxy_url, data=json.dumps(data),
                                            headers=headers)
                elif proxy_type == 'normal':
                    # i'm not even checking if http or https is in the pdf_url,
                    # since the default proxy of None is already being tried in
                    # this loop
                    proxies = {
                        "http": proxy_url,
                        "https": proxy_url,
                    }
                    headers = kwargs.get('headers', None)
                    # I don't know if passing None or {} for headers is bad, so
                    # I put this if:
                    if headers is not None:
                        response = requests.get(pdf_url, headers=headers,
                                                proxies=proxies)
                    else:
                        response = requests.get(pdf_url, proxies=proxies)
            if use_generator:
                yield response
            else:
                _log('checking \'PDF\' in response.headers')
                if "pdf" in response.headers["content-type"]:
                    extension = ".pdf"
                    _log('yielding tuply with PDF in response')
                    # yield (response, extension)
                    proxies_left_to_try = 0
                    break
                    # return

            if 'proxies_remaining' in response.headers:
                remaining = response.headers['proxies_remaining']
                _log('proxies_remaining in headers: %s' % remaining)
                # decrement the index if the custom proxy doesn't have any more
                # internal proxies to try
                if response.headers['proxies_remaining'] == 0 or \
                   response.headers['proxies_remaining'] == '0':
                    proxies_left_to_try -= 1
                    request_iteration = 0
                    proxy_url_index += 1
                else:
                    _log('request_iteration+=1')
                    request_iteration += 1

            else:
                # decrement the index to move on to the next proxy in our
                # proxy_list
                proxies_left_to_try -= 1
                request_iteration = 0
                proxy_url_index += 1
        if use_generator:
            return
        _log('last yield in paperbot_download_request')
        yield (response, extension)


def download(phenny, input, verbose=True):
    """
    Downloads a paper.
    """
    if logchannel:
        _log = lambda x: phenny.msg("#%s" % logchannel, x)
    else:
        _log = lambda x: None
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
    if len(line) < 5 or ("http://" not in line and "https://" not in line) or \
       not line.startswith("http"):
        return
    for line in re.findall(URL_REGEX, line):
        # fix an UnboundLocalError problem
        shurl = None

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

            if "DOI" in item:
                _log("Translator DOI")
                lgre = requests.post(LIBGEN_FORM,
                                     data={"doi": item["DOI"]})
                tree = parse_html(lgre.content)
                if tree.xpath("//h1")[0].text != "No file selected":
                    phenny.say("http://libgen.info/scimag/get.php?doi=%s"
                               % urllib.quote_plus(item["DOI"]))
                    return

            if "attachments" in item:
                pdf_url = None
                for attachment in item["attachments"]:
                    if "mimeType" in attachment and \
                       "application/pdf" in attachment["mimeType"]:
                        pdf_url = attachment["url"]
                        break

                if pdf_url:
                    user_agent = USER_AGENT
                    paperbot_download_request_obj = paperbot_download_request()
                    paperbot_download_request_obj._log = _log
                    gen = paperbot_download_request_obj.get(pdf_url,
                                                            use_generator=False,
                                                            headers=headers)
                    # this is stupidly ugly
                    for genresponse in gen:
                        response, extension = genresponse

                    # detect failure
                    if response.status_code != 200:
                        shurl, _ = modules.scihub.scihubber(pdf_url)
                        if shurl:
                            if "libgen" in shurl:
                                phenny.say("http://libgen.info/scimag/get.php?doi=%s" % urllib.quote_plus(item["DOI"]))
                            elif "pdfcache" not in shurl:
                                phenny.say(shurl)
                            else:
                                pdfstr = modules.scihub.scihub_dl(shurl)
                                phenny.say(modules.scihub.libgen(pdfstr, item["DOI"]))
                        return

                    data = response.content

                    if "pdf" in response.headers["content-type"]:
                        try:
                            data = pdfparanoia.scrub(StringIO(data))
                            try:
                                _log('after pdfparanoia.scrub')
                                requests.get('http://localhost:8500/remoteprint',
                                             headers={'msg': 'after pdfparanoia.scrub'})
                            except:
                                pass
                            break
                        except:
                            # this is to avoid a PDFNotImplementedError
                            pass

                    if "DOI" in item:
                        phenny.say(modules.scihub.libgen(data, item["DOI"]))
                        return

                    # grr..
                    title = title.encode("ascii", "ignore")

                    path = os.path.join(ARCHIVE_DIR, title + ".pdf")

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
                    _log("Translation server PDF fail")
                    shurl, doi = modules.scihub.scihubber(line)
                    continue
            elif verbose and explicit:
                _log("Translation server PDF fail")
                shurl, doi = modules.scihub.scihubber(line)
                phenny.say(download_url(line, _log))
                continue
        elif verbose and explicit:
            _log("Translation server fail")
            shurl, doi = modules.scihub.scihubber(line)
            _log("Scihubber -> (%s, %s)" % (shurl, doi))
        if shurl:
            if "pdfcache" in shurl:
                if doi:
                    pdfstr = modules.scihub.scihub_dl(shurl)
                    phenny.say(modules.scihub.libgen(pdfstr, doi))
                else:
                    phenny.say(download_url(shurl, _log,
                                            cookies=modules.scihub.shcookie))
            else:
                phenny.say(shurl)
        elif verbose and explicit:
            _log("All approaches failed")
            phenny.say(download_url(line, _log))
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


def download_url(url, _log=nullLog, **kwargs):
    paperbot_download_request_obj = paperbot_download_request()
    paperbot_download_request_obj._log = _log
    response_generator = paperbot_download_request_obj.get(url,
                                                           use_generator=True,
                                                           headers={"User-Agent": "origami-pdf"})
    cc = 0
    for response in response_generator:
        _log('using generator for %s time' % cc)
        cc += 1
        paperbot_download_request_obj2 = paperbot_download_request()
        paperbot_download_request_obj2._log = _log
        content = response.content
        # response = requests.get(url, headers={"User-Agent": "origami-pdf"}, **kwargs)
        # content = response.content

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
            if citation_pdf_url and citation_title and \
               "ieeexplore.ieee.org" not in citation_pdf_url:
                citation_title = citation_title.encode("ascii", "ignore")
                response = requests.get(citation_pdf_url,
                                        headers=HEADERS_DEFENSE)
                content = response.content
                if "pdf" in response.headers["content-type"]:
                    extension = ".pdf"
                    title = citation_title
            else:
                if "sciencedirect.com" in url and "ShoppingCart" not in url:
                    _log('download_url got a sciencedirect URL')
                    try:
                        try:
                            title_xpath = "//h1[@class='svTitle']"
                            title = tree.xpath(title_xpath)[0].text
                            pdf_url = tree.xpath("//a[@id='pdfLink']/@href")[0]
                        except IndexError:
                            title = tree.xpath("//title")[0].text
                            pdf_url = tree.xpath("//a[@id='pdfLink']/@href")[0]

                        if 'http' not in pdf_url:
                            main_url_split = response.url.split('//')
                            http_prefix = main_url_split[0]
                            if 'http' in http_prefix:
                                domain_url = main_url_split[1].split('/')[0]
                                slash = '/' if pdf_url[0] != '/' else ''
                                pdf_url = http_prefix + '//' + domain_url + slash + pdf_url
                        gen = paperbot_download_request_obj2.get(pdf_url,
                                                                 use_generator=False,
                                                                 headers={"User-Agent": "sdf-macross"})
                        # this is stupidly ugly
                        for genresponse in gen:
                            new_response, extension = genresponse
                        new_content = new_response.content
                        _log('paperbot_download_request_obj2 content-type: %s'
                             % new_response.headers["content-type"])
                        if "pdf" in new_response.headers["content-type"]:
                            extension = ".pdf"
                            break
                    except Exception as e:
                        _log(traceback.format_exc())
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
                            input_xpath = "//input[@name='ppv-title']/@value"
                            title = tree.xpath(input_xpath)[0]
                        except Exception:
                            pass

                    # get the document id
                    document_id = None
                    if url[-1] != "/":
                        # if "stable/" in url:
                        # elif "discover/" in url:
                        # elif "action/showShelf?candidate=" in url:
                        # elif "pss/" in url:
                        document_id = url.split("/")[-1]

                    if document_id.isdigit():
                        try:
                            pdf_url = make_jstor_url(document_id)
                            new_response = requests.get(pdf_url,
                                                        headers=HEADERS_TM_11)
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
                        pdf_url = [link for link in tree.xpath("//a/@href")
                                   if "getpdf" in link][0]
                        new_response = requests.get(pdf_url,
                                                    headers=HEADERS_TM_1)
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
                        pdf_url = [url for url in tree.xpath("//frame/@src")
                                   if "pdf" in url][0]
                        new_response = requests.get(pdf_url,
                                                    headers=HEADERS_TM_2)
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
                        title_xpath = "//h1[@class='articleTitle']"
                        title = tree.xpath(title_xpath)[0].text
                        title = title.encode("ascii", "ignore")
                        url_xpath = "//a[@title='View the Full Text PDF']/@href"
                        pdf_url = tree.xpath(url_xpath)[0]
                    except:
                        pass
                    else:
                        if pdf_url.startswith("/"):
                            url_start = url[:url.find("/", 8)]
                            pdf_url = url_start + pdf_url
                        response = requests.get(pdf_url,
                                                headers=HEADERS_TEAPOT)
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

    path = os.path.join(ARCHIVE_DIR, title + extension)

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
    url = ARCHIVE_BASE + requests.utils.quote(title) + extension

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
    if citation_pdf_url and not citation_pdf_url.startswith("http"):
        if citation_pdf_url.startswith("/"):
            url_start = url[:url.find("/", 8)]
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

            return IEEE_EXPLORE_BASE + arnumber

    # default case when things go wrong
    return url


def fix_jstor_pdf_urls(url):
    """
    Fixes urls pointing to jstor pdfs.
    """
    if "jstor.org/" in url:
        if ".pdf" in url and "?acceptTC=true" not in url:
            url += "?acceptTC=true"
    return url
